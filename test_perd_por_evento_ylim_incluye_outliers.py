"""
test_perd_por_evento_ylim_incluye_outliers.py
=================================================

Regresion para bug alto #17 (QA ronda 3): en el gráfico "Perd por
Evento" (boxplot por evento de riesgo), showfliers=False oculta los
outliers, y matplotlib autoescala el eje Y SOLO en base a las
cajas/bigotes visibles, SIN considerar los outliers ocultos. Para una
severidad de cola pesada (la norma en riesgo operacional), el Máximo
real y los percentiles P90/P95 -- registrados como tooltips
(add_tooltip_data) usando los valores REALES -- podían caer fuera del
rango visible del eje Y, haciendo esos tooltips inalcanzables con el
mouse aunque los datos existieran.

El fix expande explícitamente el ylim del boxplot para cubrir el rango
real (mín/máx) de todos los eventos, sin volver a dibujar los
marcadores de outliers (showfliers sigue en False).

Este test construye un evento con severidad muy sesgada (la mayoría de
los valores bajos, unos pocos extremadamente altos -- un caso clásico
de whisker teórico << máximo real) y verifica que, tras graficar, el
ylim del eje del boxplot efectivamente cubre el valor máximo real (el
punto donde se registró el tooltip de "Máximo").
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
print("BUG ALTO #17: ylim de 'Perd por Evento' debe incluir el Máximo real (outlier oculto)")
print("=" * 70)

rng = np.random.default_rng(3)
N = 2000
# Severidad muy sesgada: 95% de los valores en [10,20], 5% extremos en
# [800,900] -- el whisker teórico (Q3+1.5*IQR) queda muy por debajo del
# máximo real, exactamente el caso que showfliers=False oculta.
perdidas_evento = np.where(rng.random(N) < 0.95, rng.uniform(10, 20, N), rng.uniform(800, 900, N))
frecuencias_totales = np.ones(N, dtype=int)
eventos = [{'id': 'a', 'nombre': 'EventoSesgado'}]
perdidas_por_evento = [perdidas_evento.copy()]
frecuencias_por_evento = [np.ones(N, dtype=int)]
perdidas_totales = perdidas_evento.copy()

maximo_real = float(np.max(perdidas_evento))
print(f"  máximo real del evento: {maximo_real:.1f}")

win = RLB.RiskLabApp()
win.graficar_resultados(perdidas_totales, frecuencias_totales, perdidas_por_evento,
                        frecuencias_por_evento, eventos)

nombres_tabs = [win.graficos_tab_widget.tabText(i) for i in range(win.graficos_tab_widget.count())]
check('Perd por Evento' in nombres_tabs, f"La pestaña 'Perd por Evento' existe (tabs: {nombres_tabs})")

idx_tab = nombres_tabs.index('Perd por Evento')
tab = win.graficos_tab_widget.widget(idx_tab)

from InteractiveFigureCanvas import InteractiveFigureCanvas
canvases = tab.findChildren(InteractiveFigureCanvas)
check(len(canvases) >= 1, f"El tab contiene un canvas de matplotlib (obtenido: {len(canvases)})")

ax = canvases[0].figure.axes[0]
y_min, y_max = ax.get_ylim()
print(f"  ylim del boxplot: ({y_min:.1f}, {y_max:.1f})")

check(y_max >= maximo_real,
      f"Bug alto #17: el ylim del boxplot cubre el Máximo real (donde se "
      f"registró el tooltip de 'Máximo'), no queda fuera del rango visible "
      f"(obtenido: ylim=({y_min:.1f}, {y_max:.1f}), máximo_real={maximo_real:.1f})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
