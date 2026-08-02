"""
test_escenarios_grafico_no_colapsa_en_cero.py
=================================================

Regresion para bug bajo #33 (QA ronda 3): en el gráfico "Escenarios"
("¿Qué pasaría si...?"), cuando TODOS los percentiles reportados
(Media, P90, P95, P99) son 0 (un año sin pérdidas materializadas en
ninguna simulación relevante), max_valor = 0, y
`ax_escenarios.set_xlim(0, max_valor * 1.35)` colapsaba el eje X a
(0, 0) -- un viewport degenerado donde las barras, etiquetas de valor y
grid quedan comprimidas/ilegibles en x=0.

El fix usa un piso de escala (_escala_para_offsets) solo para el
viewport y los offsets de las etiquetas, sin alterar el valor real de
las barras (que siguen representando fielmente 0).

Este test construye una distribución de pérdidas enteramente cero,
llama a graficar_resultados, y verifica que el xlim del gráfico
"Escenarios" NO sea degenerado (ancho > 0).
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
print("BUG BAJO #33: gráfico Escenarios no debe colapsar el eje X cuando todo es 0")
print("=" * 70)

N = 1000
perdidas_totales = np.zeros(N)
frecuencias_totales = np.zeros(N, dtype=int)
eventos = [{'id': 'a', 'nombre': 'EventoSinPerdidas'}]
perdidas_por_evento = [perdidas_totales.copy()]
frecuencias_por_evento = [frecuencias_totales.copy()]

win = RLB.RiskLabApp()
win.graficar_resultados(perdidas_totales, frecuencias_totales, perdidas_por_evento,
                        frecuencias_por_evento, eventos)

ax = getattr(win, 'ax_escenarios', None)
check(ax is not None, "self.ax_escenarios se guardó correctamente")

if ax is not None:
    xlim = ax.get_xlim()
    print(f"  xlim obtenido: {xlim}")
    check(xlim[1] > xlim[0],
          f"Bug bajo #33: el eje X del gráfico Escenarios tiene ancho > 0 "
          f"(no degenerado) aún cuando todas las pérdidas son 0 "
          f"(obtenido: {xlim})")
    check(xlim[1] >= 1.0,
          f"El límite superior del eje X usa un piso de escala razonable "
          f"cuando max_valor=0 (obtenido: {xlim[1]})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
