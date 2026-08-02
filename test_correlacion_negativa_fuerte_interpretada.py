"""
test_correlacion_negativa_fuerte_interpretada.py
====================================================

Regresion para bug medio #23 (QA ronda 3): en el export IA,
_build_chart_summaries interpretaba la correlación entre frecuencia y
pérdida agregada (dispersion_freq_vs_perdida) solo reconociendo
corr > 0.5 como "fuerte" (positiva). Una correlación NEGATIVA fuerte
(p.ej. -0.9) se etiquetaba genéricamente como "moderada o débil",
cuando en realidad es una relación muy fuerte (solo que inversa) --
información relevante para un agente IA que analice el archivo.

El fix agrega una rama para corr < -0.5, describiendo explícitamente
la relación inversa fuerte.

Este test construye datos con una correlación negativa fuerte
(perdidas_totales = -frecuencias_totales + ruido pequeño) y verifica
que el texto de interpretación mencione la correlación negativa
fuerte, no el texto genérico de "moderada o débil".
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
print("BUG MEDIO #23: correlación negativa fuerte debe interpretarse explícitamente")
print("=" * 70)

rng = np.random.default_rng(51)
N = 500
frecuencias_totales = rng.integers(1, 20, N).astype(np.int32)
# Relación inversa fuerte: a más frecuencia, menor pérdida (mas eventos
# 'pequeños' compensan, escenario atípico pero perfectamente valido
# matematicamente para el chequeo).
perdidas_totales = (1000 - frecuencias_totales * 40 + rng.normal(0, 5, N)).clip(min=0)

corr_real = float(np.corrcoef(frecuencias_totales, perdidas_totales)[0, 1])
print(f"  correlación real construida: {corr_real:.3f}")
check(corr_real < -0.5, f"Precondición: la correlación construida es negativa fuerte (obtenido: {corr_real:.3f})")

win = RLB.RiskLabApp()
eventos = [{'id': 'a', 'nombre': 'EventoA'}]
perdidas_por_evento = [perdidas_totales.copy()]
resumen = win._build_chart_summaries(perdidas_totales, frecuencias_totales, perdidas_por_evento, eventos, {})

interpretacion = resumen['dispersion_freq_vs_perdida']['interpretacion']
print(f"  interpretación: {interpretacion!r}")

check('negativa fuerte' in interpretacion.lower() or 'inversa' in interpretacion.lower(),
      f"Bug medio #23: la interpretación menciona la correlación NEGATIVA fuerte "
      f"(obtenido: {interpretacion!r})")
check('moderada o débil' not in interpretacion,
      f"Bug medio #23: ya NO usa el texto genérico 'moderada o débil' para una "
      f"correlación negativa fuerte (obtenido: {interpretacion!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
