"""
test_frecuencia_tooltip_moda_no_tapado.py
=============================================

Regresion para bug bajo #34 (QA ronda 3): en el gráfico "Frecuencia",
InteractiveFigureCanvas._process_tooltip recorre `tooltip_labels` EN
ORDEN y muestra el tooltip del PRIMER dataset cuyo punto más cercano cae
dentro del umbral (hace `break` en el primer match, sin comparar
distancias entre datasets). El dataset genérico de bins (agregado
primero) cubre exactamente el mismo punto (x=idx_max) que el tooltip
especial de la "Moda" (resaltado en rojo, agregado después) -- por lo
que el tooltip genérico siempre "tapaba" (shadowing) al de la moda, que
nunca se mostraba pese a estar registrado.

El fix reordena el registro: los tooltips especiales de Moda y Media se
agregan ANTES del dataset genérico, para que ganen el empate.

Este test construye el gráfico Frecuencia real, simula un evento de
hover EXACTAMENTE sobre el punto de la moda, y verifica que el tooltip
mostrado sea el especial ("Moda: ..." con highlight rojo), no el
genérico.
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
print("BUG BAJO #34: tooltip de 'Moda' en Frecuencia no debe quedar tapado")
print("=" * 70)

rng = np.random.default_rng(7)
N = 5000
frecuencias_totales = rng.poisson(3, N)
perdidas_totales = rng.lognormal(10, 1, N)
eventos = [{'id': 'a', 'nombre': 'EventoA'}]
perdidas_por_evento = [perdidas_totales.copy()]
frecuencias_por_evento = [frecuencias_totales.copy()]

win = RLB.RiskLabApp()
win.graficar_resultados(perdidas_totales, frecuencias_totales, perdidas_por_evento,
                        frecuencias_por_evento, eventos)

nombres_tabs = [win.graficos_tab_widget.tabText(i) for i in range(win.graficos_tab_widget.count())]
check('Frecuencia' in nombres_tabs, f"La pestaña 'Frecuencia' existe (tabs: {nombres_tabs})")

idx_tab = nombres_tabs.index('Frecuencia')
tab = win.graficos_tab_widget.widget(idx_tab)

from InteractiveFigureCanvas import InteractiveFigureCanvas
canvases = tab.findChildren(InteractiveFigureCanvas)
check(len(canvases) >= 1, f"El tab contiene un canvas de matplotlib (obtenido: {len(canvases)})")

canvas = canvases[0]
ax = canvas.figure.axes[0]

frecuencia_counts = np.bincount(frecuencias_totales.astype(int))
idx_max = int(np.argmax(frecuencia_counts))
print(f"  moda (idx_max)={idx_max}, conteo={frecuencia_counts[idx_max]}")


class _FakeEvent:
    def __init__(self, inaxes, xdata, ydata):
        self.inaxes = inaxes
        self.xdata = xdata
        self.ydata = ydata


ev = _FakeEvent(ax, float(idx_max), float(frecuencia_counts[idx_max]))
canvas._process_tooltip(ev)

texto = canvas.hover_artist.get_text() if getattr(canvas, 'hover_artist', None) is not None else None
print(f"  texto del tooltip mostrado: {texto!r}")

check(texto is not None, "Se mostró un tooltip al hacer hover sobre el punto de la moda")
if texto is not None:
    check('Moda' in texto,
          f"Bug bajo #34: el tooltip mostrado sobre el punto de la moda es "
          f"el especial ('Moda: ...'), no el genérico (obtenido: {texto!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
