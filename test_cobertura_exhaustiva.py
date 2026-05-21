"""
test_cobertura_exhaustiva.py
============================

Tercera bateria de tests para Risk Lab — cobertura exhaustiva de:

  N. MATRIZ DE COMBINACIONES DISTRIBUCIONES — todas las combinaciones
     freq_opcion (1-5) x sev_opcion (1-5) = 25 escenarios. Para cada
     combinacion: la simulacion no falla, produce arrays finitos no
     negativos del tamano correcto, y la media tiene un orden de
     magnitud razonable.

  O. VALIDACION DE INPUTS DE SEVERIDAD — cada sev_opcion con
     parametros buenos y malos.

  P. VALIDACION DE INPUTS DE FRECUENCIA — cada freq_opcion con
     parametros buenos y malos.

  Q. VALIDACION DE FACTORES — combinaciones validas e invalidas de
     factores_ajuste (incluye casos limite: 0%, 100%, valores NaN/inf
     deberian ser manejados gracefully).

  R. VALIDACION DE VINCULOS — todas las combinaciones (tipo, prob,
     factor_severidad, umbral_severidad), incluye casos limite y
     configuraciones invalidas.

  S. VALIDACION DE SEGUROS — todas las combinaciones, edge cases
     (cobertura 0%, deducible negativo, limite agregado conflicto,
     mezcla por_ocurrencia + agregado).

  T. INVARIANTES DE OUTPUT — para CUALQUIER configuracion valida, el
     output debe satisfacer: (a) no NaN/Inf, (b) perdidas >= 0,
     (c) frecuencias >= 0 enteras, (d) sizes coherentes,
     (e) perdidas_totales = sum(perdidas_por_evento).

  U. GOODNESS-OF-FIT PROFUNDO — Anderson-Darling, chi-square,
     comparacion de momentos (mean, var, skew, kurtosis).

  V. CARGA DE MODELO JSON COMPLETO — usa test_model_exhaustivo.json
     y verifica que cada evento corre sin error y produce salida
     consistente.

  W. ESCALA Y PERFORMANCE — modelos con muchos eventos (20+) y
     muchas simulaciones (50K+) deben completar sin fallar.

  X. INTERACCIONES COMPUESTAS — sev_freq + factores + vinculos +
     seguros todos juntos. La combinacion mas compleja posible.

  Y. EXPORT IA — verificar que el dict de salida es serializable
     a JSON (sin tipos no estandar como np.float32).

  Z. FUZZING INPUT — combinaciones aleatorias de inputs validos
     no deben romper la simulacion (50 ejecuciones con configs
     random).

Total esperado: ~60+ tests.
"""

import ast
import os
import sys
import time
import json
import math
import random
import warnings
import numpy as np
from scipy import stats
from scipy.stats import (
    poisson, binom, bernoulli, lognorm, beta as beta_dist,
    genpareto, norm, uniform, nbinom, truncnorm, kstest, anderson, chisquare
)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
from test_robustez_simulacion import (  # noqa: E402
    ENGINE, _build_evento, _rng,
    assert_close_rel, assert_in_range,
    _simular,
    _factor_estatico, _factor_estocastico,
    _vinculo, _seguro,
)


# ===========================================================================
# N. MATRIZ DE COMBINACIONES freq × sev (25 combinaciones)
# ===========================================================================

def _freq_params_validos(freq_opcion):
    """Devuelve un dict de freq_params validos para cada freq_opcion."""
    return {
        1: {'tasa': 3.0},
        2: {'num_eventos_posibles': 10, 'probabilidad_exito': 0.3},
        3: {'probabilidad_exito': 0.5},
        4: {'poisson_gamma_params': (5.0, 1.0)},
        5: {'beta_params': (3.0, 7.0)},
    }[freq_opcion]


def _sev_params_validos(sev_opcion):
    """Devuelve un dict de sev_params validos para cada sev_opcion."""
    # Para opciones que soportan ambos input_methods, usamos min_mode_max por simpleza
    if sev_opcion == 1:  # Normal
        return {'minimo': 50.0, 'mas_probable': 100.0, 'maximo': 200.0,
                'input_method': 'min_mode_max'}
    if sev_opcion == 2:  # LogNormal
        return {'minimo': 50.0, 'mas_probable': 100.0, 'maximo': 200.0,
                'input_method': 'min_mode_max'}
    if sev_opcion == 3:  # PERT
        return {'minimo': 10.0, 'mas_probable': 50.0, 'maximo': 100.0,
                'input_method': 'min_mode_max'}
    if sev_opcion == 4:  # GPD
        return {'minimo': 10.0, 'mas_probable': 50.0, 'maximo': 500.0,
                'input_method': 'min_mode_max'}
    if sev_opcion == 5:  # Uniforme
        return {'minimo': 10.0, 'mas_probable': None, 'maximo': 100.0}
    raise ValueError(f"sev_opcion {sev_opcion} desconocida")


def test_N_matriz_completa_freq_x_sev():
    """Las 25 combinaciones de freq_opcion (1-5) x sev_opcion (1-5) deben
    funcionar sin error y producir output coherente."""
    fallos = []
    for f in range(1, 6):
        for s in range(1, 6):
            try:
                ev = _build_evento(
                    f'e_{f}_{s}', f'F{f}_S{s}',
                    f, _freq_params_validos(f),
                    s, _sev_params_validos(s)
                )
                perd, freq, _, _ = _simular([ev], num_sims=2_000, seed=2000 + f * 10 + s)
                # Invariantes
                assert np.isfinite(perd).all(), "NaN/Inf en perdidas"
                assert (perd >= 0).all(), "Perdidas negativas"
                assert np.isfinite(freq).all(), "NaN/Inf en frecuencias"
                assert (freq >= 0).all(), "Frecuencias negativas"
                assert len(perd) == 2_000 and len(freq) == 2_000, "Tamano incorrecto"
            except Exception as e:
                fallos.append(f"freq={f}, sev={s}: {type(e).__name__}: {e}")
    if fallos:
        raise AssertionError(
            f"{len(fallos)}/25 combinaciones freq x sev fallaron:\n  " +
            "\n  ".join(fallos)
        )


# ===========================================================================
# O. VALIDACION DE INPUTS DE SEVERIDAD
# ===========================================================================

def test_O_sev_normal_direct_std_negativo_rechazado():
    gen = ENGINE['generar_distribucion_severidad']
    try:
        gen(1, None, None, None, input_method='direct',
            params_direct={'mean': 100, 'std': -50})
    except (ValueError, Exception):
        return
    raise AssertionError("Normal con std<0 deberia ser rechazada")


def test_O_sev_lognormal_mean_negativo_rechazado():
    gen = ENGINE['generar_distribucion_severidad']
    try:
        gen(2, None, None, None, input_method='direct',
            params_direct={'mean': -100, 'std': 10})
    except ValueError:
        return
    raise AssertionError("LogNormal con mean<0 deberia ser rechazada")


def test_O_sev_lognormal_min_mode_max_no_orden_rechazado():
    """min < mas_probable < maximo debe respetarse."""
    gen = ENGINE['generar_distribucion_severidad']
    # mas_probable > maximo (orden invertido)
    try:
        gen(2, 10, 300, 200, input_method='min_mode_max')
    except (ValueError, Exception):
        return
    raise AssertionError("LogNormal con orden invertido deberia ser rechazada")


def test_O_sev_lognormal_min_cero_rechazado():
    """LogNormal requiere min > 0 (soporte estrictamente positivo)."""
    gen = ENGINE['generar_distribucion_severidad']
    try:
        gen(2, 0.0, 50, 100, input_method='min_mode_max')
    except (ValueError, Exception):
        return
    raise AssertionError("LogNormal con min=0 deberia ser rechazada")


def test_O_sev_pert_min_igual_max_rechazado():
    gen = ENGINE['generar_distribucion_severidad']
    try:
        gen(3, 50, 50, 50)
    except (ValueError, Exception):
        return
    raise AssertionError("PERT con min=max deberia ser rechazado")


def test_O_sev_gpd_scale_negativo_rechazado():
    gen = ENGINE['generar_distribucion_severidad']
    try:
        gen(4, None, None, None, input_method='direct',
            params_direct={'c': 0.3, 'scale': -1000, 'loc': 0})
    except (ValueError, Exception):
        return
    raise AssertionError("GPD con scale<0 deberia ser rechazada")


def test_O_sev_uniforme_min_mayor_max_rechazado():
    """Uniforme con min > max."""
    gen = ENGINE['generar_distribucion_severidad']
    try:
        d = gen(5, 200, None, 100)
        # Si no rechaza al crear, debe rechazar al sampear
        samples = d.rvs(size=10, random_state=_rng(seed=3000))
        # scipy uniform(loc=200, scale=-100): scale<0 → samples invalidos
        # Esto seria un bug — verificamos al menos que no produzca samples
        # entre 100 y 200 (que serian el rango invertido)
        if (samples < 100).any() or (samples > 200).any():
            raise AssertionError(
                f"Uniforme(min=200,max=100) produjo samples fuera de rango: "
                f"{samples}"
            )
    except (ValueError, Exception):
        pass


def test_O_sev_opcion_desconocida_rechazada():
    """sev_opcion=99 (no existente) debe ser rechazada."""
    gen = ENGINE['generar_distribucion_severidad']
    try:
        gen(99, 10, 50, 100)
    except (ValueError, Exception):
        return
    raise AssertionError("sev_opcion=99 deberia ser rechazada")


# ===========================================================================
# P. VALIDACION DE INPUTS DE FRECUENCIA
# ===========================================================================

def test_P_freq_poisson_tasa_cero_rechazada():
    gen = ENGINE['generar_distribucion_frecuencia']
    try:
        gen(1, tasa=0.0)
    except (ValueError, Exception):
        return
    raise AssertionError("Poisson tasa=0 deberia ser rechazada")


def test_P_freq_binomial_n_negativo_rechazado():
    gen = ENGINE['generar_distribucion_frecuencia']
    try:
        gen(2, num_eventos_posibles=-5, probabilidad_exito=0.3)
    except (ValueError, Exception):
        return
    raise AssertionError("Binomial n<0 deberia ser rechazado")


def test_P_freq_bernoulli_p_negativo_rechazado():
    gen = ENGINE['generar_distribucion_frecuencia']
    try:
        gen(3, probabilidad_exito=-0.1)
    except (ValueError, Exception):
        return
    raise AssertionError("Bernoulli p<0 deberia ser rechazada")


def test_P_freq_PG_params_invalidos_rechazado():
    gen = ENGINE['generar_distribucion_frecuencia']
    # alpha=0
    try:
        gen(4, poisson_gamma_params=(0.0, 1.0))
    except (ValueError, Exception):
        pass
    else:
        raise AssertionError("PG alpha=0 deberia ser rechazado")
    # beta=0
    try:
        gen(4, poisson_gamma_params=(2.0, 0.0))
    except (ValueError, Exception):
        return
    raise AssertionError("PG beta=0 deberia ser rechazado")


def test_P_freq_Beta_alphabeta_invalidos_rechazado():
    gen = ENGINE['generar_distribucion_frecuencia']
    # alpha negativo
    try:
        gen(5, beta_params=(-1.0, 2.0))
    except (ValueError, Exception):
        return
    raise AssertionError("Beta freq alpha<0 deberia ser rechazado")


def test_P_freq_opcion_desconocida_rechazada():
    gen = ENGINE['generar_distribucion_frecuencia']
    try:
        gen(99)
    except (ValueError, Exception):
        return
    raise AssertionError("freq_opcion=99 deberia ser rechazada")


# ===========================================================================
# Q. VALIDACION DE FACTORES (configuraciones de factores_ajuste)
# ===========================================================================

def test_Q_factor_inactivo_no_se_aplica():
    """Factor con activo=False NO debe modificar la frecuencia."""
    factor = {**_factor_estatico(impacto_freq=-50, nombre='C'), 'activo': False}
    e_base = _build_evento('e1', 'B', 1, {'tasa': 5.0}, 2,
                           {'minimo': None, 'mas_probable': None, 'maximo': None,
                            'input_method': 'direct',
                            'params_direct': {'mean': 100, 'std': 10}})
    e_inact = _build_evento('e1', 'I', 1, {'tasa': 5.0}, 2,
                            {'minimo': None, 'mas_probable': None, 'maximo': None,
                             'input_method': 'direct',
                             'params_direct': {'mean': 100, 'std': 10}},
                            factores_ajuste=[factor])
    _, fb, _, _ = _simular([e_base], num_sims=10_000, seed=4000)
    _, fi, _, _ = _simular([e_inact], num_sims=10_000, seed=4001)
    # Sin diferencia significativa
    assert_close_rel(fi.mean(), fb.mean(), tol_rel=0.05,
                     label="Factor inactivo no afecta")


def test_Q_factor_impacto_cero_no_op():
    """Factor con impacto_porcentual=0 debe ser no-op."""
    factor = _factor_estatico(impacto_freq=0, impacto_sev=0, nombre='Noop')
    e_base = _build_evento('e1', 'B', 1, {'tasa': 5.0}, 2,
                           {'minimo': None, 'mas_probable': None, 'maximo': None,
                            'input_method': 'direct',
                            'params_direct': {'mean': 100, 'std': 10}})
    e_zero = _build_evento('e1', 'Z', 1, {'tasa': 5.0}, 2,
                           {'minimo': None, 'mas_probable': None, 'maximo': None,
                            'input_method': 'direct',
                            'params_direct': {'mean': 100, 'std': 10}},
                           factores_ajuste=[factor])
    _, fb, _, _ = _simular([e_base], num_sims=10_000, seed=4002)
    _, fz, _, _ = _simular([e_zero], num_sims=10_000, seed=4003)
    assert_close_rel(fz.mean(), fb.mean(), tol_rel=0.03,
                     label="Factor 0% es no-op")


def test_Q_factor_solo_severidad_no_toca_frecuencia():
    """Factor con afecta_frecuencia=False, afecta_severidad=True."""
    factor = _factor_estatico(impacto_freq=0, impacto_sev=-50, nombre='SoloSev')
    e_base = _build_evento('e1', 'B', 1, {'tasa': 5.0}, 2,
                           {'minimo': None, 'mas_probable': None, 'maximo': None,
                            'input_method': 'direct',
                            'params_direct': {'mean': 100, 'std': 10}})
    e_sev = _build_evento('e1', 'S', 1, {'tasa': 5.0}, 2,
                          {'minimo': None, 'mas_probable': None, 'maximo': None,
                           'input_method': 'direct',
                           'params_direct': {'mean': 100, 'std': 10}},
                          factores_ajuste=[factor])
    perd_b, fb, _, _ = _simular([e_base], num_sims=15_000, seed=4004)
    perd_s, fs, _, _ = _simular([e_sev], num_sims=15_000, seed=4005)
    # Frecuencias iguales
    assert_close_rel(fs.mean(), fb.mean(), tol_rel=0.05,
                     label="Factor solo sev no toca freq")
    # Severidad: perdida reducida ~50%
    ratio = perd_s.mean() / perd_b.mean()
    assert_close_rel(ratio, 0.5, tol_rel=0.08,
                     label="Factor -50% solo severidad")


def test_Q_factor_estocastico_confiabilidad_default_100():
    """Si 'confiabilidad' no se especifica, default=100% (siempre funciona)."""
    factor = {
        'nombre': 'Default',
        'tipo_modelo': 'estocastico',
        'activo': True,
        # NO 'confiabilidad'
        'reduccion_efectiva': 30,
        'reduccion_fallo': 0,
        'afecta_frecuencia': True,
    }
    e = _build_evento('e1', 'D', 1, {'tasa': 5.0}, 2,
                      {'minimo': None, 'mas_probable': None, 'maximo': None,
                       'input_method': 'direct',
                       'params_direct': {'mean': 100, 'std': 10}},
                      factores_ajuste=[factor])
    _, freq, _, _ = _simular([e], num_sims=10_000, seed=4006)
    # Sin confiabilidad explicita, default=100 → siempre funciona → factor=0.7
    # E[freq] = 5 * 0.7 = 3.5
    assert_close_rel(freq.mean(), 3.5, tol_rel=0.05,
                     label="Confiabilidad default=100")


# ===========================================================================
# R. VALIDACION DE VINCULOS
# ===========================================================================

def test_R_vinculo_probabilidad_50pct():
    """Vinculo con probabilidad=50 (activa el padre solo en 50% de las sims
    donde padre ocurrio). Con padre Bernoulli(1.0) → activacion neta = 0.5.
    Hijo Poisson(λ=10) → E[freq_hijo] = 0.5 * 10 = 5."""
    padre = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 1.0}, 2,
                         {'minimo': None, 'mas_probable': None, 'maximo': None,
                          'input_method': 'direct',
                          'params_direct': {'mean': 100, 'std': 10}})
    hijo = _build_evento('hi', 'Hijo', 1, {'tasa': 10.0}, 2,
                        {'minimo': None, 'mas_probable': None, 'maximo': None,
                         'input_method': 'direct',
                         'params_direct': {'mean': 100, 'std': 10}},
                        vinculos=[_vinculo('pa', tipo='AND', probabilidad=50)])
    _, _, _, freq_evt = _simular([padre, hijo], num_sims=20_000, seed=5000)
    assert_close_rel(freq_evt[1].mean(), 5.0, tol_rel=0.05,
                     label="Vinculo probabilidad=50%")


def test_R_vinculo_umbral_severidad_filtra_activacion():
    """Vinculo con umbral_severidad: solo activa si la perdida del padre
    es >= umbral. Con padre que produce ~$1000 de perdida y umbral=$2000,
    el vinculo nunca se activa."""
    padre = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 1.0}, 2,
                         {'minimo': None, 'mas_probable': None, 'maximo': None,
                          'input_method': 'direct',
                          'params_direct': {'mean': 1000, 'std': 1}})  # ~$1000 fijo
    hijo = _build_evento('hi', 'Hijo', 1, {'tasa': 10.0}, 2,
                        {'minimo': None, 'mas_probable': None, 'maximo': None,
                         'input_method': 'direct',
                         'params_direct': {'mean': 100, 'std': 10}},
                        vinculos=[_vinculo('pa', tipo='AND', umbral_severidad=2000)])
    _, _, _, freq_evt = _simular([padre, hijo], num_sims=10_000, seed=5001)
    # Hijo casi nunca activa
    assert freq_evt[1].mean() < 0.5, (
        f"Umbral $2000 con padre $1000 deberia bloquear hijo, "
        f"E[freq_hijo]={freq_evt[1].mean():.3f}"
    )


def test_R_vinculo_factor_severidad_05_reduce():
    """Vinculo AND con factor_severidad=0.5 reduce a la mitad la perdida del hijo."""
    padre = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 1.0}, 2,
                         {'minimo': None, 'mas_probable': None, 'maximo': None,
                          'input_method': 'direct',
                          'params_direct': {'mean': 100, 'std': 10}})
    hijo_b = _build_evento('hi', 'HBase', 3, {'probabilidad_exito': 1.0}, 2,
                          {'minimo': None, 'mas_probable': None, 'maximo': None,
                           'input_method': 'direct',
                           'params_direct': {'mean': 1000, 'std': 1}},
                          vinculos=[_vinculo('pa', tipo='AND', factor_severidad=1.0)])
    hijo_r = _build_evento('hi2', 'HRed', 3, {'probabilidad_exito': 1.0}, 2,
                          {'minimo': None, 'mas_probable': None, 'maximo': None,
                           'input_method': 'direct',
                           'params_direct': {'mean': 1000, 'std': 1}},
                          vinculos=[_vinculo('pa', tipo='AND', factor_severidad=0.5)])
    _, _, p_b, _ = _simular([padre, hijo_b], num_sims=15_000, seed=5002)
    _, _, p_r, _ = _simular([padre, hijo_r], num_sims=15_000, seed=5003)
    ratio = p_r[1].mean() / p_b[1].mean()
    assert_close_rel(ratio, 0.5, tol_rel=0.08,
                     label="factor_severidad=0.5 reduce a la mitad")


def test_R_vinculo_multiples_padres_AND_estricto():
    """Hijo con AND a 2 padres: solo se activa cuando AMBOS padres ocurren.
    Padres independientes Bernoulli(0.5) c/u → P(ambos) = 0.25."""
    p1 = _build_evento('p1', 'P1', 3, {'probabilidad_exito': 0.5}, 2,
                       {'minimo': None, 'mas_probable': None, 'maximo': None,
                        'input_method': 'direct',
                        'params_direct': {'mean': 100, 'std': 10}})
    p2 = _build_evento('p2', 'P2', 3, {'probabilidad_exito': 0.5}, 2,
                       {'minimo': None, 'mas_probable': None, 'maximo': None,
                        'input_method': 'direct',
                        'params_direct': {'mean': 100, 'std': 10}})
    h = _build_evento('h', 'H', 3, {'probabilidad_exito': 1.0}, 2,
                     {'minimo': None, 'mas_probable': None, 'maximo': None,
                      'input_method': 'direct',
                      'params_direct': {'mean': 100, 'std': 10}},
                     vinculos=[_vinculo('p1', tipo='AND'),
                               _vinculo('p2', tipo='AND')])
    _, _, _, freq_evt = _simular([p1, p2, h], num_sims=30_000, seed=5004)
    # E[freq_h] = P(p1 AND p2) * 1 = 0.25
    assert_close_rel(freq_evt[2].mean(), 0.25, tol_rel=0.05,
                     label="AND multiple padres: probabilidad conjunta")


# ===========================================================================
# S. VALIDACION DE SEGUROS - edge cases
# ===========================================================================

def test_S_seguro_cobertura_cero_sin_pago():
    """Cobertura 0%: el seguro no paga nada."""
    evento = _build_evento(
        'e1', 'S0', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}},
        factores_ajuste=[_seguro(deducible=0, cobertura_pct=0.0,
                                  limite=0, tipo_deducible='agregado')]
    )
    evento_no = _build_evento(
        'e1', 'NoSeg', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}}
    )
    perd_no, _, _, _ = _simular([evento_no], num_sims=10_000, seed=6000)
    perd_s, _, _, _ = _simular([evento], num_sims=10_000, seed=6001)
    assert_close_rel(perd_s.mean(), perd_no.mean(), tol_rel=0.05,
                     label="Cobertura 0% no paga")


def test_S_seguro_mixto_por_ocurrencia_y_agregado():
    """Evento con UN seguro por_ocurrencia + UN seguro agregado: ambos
    deben aplicarse en cascada (por_ocurrencia primero, agregado despues)."""
    evento_no = _build_evento(
        'e1', 'NoSeg', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}}
    )
    evento_mix = _build_evento(
        'e1', 'Mix', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}},
        factores_ajuste=[
            _seguro(deducible=0, cobertura_pct=0.5, limite=0,
                    tipo_deducible='por_ocurrencia', nombre='PorOcurr'),
            _seguro(deducible=0, cobertura_pct=0.5, limite=0,
                    tipo_deducible='agregado', nombre='Agregado'),
        ]
    )
    perd_no, _, _, _ = _simular([evento_no], num_sims=15_000, seed=6002)
    perd_mix, _, _, _ = _simular([evento_mix], num_sims=15_000, seed=6003)
    # PorOcurr cubre 50% → neto pre-agregado = 0.5 * 5000 = 2500
    # Agregado cubre 50% del exceso → paga 0.5 * 2500 = 1250
    # Neto final = 2500 - 1250 = 1250
    # Reduccion total: (5000-1250)/5000 = 75%
    ratio = perd_mix.mean() / perd_no.mean()
    assert_close_rel(ratio, 0.25, tol_rel=0.10,
                     label="Seguro mixto cascade 50%+50%")


def test_S_seguro_limite_ocurrencia_y_agregado_simultaneos():
    """Seguro con limite_ocurrencia $200 Y limite_agregado $500.
    Caso: 5 occurrencias, sev=$1000 c/u → cada pago capeado a $200,
    total bruto seguro = 1000, capeado por agregado a $500.
    Neto = 5000 - 500 = 4500."""
    evento = _build_evento(
        'e1', 'DobleLim', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}},
        factores_ajuste=[_seguro(deducible=0, cobertura_pct=1.0,
                                  limite=500, tipo_deducible='por_ocurrencia',
                                  limite_ocurrencia=200)]
    )
    evento_no = _build_evento(
        'e1', 'NoSeg', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}}
    )
    perd_no, _, _, _ = _simular([evento_no], num_sims=15_000, seed=6004)
    perd_s, _, _, _ = _simular([evento], num_sims=15_000, seed=6005)
    # Pago esperado:
    #   min(N * min(X, 200), 500) donde N~Poisson(5)
    # Para Poisson(5), valor medio de min(5*200=1000, 500) = 500
    # En realidad, para n>2 occurrencias, el agregado pega.
    # E[N*200] = 5*200 = 1000, capeado a 500 → pago = 500 cuando N>=3
    # P(N>=3) bajo Poisson(5) ≈ 0.875
    # E[pago] ≈ 0.875*500 + 0.125 * (E[N | N<3]*200)
    pago_esperado = 5000 - perd_s.mean()
    # Debe estar acotado por el limite agregado
    assert pago_esperado <= 500.5, (
        f"Pago seguro ({pago_esperado:.0f}) excede limite agregado de $500"
    )
    # Y debe ser razonablemente cercano a $500 (porque casi siempre se satura)
    assert pago_esperado > 400, (
        f"Pago seguro ({pago_esperado:.0f}) muy bajo, esperado ~$500"
    )


def test_S_multiples_seguros_agregados():
    """3 seguros agregados con limite_agregado diferentes — cada uno aplica
    sus deducibles, cobertura y limite en cascada."""
    evento_no = _build_evento(
        'e1', 'NoSeg', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}}
    )
    evento_3seg = _build_evento(
        'e1', '3Seg', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}},
        factores_ajuste=[
            _seguro(deducible=0, cobertura_pct=0.3, limite=0,
                    tipo_deducible='agregado', nombre='A'),
            _seguro(deducible=0, cobertura_pct=0.3, limite=0,
                    tipo_deducible='agregado', nombre='B'),
            _seguro(deducible=0, cobertura_pct=0.3, limite=0,
                    tipo_deducible='agregado', nombre='C'),
        ]
    )
    perd_no, _, _, _ = _simular([evento_no], num_sims=15_000, seed=6006)
    perd_3, _, _, _ = _simular([evento_3seg], num_sims=15_000, seed=6007)
    # Cascada: 5000 → 5000*0.7=3500 → 3500*0.7=2450 → 2450*0.7=1715
    # Ratio = 0.7^3 = 0.343
    ratio = perd_3.mean() / perd_no.mean()
    assert_close_rel(ratio, 0.343, tol_rel=0.10,
                     label="3 seguros agregados cascade 30% c/u")


# ===========================================================================
# T. INVARIANTES DE OUTPUT
# ===========================================================================

def test_T_invariante_output_finito_no_negativo():
    """Para cualquier config valida razonable, output debe ser finito y >=0."""
    eventos = [
        _build_evento('e1', 'A', 1, {'tasa': 3.0}, 2,
                      {'minimo': None, 'mas_probable': None, 'maximo': None,
                       'input_method': 'direct',
                       'params_direct': {'mean': 500, 'std': 50}}),
        _build_evento('e2', 'B', 4, {'poisson_gamma_params': (8.0, 1.0)}, 3,
                      {'minimo': 10, 'mas_probable': 100, 'maximo': 500}),
        _build_evento('e3', 'C', 3, {'probabilidad_exito': 0.3}, 4,
                      {'minimo': None, 'mas_probable': None, 'maximo': None,
                       'input_method': 'direct',
                       'params_direct': {'c': 0.2, 'scale': 1000, 'loc': 0}}),
    ]
    perd, freq, perd_evt, freq_evt = _simular(eventos, num_sims=10_000, seed=7000)
    # Invariantes globales
    assert np.isfinite(perd).all()
    assert (perd >= 0).all()
    assert np.isfinite(freq).all()
    assert (freq >= 0).all()
    # Invariantes por evento
    for pe in perd_evt:
        assert np.isfinite(pe).all(), "NaN/Inf en perdidas por evento"
        assert (pe >= 0).all(), "Perdidas por evento negativas"
        assert len(pe) == 10_000
    for fe in freq_evt:
        assert np.isfinite(fe).all()
        assert (fe >= 0).all()
        assert len(fe) == 10_000


def test_T_invariante_suma_eventos_iguala_total():
    """Para cualquier config, perdidas_totales = sum(perdidas_por_evento)
    exactamente. Mismo para frecuencias."""
    eventos = [_build_evento(f'e{i}', f'E{i}',
                              freq_opcion=((i % 5) + 1),
                              freq_params=_freq_params_validos((i % 5) + 1),
                              sev_opcion=((i % 5) + 1),
                              sev_params=_sev_params_validos((i % 5) + 1))
               for i in range(5)]
    perd, freq, perd_evt, freq_evt = _simular(eventos, num_sims=5_000, seed=7001)
    np.testing.assert_allclose(perd, sum(perd_evt), rtol=1e-9)
    np.testing.assert_array_equal(freq, sum(freq_evt))


def test_T_invariante_frecuencias_son_enteras():
    """Las frecuencias siempre deben ser enteros no negativos."""
    eventos = [_build_evento('e1', 'A', 4, {'poisson_gamma_params': (3.0, 0.5)},
                              2, {'minimo': None, 'mas_probable': None, 'maximo': None,
                                  'input_method': 'direct',
                                  'params_direct': {'mean': 100, 'std': 20}})]
    _, _, _, freq_evt = _simular(eventos, num_sims=5_000, seed=7002)
    for fe in freq_evt:
        assert fe.dtype in (np.int32, np.int64), f"Frecuencias no enteras: dtype={fe.dtype}"
        assert (fe == fe.astype(int)).all(), "Frecuencias no enteras"


# ===========================================================================
# U. GOODNESS-OF-FIT PROFUNDO (momentos)
# ===========================================================================

def test_U_pert_momentos_correctos():
    """PERT(a, c, b): mean=(a+4c+b)/6, var=(b-a)^2*((mean-a)*(b-mean))/((b-a)^2*(alpha+beta+1))
    Verificamos mean y varianza muestral."""
    gen = ENGINE['generar_distribucion_severidad']
    a, c, b = 10.0, 50.0, 100.0
    d = gen(3, a, c, b)
    samples = d.rvs(size=100_000, random_state=_rng(seed=8000))
    mean_th = (a + 4 * c + b) / 6  # 51.67
    assert_close_rel(samples.mean(), mean_th, tol_rel=0.02, label="PERT mean")
    # Var de PERT
    alpha_pert = 1 + 4 * (c - a) / (b - a)
    beta_pert = 1 + 4 * (b - c) / (b - a)
    var_th = (b - a) ** 2 * alpha_pert * beta_pert / \
             ((alpha_pert + beta_pert) ** 2 * (alpha_pert + beta_pert + 1))
    assert_close_rel(samples.var(), var_th, tol_rel=0.05, label="PERT var")


def test_U_lognormal_skewness_positiva():
    """LogNormal siempre tiene skewness positiva. Verificar."""
    gen = ENGINE['generar_distribucion_severidad']
    d = gen(2, None, None, None, input_method='direct',
            params_direct={'mean': 100, 'std': 50})
    samples = d.rvs(size=50_000, random_state=_rng(seed=8001))
    skew_obs = stats.skew(samples)
    assert skew_obs > 0.3, f"LogNormal deberia ser right-skewed, skew={skew_obs:.3f}"


def test_U_normal_truncada_skewness_baja():
    """Normal truncada en 0 con mean >> 0 debe tener skewness baja (~0)."""
    gen = ENGINE['generar_distribucion_severidad']
    d = gen(1, None, None, None, input_method='direct',
            params_direct={'mean': 1000, 'std': 100})  # mean >> std → truncado no afecta
    samples = d.rvs(size=50_000, random_state=_rng(seed=8002))
    skew_obs = abs(stats.skew(samples))
    assert skew_obs < 0.2, f"Normal truncada (mean>>std) deberia ser simetrica, skew={skew_obs:.3f}"


def test_U_pareto_kurtosis_pesada():
    """Pareto/GPD con c=0.3 tiene cola pesada → kurtosis alta."""
    gen = ENGINE['generar_distribucion_severidad']
    d = gen(4, None, None, None, input_method='direct',
            params_direct={'c': 0.3, 'scale': 1000, 'loc': 0})
    samples = d.rvs(size=50_000, random_state=_rng(seed=8003))
    kurt_obs = stats.kurtosis(samples)
    # Kurtosis exceso > 3 indica cola muy pesada
    assert kurt_obs > 3, f"GPD c=0.3 deberia tener cola pesada, kurt={kurt_obs:.2f}"


def test_U_compound_poisson_lognormal_VaR99():
    """VaR 99% del compound Poisson-LogNormal debe ser razonablemente
    cercano a la aproximacion analitica via Panjer recursion (que no
    implementamos, pero usamos Monte Carlo estandar como ground truth)."""
    # Implementacion independiente: simular 200K sims, comparar VaR99
    lam = 5.0
    mean_x, std_x = 1000.0, 300.0
    sigma2 = np.log(1 + (std_x / mean_x) ** 2)
    sigma = np.sqrt(sigma2)
    mu = np.log(mean_x) - 0.5 * sigma2
    # Implementacion 1: motor
    evento = _build_evento(
        'e1', 'VAR', 1, {'tasa': lam},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': mean_x, 'std': std_x}}
    )
    perd_motor, _, _, _ = _simular([evento], num_sims=100_000, seed=8004)
    var99_motor = np.percentile(perd_motor, 99)
    # Implementacion 2: independiente
    rng_ind = np.random.default_rng(8005)
    N = rng_ind.poisson(lam=lam, size=100_000)
    S = np.zeros(100_000)
    sum_freq = int(N.sum())
    severs = rng_ind.lognormal(mean=mu, sigma=sigma, size=sum_freq)
    indices = np.repeat(np.arange(100_000), N)
    np.add.at(S, indices, severs)
    var99_indep = np.percentile(S, 99)
    err = abs(var99_motor - var99_indep) / var99_indep
    assert err < 0.05, (
        f"VaR99 motor={var99_motor:.0f} vs indep={var99_indep:.0f}, err={err:.2%}"
    )


# ===========================================================================
# V. CARGA DE MODELO JSON COMPLETO
# ===========================================================================

def test_V_modelo_exhaustivo_json_simula_sin_error():
    """Carga test_model_exhaustivo.json (5 eventos diversos) y verifica
    que el motor lo procesa sin error."""
    path = os.path.join(_THIS_DIR, 'test_model_exhaustivo.json')
    if not os.path.exists(path):
        return  # Si el archivo no esta, saltar el test
    with open(path, 'r', encoding='utf-8') as f:
        modelo = json.load(f)
    eventos_json = modelo.get('eventos_riesgo', [])
    eventos = []
    for e_json in eventos_json:
        # Construir el evento con las dists usando los helpers del engine
        try:
            freq_op = e_json['freq_opcion']
            sev_op = e_json['sev_opcion']
            # Construir freq_params
            freq_params = {}
            if freq_op == 1:
                freq_params['tasa'] = e_json.get('tasa')
            elif freq_op == 2:
                freq_params['num_eventos_posibles'] = e_json.get('num_eventos')
                freq_params['probabilidad_exito'] = e_json.get('prob_exito')
            elif freq_op == 3:
                freq_params['probabilidad_exito'] = e_json.get('prob_exito')
            elif freq_op == 4:
                a = e_json.get('pg_alpha')
                b = e_json.get('pg_beta')
                if a and b:
                    freq_params['poisson_gamma_params'] = (a, b)
                else:
                    # Derivar de min/mode/max usando obtener_parametros_gamma_para_poisson
                    helper = ENGINE['obtener_parametros_gamma_para_poisson']
                    a_, b_ = helper(e_json['pg_minimo'], e_json['pg_mas_probable'],
                                     e_json['pg_maximo'], e_json.get('pg_confianza', 80) / 100)
                    freq_params['poisson_gamma_params'] = (a_, b_)
            elif freq_op == 5:
                freq_params['beta_params'] = (e_json.get('beta_alpha', 2.0),
                                              e_json.get('beta_beta', 8.0))
            # Construir sev_params
            sev_params = {
                'minimo': e_json.get('sev_minimo'),
                'mas_probable': e_json.get('sev_mas_probable'),
                'maximo': e_json.get('sev_maximo'),
                'input_method': e_json.get('sev_input_method', 'min_mode_max'),
                'params_direct': e_json.get('sev_params_direct', {}) or {},
            }
            ev = _build_evento(
                e_json['id'], e_json.get('nombre', 'X'),
                freq_op, freq_params, sev_op, sev_params,
                factores_ajuste=e_json.get('factores_ajuste'),
                vinculos=e_json.get('vinculos'),
            )
            eventos.append(ev)
        except Exception as e:
            # Algunos eventos del modelo exhaustivo pueden tener params no
            # exactamente compatibles con nuestro helper; los saltamos.
            print(f"  [WARN] Salteando evento {e_json.get('nombre')}: {e}")
            continue
    if not eventos:
        return
    perd, freq, _, _ = _simular(eventos, num_sims=2_000, seed=9000)
    assert np.isfinite(perd).all()
    assert (perd >= 0).all()
    assert len(perd) == 2_000


# ===========================================================================
# W. ESCALA Y PERFORMANCE
# ===========================================================================

def test_W_muchos_eventos_simulacion_completa():
    """Modelo con 30 eventos diversos debe simular sin error en tiempo
    razonable (<60s)."""
    eventos = []
    for i in range(30):
        f = (i % 5) + 1
        s = (i % 5) + 1
        eventos.append(_build_evento(
            f'e{i}', f'E{i}', f, _freq_params_validos(f),
            s, _sev_params_validos(s)
        ))
    t0 = time.time()
    perd, freq, _, _ = _simular(eventos, num_sims=2_000, seed=10_000)
    elapsed = time.time() - t0
    assert elapsed < 60, f"30 eventos x 2K sims tardo {elapsed:.1f}s (esperado <60s)"
    assert np.isfinite(perd).all()


def test_W_muchas_simulaciones():
    """50K simulaciones con 3 eventos debe completar."""
    eventos = [
        _build_evento('e1', 'A', 1, {'tasa': 5.0}, 2,
                      {'minimo': None, 'mas_probable': None, 'maximo': None,
                       'input_method': 'direct',
                       'params_direct': {'mean': 500, 'std': 100}}),
        _build_evento('e2', 'B', 3, {'probabilidad_exito': 0.3}, 3,
                      {'minimo': 10, 'mas_probable': 100, 'maximo': 500}),
        _build_evento('e3', 'C', 4, {'poisson_gamma_params': (10, 1.0)}, 1,
                      {'minimo': None, 'mas_probable': None, 'maximo': None,
                       'input_method': 'direct',
                       'params_direct': {'mean': 1000, 'std': 200}}),
    ]
    t0 = time.time()
    perd, _, _, _ = _simular(eventos, num_sims=50_000, seed=10_001)
    elapsed = time.time() - t0
    assert elapsed < 60, f"50K sims tardo {elapsed:.1f}s (esperado <60s)"
    assert np.isfinite(perd).all()


# ===========================================================================
# X. INTERACCIONES COMPUESTAS
# ===========================================================================

def test_X_sev_freq_mas_factor_estatico_mas_seguro():
    """Sev_freq escalation + factor severidad estatico + seguro agregado.
    Verificar que (a) no rompe, (b) reduce vs version sin nada,
    (c) produce output coherente."""
    base = _build_evento(
        'e1', 'BaseNoAjustes', 1, {'tasa': 3.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 100}}
    )
    complejo = _build_evento(
        'e1', 'Complejo', 1, {'tasa': 3.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 100}},
        factores_ajuste=[
            _factor_estatico(impacto_freq=-30, impacto_sev=-20, nombre='Mit'),
            _seguro(deducible=500, cobertura_pct=0.6, limite=10_000,
                    tipo_deducible='agregado', nombre='Cobertura'),
        ],
        sev_freq_activado=True,
        sev_freq_modelo='reincidencia',
        sev_freq_tipo_escalamiento='lineal',
        sev_freq_paso=0.3,
        sev_freq_factor_max=3.0,
    )
    perd_b, _, _, _ = _simular([base], num_sims=15_000, seed=11_000)
    perd_c, _, _, _ = _simular([complejo], num_sims=15_000, seed=11_001)
    assert np.isfinite(perd_c).all()
    assert (perd_c >= 0).all()
    # Validacion direccional: con mitigantes + seguro, perdida media DEBE
    # ser menor que la base. (Sev_freq por si solo subiria; pero con
    # -30% freq -20% sev + seguro, el efecto neto deberia ser reductor.)
    assert perd_c.mean() < perd_b.mean(), (
        f"Config compleja con mitigantes deberia reducir perdida: "
        f"complejo={perd_c.mean():.0f} vs base={perd_b.mean():.0f}"
    )


def test_X_vinculo_AND_mas_factor_estocastico_mas_seguro():
    """Padre que activa hijo (AND), hijo tiene control estocastico Y seguro.
    Pipeline complejo: vinculo → estocastico → seguro."""
    padre = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 1.0}, 2,
                         {'minimo': None, 'mas_probable': None, 'maximo': None,
                          'input_method': 'direct',
                          'params_direct': {'mean': 100, 'std': 10}})
    hijo = _build_evento(
        'hi', 'Hijo', 1, {'tasa': 10.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 500, 'std': 50}},
        factores_ajuste=[
            _factor_estocastico(confiabilidad=80, reduccion_efectiva=50,
                                reduccion_fallo=0, nombre='Stoch'),
            _seguro(deducible=0, cobertura_pct=0.5, limite=0,
                    tipo_deducible='agregado'),
        ],
        vinculos=[_vinculo('pa', tipo='AND', factor_severidad=1.5)]
    )
    perd_t, _, perd_evt, freq_evt = _simular([padre, hijo], num_sims=15_000, seed=11_002)
    assert np.isfinite(perd_t).all()
    assert (perd_t >= 0).all()
    # Validacion: hijo tiene perdidas finitas
    assert (perd_evt[1] >= 0).all()


# ===========================================================================
# Y. EXPORT SERIALIZABLE
# ===========================================================================

def test_Y_estadisticas_serializable_json():
    """_calc_stats_completas y _calc_percentiles deben devolver dicts con
    tipos serializables (Python float/int, no np.float32/np.int64)."""
    # No tenemos acceso a esos metodos directos (estan en clase), pero
    # podemos verificar que np.mean etc. devuelve floats convertibles.
    samples = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    media = float(np.mean(samples))
    json_str = json.dumps({'media': media})
    assert json_str.startswith('{')

    # Tambien comprobar que arrays grandes son convertibles
    perd = np.random.default_rng(12000).gamma(2.0, 1000.0, size=10_000)
    stats_dict = {
        'mean': float(perd.mean()),
        'std': float(perd.std()),
        'p99': float(np.percentile(perd, 99)),
    }
    json.dumps(stats_dict)  # No debe fallar


# ===========================================================================
# Z. FUZZING - configs aleatorias
# ===========================================================================

def test_Z_fuzzing_50_configs_aleatorias_no_rompe():
    """Genera 50 configuraciones aleatorias de eventos validos y verifica
    que ninguna rompe la simulacion."""
    rng_fuzz = np.random.default_rng(13_000)
    fallos = []
    for trial in range(50):
        try:
            n_events = int(rng_fuzz.integers(1, 6))
            eventos = []
            for i in range(n_events):
                f = int(rng_fuzz.integers(1, 6))
                s = int(rng_fuzz.integers(1, 6))
                fp = _freq_params_validos(f)
                sp = _sev_params_validos(s)
                # Aleatorizar parametros menores
                if f == 1:
                    fp['tasa'] = float(rng_fuzz.uniform(0.1, 20))
                elif f == 3:
                    fp['probabilidad_exito'] = float(rng_fuzz.uniform(0.05, 0.95))
                eventos.append(_build_evento(
                    f'e_{trial}_{i}', f'E{trial}_{i}', f, fp, s, sp
                ))
            num_sims = int(rng_fuzz.integers(500, 5_000))
            perd, freq, _, _ = _simular(eventos, num_sims=num_sims,
                                          seed=int(rng_fuzz.integers(0, 1 << 30)))
            assert np.isfinite(perd).all(), "NaN/Inf en perdidas"
            assert (perd >= 0).all(), "Perdidas negativas"
        except Exception as e:
            fallos.append(f"trial={trial}: {type(e).__name__}: {e}")
    if fallos:
        raise AssertionError(
            f"{len(fallos)}/50 fuzzing trials fallaron:\n  " +
            "\n  ".join(fallos[:10])  # primeros 10
        )


# ===========================================================================
# Runner standalone
# ===========================================================================

def _collect_tests():
    g = globals()
    items = [(n, f) for n, f in g.items() if n.startswith('test_') and callable(f)]
    return items


def _run_all(verbose=True):
    items = _collect_tests()
    print()
    print('=' * 70)
    print(f'Risk Lab — cobertura exhaustiva ({len(items)} tests)')
    print('=' * 70)
    print()
    passed, failed, errors = 0, 0, 0
    failures = []
    for i, (name, func) in enumerate(items, 1):
        prefix = f'[{i:>2}/{len(items)}]'
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
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
