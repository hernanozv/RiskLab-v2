"""
test_semaforo_probabilidades_suman_100.py
=============================================

Regresion para bug alto #10 (QA ronda 2): en el gráfico "Semáforo"
(Probabilidad por Nivel de Impacto), el bin "Crítico" se definía como
el rango (umbral_alto, np.max(perdidas_totales)) y usaba la MISMA máscara
de comparación estricta "< max_val" que los demás bins. Si hay una masa
puntual en el máximo (p.ej. un evento con severidad determinista que
supera el umbral "alto" en TODAS las simulaciones, o un límite de póliza
que satura muchas simulaciones exactamente en el mismo valor), esas
simulaciones no son estrictamente menores que max_val (son iguales),
así que la máscara "< max_val" las excluye — y como también son
">= umbral_alto", no caen en ningún otro bin tampoco. Resultado: esas
simulaciones no se cuentan en NINGÚN bin, y las 4 probabilidades
(Bajo+Moderado+Alto+Crítico) pueden sumar mucho menos que 100% (en el
caso extremo reproducido aquí, exactamente 0%, ya que TODA la masa está
en ese máximo).

El gráfico Termómetro no tiene este bug: la referencia real (export IA,
_build_risk_classification) calcula el bin más alto como
"perdidas_totales >= umbral_alto" SIN límite superior, por lo que las 4
probabilidades siempre suman exactamente 100%.

Este test construye un evento con severidad determinista muy por encima
del umbral "alto" (de modo que TODAS las simulaciones caen exactamente en
el máximo) y verifica que las probabilidades dibujadas en el gráfico
Semáforo sumen ~100%, no 0%.
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
print("BUG ALTO #10: Semáforo - las 4 probabilidades deben sumar ~100%")
print("=" * 70)

N = 2000
# Evento con severidad DETERMINISTA muy por encima del umbral "alto"
# ($110M): TODAS las simulaciones caen exactamente en el mismo valor
# máximo, dentro de la zona "Crítico". Este es el escenario que dispara
# el bug: mask "< np.max(perdidas_totales)" excluye absolutamente todo.
VALOR_CRITICO = 200_000_000.0
perdidas_totales = np.full(N, VALOR_CRITICO)
frecuencias_totales = np.ones(N, dtype=int)
eventos = [{'id': 'a', 'nombre': 'EventoCriticoDeterminista'}]
perdidas_por_evento = [perdidas_totales.copy()]
frecuencias_por_evento = [np.ones(N, dtype=int)]

check(np.max(perdidas_totales) == VALOR_CRITICO and np.min(perdidas_totales) == VALOR_CRITICO,
      "Precondición: todas las simulaciones caen exactamente en el mismo valor (masa puntual)")

win = RLB.RiskLabApp()
win.graficar_resultados(perdidas_totales, frecuencias_totales, perdidas_por_evento,
                        frecuencias_por_evento, eventos)

nombres_tabs = [win.graficos_tab_widget.tabText(i) for i in range(win.graficos_tab_widget.count())]
check('Semáforo' in nombres_tabs, f"La pestaña 'Semáforo' existe (tabs: {nombres_tabs})")

idx_semaforo = nombres_tabs.index('Semáforo')
tab_semaforo = win.graficos_tab_widget.widget(idx_semaforo)

from InteractiveFigureCanvas import InteractiveFigureCanvas
canvases = tab_semaforo.findChildren(InteractiveFigureCanvas)
check(len(canvases) >= 1, f"El tab Semáforo contiene un canvas de matplotlib (obtenido: {len(canvases)})")

canvas = canvases[0]
ax = canvas.figure.axes[0]
probabilidades = [bar.get_width() for bar in ax.patches]

check(len(probabilidades) == 4,
      f"Se dibujan 4 barras (Bajo/Moderado/Alto/Crítico) (obtenido: {len(probabilidades)})")

suma = sum(probabilidades)
check(abs(suma - 100.0) < 0.5,
      f"Bug alto #10: las 4 probabilidades del Semáforo suman ~100% "
      f"(obtenido: {suma:.2f}%, individuales: {[round(p, 2) for p in probabilidades]})")

# La última barra (Crítico) debe concentrar prácticamente toda la masa,
# ya que TODA la pérdida cae en la zona crítica.
check(probabilidades[-1] > 99.0,
      f"La barra 'Crítico' (última) concentra ~100% de la probabilidad "
      f"(obtenido: {probabilidades[-1]:.2f}%)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
