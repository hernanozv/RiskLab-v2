"""
test_calendar_periodo_retorno_tipo_consistente.py
=====================================================

Regresion para bug medio #30 (QA ronda 3): _build_calendar_periods (usado
por el export IA, bloque "calendar_periods_of_return") devolvía, para el
campo "periodo_retorno_años" de cada nivel, un `float` normalmente, pero
el STRING literal "infinito" cuando la probabilidad de excedencia anual
era 0 (ningún nivel superado en la simulación) -- un tipo mixto
(number | string) no documentado en EXPORT_SCHEMA.md, que podía romper
cualquier consumidor (IA u otra herramienta) que esperara siempre un
número para ese campo.

El fix hace que "periodo_retorno_años" sea siempre `number` o `null`
(nunca un string): cuando el período de retorno no está acotado por los
datos observados, el valor es `None` (-> `null` en JSON), y la
información legible para humanos sigue disponible en "etiqueta"
(">100 años"). EXPORT_SCHEMA.md fue actualizado para documentar esto
explícitamente.

Este test construye una distribución de pérdidas donde NINGUNA
simulación supera el umbral "CRITICO" (garantizando p_exc=0 para ese
nivel) y verifica que "periodo_retorno_años" sea None (no el string
"infinito") para ese nivel, y sea un float para los niveles sí
superados.
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
print("BUG MEDIO #30: periodo_retorno_años debe ser siempre number o null, nunca string")
print("=" * 70)

ua = RLB._UMBRALES_RIESGO_USD["alto"]
# Ninguna simulación supera 1.5x el umbral "alto" (ni el percentil 99.5,
# que determina el umbral "CRITICO" en _build_calendar_periods) -> p_exc=0
# para el nivel CRITICO garantizado.
N = 1000
perdidas_totales = np.full(N, ua * 0.1)
frecuencias_totales = np.ones(N, dtype=int)

win = RLB.RiskLabApp()
bloque = win._build_calendar_periods(perdidas_totales, frecuencias_totales)

check(bloque is not None, "El bloque calendar_periods se construyó")

niveles = bloque.get("niveles", []) if bloque else []
por_nombre = {n["nivel"]: n for n in niveles}
print(f"  niveles obtenidos: {[(n['nivel'], n['periodo_retorno_años']) for n in niveles]}")

check("CRITICO" in por_nombre, "El nivel CRITICO está presente")
if "CRITICO" in por_nombre:
    valor_critico = por_nombre["CRITICO"]["periodo_retorno_años"]
    check(valor_critico is None,
          f"Bug medio #30: cuando el período de retorno no está acotado, "
          f"'periodo_retorno_años' es None (JSON null), no el string "
          f"'infinito' (obtenido: {valor_critico!r}, tipo: {type(valor_critico).__name__})")
    check(">100 años" in por_nombre["CRITICO"]["etiqueta"],
          f"La etiqueta legible sigue indicando '>100 años' (obtenido: {por_nombre['CRITICO']['etiqueta']!r})")

check("BAJO" in por_nombre, "El nivel BAJO está presente")
if "BAJO" in por_nombre:
    valor_bajo = por_nombre["BAJO"]["periodo_retorno_años"]
    check(isinstance(valor_bajo, float),
          f"El nivel BAJO (superado por todas las simulaciones) tiene un "
          f"float normal (obtenido: {valor_bajo!r}, tipo: {type(valor_bajo).__name__})")

# Ningún nivel debe tener jamás el string "infinito" como valor de
# periodo_retorno_años -- el tipo debe ser siempre number o None.
check(all(not isinstance(n["periodo_retorno_años"], str) for n in niveles),
      f"Ningún nivel usa el string 'infinito' como periodo_retorno_años "
      f"(obtenido: {[(n['nivel'], type(n['periodo_retorno_años']).__name__) for n in niveles]})")

import json
try:
    json.dumps(bloque)
    check(True, "El bloque completo es serializable a JSON estándar sin errores")
except (TypeError, ValueError) as e:
    check(False, f"El bloque completo es serializable a JSON estándar sin errores (error: {e})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
