"""
test_excedencia_tolerancia_label_no_se_desplaza.py
======================================================

Regresion para bug alto #13 (QA ronda 3): actualizar_linea_tolerancia_
graficos calculaba la posición X de la etiqueta "Tolerancia" (en la
curva de Excedencia) con:

    x_range = max(1e-3, x_right - x_left)
    x_pos = x_left + 0.98 * x_range

La curva de Excedencia usa ax3.invert_xaxis() (dibujo inicial, línea
~15337), por lo que ax.get_xlim() devuelve x_left > x_right (rango
invertido) y (x_right - x_left) es NEGATIVO. El max(1e-3, ...) pisaba
ese negativo con el piso positivo de 0.001, colapsando x_range a un
valor casi nulo y pegando la etiqueta al valor de x_left (borde
visual, en vez de la posición legible "2% hacia adentro" que sí se
calcula correctamente en el dibujo inicial). Esta función se llama en
CADA cambio del spinbox/checkbox de tolerancia -- el uso normal más
básico del control.

El fix usa la MISMA fórmula que el dibujo inicial
(x_pos = x_left - 0.02*abs(x_right-x_left)), consistente entre el
dibujo inicial y cada actualización posterior.

Este test genera resultados reales (con invert_xaxis aplicado), lee la
posición X inicial de la etiqueta, cambia el valor de tolerancia
(disparando actualizar_linea_tolerancia_graficos vía
actualizar_probabilidad_excedencia) y verifica que la posición X de la
etiqueta se mantenga cerca de la posición inicial (2% hacia adentro
desde x_left), no pegada/colapsada al valor de x_left.
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
print("BUG ALTO #13: etiqueta 'Tolerancia' no debe desplazarse al borde en uso normal")
print("=" * 70)

rng = np.random.default_rng(5)
N = 2000
perdidas_totales = rng.lognormal(mean=8, sigma=1.5, size=N)
frecuencias_totales = np.ones(N, dtype=int)
eventos = [{'id': 'a', 'nombre': 'EventoA'}]
perdidas_por_evento = [perdidas_totales.copy()]
frecuencias_por_evento = [np.ones(N, dtype=int)]

win = RLB.RiskLabApp()
win.graficar_resultados(perdidas_totales, frecuencias_totales, perdidas_por_evento,
                        frecuencias_por_evento, eventos)

check(getattr(win, 'ax_exceed_tol_label', None) is not None,
      "Se creó la etiqueta de tolerancia en la curva de Excedencia")

x_left, x_right = win.ax_exceed_tol_line.axes.get_xlim()
print(f"  xlim tras invert_xaxis: ({x_left:.2f}, {x_right:.2f})")
check(x_left > x_right, "Precondición: el eje X está invertido (x_left > x_right)")

x_pos_inicial = win.ax_exceed_tol_label.get_position()[0]
print(f"  posición X inicial de la etiqueta: {x_pos_inicial:.2f}")

# Simular el uso normal más básico: cambiar el valor de tolerancia.
nuevo_valor = float(win.tolerancia_ex_spin.value()) * 1.1
win.tolerancia_ex_spin.setValue(nuevo_valor)
win.actualizar_linea_tolerancia_graficos()

x_pos_tras_update = win.ax_exceed_tol_label.get_position()[0]
print(f"  posición X tras actualizar (cambio de tolerancia): {x_pos_tras_update:.2f}")

ancho_eje = abs(x_right - x_left)
x_pos_esperado = x_left - 0.02 * ancho_eje
check(abs(x_pos_tras_update - x_pos_esperado) < 0.001 * ancho_eje,
      f"Bug alto #13: la posición X tras actualizar coincide con la fórmula "
      f"correcta (2% hacia adentro desde x_left, misma que el dibujo inicial) "
      f"(obtenido: x_pos={x_pos_tras_update:.2f}, esperado≈{x_pos_esperado:.2f})")
check(abs(x_pos_tras_update - x_left) > 0.005 * ancho_eje,
      f"Bug alto #13: la etiqueta NO queda exactamente pegada a x_left (síntoma "
      f"del bug: x_range colapsado al piso de 1e-3 por el signo invertido) "
      f"(obtenido: x_pos={x_pos_tras_update:.2f}, x_left={x_left:.2f})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
