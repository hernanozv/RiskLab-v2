"""
test_tooltip_normalizacion.py
==============================

Regresion para bug #25: InteractiveFigureCanvas._process_tooltip calculaba
la distancia entre el cursor y los puntos de datos con distancia euclidiana
cruda en unidades de datos, sin normalizar por el rango de cada eje. En
gráficos donde los dos ejes tienen escalas muy distintas (p.ej. frecuencia
0-30 vs pérdida en millones de USD), esto hacía que la distancia quedara
dominada casi exclusivamente por el eje de mayor magnitud absoluta, y el
tooltip podía terminar mostrando un punto visualmente lejano en vez del
punto realmente más cercano al cursor.

De paso, esta suite instancia InteractiveFigureCanvas para confirmar que
add_tooltip_data/_optimize_tooltip_data/_on_mouse_move/_process_tooltip
tienen una única definición viva (el archivo tenía 2 copias idénticas de
cada método; la primera era código muerto porque Python usa la última
definición de un método en el cuerpo de una clase).
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

from PyQt5 import QtWidgets
from matplotlib.figure import Figure

from InteractiveFigureCanvas import InteractiveFigureCanvas

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


class _FakeEvent:
    def __init__(self, inaxes, xdata, ydata):
        self.inaxes = inaxes
        self.xdata = xdata
        self.ydata = ydata


print("=" * 70)
print("BUG #25: Normalización de distancia en tooltips de hover")
print("=" * 70)

# --- 0. No debe haber metodos duplicados (la primera copia era codigo muerto) ---
import ast
with open(os.path.join(_THIS_DIR, 'InteractiveFigureCanvas.py'), encoding='utf-8') as f:
    tree = ast.parse(f.read())
clase = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'InteractiveFigureCanvas')
for nombre_metodo in ('add_tooltip_data', '_optimize_tooltip_data', '_on_mouse_move', '_process_tooltip'):
    defs = [n for n in clase.body if isinstance(n, ast.FunctionDef) and n.name == nombre_metodo]
    check(len(defs) == 1, f"'{nombre_metodo}' tiene una unica definicion (antes habia 2 copias identicas)")

# --- 1. Escenario con ejes de escalas muy distintas: X en [0,30] (frecuencia),
#        Y en [0, 100_000_000] (perdida en USD) ---
fig = Figure()
ax = fig.add_subplot(111)
ax.set_xlim(0, 30)
ax.set_ylim(0, 100_000_000)

canvas = InteractiveFigureCanvas(fig)

# Punto A: visualmente el mas cercano al cursor (cerca en X Y en Y, como
# fraccion de sus respectivos rangos).
# Punto B: visualmente mas lejano (mas lejos en X como fraccion del rango),
# pero con una diferencia en Y minuscula en terminos ABSOLUTOS -> con el bug
# viejo (distancia euclidiana sin normalizar, dominada por el eje Y de
# magnitud enorme) el punto B "ganaba" por error.
punto_A = (5.05, 1_500_000)
punto_B = (5.50, 1_000_050)
canvas.add_tooltip_data(ax, x_data=[punto_A[0], punto_B[0]], y_data=[punto_A[1], punto_B[1]],
                        labels=['A_correcto', 'B_incorrecto_bajo_bug'])

registrados = []
canvas._show_tooltip = lambda ax_, x, y, text, highlight_color=None: registrados.append((x, y, text))

evento = _FakeEvent(ax, xdata=5.0, ydata=1_000_000)
canvas._process_tooltip(evento)

check(len(registrados) == 1, "Se muestra exactamente un tooltip")
if registrados:
    x_mostrado, y_mostrado, texto_mostrado = registrados[0]
    check((x_mostrado, y_mostrado) == punto_A,
          f"Bug #25: el tooltip muestra el punto A (visualmente mas cercano), no B "
          f"(mostrado: {(x_mostrado, y_mostrado)})")
    check('A_correcto' in texto_mostrado,
          "El texto del tooltip corresponde a la etiqueta del punto A")

print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
