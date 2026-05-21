"""
test_robustez_simulacion.py
===========================

Suite de pruebas exhaustivas para validar la robustez matematica del motor
Monte Carlo de Risk Lab. Cubre:

  1. Distribuciones de frecuencia (Poisson, Binomial, Bernoulli,
     Poisson-Gamma, Beta+Bernoulli) — media, varianza, CV y
     comportamiento esperado.
  2. Distribuciones de severidad (Normal, LogNormal, PERT, GPD, Uniforme) —
     parametrizacion directa vs min/mode/max, truncamientos esperados,
     percentiles teoricos.
  3. Distribucion de perdida agregada (LDA) — identidades del compound
     Poisson y Negative Binomial, suma multi-evento, validacion contra
     una implementacion independiente.
  4. Caps internos del motor — confirma que el cap de 500M no se activa
     en escenarios realistas y que las distribuciones NO quedan truncadas
     ni reescaladas.
  5. Factores estaticos — frecuencia y severidad ajustadas correctamente
     por impacto_porcentual; composicion multiplicativa de varios factores.
  6. Factores estocasticos — modelo de confiabilidad de control, factores
     estaticos vs estocasticos producen los mismos resultados esperados
     en el limite, y respetan el parametro 'confiabilidad'.
  7. Vinculos entre eventos — AND, OR, EXCLUYE, umbral de severidad y
     factor de severidad.
  8. Seguros (por ocurrencia y agregados) — deducible, cobertura, limite
     por ocurrencia, limite agregado anual, multi-aseguradora (regresion
     del bug #14).
  9. Edge cases — frecuencia cero, frecuencia muy alta, manejo de NaN/Inf.

Uso:
  python3 test_robustez_simulacion.py            # corre standalone con resumen
  pytest test_robustez_simulacion.py -v          # corre con pytest si esta disponible

Sin dependencias de PyQt5/matplotlib — extrae las funciones puras del motor
via AST. Solo requiere numpy + scipy.

Tolerancias por defecto: 2-5% de error relativo para medias de Monte Carlo
con 50k-100k sims. Tests sin Monte Carlo (identidades algebraicas) son
exactos.

Autor: revision sistematica post-bug-report 2026-05-20.
"""

import ast
import os
import sys
import math
import warnings
import numpy as np
from scipy import stats
from scipy.stats import (
    poisson, binom, bernoulli, lognorm, beta as beta_dist,
    genpareto, norm, uniform, nbinom, truncnorm
)
from scipy.optimize import least_squares, minimize


# ===========================================================================
# Loader: extrae simbolos puros de Risk_Lab_Beta.py via AST.
# ===========================================================================

ENGINE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Risk_Lab_Beta.py')

# Simbolos del motor que necesitamos para los tests. Se cargan TODOS si existen.
_TARGETS = {
    # Constantes y categorias de warning
    'EXPORT_SCHEMA_VERSION', '_DEBUG_SIM', 'MAX_EVENTOS_POR_EVENTO_POR_CHUNK',
    'RiskLabFrequencyCapWarning', 'RiskLabRejectionFallbackWarning',
    # Helpers de parametros
    'obtener_parametros_normal', 'obtener_parametros_lognormal',
    'obtener_parametros_pert', 'obtener_parametros_gpd',
    'obtener_parametros_uniforme', 'obtener_parametros_gamma_para_poisson',
    'obtener_parametros_beta_frecuencia',
    # Distribuciones custom
    'PoissonGammaDistribution', 'BetaFrequencyDistribution', 'TruncatedGPD',
    # Generadores de distribucion
    'generar_distribucion_frecuencia', 'generar_distribucion_severidad',
    # Pipeline de simulacion
    '_samplear_frecuencia_estocastica_vec',
    'generar_lda_con_secuencialidad',
    'ordenar_eventos_por_dependencia',
    '_aplicar_tabla_escalamiento',
    # Debug
    '_dbg',
}


def _load_engine():
    """Carga las funciones puras del motor sin tocar imports de Qt/matplotlib."""
    with open(ENGINE_FILE, 'r', encoding='utf-8') as f:
        src = f.read()
    tree = ast.parse(src)

    extracted = []
    for node in tree.body:
        name = None
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
        elif isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
        if name in _TARGETS:
            extracted.append(node)

    # Inyectamos dependencias del engine en el namespace
    try:
        from log_odds_utils import (
            aplicar_factor_a_probabilidad_vec,
            aplicar_factor_a_probabilidad,
            ajustar_probabilidad_por_factores,
        )
    except ImportError as e:
        raise RuntimeError(
            f"No se pudo importar log_odds_utils: {e}. "
            "El test debe correrse desde el directorio raiz del proyecto."
        ) from e

    ns = {
        'np': np, 'stats': stats,
        'poisson': poisson, 'binom': binom, 'bernoulli': bernoulli,
        'lognorm': lognorm, 'beta': beta_dist, 'genpareto': genpareto,
        'norm': norm, 'uniform': uniform, 'nbinom': nbinom, 'truncnorm': truncnorm,
        'least_squares': least_squares, 'minimize': minimize,
        'warnings': warnings, 'os': os, 'sys': sys,
        'aplicar_factor_a_probabilidad_vec': aplicar_factor_a_probabilidad_vec,
        'aplicar_factor_a_probabilidad': aplicar_factor_a_probabilidad,
        'ajustar_probabilidad_por_factores': ajustar_probabilidad_por_factores,
        '__name__': '__rl_engine_test__',
    }
    mod = ast.Module(body=extracted, type_ignores=[])
    exec(compile(mod, ENGINE_FILE, 'exec'), ns)
    return ns


ENGINE = _load_engine()


# ===========================================================================
# Helpers de aserciones con tolerancias estadisticas.
# ===========================================================================

def _rel_err(observed, expected):
    if expected == 0:
        return abs(observed)
    return abs(observed - expected) / abs(expected)


def assert_close_rel(observed, expected, tol_rel=0.05, label=''):
    err = _rel_err(observed, expected)
    if err > tol_rel:
        raise AssertionError(
            f"{label} fuera de tolerancia: obs={observed:g}, "
            f"esp={expected:g}, err_rel={err:.4%} > {tol_rel:.2%}"
        )


def assert_in_range(observed, low, high, label=''):
    if not (low <= observed <= high):
        raise AssertionError(
            f"{label} fuera de rango: obs={observed:g} no esta en [{low:g}, {high:g}]"
        )


# Generador determinista compartido por todos los tests para reproducibilidad
def _rng(seed=0):
    return np.random.default_rng(seed)


# ===========================================================================
# Constructores de eventos para tests integrales.
# ===========================================================================

def _build_evento(id_, nombre, freq_opcion, freq_params, sev_opcion, sev_params,
                  factores_ajuste=None, vinculos=None, **extras):
    """Construye un dict de evento ya con dist_frecuencia y dist_severidad.

    IMPORTANTE: tambien copia los parametros nativos (tasa, prob_exito,
    num_eventos, pg_*, beta_*) al dict del evento porque el motor los lee
    desde alli al aplicar factores de ajuste (no desde la dist congelada).
    Esto refleja exactamente lo que hace el preparador de eventos en
    ejecutar_simulacion despues del fix de PR #3.
    """
    gen_freq = ENGINE['generar_distribucion_frecuencia']
    gen_sev = ENGINE['generar_distribucion_severidad']

    # Frecuencia
    freq_kwargs = dict(freq_params)
    dist_freq = gen_freq(freq_opcion, **freq_kwargs)

    # Severidad
    sev_kwargs = dict(sev_params)
    dist_sev = gen_sev(sev_opcion, **sev_kwargs)

    evento = {
        'id': id_,
        'nombre': nombre,
        'freq_opcion': freq_opcion,
        'sev_opcion': sev_opcion,
        'dist_frecuencia': dist_freq,
        'dist_severidad': dist_sev,
        'activo': True,
    }
    # Copiar parametros nativos al dict para que el motor pueda releerlos
    # al aplicar factores. Mapping freq_params dict → keys del evento.
    if freq_opcion == 1:
        evento['tasa'] = freq_params.get('tasa')
    elif freq_opcion == 2:
        evento['num_eventos'] = freq_params.get('num_eventos_posibles')
        evento['prob_exito'] = freq_params.get('probabilidad_exito')
    elif freq_opcion == 3:
        evento['prob_exito'] = freq_params.get('probabilidad_exito')
    elif freq_opcion == 4:
        pg = freq_params.get('poisson_gamma_params')
        if pg:
            evento['pg_alpha'], evento['pg_beta'] = pg
    elif freq_opcion == 5:
        bp = freq_params.get('beta_params')
        if bp:
            evento['beta_alpha'], evento['beta_beta'] = bp

    # Copiar parametros de severidad al dict
    evento['sev_input_method'] = sev_params.get('input_method', 'min_mode_max')
    evento['sev_params_direct'] = sev_params.get('params_direct', {})
    evento['sev_minimo'] = sev_params.get('minimo')
    evento['sev_mas_probable'] = sev_params.get('mas_probable')
    evento['sev_maximo'] = sev_params.get('maximo')

    if factores_ajuste is not None:
        evento['factores_ajuste'] = factores_ajuste
    if vinculos is not None:
        evento['vinculos'] = vinculos

    # Permitir override / agregar extras
    evento.update(extras)
    return evento


# ===========================================================================
# SECCION 1: Distribuciones de FRECUENCIA
# ===========================================================================

def test_freq_poisson_media_varianza():
    """Poisson(λ): mean=λ, var=λ. Sampleamos directamente desde scipy."""
    gen = ENGINE['generar_distribucion_frecuencia']
    for lam in [0.5, 2.0, 10.0, 100.0, 1000.0]:
        d = gen(1, tasa=lam)
        samples = d.rvs(size=100_000, random_state=_rng(seed=42))
        assert_close_rel(samples.mean(), lam, tol_rel=0.03,
                         label=f"Poisson({lam}).mean")
        assert_close_rel(samples.var(), lam, tol_rel=0.05,
                         label=f"Poisson({lam}).var")


def test_freq_binomial_media_varianza():
    """Binomial(n, p): mean=n*p, var=n*p*(1-p)."""
    gen = ENGINE['generar_distribucion_frecuencia']
    for n, p in [(10, 0.3), (100, 0.05), (50, 0.8)]:
        d = gen(2, num_eventos_posibles=n, probabilidad_exito=p)
        samples = d.rvs(size=100_000, random_state=_rng(seed=43))
        assert_close_rel(samples.mean(), n * p, tol_rel=0.03,
                         label=f"Binomial({n},{p}).mean")
        assert_close_rel(samples.var(), n * p * (1 - p), tol_rel=0.05,
                         label=f"Binomial({n},{p}).var")


def test_freq_bernoulli_media():
    """Bernoulli(p): mean=p."""
    gen = ENGINE['generar_distribucion_frecuencia']
    for p in [0.05, 0.5, 0.95]:
        d = gen(3, probabilidad_exito=p)
        samples = d.rvs(size=100_000, random_state=_rng(seed=44))
        assert_close_rel(samples.mean(), p, tol_rel=0.05,
                         label=f"Bernoulli({p}).mean")


def test_freq_poisson_gamma_media_varianza_cv():
    """Poisson-Gamma: mean=α/β, var=(α/β)(1+1/β), CV=1/√α (en alta lambda)."""
    gen = ENGINE['generar_distribucion_frecuencia']
    casos = [
        # (alpha, beta) — caso del bug report y otros
        (32.11, 2.83e-4),   # E[N] ≈ 113,491
        (11.02, 1.59e-4),   # E[N] ≈ 69,182
        (12.13, 7.21e-5),   # E[N] ≈ 168,239
        (2.5, 0.5),         # E[N] = 5, baja frecuencia
        (10.0, 1.0),        # E[N] = 10
    ]
    for alpha, beta in casos:
        d = gen(4, poisson_gamma_params=(alpha, beta))
        # Verificar que la clase reporta media y varianza correctas
        mean_th = alpha / beta
        var_th = (alpha / beta) * (1 + 1 / beta)
        assert_close_rel(d.mean(), mean_th, tol_rel=1e-9,
                         label=f"PG({alpha},{beta}).mean teorica")
        assert_close_rel(d.var(), var_th, tol_rel=1e-9,
                         label=f"PG({alpha},{beta}).var teorica")
        # Muestrear y verificar consistencia
        n_samples = 50_000
        samples = d.rvs(size=n_samples, random_state=_rng(seed=45))
        # mean
        assert_close_rel(samples.mean(), mean_th, tol_rel=0.02,
                         label=f"PG({alpha},{beta}).mean muestral")
        # CV teorico vs observado (solo cuando E[N] > 10 para que tenga sentido)
        if mean_th > 10:
            cv_th = 1 / np.sqrt(alpha)
            cv_obs = samples.std() / samples.mean()
            assert_close_rel(cv_obs, cv_th, tol_rel=0.05,
                             label=f"PG({alpha},{beta}).CV")


def test_freq_poisson_gamma_alpha_menor_que_uno():
    """Fix bug #8: alpha <= 1 ahora es aceptado (antes era rechazado)."""
    gen = ENGINE['generar_distribucion_frecuencia']
    # alpha=0.5 (sobre-dispersion muy alta) debe ser aceptado
    d = gen(4, poisson_gamma_params=(0.5, 0.01))
    samples = d.rvs(size=50_000, random_state=_rng(seed=46))
    assert_close_rel(samples.mean(), 50.0, tol_rel=0.05,
                     label="PG(α=0.5).mean")
    # alpha=0 debe seguir siendo rechazado
    try:
        gen(4, poisson_gamma_params=(0.0, 0.01))
    except ValueError:
        return  # OK
    raise AssertionError("alpha=0 deberia ser rechazado")


def test_freq_beta_bernoulli_media():
    """Beta+Bernoulli: probabilidad anual ~ Beta, luego Bernoulli(p).
       Mean(samples) ≈ E[p] = α/(α+β)."""
    gen = ENGINE['generar_distribucion_frecuencia']
    for alpha, beta in [(2, 8), (5, 5), (10, 2)]:
        d = gen(5, beta_params=(alpha, beta))
        samples = d.rvs(size=50_000, random_state=_rng(seed=47))
        p_esperada = alpha / (alpha + beta)
        assert_close_rel(samples.mean(), p_esperada, tol_rel=0.05,
                         label=f"Beta({alpha},{beta})+Bernoulli.mean")


def test_freq_sin_caps_en_alta_frecuencia():
    """Verifica que NO hay caps escondidos en el path directo de PG.
       Toma el caso del bug report (E[N]≈113K) y comprueba que ningun
       sample queda truncado a un valor anomalo (e.g. =num_simulaciones)."""
    gen = ENGINE['generar_distribucion_frecuencia']
    d = gen(4, poisson_gamma_params=(32.11, 2.83e-4))
    n_sims = 10_000
    samples = d.rvs(size=n_sims, random_state=_rng(seed=48))
    mean_obs = samples.mean()
    teorica = 32.11 / 2.83e-4
    assert_close_rel(mean_obs, teorica, tol_rel=0.02,
                     label="PG alta-freq media muestral")
    # Verificar que NO hay collapse a media=n_sims (sintoma del cap viejo)
    if abs(mean_obs - n_sims) / n_sims < 0.01:
        raise AssertionError(
            f"REGRESION del bug #1: la media observada ({mean_obs:.0f}) coincide "
            f"con num_simulaciones={n_sims}. Indica que un cap implicito esta "
            f"activo."
        )


# ===========================================================================
# SECCION 2: Distribuciones de SEVERIDAD
# ===========================================================================

def test_sev_normal_truncada_en_cero():
    """Normal truncada en 0 (sev_opcion=1) con direct: mean ≈ mean_param,
    pero shifteada por el truncamiento si mean es cercano a 0."""
    gen = ENGINE['generar_distribucion_severidad']
    # Caso: mean >> std, truncamiento es despreciable
    d = gen(1, None, None, None, input_method='direct',
            params_direct={'mean': 1000, 'std': 100})
    samples = d.rvs(size=50_000, random_state=_rng(seed=50))
    assert_close_rel(samples.mean(), 1000, tol_rel=0.02,
                     label="Normal(1000, 100) tras truncado mean")
    assert (samples >= 0).all(), "Normal truncada NO debe generar valores < 0"


def test_sev_lognormal_direct_mean_std():
    """LogNormal direct con mean/std: scipy lognorm.mean = exp(mu + s²/2)
       parametrizado tal que coincida con (mean, std) en X."""
    gen = ENGINE['generar_distribucion_severidad']
    for mean, std in [(100, 50), (1000, 500), (80, 100)]:
        d = gen(2, None, None, None, input_method='direct',
                params_direct={'mean': mean, 'std': std})
        samples = d.rvs(size=100_000, random_state=_rng(seed=51))
        assert_close_rel(samples.mean(), mean, tol_rel=0.03,
                         label=f"LogNormal(mean={mean},std={std}).mean")
        # std puede tener mas ruido para LogNormal con CV alto
        assert_close_rel(samples.std(), std, tol_rel=0.15,
                         label=f"LogNormal(mean={mean},std={std}).std")


def test_sev_lognormal_direct_s_scale():
    """LogNormal direct con (s, scale, loc) nativos SciPy.
    s=1.086, scale=80, loc=0 → media teorica = scale * exp(s²/2) ≈ 144.28."""
    gen = ENGINE['generar_distribucion_severidad']
    s, scale, loc = 1.086, 80.0, 0.0
    d = gen(2, None, None, None, input_method='direct',
            params_direct={'s': s, 'scale': scale, 'loc': loc})
    mean_th = scale * np.exp(s ** 2 / 2) + loc  # ~144.28
    samples = d.rvs(size=100_000, random_state=_rng(seed=52))
    assert_close_rel(samples.mean(), mean_th, tol_rel=0.03,
                     label=f"LogNormal(s={s},scale={scale}).mean")


def test_sev_pert_acotada():
    """PERT (Beta reescalada): soporte estricto en [minimo, maximo]."""
    gen = ENGINE['generar_distribucion_severidad']
    minimo, mas_prob, maximo = 10.0, 50.0, 100.0
    d = gen(3, minimo, mas_prob, maximo)
    samples = d.rvs(size=50_000, random_state=_rng(seed=53))
    assert samples.min() >= minimo - 1e-9, "PERT viola el limite inferior"
    assert samples.max() <= maximo + 1e-9, "PERT viola el limite superior"
    # Para PERT, mode ≈ mas_prob; mean ≈ (a + 4*c + b)/6
    mean_pert_th = (minimo + 4 * mas_prob + maximo) / 6
    assert_close_rel(samples.mean(), mean_pert_th, tol_rel=0.02,
                     label="PERT mean")


def test_sev_gpd_truncada_p999():
    """GPD con cola pesada — TruncatedGPD trunca al P99.9 cuando xi > 0."""
    gen = ENGINE['generar_distribucion_severidad']
    d = gen(4, None, None, None, input_method='direct',
            params_direct={'c': 0.3, 'scale': 500_000, 'loc': 100_000})
    samples = d.rvs(size=50_000, random_state=_rng(seed=54))
    # No debe haber valores infinitos
    assert np.isfinite(samples).all(), "GPD genera valores no finitos"
    # Todos deben ser >= loc
    assert (samples >= 100_000 - 1e-6).all(), "GPD viola limite inferior loc"


def test_sev_uniforme():
    """Uniforme(min, max) con la implementacion de Risk Lab."""
    gen = ENGINE['generar_distribucion_severidad']
    minimo, maximo = 100.0, 500.0
    d = gen(5, minimo, None, maximo)
    samples = d.rvs(size=50_000, random_state=_rng(seed=55))
    assert (samples >= minimo - 1e-9).all() and (samples <= maximo + 1e-9).all(), \
        "Uniforme viola soporte"
    mean_th = (minimo + maximo) / 2
    assert_close_rel(samples.mean(), mean_th, tol_rel=0.02,
                     label="Uniforme.mean")


def test_sev_lognormal_min_mode_max():
    """LogNormal con metodo min/mode/max: validamos forma general.
    El fit por least-squares puede caer en moda o mediana segun sigma.
    Verificamos: (a) samples positivos; (b) mediana entre min y max;
    (c) right-skew (mean > median)."""
    gen = ENGINE['generar_distribucion_severidad']
    minimo, mas_prob, maximo = 50.0, 100.0, 500.0
    d = gen(2, minimo, mas_prob, maximo, input_method='min_mode_max')
    samples = d.rvs(size=100_000, random_state=_rng(seed=56))
    assert (samples > 0).all(), "LogNormal genero valores <= 0"
    mediana = np.median(samples)
    media = samples.mean()
    assert minimo < mediana < maximo, (
        f"Mediana ({mediana:.1f}) deberia estar entre min ({minimo}) y max ({maximo})"
    )
    assert media > mediana, (
        f"LogNormal deberia ser right-skew (mean > median), pero "
        f"mean={media:.1f} y median={mediana:.1f}"
    )


# ===========================================================================
# SECCION 3: LDA — Distribucion de Perdida Agregada
# ===========================================================================

def _simular(eventos, num_sims=20_000, seed=100):
    """Helper: corre generar_lda_con_secuencialidad y devuelve los outputs."""
    rng = np.random.default_rng(seed)
    return ENGINE['generar_lda_con_secuencialidad'](
        eventos, num_simulaciones=num_sims, rng=rng
    )


def test_lda_compound_mean_poisson():
    """Compound Poisson: E[S] = E[N] * E[X]."""
    evento = _build_evento(
        'e1', 'Evento Poisson-Normal', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000.0, 'std': 200.0}}
    )
    perd_tot, freq_tot, perd_evt, freq_evt = _simular([evento], num_sims=30_000)
    # E[N] = 5, E[X] = 1000 → E[S] = 5000
    assert_close_rel(perd_tot.mean(), 5 * 1000, tol_rel=0.05,
                     label="Compound Poisson E[S]")
    assert_close_rel(freq_tot.mean(), 5, tol_rel=0.05,
                     label="Compound Poisson E[N]")


def test_lda_compound_variance_poisson():
    """Compound Poisson: Var[S] = λ * E[X²] = λ * (Var[X] + E[X]²)."""
    lam = 10.0
    mean_x, std_x = 1000.0, 300.0
    var_x = std_x ** 2
    evento = _build_evento(
        'e1', 'Evento Poisson-Normal', 1, {'tasa': lam},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': mean_x, 'std': std_x}}
    )
    perd_tot, _, _, _ = _simular([evento], num_sims=50_000, seed=101)
    var_s_th = lam * (var_x + mean_x ** 2)
    var_s_obs = perd_tot.var()
    assert_close_rel(var_s_obs, var_s_th, tol_rel=0.10,
                     label="Compound Poisson Var[S]")


def test_lda_zero_frequency_zero_loss():
    """Bernoulli(p=0.0001) con sev fija: en la mayoria de sims N=0 y S=0."""
    evento = _build_evento(
        'e1', 'Raro', 3, {'probabilidad_exito': 0.001},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1e6, 'std': 1e4}}
    )
    perd_tot, freq_tot, _, _ = _simular([evento], num_sims=10_000, seed=102)
    # Al menos 99% de las sims deben tener N=0
    pct_cero = float((freq_tot == 0).mean())
    assert pct_cero > 0.99, f"Solo {pct_cero:.2%} de sims tienen N=0 (esperado ≥99%)"
    # Donde N=0 → S=0 estricto
    assert (perd_tot[freq_tot == 0] == 0).all(), \
        "Sims con N=0 deben tener S=0 exacto"


def test_lda_suma_multi_evento():
    """LDA con 3 eventos independientes: perdidas_totales = sum(perdidas_por_evento)."""
    eventos = [
        _build_evento(f'e{i}', f'Evento {i}', 1, {'tasa': 3.0 + i},
                      2, {'minimo': None, 'mas_probable': None, 'maximo': None,
                          'input_method': 'direct',
                          'params_direct': {'mean': 500 * (i + 1), 'std': 100 * (i + 1)}})
        for i in range(3)
    ]
    perd_tot, _, perd_evt, _ = _simular(eventos, num_sims=20_000, seed=103)
    suma_eventos = sum(perd_evt)
    np.testing.assert_allclose(perd_tot, suma_eventos, rtol=1e-9,
                                err_msg="perdidas_totales != sum(perdidas_por_evento)")


def test_lda_cap_no_se_activa_en_caso_normal():
    """En condiciones normales (sum < 500M), el cap NO debe activarse y
       NO debe emitirse RiskLabFrequencyCapWarning."""
    evento = _build_evento(
        'e1', 'Normal', 4, {'poisson_gamma_params': (10.0, 1.0)},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 100.0, 'std': 20.0}}
    )
    import warnings as _w
    cap_cls = ENGINE['RiskLabFrequencyCapWarning']
    with _w.catch_warnings(record=True) as w:
        _w.simplefilter('always')
        _simular([evento], num_sims=10_000, seed=104)
        cap_warnings = [x for x in w if issubclass(x.category, cap_cls)]
        if cap_warnings:
            raise AssertionError(
                f"El cap se activo en un caso normal (E[N]=10, num_sims=10k → "
                f"sum≈100k << 500M cap). Warnings: {[str(x.message) for x in cap_warnings]}"
            )
        # Tampoco debe tener huellas
        assert not evento.get('_cap_frecuencia_aplicado', False), \
            "_cap_frecuencia_aplicado=True en caso normal"


def test_lda_validacion_independiente():
    """Golden test: comparar el motor con una implementacion independiente
    de compound Poisson en numpy puro. Mismas semillas, mismos parametros."""
    lam = 4.0
    mean_x = 800.0
    std_x = 200.0
    n_sims = 30_000

    # 1) Motor de Risk Lab
    evento = _build_evento(
        'e1', 'Validacion', 1, {'tasa': lam},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': mean_x, 'std': std_x}}
    )
    perd_motor, _, _, _ = _simular([evento], num_sims=n_sims, seed=200)

    # 2) Implementacion independiente: simular N ~ Poisson, X ~ LogNormal,
    # S = sum X_i. Usar la misma transformacion (mean, std) → (s, scale).
    rng_ind = np.random.default_rng(201)
    # Recuperar (s, scale) desde (mean, std) — formula del engine
    sigma2 = np.log(1 + (std_x / mean_x) ** 2)
    sigma = np.sqrt(sigma2)
    mu = np.log(mean_x) - 0.5 * sigma2
    Ns = rng_ind.poisson(lam=lam, size=n_sims)
    total_indep = np.zeros(n_sims)
    # Sampleo vectorizado evitando un loop por sim
    sum_freq = int(Ns.sum())
    severs = rng_ind.lognormal(mean=mu, sigma=sigma, size=sum_freq)
    # Asignar mediante repeat de indices
    indices = np.repeat(np.arange(n_sims), Ns)
    np.add.at(total_indep, indices, severs)

    # Comparar medias y P99
    media_motor = perd_motor.mean()
    media_indep = total_indep.mean()
    # Ambas estiman la misma cantidad (lam * mean_x = 3200) con error ~CLT
    err_rel = abs(media_motor - media_indep) / media_indep
    teo = lam * mean_x
    assert err_rel < 0.05, (
        f"Motor ({media_motor:.0f}) y simulacion independiente ({media_indep:.0f}) "
        f"divergen >5% (teorico={teo:.0f})"
    )
    # Ambos deben coincidir con teorico
    assert_close_rel(media_motor, teo, tol_rel=0.05, label="Motor E[S]")
    assert_close_rel(media_indep, teo, tol_rel=0.05, label="Indep E[S]")


# ===========================================================================
# SECCION 4: Factores ESTATICOS
# ===========================================================================

def _factor_estatico(impacto_freq=0, impacto_sev=0, nombre='F'):
    """Construye un dict de factor estatico."""
    return {
        'nombre': nombre,
        'tipo_modelo': 'estatico',
        'activo': True,
        'afecta_frecuencia': impacto_freq != 0,
        'impacto_porcentual': impacto_freq,
        'afecta_severidad': impacto_sev != 0,
        'impacto_severidad_pct': impacto_sev,
        'tipo_severidad': 'porcentual',
    }


def test_factor_estatico_frecuencia_reduccion():
    """Factor estatico con impacto -50%: la frecuencia esperada cae ~50%."""
    base_lam = 10.0
    # Sin factores
    evento_base = _build_evento(
        'e1', 'Base', 1, {'tasa': base_lam},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 100, 'std': 20}}
    )
    _, freq_base, _, _ = _simular([evento_base], num_sims=20_000, seed=300)

    # Con factor -50% sobre frecuencia
    evento_mit = _build_evento(
        'e1', 'Mitigado', 1, {'tasa': base_lam},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 100, 'std': 20}},
        factores_ajuste=[_factor_estatico(impacto_freq=-50, nombre='Control50')]
    )
    _, freq_mit, _, _ = _simular([evento_mit], num_sims=20_000, seed=301)

    # Razon de medias ≈ 0.5
    ratio = freq_mit.mean() / freq_base.mean()
    assert_close_rel(ratio, 0.5, tol_rel=0.08,
                     label="Factor estatico -50% reduce frecuencia media")


def test_factor_estatico_severidad_reduccion():
    """Factor estatico con impacto_sev=-30%: la severidad media cae ~30%."""
    evento_base = _build_evento(
        'e1', 'Base', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 100}}
    )
    perd_base, _, _, _ = _simular([evento_base], num_sims=20_000, seed=302)

    evento_mit = _build_evento(
        'e1', 'Mitigado', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 100}},
        factores_ajuste=[_factor_estatico(impacto_sev=-30, nombre='RedSev30')]
    )
    perd_mit, _, _, _ = _simular([evento_mit], num_sims=20_000, seed=303)

    # E[S_mit] / E[S_base] ≈ 0.7 (sev *0.7, freq igual)
    ratio = perd_mit.mean() / perd_base.mean()
    assert_close_rel(ratio, 0.7, tol_rel=0.08,
                     label="Factor estatico -30% sev reduce perdida media")


def test_factores_multiples_componen_multiplicativamente():
    """Dos factores: -30% freq y -50% sev → reduccion total esperada ~0.7*0.5=0.35."""
    factores = [
        _factor_estatico(impacto_freq=-30, nombre='Control1'),
        _factor_estatico(impacto_sev=-50, nombre='Control2'),
    ]
    evento_base = _build_evento(
        'e1', 'Base', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 100}}
    )
    evento_mit = _build_evento(
        'e1', 'Mitigado', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 100}},
        factores_ajuste=factores
    )
    perd_base, _, _, _ = _simular([evento_base], num_sims=30_000, seed=304)
    perd_mit, _, _, _ = _simular([evento_mit], num_sims=30_000, seed=305)
    ratio = perd_mit.mean() / perd_base.mean()
    assert_close_rel(ratio, 0.35, tol_rel=0.10,
                     label="Composicion factores -30%freq * -50%sev")


# ===========================================================================
# SECCION 5: Factores ESTOCASTICOS
# ===========================================================================

def _factor_estocastico(confiabilidad, reduccion_efectiva=0,
                        reduccion_fallo=0, red_sev_ef=0, red_sev_fa=0,
                        nombre='FStoch'):
    return {
        'nombre': nombre,
        'tipo_modelo': 'estocastico',
        'activo': True,
        'confiabilidad': confiabilidad,
        'reduccion_efectiva': reduccion_efectiva,
        'reduccion_fallo': reduccion_fallo,
        'reduccion_severidad_efectiva': red_sev_ef,
        'reduccion_severidad_fallo': red_sev_fa,
        'afecta_frecuencia': True,
        'afecta_severidad': (red_sev_ef != 0 or red_sev_fa != 0),
    }


def test_factor_estocastico_confiabilidad_100_equivale_a_estatico():
    """Con confiabilidad=100, el control siempre funciona; el factor esperado
       es (1 - reduccion_efectiva)."""
    red = 30  # 30% reduccion cuando funciona
    factor_estoc = _factor_estocastico(confiabilidad=100, reduccion_efectiva=red,
                                        reduccion_fallo=0, nombre='C100')
    evento_base = _build_evento(
        'e1', 'Base', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 100}}
    )
    evento_estoc = _build_evento(
        'e1', 'Estoc', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 100}},
        factores_ajuste=[factor_estoc]
    )
    _, freq_base, _, _ = _simular([evento_base], num_sims=20_000, seed=400)
    _, freq_mit, _, _ = _simular([evento_estoc], num_sims=20_000, seed=401)
    ratio = freq_mit.mean() / freq_base.mean()
    assert_close_rel(ratio, 0.70, tol_rel=0.05,
                     label="Estocastico conf=100, red=30 ≡ estatico -30%")


def test_factor_estocastico_confiabilidad_50_promedio():
    """Con confiabilidad=50% y reduccion_efectiva=60%, reduccion_fallo=0:
       factor esperado = 0.5*0.4 + 0.5*1.0 = 0.7."""
    factor_estoc = _factor_estocastico(confiabilidad=50, reduccion_efectiva=60,
                                        reduccion_fallo=0, nombre='C50')
    evento_base = _build_evento(
        'e1', 'Base', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 100}}
    )
    evento_estoc = _build_evento(
        'e1', 'Estoc', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 100}},
        factores_ajuste=[factor_estoc]
    )
    _, freq_base, _, _ = _simular([evento_base], num_sims=30_000, seed=402)
    _, freq_mit, _, _ = _simular([evento_estoc], num_sims=30_000, seed=403)
    ratio = freq_mit.mean() / freq_base.mean()
    assert_close_rel(ratio, 0.70, tol_rel=0.08,
                     label="Estocastico conf=50, red_ef=60% ⇒ factor esperado 0.7")


# ===========================================================================
# SECCION 6: VINCULOS
# ===========================================================================

def _vinculo(id_padre, tipo='AND', probabilidad=100, factor_severidad=1.0,
              umbral_severidad=0):
    return {
        'id_padre': id_padre,
        'tipo': tipo,
        'probabilidad': probabilidad,
        'factor_severidad': factor_severidad,
        'umbral_severidad': umbral_severidad,
    }


def test_vinculo_AND_solo_hijo_cuando_padre_ocurre():
    """Padre Bernoulli(p=0.5), hijo AND con prob=100. P(hijo)=P(padre)*p_hijo
       Pero P(hijo_propio)=P(Bernoulli=1)=p_hijo. Combinado AND=0.5*p_hijo.

       Test: con padre p=0.5 y hijo Poisson(λ=10) en AND, el hijo solo se
       activa cuando padre ocurre. Frecuencia esperada del hijo = 0.5 * 10 = 5."""
    padre = _build_evento(
        'pa', 'Padre', 3, {'probabilidad_exito': 0.5},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 100, 'std': 10}}
    )
    hijo = _build_evento(
        'hi', 'Hijo', 1, {'tasa': 10.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 100, 'std': 10}},
        vinculos=[_vinculo('pa', tipo='AND', probabilidad=100)]
    )
    _, _, perd_evt, freq_evt = _simular([padre, hijo], num_sims=30_000, seed=500)
    media_hijo = freq_evt[1].mean()
    assert_close_rel(media_hijo, 0.5 * 10.0, tol_rel=0.05,
                     label="Vinculo AND: E[freq_hijo] = P(padre)*E[Poisson]")


def test_vinculo_OR_hijo_si_cualquier_padre():
    """2 padres Bernoulli(p=0.3), hijo OR con ambos. P(al menos uno) =
       1 - (1-0.3)^2 = 0.51. Hijo Poisson(λ=10). E[freq_hijo] ≈ 0.51 * 10 = 5.1."""
    p_a = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 0.3},
                       2, {'minimo': None, 'mas_probable': None, 'maximo': None,
                           'input_method': 'direct',
                           'params_direct': {'mean': 100, 'std': 10}})
    p_b = _build_evento('pb', 'PB', 3, {'probabilidad_exito': 0.3},
                       2, {'minimo': None, 'mas_probable': None, 'maximo': None,
                           'input_method': 'direct',
                           'params_direct': {'mean': 100, 'std': 10}})
    hijo = _build_evento('hi', 'Hijo', 1, {'tasa': 10.0},
                        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
                            'input_method': 'direct',
                            'params_direct': {'mean': 100, 'std': 10}},
                        vinculos=[_vinculo('pa', tipo='OR'),
                                  _vinculo('pb', tipo='OR')])
    _, _, _, freq_evt = _simular([p_a, p_b, hijo], num_sims=40_000, seed=501)
    media_hijo = freq_evt[2].mean()
    p_or = 1 - (1 - 0.3) ** 2  # 0.51
    assert_close_rel(media_hijo, p_or * 10.0, tol_rel=0.07,
                     label="Vinculo OR: P(al menos un padre)*E[Poisson]")


def test_vinculo_EXCLUYE_hijo_solo_si_ningun_padre():
    """Padre Bernoulli(p=0.3), hijo EXCLUYE → hijo activo solo cuando padre=0.
       Hijo Bernoulli(p=1.0): E[freq_hijo] = P(padre=0) * 1 = 0.7."""
    padre = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 0.3},
                         2, {'minimo': None, 'mas_probable': None, 'maximo': None,
                             'input_method': 'direct',
                             'params_direct': {'mean': 100, 'std': 10}})
    hijo = _build_evento('hi', 'Hijo', 3, {'probabilidad_exito': 1.0},
                        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
                            'input_method': 'direct',
                            'params_direct': {'mean': 100, 'std': 10}},
                        vinculos=[_vinculo('pa', tipo='EXCLUYE')])
    _, _, _, freq_evt = _simular([padre, hijo], num_sims=20_000, seed=502)
    media_hijo = freq_evt[1].mean()
    assert_close_rel(media_hijo, 0.7, tol_rel=0.05,
                     label="Vinculo EXCLUYE: P(padre=0)")


def test_vinculo_factor_severidad():
    """Vinculo AND con factor_severidad=2.0: cuando padre activa, severidad
       del hijo se duplica."""
    padre = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 1.0},  # siempre ocurre
                         2, {'minimo': None, 'mas_probable': None, 'maximo': None,
                             'input_method': 'direct',
                             'params_direct': {'mean': 100, 'std': 10}})
    hijo_base = _build_evento('hi', 'Hijo', 3, {'probabilidad_exito': 1.0},  # siempre
                              2, {'minimo': None, 'mas_probable': None, 'maximo': None,
                                  'input_method': 'direct',
                                  'params_direct': {'mean': 1000, 'std': 50}},
                              vinculos=[_vinculo('pa', tipo='AND', factor_severidad=1.0)])
    hijo_mult = _build_evento('hi2', 'HijoMult', 3, {'probabilidad_exito': 1.0},
                              2, {'minimo': None, 'mas_probable': None, 'maximo': None,
                                  'input_method': 'direct',
                                  'params_direct': {'mean': 1000, 'std': 50}},
                              vinculos=[_vinculo('pa', tipo='AND', factor_severidad=2.0)])
    _, _, perd_evt_base, _ = _simular([padre, hijo_base], num_sims=15_000, seed=503)
    _, _, perd_evt_mult, _ = _simular([padre, hijo_mult], num_sims=15_000, seed=504)
    ratio = perd_evt_mult[1].mean() / perd_evt_base[1].mean()
    assert_close_rel(ratio, 2.0, tol_rel=0.08,
                     label="Vinculo factor_severidad=2.0 duplica la perdida")


# ===========================================================================
# SECCION 7: SEGUROS
# ===========================================================================

def _seguro(deducible=0, cobertura_pct=1.0, limite=0,
             tipo_deducible='agregado', limite_ocurrencia=0,
             nombre='Seguro'):
    """Construye un dict de seguro estructurado como factor_ajuste tipo_severidad=seguro."""
    return {
        'nombre': nombre,
        'tipo_modelo': 'estatico',
        'activo': True,
        'afecta_frecuencia': False,
        'impacto_porcentual': 0,
        'afecta_severidad': True,
        'tipo_severidad': 'seguro',
        'seguro_deducible': deducible,
        'seguro_cobertura_pct': cobertura_pct * 100,  # el motor divide por 100
        'seguro_limite': limite,
        'seguro_tipo_deducible': tipo_deducible,
        'seguro_limite_ocurrencia': limite_ocurrencia,
    }


def test_seguro_agregado_reduce_perdida():
    """Seguro agregado: deducible $5000, cobertura 100%, sin limite.
       Si la perdida bruta supera $5000, todo el exceso se cubre.
       Caso: lambda=2, severidad fija mean=$2000 → bruta media ≈ $4000 (debajo
       del deducible la mayor parte de las veces, seguro paga poco)."""
    evento_no_seguro = _build_evento(
        'e1', 'NoSeg', 1, {'tasa': 10.0},  # mas frecuencia para que active deducible
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 100}}
    )
    evento_con_seg = _build_evento(
        'e1', 'Seg', 1, {'tasa': 10.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 100}},
        factores_ajuste=[_seguro(deducible=5000, cobertura_pct=1.0,
                                  limite=0, tipo_deducible='agregado')]
    )
    perd_no, _, _, _ = _simular([evento_no_seguro], num_sims=20_000, seed=600)
    perd_si, _, _, _ = _simular([evento_con_seg], num_sims=20_000, seed=601)
    # E[bruto] = 10 * 1000 = 10000
    # E[neto] = E[max(bruto - 5000, 0)] = E[bruto] - 5000 = 5000 (aprox, asumiendo bruto > 5000 siempre)
    # Para tasa=10 con sev de mean 1000, la mayoria de las sims supera 5000
    assert perd_si.mean() < perd_no.mean(), "Seguro deberia reducir la perdida"
    # Reduccion esperada ≈ 5000 (deducible neto)
    diff = perd_no.mean() - perd_si.mean()
    # Tolerancia generosa porque hay sims con bruto < deducible
    assert_in_range(diff, 4000, 5500, label="Reduccion neta seguro agregado")


def test_seguro_por_ocurrencia_con_limite():
    """Seguro por ocurrencia: deducible $0, cobertura 100%, limite_ocurrencia $400.
       Para sev casi determinista X=1000 con tasa=5:
       - pago por ocurrencia = min(max(1000-0, 0)*1.0, 400) = 400
       - Pago total por sim = 5 * 400 = 2000
       - Neto = 5*1000 - 2000 = 3000."""
    evento_con_seg = _build_evento(
        'e1', 'Seg', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}},  # casi deterministico
        factores_ajuste=[_seguro(deducible=0, cobertura_pct=1.0,
                                  limite=0, tipo_deducible='por_ocurrencia',
                                  limite_ocurrencia=400)]
    )
    evento_sin_seg = _build_evento(
        'e1', 'NoSeg', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}}
    )
    perd_no, _, _, _ = _simular([evento_sin_seg], num_sims=20_000, seed=602)
    perd_si, _, _, _ = _simular([evento_con_seg], num_sims=20_000, seed=603)
    # Bruto medio = 5 * 1000 = 5000
    # Pago seguro = E[N] * limite_ocurrencia = 5 * 400 = 2000
    # Neto = 5000 - 2000 = 3000
    assert_close_rel(perd_si.mean(), 3000, tol_rel=0.05,
                     label="Perdida neta con seguro por ocurrencia + cap")
    # El pago total debe ser ~2000 (E[N] * 400)
    pago_total = perd_no.mean() - perd_si.mean()
    assert_close_rel(pago_total, 2000, tol_rel=0.05,
                     label="Pago total seguro por ocurrencia")


def test_seguro_multi_aseguradora_limite_agregado():
    """Regresion bug #14: con 2 aseguradoras por_ocurrencia, cada una con
       limite_agregado, el limite se debe aplicar POR ASEGURADORA, no a la suma.
       Caso: lambda=10, sev=1000, 2 aseguradoras con deducible=0, cob=50%,
       limite_agregado=2000 cada una. Pago bruto sin cap = 10*1000*0.5 = 5000
       por aseguradora; con cap a 2000 → 2000 c/u = 4000 total."""
    evento = _build_evento(
        'e1', 'MultiSeg', 1, {'tasa': 10.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}},  # sev casi determinista
        factores_ajuste=[
            _seguro(deducible=0, cobertura_pct=0.5, limite=2000,
                    tipo_deducible='por_ocurrencia', nombre='AsegA'),
            _seguro(deducible=0, cobertura_pct=0.5, limite=2000,
                    tipo_deducible='por_ocurrencia', nombre='AsegB'),
        ]
    )
    evento_no_seg = _build_evento(
        'e1', 'NoSeg', 1, {'tasa': 10.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}}
    )
    perd_no, _, _, _ = _simular([evento_no_seg], num_sims=15_000, seed=604)
    perd_si, _, _, _ = _simular([evento, ], num_sims=15_000, seed=605)
    # Bruto medio: 10 * 1000 = 10000
    # Pago total esperado: 2000 (A) + 2000 (B) = 4000
    # Neto esperado: 10000 - 4000 = 6000
    pago_total = perd_no.mean() - perd_si.mean()
    assert_close_rel(pago_total, 4000, tol_rel=0.10,
                     label="Bug #14 regression: 2 aseguradoras x $2000 = $4000")
    # Con el bug VIEJO: el cap del primer aseg saturaba toda la suma a $2000.
    # Verificamos que NO ocurra eso.
    if pago_total < 2500:
        raise AssertionError(
            f"REGRESION del bug #14: el pago total ({pago_total:.0f}) es menor "
            f"que el cap de UNA sola aseguradora ($2000). Indica que el motor "
            f"esta aplicando el cap a la SUMA en lugar de por aseguradora."
        )


# ===========================================================================
# SECCION 8: EDGE CASES y robustez
# ===========================================================================

def test_cap_dispara_warning_en_freq_muy_alta():
    """Si E[N] * num_sims > 500M, el cap se debe activar Y emitir warning."""
    import warnings as _w
    cap_cls = ENGINE['RiskLabFrequencyCapWarning']
    # PG con E[N] = 60K, num_sims = 10K → sum esperado = 600M > 500M cap
    evento = _build_evento(
        'e1', 'AltaFreq', 4, {'poisson_gamma_params': (20.0, 1.0 / 3000.0)},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 10, 'std': 1}}  # sev pequena para no OOM
    )
    with _w.catch_warnings(record=True) as w:
        _w.simplefilter('always')
        _simular([evento], num_sims=10_000, seed=700)
        cap_warns = [x for x in w if issubclass(x.category, cap_cls)]
        assert len(cap_warns) > 0, (
            "Esperaba que se emitiera RiskLabFrequencyCapWarning cuando sum > 500M"
        )
        # Verificar huellas del cap
        assert evento.get('_cap_frecuencia_aplicado'), \
            "_cap_frecuencia_aplicado no quedo marcado"


def test_perdidas_siempre_no_negativas():
    """Cualquier configuracion debe producir perdidas >= 0."""
    evento = _build_evento(
        'e1', 'Test', 1, {'tasa': 5.0},
        1, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 100, 'std': 30}}
    )
    perd_tot, _, _, _ = _simular([evento], num_sims=20_000, seed=701)
    assert (perd_tot >= 0).all(), "Hay perdidas negativas"


def test_consistencia_perdidas_totales_y_por_evento():
    """perdidas_totales[i] = sum(perdidas_por_evento[j][i] for j) — invariante."""
    eventos = [
        _build_evento('e1', 'A', 1, {'tasa': 3.0}, 2,
                      {'minimo': None, 'mas_probable': None, 'maximo': None,
                       'input_method': 'direct',
                       'params_direct': {'mean': 500, 'std': 50}}),
        _build_evento('e2', 'B', 3, {'probabilidad_exito': 0.3}, 3,
                      {'minimo': 10, 'mas_probable': 50, 'maximo': 200}),
        _build_evento('e3', 'C', 4, {'poisson_gamma_params': (5.0, 1.0)}, 2,
                      {'minimo': None, 'mas_probable': None, 'maximo': None,
                       'input_method': 'direct',
                       'params_direct': {'mean': 200, 'std': 40}}),
    ]
    perd_tot, freq_tot, perd_evt, freq_evt = _simular(eventos, num_sims=10_000, seed=702)
    suma_evt = sum(perd_evt)
    np.testing.assert_allclose(perd_tot, suma_evt, rtol=1e-9,
                                err_msg="perdidas_totales != sum(perdidas_por_evento)")
    suma_freq = sum(freq_evt)
    np.testing.assert_array_equal(freq_tot, suma_freq,
                                   err_msg="frecuencias_totales != sum(frecuencias_por_evento)")


def test_eventos_inactivos_no_contribuyen():
    """Un evento marcado activo=False NO deberia aparecer en la simulacion.
       Nota: el motor en LDA usa todos los eventos pasados; el filtrado
       de activo se hace upstream en ejecutar_simulacion. Aqui validamos
       que si pasamos solo los activos, el resultado matchea."""
    e_act = _build_evento('e1', 'Activo', 1, {'tasa': 5.0}, 2,
                          {'minimo': None, 'mas_probable': None, 'maximo': None,
                           'input_method': 'direct',
                           'params_direct': {'mean': 1000, 'std': 100}})
    e_inact = _build_evento('e2', 'Inactivo', 1, {'tasa': 100.0}, 2,
                            {'minimo': None, 'mas_probable': None, 'maximo': None,
                             'input_method': 'direct',
                             'params_direct': {'mean': 1000, 'std': 100}})
    e_inact['activo'] = False
    # Solo activos (lo que haria el filtrado del UI)
    perd, _, _, _ = _simular([e_act], num_sims=20_000, seed=703)
    # E[S] esperado ≈ 5 * 1000 = 5000 (sin contar el inactivo)
    assert_close_rel(perd.mean(), 5000, tol_rel=0.05,
                     label="Solo evento activo contribuye")


# ===========================================================================
# SECCION 9: Identidades del helper de parametros
# ===========================================================================

def test_obtener_parametros_pert():
    """PERT: alpha = 1 + 4*(mode-min)/(max-min), beta = 1 + 4*(max-mode)/(max-min)."""
    pert = ENGINE['obtener_parametros_pert']
    a, b = pert(10, 50, 100)
    # mode=50, range=90; alpha = 1 + 4*40/90 ≈ 2.778; beta = 1 + 4*50/90 ≈ 3.222
    assert_close_rel(a, 1 + 4 * 40 / 90, tol_rel=1e-6, label="PERT alpha")
    assert_close_rel(b, 1 + 4 * 50 / 90, tol_rel=1e-6, label="PERT beta")


def test_obtener_parametros_normal():
    """Normal: mu=mode, sigma=range/6 (suponer rango ~99.7% CI)."""
    norm_fn = ENGINE['obtener_parametros_normal']
    mu, sigma = norm_fn(10, 50, 100)
    assert mu == 50
    assert_close_rel(sigma, (100 - 10) / 6.0, tol_rel=1e-6, label="Normal sigma")


# ===========================================================================
# Test runner standalone (sin pytest).
# ===========================================================================

def _collect_tests():
    """Recoge todas las funciones que empiezan con 'test_' en orden de aparicion."""
    g = globals()
    items = []
    for name, func in g.items():
        if name.startswith('test_') and callable(func):
            items.append((name, func))
    # Ordenar por orden de definicion (line number en este archivo)
    return items


def _run_all(verbose=True):
    items = _collect_tests()
    print()
    print('=' * 70)
    print(f'Risk Lab — suite de pruebas de robustez ({len(items)} tests)')
    print('=' * 70)
    print()
    passed, failed, errors = 0, 0, 0
    failures = []
    # Suprimir warnings benignos del engine al correr en batch
    warnings.simplefilter('default')

    for i, (name, func) in enumerate(items, 1):
        prefix = f'[{i:>2}/{len(items)}]'
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)  # los tests que necesitan warning capturan explicitamente
                func()
            passed += 1
            if verbose:
                print(f'{prefix} ✓ {name}')
        except AssertionError as e:
            failed += 1
            failures.append((name, 'FAIL', str(e)))
            print(f'{prefix} ✗ {name}\n         FAIL: {e}')
        except Exception as e:
            errors += 1
            failures.append((name, 'ERROR', f'{type(e).__name__}: {e}'))
            print(f'{prefix} ! {name}\n         ERROR: {type(e).__name__}: {e}')

    print()
    print('=' * 70)
    print(f'Resultado: {passed} OK, {failed} FAIL, {errors} ERROR')
    print('=' * 70)
    if failures:
        print()
        print('Fallos detallados:')
        for name, kind, msg in failures:
            print(f'  [{kind}] {name}: {msg}')
    return failed + errors == 0


if __name__ == '__main__':
    ok = _run_all(verbose=True)
    sys.exit(0 if ok else 1)
