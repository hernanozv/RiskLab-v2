"""
test_calendario_niveles_no_superpuestos.py
==============================================

Regresion para bug alto #18 (QA ronda 3): en el gráfico "Calendario"
(línea de tiempo de período de retorno), y_positions=[1.5,-1.5,1.5,-1.5]
asignaba la MISMA fila a BAJO/ALTO (índices 0,2) y a MODERADO/CRÍTICO
(índices 1,3). El período de retorno se capea a 100 años para la
visualización (min(periodo, 100)); cuando dos niveles con la misma
paridad de fila tenían período real >= 100 años, ambos quedaban
EXACTAMENTE en el mismo punto (x=100, misma fila), y el cuadro de texto
de uno tapaba por completo al del otro (mismo x, mismo y, z-order solo
determinado por orden de dibujo).

El fix usa 4 filas DISTINTAS (una por nivel), sin perder la alternancia
visual arriba/abajo.

Este test construye una distribución donde tanto el umbral MODERADO
como el CRÍTICO tienen periodo de retorno >= 100 años (ambos capeados
al mismo x=100), y verifica que sus posiciones Y sean diferentes.
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
print("BUG ALTO #18: niveles de riesgo del Calendario no deben superponerse")
print("=" * 70)

N = 100_000
perdidas_totales = np.zeros(N)
# 0.2% de las simulaciones con una pérdida extrema: dispara tanto el
# umbral MODERADO (32M) como el CRÍTICO (~165M) con periodo >= 100 años.
idx_extremos = np.arange(0, N, 500)  # 200 de 100.000 = 0.2%
perdidas_totales[idx_extremos] = 200_000_000.0
frecuencias_totales = np.ones(N, dtype=int)
eventos = [{'id': 'a', 'nombre': 'EventoRaro'}]
perdidas_por_evento = [perdidas_totales.copy()]
frecuencias_por_evento = [np.ones(N, dtype=int)]

win = RLB.RiskLabApp()
win.graficar_resultados(perdidas_totales, frecuencias_totales, perdidas_por_evento,
                        frecuencias_por_evento, eventos)

nombres_tabs = [win.graficos_tab_widget.tabText(i) for i in range(win.graficos_tab_widget.count())]
check('Calendario' in nombres_tabs, f"La pestaña 'Calendario' existe (tabs: {nombres_tabs})")

idx_cal = nombres_tabs.index('Calendario')
tab_cal = win.graficos_tab_widget.widget(idx_cal)

from InteractiveFigureCanvas import InteractiveFigureCanvas
canvases = tab_cal.findChildren(InteractiveFigureCanvas)
check(len(canvases) >= 1, f"El tab Calendario contiene un canvas de matplotlib (obtenido: {len(canvases)})")

ax = canvases[0].figure.axes[0]
# Los textos de nivel tienen posición (x=periodo_capeado, y=y_pos).
textos_niveles = [t for t in ax.texts if any(n in t.get_text() for n in ('MODERADO', 'CRÍTICO', 'CRITICO'))]
print(f"  textos encontrados: {[t.get_text().split(chr(10))[0] for t in textos_niveles]}")
check(len(textos_niveles) == 2,
      f"Se encontraron los textos de MODERADO y CRÍTICO (obtenido: {len(textos_niveles)})")

if len(textos_niveles) == 2:
    pos = [t.get_position() for t in textos_niveles]
    print(f"  posiciones: {pos}")
    check(abs(pos[0][0] - pos[1][0]) < 1.0,
          f"Precondición: ambos niveles quedan capeados al mismo x≈100 "
          f"(obtenido: x0={pos[0][0]:.1f}, x1={pos[1][0]:.1f})")
    check(abs(pos[0][1] - pos[1][1]) > 0.5,
          f"Bug alto #18: MODERADO y CRÍTICO tienen posiciones Y DIFERENTES "
          f"(no se superponen), aunque compartan el mismo x capeado "
          f"(obtenido: y0={pos[0][1]}, y1={pos[1][1]})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
