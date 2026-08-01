"""
Regresión permanente para 3 bugs críticos corregidos en el motor de
simulación y en el cálculo de métricas de riesgo:

1. Período de retorno: se calculaba como 1/(prob_exceder * eventos_por_año)
   en vez de 1/prob_exceder (prob_exceder ya es una probabilidad anual).
   Producía errores de 5-15x en "Calendario de Riesgo" y en el export JSON.

2. CVaR/OpVaR (Expected Shortfall 99% y tail_analysis P80): cuando el
   percentil usado como umbral es 0 (eventos raros donde >=1% o >=20% de
   las simulaciones no tienen pérdida), filtrar con `>=` incluye TODA la
   distribución (las pérdidas nunca son negativas), colapsando la media
   condicional a la media incondicional. Subestimaba el riesgo real hasta
   ~100-200x. Se corrigió centralizando el cálculo en
   `media_cola_condicional()`, que filtra estrictamente `>`.

3. Beta-Bernoulli (freq_opcion=5) con factores de ajuste ESTÁTICOS: el
   código llamaba a `beta(a=alpha_ajustado, b=beta_ajustado)` esperando
   invocar `scipy.stats.beta`, pero dentro de la misma función
   `generar_lda_con_secuencialidad` la rama de Poisson-Gamma (freq_opcion=4)
   asigna una variable local `beta = mu / (sigma ** 2)`. Por las reglas de
   scope de Python, cualquier asignación a un nombre en una función lo
   vuelve local en TODA la función, así que `beta(...)` lanzaba
   UnboundLocalError. Esto quedaba enmascarado por un `except:` genérico
   que caía a un Bernoulli con p FIJO en lugar del Beta-Bernoulli con
   incertidumbre sobre p (el evento SÍ disparaba, pero perdiendo el modelo
   de incertidumbre paramétrica pretendido). Se corrigió usando la clase
   `BetaFrequencyDistribution` ya existente en el código, que no colisiona
   con el nombre local `beta`.
"""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import Risk_Lab_Beta as RLB
from Risk_Lab_Beta import (
    RiskLabApp,
    media_cola_condicional,
    generar_lda_con_secuencialidad,
    generar_distribucion_frecuencia,
    generar_distribucion_severidad,
    _UMBRALES_RIESGO_USD,
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


def _simular(eventos, num_sims=20_000, seed=42):
    rng = np.random.default_rng(seed)
    return generar_lda_con_secuencialidad(eventos, num_simulaciones=num_sims, rng=rng)


# ==============================================================================
# BUG 1: Período de retorno = 1/prob_exceder (no debe multiplicarse por
# eventos_por_año)
# ==============================================================================
print("\n" + "=" * 70)
print("BUG 1: Período de retorno")
print("=" * 70)

N = 100_000
umbral_bajo = _UMBRALES_RIESGO_USD["bajo"]
n_exceed = int(0.05 * N)
perdidas = np.zeros(N)
perdidas[:n_exceed] = umbral_bajo * 2
frecuencias_10 = np.full(N, 10.0)
frecuencias_2 = np.full(N, 2.0)

resultado_10 = RiskLabApp._build_calendar_periods(None, perdidas, frecuencias_10)
resultado_2 = RiskLabApp._build_calendar_periods(None, perdidas, frecuencias_2)
nivel_10 = next(n for n in resultado_10["niveles"] if n["nivel"] == "BAJO")
nivel_2 = next(n for n in resultado_2["niveles"] if n["nivel"] == "BAJO")

check(abs(nivel_10["periodo_retorno_años"] - 20.0) < 0.5,
      f"periodo_retorno_años ≈ 20 (1/0.05) con eventos_por_año=10: "
      f"actual={nivel_10['periodo_retorno_años']}")
check(nivel_10["periodo_retorno_años"] == nivel_2["periodo_retorno_años"],
      "periodo_retorno_años es independiente de eventos_por_año (no debe "
      "cambiar al variar la frecuencia de eventos individuales)")
check(resultado_10["frecuencia_eventos_por_año_esperada"] == 10.0,
      "frecuencia_eventos_por_año_esperada se sigue reportando correctamente")


# ==============================================================================
# BUG 2: CVaR/OpVaR con VaR99=0 (evento raro) no debe colapsar a la media
# incondicional
# ==============================================================================
print("\n" + "=" * 70)
print("BUG 2: CVaR/OpVaR cuando VaR99=0")
print("=" * 70)

rng = np.random.default_rng(123)
N2 = 100_000
n_positivos = int(0.005 * N2)
perdidas_raras = np.zeros(N2)
perdidas_raras[:n_positivos] = rng.lognormal(mean=np.log(10_000_000), sigma=0.3, size=n_positivos)
rng.shuffle(perdidas_raras)

var_99 = float(np.percentile(perdidas_raras, 99))
media_incondicional = perdidas_raras.mean()
media_condicional_real = perdidas_raras[perdidas_raras > 0].mean()

check(var_99 == 0.0, "Escenario de prueba logra VaR99=0 (evento raro)")

opvar = media_cola_condicional(perdidas_raras, var_99)
check(abs(opvar - media_condicional_real) < 1.0,
      f"media_cola_condicional da la media condicional real "
      f"(${media_condicional_real:,.0f}), no la incondicional (${media_incondicional:,.0f})")
check(opvar > media_incondicional * 50,
      f"CVaR corregido es >>50x la media incondicional (evidencia de que ya "
      f"no colapsa al caso degenerado): ratio={opvar/media_incondicional:.0f}x")

# Caso degenerado: todas las pérdidas son cero
opvar_cero = media_cola_condicional(np.zeros(10_000), 0.0)
check(opvar_cero == 0.0, "Caso degenerado (todas las pérdidas=0) devuelve 0 sin crashear")

# Caso normal: VaR99 > 0, el fix no debe alterar el resultado
perdidas_normales = rng.lognormal(mean=np.log(1_000_000), sigma=0.5, size=50_000)
var_99_normal = float(np.percentile(perdidas_normales, 99))
opvar_nuevo = media_cola_condicional(perdidas_normales, var_99_normal)
opvar_viejo = perdidas_normales[perdidas_normales >= var_99_normal].mean()
check(abs(opvar_nuevo - opvar_viejo) / opvar_viejo < 0.01,
      "Caso normal (VaR99>0, distribución continua): el fix no cambia el resultado")

# _calc_var_opvar (usado en el export JSON) debe usar el mismo helper
calc_var_opvar = None
for name in dir(RLB):
    obj = getattr(RLB, name)
    if isinstance(obj, type) and hasattr(obj, '_calc_var_opvar'):
        calc_var_opvar = obj._calc_var_opvar
        break
check(calc_var_opvar is not None, "Se encuentra _calc_var_opvar en el módulo")
if calc_var_opvar is not None:
    resultado_json = calc_var_opvar(perdidas_raras)
    check(abs(resultado_json['expected_shortfall_99'] - media_condicional_real) < 1.0,
          "_calc_var_opvar (export JSON) usa el cálculo corregido")


# ==============================================================================
# BUG 3: Beta-Bernoulli (freq_opcion=5) con factor de ajuste ESTÁTICO
# ==============================================================================
print("\n" + "=" * 70)
print("BUG 3: Beta-Bernoulli con factor estático")
print("=" * 70)


def _build_evento_beta_static(beta_mas_probable, beta_minimo, beta_maximo, impacto_freq,
                               con_factor=True):
    alpha0, beta0 = 3.0, 7.0
    dist_freq = generar_distribucion_frecuencia(5, beta_params=(alpha0, beta0))
    dist_sev = generar_distribucion_severidad(3, minimo=100.0, mas_probable=500.0, maximo=1000.0)
    evento = {
        'id': 'e1', 'nombre': 'BetaStatic', 'freq_opcion': 5, 'sev_opcion': 3,
        'dist_frecuencia': dist_freq, 'dist_severidad': dist_sev, 'activo': True,
        'beta_alpha': alpha0, 'beta_beta': beta0,
        'beta_mas_probable': beta_mas_probable, 'beta_minimo': beta_minimo,
        'beta_maximo': beta_maximo, 'beta_confianza': 90,
        'sev_input_method': 'min_mode_max', 'sev_params_direct': {},
        'sev_minimo': 100.0, 'sev_mas_probable': 500.0, 'sev_maximo': 1000.0,
    }
    if con_factor:
        evento['factores_ajuste'] = [{
            'nombre': 'ControlEstatico', 'tipo_modelo': 'estatico', 'activo': True,
            'afecta_frecuencia': True, 'impacto_porcentual': impacto_freq,
            'afecta_severidad': False, 'impacto_severidad_pct': 0,
            'tipo_severidad': 'porcentual',
        }]
    return evento


evento_sin_factor = _build_evento_beta_static(30.0, 5.0, 80.0, impacto_freq=0, con_factor=False)
_, freq_sin, _, _ = _simular([evento_sin_factor], seed=1)
check(freq_sin.mean() > 0.10,
      f"Control (sin factores): frecuencia media = {freq_sin.mean():.4f} (esperado ~0.30)")

evento_agravante = _build_evento_beta_static(30.0, 5.0, 80.0, impacto_freq=20)
_, freq_agravante, _, freq_por_evento_agravante = _simular([evento_agravante], seed=2)
check(freq_agravante.mean() > 0.05,
      f"Con factor estático +20%: frecuencia media = {freq_agravante.mean():.4f} "
      f"(el bug original producía 0.0000 -> evento nunca disparaba)")

evento_mitigante = _build_evento_beta_static(30.0, 5.0, 80.0, impacto_freq=-50)
_, freq_mitigante, _, _ = _simular([evento_mitigante], seed=3)
check(freq_mitigante.mean() > 0.02, "Con factor estático -50%: el evento aún dispara ocasionalmente")
check(freq_mitigante.mean() < freq_sin.mean(), "Factor -50% reduce la frecuencia vs. el control")

valores_unicos = np.unique(freq_por_evento_agravante[0])
check(set(valores_unicos.tolist()).issubset({0, 1}),
      f"Las muestras de Beta-Bernoulli son estrictamente binarias (0/1): {valores_unicos}")


# ==============================================================================
# RESUMEN
# ==============================================================================
print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
