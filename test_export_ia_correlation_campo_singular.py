"""
test_export_ia_correlation_campo_singular.py
================================================

Regresion para bug bajo #35 (QA ronda 3): en la sección "results" del
export IA, el campo que reporta la correlación de Pearson entre
frecuencia total y pérdida total se llamaba "correlations" (PLURAL),
pero solo contiene UN único valor reportado
(frecuencia_total_vs_perdida_total) -- el nombre en plural sugería
erróneamente que había varios pares de correlación disponibles,
confundiendo a un agente IA que interprete el archivo.

El fix renombra el campo a "correlation" (singular), actualizado
también en EXPORT_SCHEMA.md. No hay otros sitios en el código que lean
la clave anterior ("correlations"), por lo que el rename es seguro.

Este test llama _build_results_section directamente y verifica que la
clave "correlation" (singular) esté presente en el resultado, y que la
clave antigua "correlations" (plural) ya NO lo esté.
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
print("BUG BAJO #35: campo 'correlations' (plural) debe ser 'correlation' (singular)")
print("=" * 70)

rng = np.random.default_rng(11)
N = 200
frecuencias_totales = rng.integers(1, 10, N).astype(np.int32)
perdidas_totales = (frecuencias_totales * 1000 + rng.normal(0, 50, N)).clip(min=0)
eventos = [{'id': 'a', 'nombre': 'EventoA'}]
perdidas_por_evento = [perdidas_totales.copy()]
frecuencias_por_evento = [np.ones(N, dtype=int)]

win = RLB.RiskLabApp()
opciones = {}
resultado = win._build_results_section(
    opciones, perdidas_totales, frecuencias_totales,
    perdidas_por_evento, frecuencias_por_evento, eventos, {}
)

print(f"  claves de nivel superior: {sorted(resultado.keys())}")

check('correlation' in resultado,
      "Bug bajo #35: el campo 'correlation' (singular) está presente")
check('correlations' not in resultado,
      "Bug bajo #35: el campo antiguo 'correlations' (plural) ya NO está presente")

if 'correlation' in resultado:
    check('frecuencia_total_vs_perdida_total' in resultado['correlation'],
          "El sub-campo 'frecuencia_total_vs_perdida_total' sigue presente dentro de 'correlation'")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
