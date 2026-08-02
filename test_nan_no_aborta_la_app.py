"""
test_nan_no_aborta_la_app.py
===============================

Regresion para bug critico R4 #2 (QA ronda 4): un solo valor NaN/Inf
aislado en perdidas_totales (o en el array de un solo evento dentro de
perdidas_por_evento) hacia que generar_resultados/graficar_resultados
lanzaran una excepcion (p.ej. pandas.errors.IntCastingNaNError al
redondear percentiles NaN a entero, o IndexError en el bloque Tail
Risk). Como simulacion_completada (el metodo que llama a ambas) es un
SLOT de Qt conectado de forma cross-thread a la señal
SimulacionThread.simulacion_completada, una excepcion que escapa de ahi
puede terminar en un SIGABRT que mata TODO el proceso (confirmado
experimentalmente durante la auditoria), no solo un traceback
recuperable -- perdiendo toda la sesion de trabajo sin ningun aviso.

El fix envuelve el pipeline de post-procesamiento (generar_resultados +
mostrar_resultados_en_interfaz + graficar_resultados) dentro de
simulacion_completada en un try/except, mostrando un QMessageBox.critical
legible y dejando la barra de progreso reseteada en vez de dejar que la
excepcion escape del slot.

Este test llama win.simulacion_completada(...) DIRECTAMENTE (mismo
llamador real que usa la señal de Qt) con un array de perdidas_totales
que contiene un solo NaN, y verifica que: (a) la llamada NO lanza
ninguna excepcion hacia afuera (antes del fix, esto SI propagaba), (b)
se muestra un QMessageBox.critical con un mensaje legible, y (c) la
barra de progreso queda reseteada a 0 (no trabada en un valor
intermedio).
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
QtWidgets.QMessageBox.warning = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)

criticals_capturados = []
QtWidgets.QMessageBox.critical = staticmethod(
    lambda *a, **kw: criticals_capturados.append(a) or QtWidgets.QMessageBox.Ok
)

print("=" * 70)
print("BUG CRÍTICO R4 #2: un NaN aislado no debe poder abortar toda la aplicación")
print("=" * 70)

N = 2000
perdidas_totales = np.random.default_rng(7).lognormal(10, 1, N)
perdidas_totales[500] = np.nan  # un solo valor corrupto, aislado
frecuencias_totales = np.random.default_rng(8).poisson(3, N)
eventos = [{'id': 'a', 'nombre': 'EventoA'}]
perdidas_por_evento = [perdidas_totales.copy()]
frecuencias_por_evento = [frecuencias_totales.copy()]

win = RLB.RiskLabApp()
win.progress_bar.setValue(42)

excepcion_escapo = None
try:
    win.simulacion_completada(perdidas_totales, frecuencias_totales,
                              perdidas_por_evento, frecuencias_por_evento, eventos)
except Exception as e:
    excepcion_escapo = e

check(excepcion_escapo is None,
      f"Bug crítico R4 #2: simulacion_completada NO deja escapar ninguna excepción "
      f"con un NaN aislado (obtenido: {excepcion_escapo!r})")
check(len(criticals_capturados) >= 1,
      f"Bug crítico R4 #2: se muestra un QMessageBox.critical legible en vez de crashear "
      f"(obtenido: {len(criticals_capturados)} diálogos)")
check(win.progress_bar.value() == 0,
      f"La barra de progreso queda reseteada a 0 (no trabada) tras el error "
      f"(obtenido: {win.progress_bar.value()})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
