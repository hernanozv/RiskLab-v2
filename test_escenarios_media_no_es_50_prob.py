"""
test_escenarios_media_no_es_50_prob.py
==========================================

Regresion para bug critico #6 (QA ronda 3): en el gráfico "Escenarios"
("¿Qué pasaría si...?"), la barra "Típico (Media)" se etiquetaba con el
texto "(50% prob.)", como si la media coincidiera con la mediana (P50).
Esto es estadísticamente falso en cualquier distribución de pérdida
sesgada (la norma en riesgo operacional, con alta masa puntual en $0):
la probabilidad real de superar la media casi nunca es 50%.

Además, esto contradecía:
  - La propia pestaña "Excedencia", que muestra el P50 real (mediana),
    que puede ser muy distinto de la media en distribuciones sesgadas
    (p.ej. $0 si el evento ocurre en menos de la mitad de los años).
  - El export IA (_build_scenario_impacts), que para el MISMO valor
    (np.mean(perdidas_totales)) ya usa la etiqueta "promedio", sin
    afirmar "50% de probabilidad".

Este test construye una distribución de pérdida MUY sesgada (85% de
los años sin pérdida, cola lognormal en el resto), donde la mediana
real es $0 pero la media es claramente positiva, y verifica que:
  1. El texto junto a la barra "Típico (Media)" diga "(promedio)",
     no "(50% prob.)".
  2. La mediana real (P50) de la distribución es efectivamente muy
     distinta de la media (confirmando que "50% prob." habría sido
     una etiqueta falsa para este dato).
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
print("BUG CRÍTICO #6: 'Típico (Media)' no debe rotularse como '50% prob.'")
print("=" * 70)

rng = np.random.default_rng(99)
N = 20_000
ocurre = rng.random(N) < 0.15  # el evento solo ocurre en el 15% de los años
perdidas_totales = np.where(ocurre, rng.lognormal(mean=10, sigma=1.0, size=N), 0.0)
frecuencias_totales = ocurre.astype(int)
eventos = [{'id': 'a', 'nombre': 'EventoSesgado'}]
perdidas_por_evento = [perdidas_totales.copy()]
frecuencias_por_evento = [frecuencias_totales.copy()]

media_real = float(np.mean(perdidas_totales))
mediana_real = float(np.median(perdidas_totales))
print(f"  media_real={media_real:.2f}, mediana_real(P50)={mediana_real:.2f}")
check(mediana_real == 0.0 and media_real > 1000,
      f"Precondición: la mediana real (P50) es $0 pero la media es claramente "
      f"positiva (media={media_real:.2f}, mediana={mediana_real:.2f}) -- confirma "
      f"que '50% prob.' habría sido una etiqueta falsa para la media")

win = RLB.RiskLabApp()
win.graficar_resultados(perdidas_totales, frecuencias_totales, perdidas_por_evento,
                        frecuencias_por_evento, eventos)

nombres_tabs = [win.graficos_tab_widget.tabText(i) for i in range(win.graficos_tab_widget.count())]
check('Escenarios' in nombres_tabs, f"La pestaña 'Escenarios' existe (tabs: {nombres_tabs})")

idx_escenarios = nombres_tabs.index('Escenarios')
tab_escenarios = win.graficos_tab_widget.widget(idx_escenarios)

from InteractiveFigureCanvas import InteractiveFigureCanvas
canvases = tab_escenarios.findChildren(InteractiveFigureCanvas)
check(len(canvases) >= 1, f"El tab Escenarios contiene un canvas de matplotlib (obtenido: {len(canvases)})")

canvas = canvases[0]
ax = canvas.figure.axes[0]
textos = [t.get_text() for t in ax.texts]
print(f"  textos dibujados: {textos}")

check(any("(promedio)" in t for t in textos),
      f"Bug crítico #6: la barra de la Media usa la etiqueta '(promedio)' "
      f"(obtenido: {textos})")
check(not any("50% prob" in t for t in textos),
      f"Bug crítico #6: ya NO aparece la etiqueta falsa '(50% prob.)' "
      f"(obtenido: {textos})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
