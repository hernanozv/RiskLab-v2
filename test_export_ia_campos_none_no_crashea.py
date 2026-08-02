"""
test_export_ia_campos_none_no_crashea.py
============================================

Regresion para bug alto #11 (QA ronda 3): _decodificar_evento_para_export
(usado por el export IA) leia varios campos numericos opcionales con
`evento.get(clave, default)`. Ese patron SOLO aplica el default si la
clave esta AUSENTE del dict; si el valor es un None EXPLICITO (posible
via un archivo JSON con 'null' literal en un campo numerico -- p.ej.
generado manualmente, por otra herramienta, o por el skill
risk-lab-modeler con un campo opcional sin completar), .get() devuelve
None igual, y un f-string con formato numerico (f"{v:,.0f}") revienta
con TypeError. Como _decodificar_evento_para_export se llama para
CADA evento sin ningun try/except individual, un solo campo None en
cualquier evento abortaba TODA la exportacion.

El fix agrega un helper _valor_o_default(valor, default) que trata
tanto la ausencia de la clave como un None explicito de la misma forma,
aplicado en los 3 puntos que antes revientaban: freq_opcion, los campos
del bloque 'seguro' (deducible/cobertura/limite_ocurrencia/limite_
agregado_anual), y 'umbral_severidad' de los vinculos.

Este test llama _decodificar_evento_para_export con freq_opcion=None,
un factor tipo seguro con varios campos en None, y un vinculo con
umbral_severidad=None, y verifica que NO lanza excepcion y que los
valores por defecto documentados se aplican.
"""
import os
import sys

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
print("BUG ALTO #11: campos None explícitos en export IA no deben crashear")
print("=" * 70)

evento = {
    'id': 'e1', 'nombre': 'EventoConNones', 'activo': True,
    'freq_opcion': None,  # explícito, no ausente
    'sev_opcion': 2,
    'factores_ajuste': [
        {
            'nombre': 'SeguroConNones', 'tipo_modelo': 'estatico', 'activo': True,
            'afecta_severidad': True, 'tipo_severidad': 'seguro',
            'seguro_tipo_deducible': 'agregado',
            'seguro_deducible': None,
            'seguro_cobertura_pct': None,
            'seguro_limite_ocurrencia': None,
            'seguro_limite': None,
        }
    ],
    'vinculos': [
        {'id_padre': 'otro', 'tipo': 'AND', 'probabilidad': None,
         'factor_severidad': None, 'umbral_severidad': None}
    ],
}

try:
    out = RLB.RiskLabApp._decodificar_evento_para_export(evento, mapa_nombres_por_id={})
    excepcion = None
except Exception as e:
    out = None
    excepcion = e

check(excepcion is None,
      f"Bug alto #11: _decodificar_evento_para_export NO lanza excepción con "
      f"campos None explícitos (obtenido: {excepcion!r})")

if out is not None:
    check(out['frecuencia']['freq_opcion'] == 3,
          f"freq_opcion=None cae al default documentado (3, Bernoulli) "
          f"(obtenido: {out['frecuencia']['freq_opcion']!r})")
    seguro = out['factores_ajuste'][0]['seguro']
    check(seguro['deducible'] == 0 and seguro['cobertura_pct'] == 0,
          f"Campos del seguro en None caen a sus defaults (0) "
          f"(obtenido: deducible={seguro['deducible']!r}, cobertura_pct={seguro['cobertura_pct']!r})")
    check('explicacion' in out['factores_ajuste'][0],
          "Se generó el texto de explicación del seguro sin crashear")
    vinculo = out['vinculos'][0]
    check(vinculo['umbral_severidad'] == 0,
          f"umbral_severidad=None cae al default (0) (obtenido: {vinculo['umbral_severidad']!r})")
    check('explicacion' in vinculo,
          "Se generó el texto de explicación del vínculo sin crashear")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
