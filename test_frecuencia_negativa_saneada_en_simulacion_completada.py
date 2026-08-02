"""
test_frecuencia_negativa_saneada_en_simulacion_completada.py
================================================================

Regresion para bug medio R4 #1 (QA ronda 4): frecuencias_totales /
frecuencias_por_evento son arrays np.int32 (cuentan ocurrencias, nunca
deberían ser negativas), pero si un NaN llega a generarse en algún punto
del pipeline antes del cast final a int32 (p.ej. algún factor de ajuste
con parámetros extremos en una combinación no cubierta por los
np.nan_to_num existentes), numpy convierte ese NaN SILENCIOSAMENTE al
asignarlo a un slot int32: no hay excepción ni warning, el valor queda
como un entero centinela (INT32_MIN = -2147483648):

    >>> a = np.zeros(3, dtype=np.int32); a[1] = np.nan  # RuntimeWarning, sin excepción
    >>> a
    array([0, -2147483648, 0], dtype=int32)

Ese centinela corrompe silenciosamente min()/max()/bincount() de los
gráficos de Frecuencia -- incluyendo callbacks de hover interactivo que
NO pasan por el try/except de generar_resultados/graficar_resultados
(fix crítico R4 #2) -- ocultando o distorsionando el gráfico sin ningún
aviso visible para el usuario.

El fix sanea frecuencias_totales/frecuencias_por_evento en
simulacion_completada (el único punto de entrada de los resultados a la
UI), clampeando a >= 0 con np.maximum -- una frecuencia nunca puede ser
negativa legítimamente, así que esto neutraliza el centinela sin afectar
ningún dato válido.

Este test llama win.simulacion_completada(...) directamente con un
frecuencias_totales que ya contiene el centinela INT32_MIN (simulando el
resultado de una conversión NaN->int32 previa) y verifica que, tras la
llamada, self.resultados_simulacion['frecuencias_totales'] (y el array
por-evento correspondiente) ya NO contengan ningún valor negativo.
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
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)

print("=" * 70)
print("BUG MEDIO R4 #1: centinela INT32_MIN en frecuencias_totales debe sanearse")
print("=" * 70)

N = 2000
INT32_MIN = np.iinfo(np.int32).min

rng = np.random.default_rng(11)
perdidas_totales = rng.lognormal(10, 1, N)
frecuencias_totales = rng.poisson(3, N).astype(np.int32)
frecuencias_totales[500] = INT32_MIN  # centinela aislado, como quedaría de un cast NaN->int32

eventos = [{'id': 'a', 'nombre': 'EventoA'}]
perdidas_por_evento = [perdidas_totales.copy()]
frecuencias_por_evento = [frecuencias_totales.copy()]

print(f"  frecuencias_totales antes de simulacion_completada: min={frecuencias_totales.min()}, "
      f"contiene centinela={INT32_MIN in frecuencias_totales}")

win = RLB.RiskLabApp()

excepcion_escapo = None
try:
    win.simulacion_completada(perdidas_totales, frecuencias_totales,
                              perdidas_por_evento, frecuencias_por_evento, eventos)
except Exception as e:
    excepcion_escapo = e

check(excepcion_escapo is None,
      f"simulacion_completada no deja escapar ninguna excepción (obtenido: {excepcion_escapo!r})")

freq_guardadas = win.resultados_simulacion['frecuencias_totales']
freq_evt_guardadas = win.resultados_simulacion['frecuencias_por_evento'][0]

print(f"  frecuencias_totales tras simulacion_completada: min={freq_guardadas.min()}")

check(freq_guardadas.min() >= 0,
      f"Bug medio R4 #1: frecuencias_totales guardado ya NO contiene el centinela "
      f"INT32_MIN negativo (obtenido: min={freq_guardadas.min()})")
check(freq_evt_guardadas.min() >= 0,
      f"Bug medio R4 #1: frecuencias_por_evento[0] guardado ya NO contiene el "
      f"centinela negativo (obtenido: min={freq_evt_guardadas.min()})")

# El resto de las frecuencias (no afectadas por el centinela) deben quedar intactas.
mascara_no_afectada = np.arange(N) != 500
check(np.array_equal(freq_guardadas[mascara_no_afectada], frecuencias_totales[mascara_no_afectada]),
      "Las frecuencias NO afectadas por el centinela quedan sin modificar")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
