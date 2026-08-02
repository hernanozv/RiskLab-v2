"""
test_tab_contribucion_eventos_deterministas.py
=================================================

Regresion para bug #40 (QA ronda 2): en graficar_resultados, el bloque del
"Gráfico 7: Gráfico de Tornado - Contribución de Eventos de Riesgo" quedó
indentado un nivel de más, anidado dentro del `if datos_plot:` del Gráfico
6 anterior (comparación de eventos por KDE). `datos_plot` solo se pone en
True si ALGÚN evento tiene `np.std(perdidas_evento) > 0` (severidad no
determinista). Con eventos de severidad fija (p.ej. una multa regulatoria
de monto constante, o cualquier evento con frecuencia y severidad
deterministas), `datos_plot` queda en False y la pestaña "Contribución"
desaparecía POR COMPLETO — sin ninguna excepción ni aviso — aun cuando las
contribuciones por evento son claramente mayores a 0 y deberían mostrarse.

La versión legacy del mismo gráfico (generar_figuras, usada por el PDF
"legacy") nunca tuvo este bug: ese bloque siempre fue independiente del
`if datos_plot`. Este test confirma que graficar_resultados ahora se
comporta igual.
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
print("BUG #40: Tab 'Contribución' con eventos de severidad determinista")
print("=" * 70)

win = RLB.RiskLabApp()

N = 2000
# 2 eventos con severidad y frecuencia COMPLETAMENTE deterministas (std=0):
# el escenario exacto donde 'datos_plot' del Gráfico 6 queda en False.
perdidas_A = np.full(N, 200_000_000.0)
perdidas_B = np.full(N, 50_000_000.0)
perdidas_totales = perdidas_A + perdidas_B
frecuencias_totales = np.ones(N, dtype=int)
eventos = [{'id': 'A', 'nombre': 'EventoDeterministaA'},
           {'id': 'B', 'nombre': 'EventoDeterministaB'}]
perdidas_por_evento = [perdidas_A, perdidas_B]
frecuencias_por_evento = [np.ones(N, dtype=int), np.ones(N, dtype=int)]

check(np.std(perdidas_A) == 0 and np.std(perdidas_B) == 0,
      "Precondición: ambos eventos son deterministas (std=0), el caso que dispara el bug")

win.graficar_resultados(perdidas_totales, frecuencias_totales, perdidas_por_evento,
                        frecuencias_por_evento, eventos)

nombres_tabs = [win.graficos_tab_widget.tabText(i) for i in range(win.graficos_tab_widget.count())]

check('Contribución' in nombres_tabs,
      f"Bug #40: la pestaña 'Contribución' aparece aun con eventos deterministas "
      f"(tabs encontradas: {nombres_tabs})")
check('Dist. por Evento' not in nombres_tabs,
      "La pestaña 'Dist. por Evento' (Gráfico 6, sí depende de varianza>0) "
      "NO aparece — confirma que el escenario realmente tiene std=0 en todos los eventos")

# --- Caso mixto: un evento determinista + uno no determinista. Ambas
#     pestañas (Dist. por Evento Y Contribución) deben aparecer. ---
rng = np.random.default_rng(0)
perdidas_C = np.full(N, 100_000_000.0)          # determinista
perdidas_D = rng.normal(10_000_000, 2_000_000, N)  # no determinista
perdidas_D = np.maximum(perdidas_D, 0)
perdidas_totales_2 = perdidas_C + perdidas_D
eventos_2 = [{'id': 'C', 'nombre': 'EventoDeterministaC'},
             {'id': 'D', 'nombre': 'EventoVariableD'}]

win2 = RLB.RiskLabApp()
win2.graficar_resultados(perdidas_totales_2, frecuencias_totales,
                         [perdidas_C, perdidas_D], frecuencias_por_evento, eventos_2)
nombres_tabs_2 = [win2.graficos_tab_widget.tabText(i) for i in range(win2.graficos_tab_widget.count())]

check('Contribución' in nombres_tabs_2,
      f"Caso mixto (1 determinista + 1 variable): 'Contribución' sigue apareciendo "
      f"(tabs: {nombres_tabs_2})")
check('Dist. por Evento' in nombres_tabs_2,
      "Caso mixto: 'Dist. por Evento' también aparece (hay al menos un evento con std>0)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
