"""
test_tooltip_normalizacion_escala_log.py
============================================

Regresion para bug medio #18 (QA ronda 2): la normalización de distancia
en tooltips (InteractiveFigureCanvas._process_tooltip, fix bug alto #6 /
#25 de rondas anteriores) asume escala LINEAL en ambos ejes: normaliza
cada coordenada como (valor - lim_inferior) / rango. Con el eje Y en
escala LOGARÍTMICA (toggle de la curva de Excedencia), get_ylim()
devuelve límites en unidades de DATOS (p.ej. 1e-6 a 1), pero el eje se
dibuja con espaciado equitativo por DÉCADA, no por unidad lineal.
Normalizar linealmente sobre ese rango comprime casi todos los valores
Y reales (que suelen ser mucho menores al límite superior) muy cerca de
0, dejando que la distancia quede dominada casi por completo por la
proximidad en X — el eje Y deja de discriminar entre puntos que están
visualmente muy separados (uno cerca del tope del gráfico, otro cerca
del fondo).

El fix transforma a log10 antes de normalizar cuando el eje tiene escala
'log' (igual que hace matplotlib al posicionar los píxeles), tanto para
el eje X como el Y, de forma independiente.

Este test arma dos puntos de tooltip en un eje con escala Y logarítmica:
- Punto A: mismo Y que el cursor, pero un poco más lejos en X.
- Punto B: X casi idéntico al cursor, pero en el extremo inferior del
  eje (visualmente muy lejos, en la parte de abajo del gráfico).
Bajo normalización lineal (bug), el término Y de ambos puntos es casi
cero (ambos son minúsculos frente al rango lineal hasta 1), así que el
punto B "gana" por estar más cerca en X, aunque esté visualmente muy
lejos. Bajo normalización logarítmica (fix), el punto A debe ganar,
porque coincide en la coordenada Y visual real.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np
from matplotlib.figure import Figure
from PyQt5 import QtWidgets

from InteractiveFigureCanvas import InteractiveFigureCanvas

PASS = 0
FAIL = 0

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)


def check(condition, msg):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {msg}")
    else:
        FAIL += 1
        print(f"  ❌ FALLO: {msg}")


class _FakeEvent:
    def __init__(self, inaxes, xdata, ydata):
        self.inaxes = inaxes
        self.xdata = xdata
        self.ydata = ydata


print("=" * 70)
print("BUG MEDIO #18: normalización de tooltips con escala Y logarítmica")
print("=" * 70)

fig = Figure()
ax = fig.add_subplot(111)
ax.set_xlim(0, 100)
ax.set_ylim(1e-6, 1)
ax.set_yscale('log')

canvas = InteractiveFigureCanvas(fig)

# Ambos puntos se registran en UNA sola llamada (mismo conjunto de datos),
# igual que hace el gráfico real de Excedencia con su curva completa —
# así la búsqueda del punto más cercano realmente compara entre ambos, en
# vez de que el primero agregado "gane" por orden de iteración.
# Punto A: visualmente al mismo nivel Y que el cursor (y=0.001), un poco
# más lejos en X. Punto B: X casi idéntico al cursor, pero en el extremo
# inferior del eje (visualmente muy lejos, en la parte de abajo del
# gráfico logarítmico).
canvas.add_tooltip_data(ax, [10, 11], [0.001, 1e-6], labels=['PuntoA', 'PuntoB'])

# Cursor: x=11 (igual a B), y=0.001 (igual a A).
evento = _FakeEvent(inaxes=ax, xdata=11, ydata=0.001)
canvas._process_tooltip(evento)

texto_mostrado = canvas.hover_artist.get_text() if canvas.hover_artist else None
check(texto_mostrado is not None, f"Se muestra un tooltip (obtenido: {texto_mostrado!r})")

if texto_mostrado:
    check('PuntoA' in texto_mostrado,
          f"Bug medio #18: se selecciona 'PuntoA' (visualmente al mismo nivel Y que el "
          f"cursor), no 'PuntoB' (visualmente muy lejos, en el fondo del eje log) "
          f"(obtenido: {texto_mostrado!r})")
    check('PuntoB' not in texto_mostrado,
          f"'PuntoB' NO es seleccionado, a pesar de tener el X más cercano al cursor "
          f"(obtenido: {texto_mostrado!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
