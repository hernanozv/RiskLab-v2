"""
test_tail_risk_titulo_distribucion_degenerada.py
====================================================

Regresion para bug medio #28 (QA ronda 3): en el gráfico "Tail Risk"
(Cola de Pérdidas), cuando la distribución es degenerada (masa puntual
en el máximo que cubre >=20% de las simulaciones), el filtro
"perdidas_totales > percentil_80" da vacío y el fallback ">=" selecciona
el 100% de los datos -- pero el título seguía diciendo "Percentil
80-100", dando la falsa impresión de una cola extrema diferenciada
cuando en realidad todos los datos son idénticos (sin diferenciación de
cola alguna).

El fix cambia el título dinámicamente a "distribución degenerada" cuando
perdidas_cola termina cubriendo el 100% de los datos.

Este test construye una distribución enteramente determinista (un único
valor para todas las simulaciones) y verifica que el título del gráfico
"Tail Risk" ya NO diga "Percentil 80-100".
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
print("BUG MEDIO #28: título de Tail Risk no debe decir 'Percentil 80-100' si es degenerada")
print("=" * 70)

N = 1000
perdidas_totales = np.full(N, 500_000.0)  # distribución enteramente determinista
frecuencias_totales = np.ones(N, dtype=int)
eventos = [{'id': 'a', 'nombre': 'EventoDeterminista'}]
perdidas_por_evento = [perdidas_totales.copy()]
frecuencias_por_evento = [np.ones(N, dtype=int)]

win = RLB.RiskLabApp()
win.graficar_resultados(perdidas_totales, frecuencias_totales, perdidas_por_evento,
                        frecuencias_por_evento, eventos)

nombres_tabs = [win.graficos_tab_widget.tabText(i) for i in range(win.graficos_tab_widget.count())]
check('Tail Risk' in nombres_tabs, f"La pestaña 'Tail Risk' existe (tabs: {nombres_tabs})")

idx_tab = nombres_tabs.index('Tail Risk')
tab = win.graficos_tab_widget.widget(idx_tab)

from InteractiveFigureCanvas import InteractiveFigureCanvas
canvases = tab.findChildren(InteractiveFigureCanvas)
check(len(canvases) >= 1, f"El tab contiene un canvas de matplotlib (obtenido: {len(canvases)})")

ax = canvases[0].figure.axes[0]
titulo = ax.get_title()
print(f"  título obtenido: {titulo!r}")

check('80-100' not in titulo and '80 al 100' not in titulo,
      f"Bug medio #28: el título ya NO dice 'Percentil 80-100' para una "
      f"distribución degenerada (obtenido: {titulo!r})")
check('degenerada' in titulo.lower(),
      f"Bug medio #28: el título indica explícitamente que es una distribución "
      f"degenerada sin diferenciación de cola (obtenido: {titulo!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
