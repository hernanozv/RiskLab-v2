"""
test_tooltips_contribucion_percentil.py
==========================================

Regresion para bug alto #11 (QA ronda 2): en el gráfico interactivo
"Contribución por Percentil", actualizar_grafico_contribucion redibuja las
barras (ax.clear() + nuevas barras) cada vez que el usuario cambia el
combo de percentil, pero nunca volvía a llamar
canvas.add_tooltip_data(...) para las barras nuevas. Como
InteractiveFigureCanvas.add_tooltip_data solo AGREGA datos (nunca
reemplaza) y el mismo objeto Axes se reutiliza entre redibujados, los
tooltips registrados la primera vez (p.ej. para "Media") seguían
mostrándose sobre las barras de un percentil distinto (p.ej. "P99"): el
usuario veía las barras de P99 pero el tooltip seguía mostrando los
valores de Media.

El fix agrega InteractiveFigureCanvas.clear_tooltip_data(ax) (limpia los
datos de tooltip previos para un eje) y actualizar_grafico_contribucion
ahora la llama antes de volver a registrar los tooltips de las barras
recién dibujadas.

Este test llama a actualizar_grafico_contribucion primero para "Media" y
luego para "P99" (mismo escenario reproducible que el bug alto #8:  97%
años sin pérdida, cola dominada por EventoA), y verifica que los tooltips
registrados tras el segundo llamado YA NO contengan los valores de Media.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np
from matplotlib.figure import Figure
from PyQt5 import QtWidgets

from InteractiveFigureCanvas import InteractiveFigureCanvas
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
print("BUG ALTO #11: tooltips de Contribución quedan obsoletos al cambiar percentil")
print("=" * 70)


class _FakeCombo:
    def __init__(self):
        self._index = 0
        self._text = "Media"

    def set(self, index, text):
        self._index = index
        self._text = text

    def currentIndex(self):
        return self._index

    def currentText(self):
        return self._text


rng = np.random.default_rng(42)
N = 100_000
tail_idx = rng.choice(N, size=int(0.03 * N), replace=False)

perdidas_evento_A = np.zeros(N)
perdidas_evento_B = np.zeros(N)
perdidas_evento_A[tail_idx] = rng.uniform(1_000_000, 5_000_000, size=len(tail_idx))
perdidas_evento_B[tail_idx] = rng.uniform(10_000, 50_000, size=len(tail_idx))
perdidas_totales = perdidas_evento_A + perdidas_evento_B

eventos = [{'id': 'a', 'nombre': 'EventoA'}, {'id': 'b', 'nombre': 'EventoB'}]
perdidas_por_evento = [perdidas_evento_A, perdidas_evento_B]

fake_self = type('FakeApp', (), {})()
fake_self.resultados_simulacion = {
    'perdidas_totales': perdidas_totales,
    'perdidas_por_evento': perdidas_por_evento,
    'eventos_riesgo': eventos,
}
combo = _FakeCombo()
fake_self.combo_percentil_contrib = combo
fake_self.fig_contribucion = Figure()
fake_self.ax_contribucion = fake_self.fig_contribucion.add_subplot(111)
fake_self.canvas_contribucion = InteractiveFigureCanvas(fake_self.fig_contribucion)

# --- 1. Dibujar "Media" primero ---
combo.set(0, "Media")
RLB.RiskLabApp.actualizar_grafico_contribucion(fake_self)

labels_media = [d['labels'][0] for d in fake_self.canvas_contribucion.tooltip_labels
                if d['ax'] is fake_self.ax_contribucion]
check(len(labels_media) > 0, f"Se registraron tooltips para 'Media' (obtenido: {len(labels_media)})")
check(any('EventoA' in (lbl or '') for lbl in labels_media),
      f"Los tooltips de 'Media' mencionan a EventoA (obtenido: {labels_media})")

# --- 2. Cambiar a "P99": las barras (y sus valores) cambian drásticamente ---
combo.set(5, "P99")
RLB.RiskLabApp.actualizar_grafico_contribucion(fake_self)

labels_p99 = [d['labels'][0] for d in fake_self.canvas_contribucion.tooltip_labels
              if d['ax'] is fake_self.ax_contribucion]
check(len(labels_p99) > 0, f"Se registraron tooltips para 'P99' (obtenido: {len(labels_p99)})")

# Bug alto #11: los tooltips de la llamada anterior (Media) no deben seguir
# presentes junto a los nuevos (P99) — deben haber sido reemplazados, no
# acumulados.
check(len(fake_self.canvas_contribucion.tooltip_labels) == len(labels_p99),
      f"Bug alto #11: los tooltips de 'Media' fueron reemplazados por los de "
      f"'P99', no acumulados (total de tooltips tras 2 llamados: "
      f"{len(fake_self.canvas_contribucion.tooltip_labels)}, esperado: {len(labels_p99)})")

check(labels_p99 != labels_media,
      f"Bug alto #11: los tooltips de 'P99' son distintos a los de 'Media' "
      f"(Media={labels_media}, P99={labels_p99})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
