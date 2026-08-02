"""
test_resumen_ejecutivo_formato_moneda.py
============================================

Regresion para bug medio #20 (QA ronda 2): _build_executive_summary (el
"resumen ejecutivo" del export a IA) formateaba los montos monetarios con
un f-string crudo "${:,.0f}" (formato en inglés, "$1,234,567", coma como
separador de miles), en vez de usar currency_format() (formato
"$1.234.567", punto como separador de miles, consistente con el resto de
la app y el PDF). Es el mismo antipatrón ya corregido en la descripción
de vínculos del PDF (fix bug #38), reaparecido acá sin corregir.

Este test llama a _build_executive_summary con una simulación conocida
(pérdida media = $1,234,567 exactos) y verifica que tanto el "headline"
como los "key_findings" usan el formato "$1.234.567" (punto como
separador de miles), no "$1,234,567".
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
print("BUG MEDIO #20: formato de moneda en el resumen ejecutivo del export IA")
print("=" * 70)

# Pérdida constante de $1.234.567 para todas las simulaciones: media,
# VaR99 y Expected Shortfall dan todos exactamente ese valor, fácil de
# verificar el formato exacto.
N = 1000
perdidas_totales = np.full(N, 1_234_567.0)
frecuencias_totales = np.ones(N, dtype=int)
eventos = [{'id': 'a', 'nombre': 'EventoA'}]
perdidas_por_evento = [perdidas_totales.copy()]

win = RLB.RiskLabApp()
results_block = {'risk_classification': {'zona_actual_segun_media': 'BAJO', 'zona_actual_segun_p99': 'BAJO'}}

resumen = win._build_executive_summary(perdidas_totales, frecuencias_totales,
                                       perdidas_por_evento, eventos, results_block)

headline = resumen.get('headline', '')
findings = resumen.get('key_findings', [])
texto_completo = headline + " " + " ".join(findings)

print(f"  headline: {headline!r}")
for f in findings:
    print(f"  finding: {f!r}")

check('$1.234.567' in texto_completo,
      f"Bug medio #20: el resumen usa el formato '$1.234.567' (punto como separador de "
      f"miles, consistente con currency_format) (obtenido: {texto_completo!r})")
check('$1,234,567' not in texto_completo,
      f"El resumen NO usa el formato crudo '$1,234,567' (coma como separador de miles) "
      f"(obtenido: {texto_completo!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
