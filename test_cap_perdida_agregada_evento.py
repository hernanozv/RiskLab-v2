"""
test_cap_perdida_agregada_evento.py
=======================================

Regresion para bug critico #1 (QA ronda 3): dentro de
generar_lda_con_secuencialidad, la perdida agregada POR EVENTO Y POR
SIMULACION se recortaba silenciosamente a un tope de seguridad de 1e12
(`np.clip(perdidas_para_este_evento, 0, 1e12, out=...)`), sin emitir
ningun warning ni dejar rastro en el dict del evento. A diferencia de
todos los demas topes del motor (cap de frecuencia, rejection sampling
de limites superiores de freq/sev), este clip era completamente
invisible: con severidad de cola muy pesada (GPD con xi alto) y
frecuencia moderada/alta, la perdida agregada real de una simulacion
puede superar $1e12 con facilidad, quedando truncada sin aviso y
subestimando el riesgo real por ordenes de magnitud.

El fix agrega: (1) un warnings.warn(RiskLabFallbackWarning) cuando el
clip realmente recorta algun valor, y (2) dos flags persistidos en el
dict del evento ('_cap_perdida_agregada_aplicado' y
'_cap_perdida_agregada_num_simulaciones') que ahora se usan tambien
para mostrar un QMessageBox.warning al usuario en
simulacion_completada (mismo patron ya usado para el cap de
frecuencia, fix alto #13 de la ronda 1).

Este test reproduce el escenario exacto: un evento con severidad GPD
de cola extremadamente pesada (xi=0.97) y frecuencia alta (Poisson
tasa=3000/anio), que garantiza que la suma agregada por simulacion
supere 1e12. Verifica que se emite RiskLabFallbackWarning y que el
dict del evento queda marcado con '_cap_perdida_agregada_aplicado',
ademas de confirmar que esos campos nuevos estan en la lista de
limpieza _CAMPOS_INTERNOS_SIMULACION (para no persistirse en el JSON
guardado, mismo patron que el fix medio #3 de la ronda 2).
"""
import ast
import os
import sys
import warnings
import numpy as np

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import Risk_Lab_Beta as RLB

PASS = 0
FAIL = 0


def check(condition, msg):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {msg}")
    else:
        FAIL += 1
        print(f"  ❌ FALLO: {msg}")


print("=" * 70)
print("BUG CRÍTICO #1 (R3): clip silencioso de pérdida agregada a 1e12")
print("=" * 70)

dist_frecuencia = RLB.generar_distribucion_frecuencia(1, tasa=3000.0)
dist_severidad = RLB.generar_distribucion_severidad(
    4, None, None, None, input_method='direct',
    params_direct={'c': 0.97, 'scale': 2e8, 'loc': 1e8}
)

evento = {
    'id': 'e1', 'nombre': 'EventoColaExtrema', 'activo': True,
    'freq_opcion': 1, 'tasa': 3000.0,
    'dist_frecuencia': dist_frecuencia,
    'sev_opcion': 4,
    'sev_input_method': 'direct',
    'sev_params_direct': {'c': 0.97, 'scale': 2e8, 'loc': 1e8},
    'dist_severidad': dist_severidad,
}

rng = np.random.default_rng(42)
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    perd_tot, freq_tot, perd_evt, freq_evt = RLB.generar_lda_con_secuencialidad(
        [evento], num_simulaciones=2000, rng=rng
    )

perdidas_evento = perd_evt[0]
num_en_cap = int(np.sum(perdidas_evento >= 1e12))
print(f"  Simulaciones con pérdida agregada == 1e12 (tope): {num_en_cap}/2000")
check(num_en_cap > 0,
      f"Precondición: el escenario efectivamente dispara el tope de 1e12 "
      f"(obtenido: {num_en_cap} simulaciones)")

warnings_fallback = [x for x in w if issubclass(x.category, RLB.RiskLabFallbackWarning)]
check(len(warnings_fallback) >= 1,
      f"Bug crítico #1: se emite un warning visible (RiskLabFallbackWarning) "
      f"cuando el tope de 1e12 recorta la pérdida agregada "
      f"(obtenido: {len(warnings_fallback)} warnings de ese tipo)")

check(evento.get('_cap_perdida_agregada_aplicado') is True,
      f"Bug crítico #1: el dict del evento queda marcado con "
      f"'_cap_perdida_agregada_aplicado'=True para que la UI pueda avisar "
      f"al usuario (obtenido: {evento.get('_cap_perdida_agregada_aplicado')!r})")

check(evento.get('_cap_perdida_agregada_num_simulaciones', 0) == num_en_cap,
      f"El flag '_cap_perdida_agregada_num_simulaciones' coincide con el número "
      f"real de simulaciones recortadas (obtenido: "
      f"{evento.get('_cap_perdida_agregada_num_simulaciones')!r}, esperado: {num_en_cap})")

# El campo interno nuevo debe estar en la lista de limpieza de campos
# internos para que no se persista al guardar la configuracion (mismo
# patron que _cap_frecuencia_* del fix medio #3 de la ronda 2).
with open(os.path.join(_THIS_DIR, 'Risk_Lab_Beta.py'), 'r', encoding='utf-8') as f:
    src = f.read()
tree = ast.parse(src)
campos_internos = None
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and \
            isinstance(node.targets[0], ast.Name) and \
            node.targets[0].id == '_CAMPOS_INTERNOS_SIMULACION':
        campos_internos = ast.literal_eval(node.value)
        break

check(campos_internos is not None, "Se encontró la lista _CAMPOS_INTERNOS_SIMULACION")
if campos_internos is not None:
    check('_cap_perdida_agregada_aplicado' in campos_internos,
          "'_cap_perdida_agregada_aplicado' está en _CAMPOS_INTERNOS_SIMULACION "
          "(no se persiste al guardar la configuración)")
    check('_cap_perdida_agregada_num_simulaciones' in campos_internos,
          "'_cap_perdida_agregada_num_simulaciones' está en _CAMPOS_INTERNOS_SIMULACION "
          "(no se persiste al guardar la configuración)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
