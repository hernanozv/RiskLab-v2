"""
test_export_ia_resumen_no_incrusta_nan_como_texto.py
========================================================

Regresion para bug medio R4 #7 (QA ronda 4): _build_executive_summary()
(la sección "resumen ejecutivo pre-procesado para el agente" del export
IA) calcula media/var_99/es_99/curtosis/asimetría/top_pct/top3_pct a
partir de perdidas_totales/perdidas_por_evento. Si esos arrays traen un
NaN aislado (posible por cualquier bug menor en un factor estocástico,
ver R4 crítico #2), numpy propaga el NaN SILENCIOSAMENTE en mean/
percentile/kurtosis/skew -- sin lanzar ninguna excepción, así que el
try/except de este método nunca se entera. currency_format()/f-strings
formatean ese NaN como el texto literal "nan" (ej. "$nan"), incrustado
directamente en 'headline' y 'key_findings' -- un resumen narrativo que
se supone legible para un agente IA externo. A diferencia de los campos
NUMÉRICOS del payload (ya saneados recursivamente por
_sanear_nan_inf_recursivo, que reemplaza NaN/Infinity por None/tokens
seguros), este texto ya es un string en el momento en que ese saneo
recursivo se aplica, así que nunca llega a corregirse.

El fix sanea media/var_99/es_99/curt/asim/top_pct/top3_pct ANTES de
construir cualquier string narrativo: los valores monetarios usan un
formateador seguro que devuelve "N/D (dato inválido)" en vez de invocar
currency_format() sobre un NaN, y los demás se reemplazan por 0.0.

Este test invoca win._build_executive_summary(...) directamente con un
perdidas_totales que tiene un NaN aislado, y verifica que:
1. Ningún string de 'headline' ni de 'key_findings' contenga la
   subcadena "nan" (verificación case-insensitive, ya que "nan" no
   aparece en ninguna palabra española normal de este contexto).
2. 'headline' sí contenga el marcador "N/D" indicando el dato inválido.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np
from PyQt5 import QtWidgets

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


app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

print("=" * 70)
print("BUG MEDIO R4 #7: resumen ejecutivo del export IA no debe incrustar 'nan' como texto")
print("=" * 70)

N = 2000
rng = np.random.default_rng(42)
perdidas_totales = rng.lognormal(10, 1, N)
perdidas_totales[777] = np.nan  # un solo valor corrupto, aislado
frecuencias_totales = rng.poisson(3, N)

eventos = [{'id': 'a', 'nombre': 'EventoA'}, {'id': 'b', 'nombre': 'EventoB'}]
perdidas_por_evento = [perdidas_totales.copy(), perdidas_totales.copy() * 0.5]

win = RLB.RiskLabApp()
resultado = win._build_executive_summary(
    perdidas_totales, frecuencias_totales, perdidas_por_evento, eventos,
    {'risk_classification': {'zona_actual_segun_media': 'Media', 'zona_actual_segun_p99': 'Alta'}}
)

headline = resultado.get('headline', '')
findings = resultado.get('key_findings', [])
texto_completo = headline + " " + " ".join(findings)

print(f"  headline: {headline!r}")
for f in findings:
    print(f"  finding: {f!r}")

check('nan' not in texto_completo.lower(),
      f"Bug medio R4 #7: ningún texto de headline/key_findings contiene la "
      f"subcadena 'nan' (obtenido: {texto_completo!r})")
check('N/D' in headline,
      f"El headline indica explícitamente que el dato de pérdida media no está "
      f"disponible/es inválido (obtenido: {headline!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
