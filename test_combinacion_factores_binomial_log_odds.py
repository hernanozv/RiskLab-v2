"""
test_combinacion_factores_binomial_log_odds.py
==================================================

Regresion para bug medio #15 (QA ronda 2): para eventos Binomial/
Bernoulli/Beta, los factores ESTÁTICOS de ajuste se combinaban de forma
distinta según si el evento tenía, además, al menos un factor
ESTOCÁSTICO presente:

  - Rama "pura estática" (ningún factor estocástico): los shifts en
    escala log-odds de cada factor se acumulan ADITIVAMENTE
    (ajustar_probabilidad_por_factores, en log_odds_utils.py).
  - Rama "mezclada" (al menos un factor estocástico presente): los
    factores estáticos se acumulaban MULTIPLICATIVAMENTE en
    factores_vector junto con el/los factor(es) estocástico(s), y luego
    aplicar_factor_a_probabilidad_vec convertía el PRODUCTO final en un
    único shift (factor-1).

Como Σ(fi-1) ≠ Π(fi)-1 para 2 o más factores estáticos, el MISMO
conjunto de controles daba un resultado distinto según hubiera o no
OTRO factor estocástico (aunque ese estocástico no tuviera ningún efecto
real). Esto ya estaba señalado como "limitación conocida" en un
comentario del propio código, pero cambiaba el resultado real de la
simulación.

El fix hace que, para Binomial/Bernoulli/Beta, los factores estáticos
en la rama mezclada también se acumulen ADITIVAMENTE (mismo criterio que
la rama pura), y solo el efecto del/los factor(es) estocástico(s) se
combine multiplicativamente entre simulaciones (ya que es
inherentemente aleatorio por simulación). Para Poisson/Poisson-Gamma no
cambia nada: ahí el factor sigue escalando λ multiplicativamente, que es
el comportamiento correcto.

Este test compara, con un evento Bernoulli con 2 factores estáticos
(-30% y -20%): (a) sin ningún factor estocástico (rama pura) vs (b) con
un factor estocástico "neutro" (confiabilidad=100%, sin reducción real)
agregado al mismo evento (rama mezclada). Antes del fix, (a) y (b) daban
resultados distintos (~37.7% vs ~39.2% de probabilidad de ocurrencia,
un salto de ~1.5 puntos porcentuales solo por la presencia del
estocástico neutro); después del fix, deben ser prácticamente iguales.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np
from scipy.special import expit

from test_robustez_simulacion import (
    _build_evento, _simular, assert_close_rel,
    _factor_estatico, _factor_estocastico,
)

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
print("BUG MEDIO #15: combinación log-odds de factores estáticos+estocásticos")
print("=" * 70)

PROB_BASE = 0.5
IMPACTO_1 = -30
IMPACTO_2 = -20

sev_params = {'minimo': None, 'mas_probable': None, 'maximo': None,
              'input_method': 'direct', 'params_direct': {'mean': 1000, 'std': 100}}

# --- Rama pura estática: 2 factores estáticos, sin ningún estocástico ---
evento_puro = _build_evento(
    'e1', 'Puro', 3, {'probabilidad_exito': PROB_BASE}, 2, sev_params,
    factores_ajuste=[
        _factor_estatico(impacto_freq=IMPACTO_1, nombre='C1'),
        _factor_estatico(impacto_freq=IMPACTO_2, nombre='C2'),
    ]
)

# --- Rama mezclada: los MISMOS 2 factores estáticos + un estocástico
#     "neutro" (confiabilidad=100%, reduccion_efectiva=0, reduccion_fallo=0)
#     que no tiene ningún efecto real por sí mismo, pero activa
#     tiene_estocasticos=True y por lo tanto la rama "mezclada" del motor. ---
evento_mezclado = _build_evento(
    'e1', 'Mezclado', 3, {'probabilidad_exito': PROB_BASE}, 2, sev_params,
    factores_ajuste=[
        _factor_estatico(impacto_freq=IMPACTO_1, nombre='C1'),
        _factor_estatico(impacto_freq=IMPACTO_2, nombre='C2'),
        _factor_estocastico(confiabilidad=100, reduccion_efectiva=0, reduccion_fallo=0, nombre='Neutro'),
    ]
)

N = 300_000
_, freq_puro, _, _ = _simular([evento_puro], num_sims=N, seed=500)
_, freq_mezclado, _, _ = _simular([evento_mezclado], num_sims=N, seed=500)

p_obs_puro = freq_puro.mean()
p_obs_mezclado = freq_mezclado.mean()

# Valor teórico esperado (ambas ramas deben coincidir tras el fix): suma
# aditiva de los shifts en escala log-odds.
shift_total = IMPACTO_1 / 100.0 + IMPACTO_2 / 100.0
p_teorico = float(expit(shift_total))  # logit(0.5)=0, asi que logit(p)=shift_total

# Valor teórico de la rama mezclada tal como se comportaba ANTES del fix
# (combinación multiplicativa de los mismos 2 factores estáticos):
# factor = (1+I1/100)*(1+I2/100), shift = factor-1.
factor_bug = (1 + IMPACTO_1 / 100.0) * (1 + IMPACTO_2 / 100.0)
p_teorico_bug = float(expit(factor_bug - 1.0))

print(f"  p_teorico (shift aditivo, correcto) = {p_teorico:.4f}")
print(f"  p_teorico_bug (combinación pre-fix) = {p_teorico_bug:.4f}")
print(f"  p_observado rama pura                = {p_obs_puro:.4f}")
print(f"  p_observado rama mezclada            = {p_obs_mezclado:.4f}")

# Confirmar que el escenario elegido realmente separa ambas hipótesis con
# margen suficiente frente al ruido de muestreo esperado (N=300k).
check(abs(p_teorico - p_teorico_bug) > 0.01,
      f"Precondición: la diferencia teórica entre combinación aditiva "
      f"({p_teorico:.4f}) y multiplicativa ({p_teorico_bug:.4f}) es "
      f"suficientemente grande para no confundirse con ruido de muestreo")

check(abs(p_obs_puro - p_teorico) < 0.01,
      f"Rama pura estática coincide con el shift aditivo teórico "
      f"(obtenido={p_obs_puro:.4f}, esperado={p_teorico:.4f})")

check(abs(p_obs_mezclado - p_teorico) < 0.01,
      f"Bug medio #15: rama mezclada (con estocástico neutro) también coincide "
      f"con el shift aditivo teórico, igual que la rama pura, en vez de "
      f"acercarse al valor de la combinación multiplicativa pre-fix "
      f"(obtenido={p_obs_mezclado:.4f}, teorico correcto={p_teorico:.4f}, "
      f"teorico pre-fix={p_teorico_bug:.4f})")

assert_close_rel(p_obs_mezclado, p_obs_puro, tol_rel=0.02,
                 label="Bug medio #15: rama pura y rama mezclada dan el mismo resultado "
                      "para el mismo conjunto de factores estáticos")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
