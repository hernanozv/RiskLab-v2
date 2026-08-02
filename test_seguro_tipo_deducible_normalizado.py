"""
test_seguro_tipo_deducible_normalizado.py
=============================================

Regresion para bug alto #10 (QA ronda 3): el motor filtraba las polizas
comparando 'tipo_deducible' con "== 'por_ocurrencia'" (linea ~3626) o
"== 'agregado'" (linea ~3750) de forma EXACTA, sin normalizar
mayusculas/espacios. Un valor como "Agregado" o "POR_OCURRENCIA"
(posible via import de un JSON con una grafia distinta a la que emite
la UI, p.ej. generado por el skill risk-lab-modeler) no calzaba con
NINGUNO de los dos filtros, y la poliza se descartaba en silencio: no
reducia la perdida y no generaba ningun aviso al usuario.

El fix normaliza 'seguro_tipo_deducible' en dos lugares: (1) el punto
canonico normalizar_factor_global (usado por todos los dialogos de
guardado y el import de JSON), y (2) defensivamente en el propio motor,
al leer el campo desde el factor crudo.

Este test construye un evento con una poliza por_ocurrencia (deducible
$0, cobertura 100%) pero con 'seguro_tipo_deducible': "Por_Ocurrencia"
(grafia no exacta) y verifica que el motor SI la aplica (reduce la
perdida neta a ~0), tanto llamando al motor directamente como
verificando que normalizar_factor_global corrige el valor.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np

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
print("BUG ALTO #10: seguro_tipo_deducible con grafía no exacta no debe anular la póliza")
print("=" * 70)

# --- 1. normalizar_factor_global corrige la grafía ---
factor_raw = {
    'nombre': 'SeguroTypo', 'tipo_modelo': 'estatico', 'activo': True,
    'afecta_severidad': True, 'tipo_severidad': 'seguro',
    'seguro_deducible': 0, 'seguro_cobertura_pct': 100,
    'seguro_tipo_deducible': 'Por_Ocurrencia',  # grafía no exacta
}
normalizado = RLB.normalizar_factor_global(factor_raw)
check(normalizado['seguro_tipo_deducible'] == 'por_ocurrencia',
      f"normalizar_factor_global normaliza 'Por_Ocurrencia' a 'por_ocurrencia' "
      f"(obtenido: {normalizado['seguro_tipo_deducible']!r})")

# --- 2. El motor aplica la póliza aunque el factor NO haya pasado por
#        normalizar_factor_global (defensivo, directamente en el motor) ---
dist_frecuencia = RLB.generar_distribucion_frecuencia(3, probabilidad_exito=1.0)
dist_severidad = RLB.generar_distribucion_severidad(
    1, None, None, None, input_method='direct', params_direct={'mean': 50_000.0, 'std': 1.0}
)
seguro_typo = {
    'nombre': 'SeguroTypo', 'tipo_modelo': 'estatico', 'activo': True,
    'afecta_frecuencia': False, 'impacto_porcentual': 0,
    'afecta_severidad': True, 'tipo_severidad': 'seguro',
    'seguro_deducible': 0, 'seguro_cobertura_pct': 100.0,
    'seguro_limite': 0, 'seguro_tipo_deducible': 'Por_Ocurrencia',  # grafía no exacta
    'seguro_limite_ocurrencia': 0,
}
evento = {
    'id': 'e1', 'nombre': 'EventoSeguroTypo', 'activo': True,
    'freq_opcion': 3, 'prob_exito': 1.0,
    'dist_frecuencia': dist_frecuencia,
    'sev_opcion': 1, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 50_000.0, 'std': 1.0},
    'dist_severidad': dist_severidad,
    'factores_ajuste': [seguro_typo],
}
rng = np.random.default_rng(21)
_, _, perd_evt, _ = RLB.generar_lda_con_secuencialidad([evento], num_simulaciones=5000, rng=rng)
perdida_neta_media = float(perd_evt[0].mean())
print(f"  pérdida neta media (con póliza 100% cobertura, grafía 'Por_Ocurrencia'): {perdida_neta_media:.0f}")

check(perdida_neta_media < 100,
      f"Bug alto #10: la póliza SE APLICA (pérdida neta ≈0) aunque "
      f"'seguro_tipo_deducible' tenga una grafía no exacta "
      f"(obtenido: {perdida_neta_media:.2f}, antes del fix hubiera dado ≈50.000 "
      f"porque la póliza se descartaba en silencio)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
