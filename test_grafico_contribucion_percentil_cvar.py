"""
test_grafico_contribucion_percentil_cvar.py
==============================================

Regresion para bug alto #8 (QA ronda 2): RiskLabApp.actualizar_grafico_
contribucion (el gráfico INTERACTIVO de "Contribución por Percentil" que
el usuario ve en la pestaña de gráficos) implementa el mismo algoritmo de
"contribución marginal por percentil" que _build_marginal_contribution
(usado por el export a IA), pero SIN el fix del bug #26 (Ronda 1).

Para calcular la "contribución marginal en el percentil X", la función
construye una ventana [percentil(pct-2.5), percentil(pct+2.5)] y toma las
simulaciones cuya pérdida total cae en ese rango. Cuando hay una masa
puntual grande en 0 (frecuente en riesgo operacional de baja frecuencia:
la mayoría de los años sin pérdida), el límite inferior de la ventana para
percentiles altos (P99) puede caer dentro de esa masa y quedar en 0. Como
las pérdidas nunca son negativas, la máscara ">= 0" termina incluyendo
TODAS las simulaciones (no solo las cercanas al percentil objetivo), y la
"contribución en P99" que el usuario ve en el gráfico colapsa a ser casi
idéntica a la contribución promedio general — subestimando la contribución
real del evento dominante en la cola hasta ~30x, según el hallazgo
original.

_build_marginal_contribution ya fue corregido para este caso (excluir del
rango las simulaciones en cero cuando el percentil objetivo es positivo).
Este test aplica el mismo escenario reproducible a
actualizar_grafico_contribucion (invocada de forma headless, sin depender
de una ventana Qt real: solo necesita los atributos que la función
efectivamente usa) y verifica que las barras dibujadas para P99 ya no
sean iguales a las de la Media.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np
from matplotlib.figure import Figure

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


print("=" * 70)
print("BUG ALTO #8: Contribución por Percentil (gráfico) - recurrencia CVaR")
print("=" * 70)


class _FakeCombo:
    def __init__(self, index, text):
        self._index = index
        self._text = text

    def currentIndex(self):
        return self._index

    def currentText(self):
        return self._text


class _FakeCanvas:
    def draw_idle(self):
        pass

    def clear_tooltip_data(self, ax):
        # Fix bug alto #11 (QA ronda 2): actualizar_grafico_contribucion
        # ahora limpia los tooltips previos del eje antes de redibujar.
        pass

    def add_tooltip_data(self, *args, **kwargs):
        pass


def _construir_self(perdidas_totales, perdidas_por_evento, eventos, idx_combo, texto_combo):
    fake_self = type('FakeApp', (), {})()
    fake_self.resultados_simulacion = {
        'perdidas_totales': perdidas_totales,
        'perdidas_por_evento': perdidas_por_evento,
        'eventos_riesgo': eventos,
    }
    fake_self.combo_percentil_contrib = _FakeCombo(idx_combo, texto_combo)
    fake_self.fig_contribucion = Figure()
    fake_self.ax_contribucion = fake_self.fig_contribucion.add_subplot(111)
    fake_self.canvas_contribucion = _FakeCanvas()
    return fake_self


def _leer_barras(fake_self):
    """Extrae {nombre_evento: contribucion} de las barras dibujadas."""
    ax = fake_self.ax_contribucion
    etiquetas = [t.get_text() for t in ax.get_yticklabels()]
    anchos = [bar.get_width() for bar in ax.patches]
    return dict(zip(etiquetas, anchos))


rng = np.random.default_rng(42)
N = 100_000
tail_idx = rng.choice(N, size=int(0.03 * N), replace=False)

perdidas_evento_A = np.zeros(N)
perdidas_evento_B = np.zeros(N)
# En la cola (3% de los años), el Evento A domina la pérdida; el Evento B
# aporta una fracción menor pero también presente.
perdidas_evento_A[tail_idx] = rng.uniform(1_000_000, 5_000_000, size=len(tail_idx))
perdidas_evento_B[tail_idx] = rng.uniform(10_000, 50_000, size=len(tail_idx))
perdidas_totales = perdidas_evento_A + perdidas_evento_B

eventos = [{'id': 'a', 'nombre': 'EventoA'}, {'id': 'b', 'nombre': 'EventoB'}]
perdidas_por_evento = [perdidas_evento_A, perdidas_evento_B]

# Media (índice de combo 0)
fake_self_media = _construir_self(perdidas_totales, perdidas_por_evento, eventos, 0, "Media")
RLB.RiskLabApp.actualizar_grafico_contribucion(fake_self_media)
barras_media = _leer_barras(fake_self_media)
check(len(barras_media) > 0, f"El gráfico de Media dibuja barras (obtenido: {barras_media})")

# P99 (índice de combo 5, ver percentiles_map en actualizar_grafico_contribucion)
fake_self_p99 = _construir_self(perdidas_totales, perdidas_por_evento, eventos, 5, "P99")
RLB.RiskLabApp.actualizar_grafico_contribucion(fake_self_p99)
barras_p99 = _leer_barras(fake_self_p99)
check(len(barras_p99) > 0, f"El gráfico de P99 dibuja barras (obtenido: {barras_p99})")

contrib_media_a = barras_media.get('EventoA', 0.0)
contrib_p99_a = barras_p99.get('EventoA', 0.0)

check(contrib_p99_a != contrib_media_a,
      f"Bug alto #8: la contribución de EventoA en P99 (${contrib_p99_a:,.0f}) ya NO es "
      f"idéntica a la de la Media (${contrib_media_a:,.0f})")

check(contrib_p99_a > contrib_media_a * 10,
      f"La contribución de EventoA en P99 (${contrib_p99_a:,.0f}) es sustancialmente mayor "
      f"a la de la Media (${contrib_media_a:,.0f}), reflejando que la cola está dominada "
      f"por sus pérdidas de $1M-$5M")

check(contrib_p99_a > 500_000,
      f"La contribución de EventoA en P99 (${contrib_p99_a:,.0f}) refleja la magnitud real "
      f"de la cola (millones), no la media diluida por el 97% de años en cero")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
