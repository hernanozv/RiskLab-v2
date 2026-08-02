"""
test_escenarios_y_calendario_tienen_tooltips.py
===================================================

Regresion para bug bajo #32 (QA ronda 3): a diferencia del resto de
gráficos de Risk Lab (que registran datos vía
InteractiveFigureCanvas.add_tooltip_data para mostrar información al
pasar el mouse), las pestañas "Escenarios" ("¿Qué pasaría si...?") y
"Calendario" (línea de tiempo de retorno) no tenían NINGÚN tooltip
interactivo -- toda su información solo estaba disponible como texto
fijo en el gráfico (etiquetas de barra / cuadros de texto), sin
posibilidad de resaltado ni de un formato consistente con el resto de
la app.

El fix agrega un tooltip por barra en "Escenarios" (nombre, valor
exacto, probabilidad) y un tooltip por punto en "Calendario" (mismo
texto informativo que ya se muestra en el cuadro fijo, más útil cuando
dos cuadros quedan visualmente próximos).

Este test construye ambos gráficos vía graficar_resultados() y verifica
que sus respectivos InteractiveFigureCanvas tengan al menos una entrada
en tooltip_labels (antes, la lista estaba vacía en ambos casos).
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
print("BUG BAJO #32: pestañas Escenarios y Calendario deben tener tooltips interactivos")
print("=" * 70)

rng = np.random.default_rng(19)
N = 5000
perdidas_totales = rng.lognormal(11, 1.2, N)
frecuencias_totales = rng.poisson(3, N)
eventos = [{'id': 'a', 'nombre': 'EventoA'}]
perdidas_por_evento = [perdidas_totales.copy()]
frecuencias_por_evento = [frecuencias_totales.copy()]

win = RLB.RiskLabApp()
win.graficar_resultados(perdidas_totales, frecuencias_totales, perdidas_por_evento,
                        frecuencias_por_evento, eventos)

canvas_escenarios = getattr(win, 'canvas_escenarios', None)
check(canvas_escenarios is not None, "self.canvas_escenarios se guardó correctamente")
if canvas_escenarios is not None:
    n_tooltips_esc = len(canvas_escenarios.tooltip_labels)
    print(f"  tooltip_labels en Escenarios: {n_tooltips_esc}")
    check(n_tooltips_esc >= 1,
          f"Bug bajo #32: la pestaña Escenarios tiene al menos un dataset de "
          f"tooltip registrado (obtenido: {n_tooltips_esc})")

nombres_tabs = [win.graficos_tab_widget.tabText(i) for i in range(win.graficos_tab_widget.count())]
check('Calendario' in nombres_tabs, f"La pestaña 'Calendario' existe (tabs: {nombres_tabs})")

if 'Calendario' in nombres_tabs:
    idx_tab = nombres_tabs.index('Calendario')
    tab = win.graficos_tab_widget.widget(idx_tab)
    from InteractiveFigureCanvas import InteractiveFigureCanvas
    canvases = tab.findChildren(InteractiveFigureCanvas)
    check(len(canvases) >= 1, f"El tab Calendario contiene un canvas (obtenido: {len(canvases)})")
    if canvases:
        n_tooltips_cal = len(canvases[0].tooltip_labels)
        print(f"  tooltip_labels en Calendario: {n_tooltips_cal}")
        check(n_tooltips_cal >= 1,
              f"Bug bajo #32: la pestaña Calendario tiene al menos un dataset de "
              f"tooltip registrado (obtenido: {n_tooltips_cal})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
