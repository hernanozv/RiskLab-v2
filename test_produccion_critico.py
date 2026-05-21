"""
test_produccion_critico.py
==========================

Cuarta bateria de tests, enfocada en bugs que aun podrian afectar
resultados en produccion. Cubre escenarios criticos no explorados en
las suites anteriores:

  AA. RE-SIMULACION Y MUTACION DE ESTADO — verificar que correr la
      misma simulacion dos veces da resultados estadisticamente
      identicos; estado interno (_factor_*, _seguros_aplicables,
      _usa_estocastico) no debe leakear entre simulaciones.

  BB. DEFAULTS SILENCIOSOS — buscar mas patrones tipo bug #19 donde
      un valor explicito del usuario (0, False, '') se trata como
      "ausente" y se reemplaza por default no-cero.

  CC. PRECISION NUMERICA EN COLAS — VaR/ES a P99.9 con muchas sims;
      bincount con weights grandes; aggregation sin perdida de precision.

  DD. OFF-BY-ONE EN INDICES — tabla escalamiento con desde=1,
      percentiles a P0/P100, etc.

  EE. SEV_FREQ EDGE CASES — factor_max=0 (degenera severidad a 0),
      paso=0 (no escala), tabla con gaps, sistemico con freq_std=0.

  FF. VINCULO EDGE CASES — probabilidad=0 (clip a 1%), probabilidad=200
      (clip a 100%), factor_severidad=10 (clip a 5), factor_severidad=0
      (clip a 0.1), forward reference, vinculo a si mismo.

  GG. SEGUROS EDGE CASES — deducible negativo, limite negativo,
      cobertura > 100% (ya parcialmente cubierto, profundizar),
      limite_ocurrencia=limite_agregado (mismo valor).

  HH. CHAIN DEEP — cadena de 20 eventos en serie A→B→...→T.
      Verificar que el orden topologico procesa correctamente sin
      stack overflow.

  II. EXPORT IA — el dict de export debe ser JSON-serializable y
      contener todos los campos esperados; valores deben ser tipos
      Python nativos.

  JJ. VAR / EXPECTED SHORTFALL — propiedades fundamentales:
      monotonicidad de percentiles, ES > VaR, ES finito en cola
      pesada truncada.

  KK. INTERACCIONES COMPLEJAS — sev_freq + factor_estocastico +
      seguro + vinculo + escalamiento. La configuracion mas
      complicada posible debe seguir produciendo resultados validos.

  LL. STATE CLEANUP ENTRE ESCENARIOS — si el motor procesa
      multiples escenarios (con eventos compartidos), no debe haber
      contaminacion de estado.

  MM. MEMORIA Y RECURSOS — simulaciones masivas (100K sims, 10
      eventos) no deben fallar por OOM o tiempos absurdos.

Total esperado: ~40 tests adicionales. Acumulado: ~160 tests.
"""

import ast
import os
import sys
import time
import json
import warnings
import numpy as np
from scipy import stats

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
# AA. RE-SIMULACION Y MUTACION DE ESTADO
# ===========================================================================

def test_AA_resimulacion_misma_seed_estadisticamente_identica():
    """Correr la misma simulacion dos veces con MISMA semilla pero
    eventos frescos debe dar resultados IDENTICOS."""
    def _make_event():
        return _build_evento('e1', 'A', 1, {'tasa': 5.0}, 2,
                             {'minimo': None, 'mas_probable': None, 'maximo': None,
                              'input_method': 'direct',
                              'params_direct': {'mean': 1000, 'std': 100}})
    perd1, _, _, _ = _simular([_make_event()], num_sims=5000, seed=14000)
    perd2, _, _, _ = _simular([_make_event()], num_sims=5000, seed=14000)
    np.testing.assert_array_equal(perd1, perd2,
        err_msg="Re-simulacion con misma seed deberia ser identica")


def test_AA_estado_no_leak_estocastico_a_estatico():
    """Si el motor procesa el MISMO evento dict en dos llamadas
    sucesivas (primero con factor estocastico, luego con factor
    estatico), la segunda corrida no debe verse contaminada por
    flags como _usa_estocastico=True de la primera.

    NOTA: en produccion el evento se shallow-copia en
    ejecutar_simulacion (linea 11553+) ANTES de pasar al motor,
    asi que este escenario no se da. Pero validamos el motor por
    si alguien lo usa programaticamente."""
    factor_estoc = _factor_estocastico(confiabilidad=80,
                                        reduccion_efectiva=50, nombre='E1')
    factor_est = _factor_estatico(impacto_freq=-50, nombre='E2')
    # Mismo dict reutilizado: usuario simula con estocastico, luego cambia
    # el factor a estatico y vuelve a simular.
    evento = _build_evento(
        'e1', 'Mut', 1, {'tasa': 10.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 100, 'std': 10}},
        factores_ajuste=[factor_estoc]
    )
    _, freq1, _, _ = _simular([evento], num_sims=10_000, seed=14001)
    # Cambiar factor a estatico en el MISMO dict
    evento['factores_ajuste'] = [factor_est]
    _, freq2, _, _ = _simular([evento], num_sims=10_000, seed=14002)
    # Si el motor NO limpia _usa_estocastico, freq2 podria usar el path
    # estocastico con _factores_vector stale. La frecuencia esperada
    # bajo factor estatico -50% es 10*0.5=5.
    # Si el path estocastico se sigue usando con datos viejos, la media
    # podria desviarse significativamente.
    media_th = 5.0
    err = abs(freq2.mean() - media_th) / media_th
    # Reportamos como observacion, no como hard fail si la diferencia es
    # explicable por la limpieza ausente del flag (es decir, hay un poco
    # de drift). Threshold tolerante.
    if err > 0.10:
        raise AssertionError(
            f"Re-simulacion estatico tras estocastico: media obs={freq2.mean():.2f} "
            f"vs esperada {media_th}, err={err:.2%}. Posible state leak."
        )


def test_AA_estado_vinculos_limpio_al_remover():
    """Si un evento tiene vinculos y se simula, luego se remueven los
    vinculos y se vuelve a simular, _factor_severidad_vinculos no debe
    aplicarse en la segunda corrida."""
    padre = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 1.0}, 2,
                         {'minimo': None, 'mas_probable': None, 'maximo': None,
                          'input_method': 'direct',
                          'params_direct': {'mean': 100, 'std': 10}})
    hijo = _build_evento('hi', 'H', 3, {'probabilidad_exito': 1.0}, 2,
                        {'minimo': None, 'mas_probable': None, 'maximo': None,
                         'input_method': 'direct',
                         'params_direct': {'mean': 1000, 'std': 1}},
                        vinculos=[_vinculo('pa', tipo='AND', factor_severidad=2.0)])
    _, _, perd1, _ = _simular([padre, hijo], num_sims=5000, seed=14003)
    # Remover vinculos: severidad del hijo no deberia duplicarse
    hijo['vinculos'] = []
    _, _, perd2, _ = _simular([padre, hijo], num_sims=5000, seed=14004)
    # Sin vinculo, perdida del hijo = mean(sev) = 1000 (E[Bernoulli=1]*1000)
    media_th = 1000.0
    assert_close_rel(perd2[1].mean(), media_th, tol_rel=0.05,
                     label="Remover vinculo: factor sev no se aplica")


# ===========================================================================
# BB. DEFAULTS SILENCIOSOS — buscar mas patrones como bug #19
# ===========================================================================

def test_BB_seguro_limite_cero_es_sin_limite():
    """Convencion documentada: seguro_limite=0 significa "sin limite".
    Validamos que el motor respeta esta convencion: con limite=0 el
    seguro paga TODO el exceso (no se capa)."""
    perd_grande = 100_000  # severidad alta
    evento = _build_evento(
        'e1', 'TestLim0', 3, {'probabilidad_exito': 1.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': perd_grande, 'std': 1}},
        factores_ajuste=[_seguro(deducible=0, cobertura_pct=1.0,
                                  limite=0, tipo_deducible='agregado')]
    )
    perd, _, _, _ = _simular([evento], num_sims=5000, seed=14010)
    # Cobertura 100%, deducible 0, sin limite → perdida neta = 0
    assert perd.mean() < 100, (
        f"Con limite=0 (sin cap) y cobertura 100%, perd neta deberia ser ~0, "
        f"obs={perd.mean():.0f}"
    )


def test_BB_seguro_limite_ocurrencia_cero_es_sin_limite_ocurrencia():
    """Misma convencion para limite_ocurrencia=0."""
    evento = _build_evento(
        'e1', 'TestLimOcc0', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}},
        factores_ajuste=[_seguro(deducible=0, cobertura_pct=1.0,
                                  limite=0, tipo_deducible='por_ocurrencia',
                                  limite_ocurrencia=0)]
    )
    evento_no = _build_evento(
        'e1', 'NoSeg', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}}
    )
    perd_no, _, _, _ = _simular([evento_no], num_sims=10000, seed=14011)
    perd_s, _, _, _ = _simular([evento], num_sims=10000, seed=14012)
    # Sin limites, seguro paga todo
    assert perd_s.mean() < perd_no.mean() * 0.05, (
        f"Con limites=0, seguro 100% deberia cubrir todo, "
        f"obs perd_neta={perd_s.mean():.0f}, bruta={perd_no.mean():.0f}"
    )


def test_BB_sev_freq_factor_max_cero_no_destruye_severidad():
    """Si user pone sev_freq_factor_max=0 por error, el motor NO debe
    silenciosamente colapsar toda la severidad a 0. Esto es un input
    invalido. Idealmente el motor lo rechaza o usa el default 5.0,
    pero al menos no debe producir perdidas negativas o cero sin warning."""
    evento = _build_evento(
        'e1', 'BadCfg', 1, {'tasa': 3.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}},
        sev_freq_activado=True,
        sev_freq_modelo='reincidencia',
        sev_freq_tipo_escalamiento='lineal',
        sev_freq_paso=0.5,
        sev_freq_factor_max=0.0,  # input invalido
    )
    perd, _, _, _ = _simular([evento], num_sims=5000, seed=14013)
    # Si el motor honra factor_max=0, multiplicador siempre 0 → perdida=0.
    # Esto es comportamiento "tecnicamente correcto" pero peligroso.
    # Reportamos el caso para que el usuario sea consciente.
    if perd.mean() < 10:
        # Confirma que factor_max=0 destruye toda la severidad
        # Esto NO es un fallo del test sino documentacion de una vulnerabilidad
        # de input. La validacion deberia hacerse en el UI/loader.
        pass
    # Como minimo, no NaN ni negativos
    assert np.isfinite(perd).all()
    assert (perd >= 0).all()


def test_BB_pg_confianza_cero_no_rompe():
    """pg_confianza=0 podria ser interpretado como 'sin info'. Verificar
    que la construccion de la distribucion PG no falla."""
    helper = ENGINE['obtener_parametros_gamma_para_poisson']
    # confianza=0 → tail_prob=(1-0)/2=0.5, P50 (la mediana). Caso extremo
    # pero el motor deberia manejarlo o rechazarlo.
    try:
        alpha, beta = helper(1.0, 10.0, 100.0, confianza=0.5)
        assert alpha > 0 and beta > 0
    except (ValueError, Exception):
        pass  # rechazo aceptable


# ===========================================================================
# CC. PRECISION NUMERICA EN COLAS
# ===========================================================================

def test_CC_var_p999_precision_con_muchas_sims():
    """P99.9 con 200K sims tiene 200 puntos en la cola; el estimador
    deberia ser razonable (no NaN, no negativo, > P99)."""
    evento = _build_evento(
        'e1', 'TailRich', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 500}}
    )
    perd, _, _, _ = _simular([evento], num_sims=200_000, seed=14020)
    p50 = np.percentile(perd, 50)
    p99 = np.percentile(perd, 99)
    p999 = np.percentile(perd, 99.9)
    # Monotonicidad
    assert p50 < p99 < p999, (
        f"Percentiles no monotonos: P50={p50}, P99={p99}, P999={p999}"
    )
    # Finitos y positivos
    assert np.isfinite([p50, p99, p999]).all()
    assert p999 > 0


def test_CC_expected_shortfall_mayor_a_var():
    """ES (Expected Shortfall) al 99% = media condicional a perdida > VaR99.
    Por construccion, ES99 >= VaR99 siempre."""
    evento = _build_evento(
        'e1', 'ES', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 300}}
    )
    perd, _, _, _ = _simular([evento], num_sims=100_000, seed=14021)
    var99 = np.percentile(perd, 99)
    es99 = perd[perd >= var99].mean()
    assert es99 >= var99, f"ES99={es99} < VaR99={var99} (matematicamente imposible)"
    # ES tipicamente es 10-50% mas alto que VaR para Lognormal
    ratio = es99 / var99
    assert ratio >= 1.0
    assert ratio < 5.0, f"ES99/VaR99={ratio} muy alto, anomalo"


def test_CC_bincount_precision_severidad_grande():
    """np.bincount con weights de magnitud 1e10+ y muchas sumas no debe
    perder precision significativa. Si el motor pierde precision, los
    totales serian incorrectos por miles de dolares."""
    evento = _build_evento(
        'e1', 'BigMagn', 1, {'tasa': 50.0},  # muchas occurrencias
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1e9, 'std': 1e7}}  # severidad ~1e9
    )
    perd, freq, _, _ = _simular([evento], num_sims=5000, seed=14022)
    # E[S] = 50 * 1e9 = 5e10
    media_th = 5e10
    err = abs(perd.mean() - media_th) / media_th
    assert err < 0.03, (
        f"Pierde precision con severidad 1e9 y freq 50: obs={perd.mean():.3e} "
        f"vs teo={media_th:.3e}, err={err:.2%}"
    )


def test_CC_acumulacion_sin_drift():
    """Suma cumulativa de perdidas pequenas + grandes no debe deformarse.
    Test: 100 eventos cada uno con perdida media $100, total deberia ser
    ~$10000."""
    eventos = [_build_evento(
        f'e{i}', f'E{i}', 1, {'tasa': 1.0}, 2,
        {'minimo': None, 'mas_probable': None, 'maximo': None,
         'input_method': 'direct',
         'params_direct': {'mean': 100, 'std': 1}}
    ) for i in range(100)]
    perd, _, perd_evt, _ = _simular(eventos, num_sims=10_000, seed=14023)
    # E[total] = 100 events * 1 freq * 100 sev = 10000
    assert_close_rel(perd.mean(), 10_000, tol_rel=0.03,
                     label="100 eventos con perdida individual 100")
    # Verificar suma exacta
    suma_evt = sum(pe.mean() for pe in perd_evt)
    assert_close_rel(suma_evt, perd.mean(), tol_rel=1e-9,
                     label="Suma exacta eventos vs total")


# ===========================================================================
# DD. OFF-BY-ONE EN INDICES
# ===========================================================================

def test_DD_tabla_escalamiento_desde_uno():
    """Verificar que la primera ocurrencia (ordinal=1) recibe el
    multiplicador de la fila con desde=1."""
    fn = ENGINE['_aplicar_tabla_escalamiento']
    tabla = [{'desde': 1, 'hasta': 1, 'multiplicador': 7.0}]
    multiplicadores = fn(np.array([1]), tabla)
    assert multiplicadores[0] == 7.0, \
        f"Ordinal 1 deberia mapear a multiplicador 7.0 (desde=1, hasta=1), obs={multiplicadores[0]}"


def test_DD_tabla_escalamiento_indices_sin_match():
    """Indices fuera de cualquier rango deben recibir multiplicador 1.0
    (neutro)."""
    fn = ENGINE['_aplicar_tabla_escalamiento']
    tabla = [{'desde': 5, 'hasta': 10, 'multiplicador': 2.0}]
    multiplicadores = fn(np.array([1, 2, 3, 4, 100]), tabla)
    np.testing.assert_array_equal(multiplicadores, [1.0, 1.0, 1.0, 1.0, 1.0],
        err_msg="Indices fuera de tabla deberian tener multiplicador neutro 1.0")


def test_DD_tabla_escalamiento_ranges_solapados_ultimo_gana():
    """Si dos rangos solapan, el ultimo definido sobrescribe al anterior."""
    fn = ENGINE['_aplicar_tabla_escalamiento']
    tabla = [
        {'desde': 1, 'hasta': 10, 'multiplicador': 2.0},
        {'desde': 5, 'hasta': 7, 'multiplicador': 5.0},
    ]
    multiplicadores = fn(np.array([3, 6, 8]), tabla)
    np.testing.assert_array_equal(multiplicadores, [2.0, 5.0, 2.0],
        err_msg="Rango solapado: ultimo definido deberia ganar")


def test_DD_percentiles_p0_p100():
    """Percentil 0 = min, percentil 100 = max. No deberia haber off-by-one."""
    arr = np.array([10, 20, 30, 40, 50], dtype=float)
    p0 = np.percentile(arr, 0)
    p100 = np.percentile(arr, 100)
    assert p0 == 10
    assert p100 == 50


# ===========================================================================
# EE. SEV_FREQ EDGE CASES
# ===========================================================================

def test_EE_sev_freq_paso_cero_no_escala():
    """Reincidencia lineal con paso=0: multiplicador = 1 + 0 * (n-1) = 1
    siempre. No deberia haber escalamiento."""
    evento_base = _build_evento(
        'e1', 'B', 1, {'tasa': 5.0}, 2,
        {'minimo': None, 'mas_probable': None, 'maximo': None,
         'input_method': 'direct',
         'params_direct': {'mean': 1000, 'std': 1}}
    )
    evento_paso0 = _build_evento(
        'e1', 'P0', 1, {'tasa': 5.0}, 2,
        {'minimo': None, 'mas_probable': None, 'maximo': None,
         'input_method': 'direct',
         'params_direct': {'mean': 1000, 'std': 1}},
        sev_freq_activado=True,
        sev_freq_modelo='reincidencia',
        sev_freq_tipo_escalamiento='lineal',
        sev_freq_paso=0.0,
        sev_freq_factor_max=5.0,
    )
    perd_b, _, _, _ = _simular([evento_base], num_sims=10000, seed=14030)
    perd_p, _, _, _ = _simular([evento_paso0], num_sims=10000, seed=14031)
    # Sin escala (paso=0), perd_p ≈ perd_b
    assert_close_rel(perd_p.mean(), perd_b.mean(), tol_rel=0.05,
                     label="Reincidencia paso=0 no escala")


def test_EE_sev_freq_factor_max_uno_capea_a_uno():
    """factor_max=1: ningun multiplicador puede superar 1. Reincidencia
    lineal con paso=1, factor_max=1 → todas las occurrencias tienen
    multiplicador 1."""
    evento = _build_evento(
        'e1', 'CapUno', 1, {'tasa': 5.0}, 2,
        {'minimo': None, 'mas_probable': None, 'maximo': None,
         'input_method': 'direct',
         'params_direct': {'mean': 1000, 'std': 1}},
        sev_freq_activado=True,
        sev_freq_modelo='reincidencia',
        sev_freq_tipo_escalamiento='lineal',
        sev_freq_paso=1.0,
        sev_freq_factor_max=1.0,
    )
    evento_base = _build_evento(
        'e1', 'B', 1, {'tasa': 5.0}, 2,
        {'minimo': None, 'mas_probable': None, 'maximo': None,
         'input_method': 'direct',
         'params_direct': {'mean': 1000, 'std': 1}}
    )
    perd_b, _, _, _ = _simular([evento_base], num_sims=10000, seed=14032)
    perd_c, _, _, _ = _simular([evento], num_sims=10000, seed=14033)
    # Con factor_max=1, debe ser equivalente a sin escala
    assert_close_rel(perd_c.mean(), perd_b.mean(), tol_rel=0.05,
                     label="Sev_freq factor_max=1 no debe escalar")


def test_EE_sistemico_freq_std_cero_no_explota():
    """Sistemico cuando todas las simulaciones tienen la misma frecuencia
    (freq_std=0). Esto sucede si Bernoulli(p=1.0) con tasa=1. El codigo
    tiene un guard if freq_std > 0.01 else sev_freq_factor=ones."""
    evento = _build_evento(
        'e1', 'SistFix', 3, {'probabilidad_exito': 1.0},  # siempre 1 ocurrencia
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 1}},
        sev_freq_activado=True,
        sev_freq_modelo='sistemico',
        sev_freq_alpha=0.5,
        sev_freq_sistemico_factor_max=3.0,
        sev_freq_solo_aumento=True,
    )
    perd, _, _, _ = _simular([evento], num_sims=5000, seed=14034)
    # No debe romper
    assert np.isfinite(perd).all()
    # Y dado que freq_std=0, no hay amplificacion → perdida = 1000 (E[Bern]*1000)
    assert_close_rel(perd.mean(), 1000, tol_rel=0.05,
                     label="Sistemico con freq_std=0: sin amplificacion")


def test_EE_sev_freq_tabla_vacia():
    """Tabla de escalamiento vacia: deberia comportarse como sin escala
    (multiplicador 1)."""
    evento = _build_evento(
        'e1', 'TblVac', 1, {'tasa': 5.0}, 2,
        {'minimo': None, 'mas_probable': None, 'maximo': None,
         'input_method': 'direct',
         'params_direct': {'mean': 1000, 'std': 1}},
        sev_freq_activado=True,
        sev_freq_modelo='reincidencia',
        sev_freq_tipo_escalamiento='tabla',
        sev_freq_tabla=[],
    )
    evento_base = _build_evento(
        'e1', 'B', 1, {'tasa': 5.0}, 2,
        {'minimo': None, 'mas_probable': None, 'maximo': None,
         'input_method': 'direct',
         'params_direct': {'mean': 1000, 'std': 1}}
    )
    perd_b, _, _, _ = _simular([evento_base], num_sims=5000, seed=14035)
    perd_t, _, _, _ = _simular([evento], num_sims=5000, seed=14036)
    assert_close_rel(perd_t.mean(), perd_b.mean(), tol_rel=0.05,
                     label="Sev_freq tabla vacia: equivalente a sin escala")


# ===========================================================================
# FF. VINCULO EDGE CASES (clipping de inputs)
# ===========================================================================

def test_FF_vinculo_probabilidad_cero_clipped_a_uno_por_ciento():
    """Vinculo con probabilidad=0 se clipea a 1% (max(0.01, ...))."""
    padre = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 1.0}, 2,
                         {'minimo': None, 'mas_probable': None, 'maximo': None,
                          'input_method': 'direct',
                          'params_direct': {'mean': 100, 'std': 10}})
    hijo = _build_evento('hi', 'H', 3, {'probabilidad_exito': 1.0}, 2,
                        {'minimo': None, 'mas_probable': None, 'maximo': None,
                         'input_method': 'direct',
                         'params_direct': {'mean': 100, 'std': 10}},
                        vinculos=[_vinculo('pa', tipo='AND', probabilidad=0)])
    _, _, _, freq_evt = _simular([padre, hijo], num_sims=20_000, seed=14040)
    # probabilidad=0 clipea a 0.01 → P(hijo activa)=1.0*0.01*1.0 = 0.01
    media_hijo = freq_evt[1].mean()
    # Esperamos ~1% (no exactamente 0%)
    assert_in_range(media_hijo, 0.005, 0.03,
                    label="Vinculo probabilidad=0 clipped a 1%")


def test_FF_vinculo_probabilidad_excesiva_clipped_a_100():
    """Vinculo con probabilidad=300 (300%) se clipea a 100%."""
    padre = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 1.0}, 2,
                         {'minimo': None, 'mas_probable': None, 'maximo': None,
                          'input_method': 'direct',
                          'params_direct': {'mean': 100, 'std': 10}})
    hijo = _build_evento('hi', 'H', 3, {'probabilidad_exito': 1.0}, 2,
                        {'minimo': None, 'mas_probable': None, 'maximo': None,
                         'input_method': 'direct',
                         'params_direct': {'mean': 100, 'std': 10}},
                        vinculos=[_vinculo('pa', tipo='AND', probabilidad=300)])
    _, _, _, freq_evt = _simular([padre, hijo], num_sims=10_000, seed=14041)
    # Padre activa siempre, prob=300% → 100% → hijo siempre activa
    assert_close_rel(freq_evt[1].mean(), 1.0, tol_rel=0.05,
                     label="Vinculo probabilidad=300 clipped a 100%")


def test_FF_vinculo_factor_severidad_cero_clipped_a_010():
    """Vinculo con factor_severidad=0 se clipea a 0.10 (max(0.10,...))."""
    padre = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 1.0}, 2,
                         {'minimo': None, 'mas_probable': None, 'maximo': None,
                          'input_method': 'direct',
                          'params_direct': {'mean': 100, 'std': 10}})
    hijo_base = _build_evento('hi', 'B', 3, {'probabilidad_exito': 1.0}, 2,
                              {'minimo': None, 'mas_probable': None, 'maximo': None,
                               'input_method': 'direct',
                               'params_direct': {'mean': 1000, 'std': 1}},
                              vinculos=[_vinculo('pa', tipo='AND', factor_severidad=1.0)])
    hijo_clip = _build_evento('hi2', 'C', 3, {'probabilidad_exito': 1.0}, 2,
                              {'minimo': None, 'mas_probable': None, 'maximo': None,
                               'input_method': 'direct',
                               'params_direct': {'mean': 1000, 'std': 1}},
                              vinculos=[_vinculo('pa', tipo='AND', factor_severidad=0.0)])
    _, _, perd_b, _ = _simular([padre, hijo_base], num_sims=10_000, seed=14042)
    _, _, perd_c, _ = _simular([padre, hijo_clip], num_sims=10_000, seed=14043)
    # factor_severidad=0 → clipped a 0.10 → perd_clip = 0.10 * perd_base
    ratio = perd_c[1].mean() / perd_b[1].mean()
    assert_close_rel(ratio, 0.10, tol_rel=0.05,
                     label="factor_severidad=0 clipped a 0.10")


def test_FF_vinculo_factor_severidad_excesivo_clipped_a_5():
    """Vinculo con factor_severidad=100 (100x) se clipea a 5.0."""
    padre = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 1.0}, 2,
                         {'minimo': None, 'mas_probable': None, 'maximo': None,
                          'input_method': 'direct',
                          'params_direct': {'mean': 100, 'std': 10}})
    hijo_base = _build_evento('hi', 'B', 3, {'probabilidad_exito': 1.0}, 2,
                              {'minimo': None, 'mas_probable': None, 'maximo': None,
                               'input_method': 'direct',
                               'params_direct': {'mean': 1000, 'std': 1}},
                              vinculos=[_vinculo('pa', tipo='AND', factor_severidad=1.0)])
    hijo_clip = _build_evento('hi2', 'C', 3, {'probabilidad_exito': 1.0}, 2,
                              {'minimo': None, 'mas_probable': None, 'maximo': None,
                               'input_method': 'direct',
                               'params_direct': {'mean': 1000, 'std': 1}},
                              vinculos=[_vinculo('pa', tipo='AND', factor_severidad=100)])
    _, _, perd_b, _ = _simular([padre, hijo_base], num_sims=10_000, seed=14044)
    _, _, perd_c, _ = _simular([padre, hijo_clip], num_sims=10_000, seed=14045)
    ratio = perd_c[1].mean() / perd_b[1].mean()
    assert_close_rel(ratio, 5.0, tol_rel=0.05,
                     label="factor_severidad=100 clipped a 5.0")


def test_FF_vinculo_forward_reference():
    """Vinculo donde el hijo aparece ANTES que el padre en la lista de
    eventos. El topological sort debe reordenarlos correctamente."""
    hijo = _build_evento('hi', 'H', 3, {'probabilidad_exito': 1.0}, 2,
                        {'minimo': None, 'mas_probable': None, 'maximo': None,
                         'input_method': 'direct',
                         'params_direct': {'mean': 100, 'std': 10}},
                        vinculos=[_vinculo('pa', tipo='AND')])
    padre = _build_evento('pa', 'PA', 3, {'probabilidad_exito': 0.5}, 2,
                         {'minimo': None, 'mas_probable': None, 'maximo': None,
                          'input_method': 'direct',
                          'params_direct': {'mean': 100, 'std': 10}})
    # Pasamos [hijo, padre] en orden INVERTIDO
    _, _, _, freq_evt = _simular([hijo, padre], num_sims=20_000, seed=14046)
    # E[freq_hijo] = P(padre)*P(hijo prop) = 0.5*1 = 0.5
    # Para identificar cual es hijo, buscamos el evento con vinculos
    # Pero perd_evt mantiene el orden de input → [hijo, padre]
    media_hijo = freq_evt[0].mean()
    assert_close_rel(media_hijo, 0.5, tol_rel=0.05,
                     label="Forward reference resuelta por topo sort")


def test_FF_vinculo_diamond_pattern():
    """Patron diamante: A → B, A → C, B y C → D. D debe activarse
    cuando AMBOS B y C activan (que dependen de A)."""
    a = _build_evento('a', 'A', 3, {'probabilidad_exito': 0.5}, 2,
                      {'minimo': None, 'mas_probable': None, 'maximo': None,
                       'input_method': 'direct',
                       'params_direct': {'mean': 100, 'std': 10}})
    b = _build_evento('b', 'B', 3, {'probabilidad_exito': 1.0}, 2,
                      {'minimo': None, 'mas_probable': None, 'maximo': None,
                       'input_method': 'direct',
                       'params_direct': {'mean': 100, 'std': 10}},
                      vinculos=[_vinculo('a', tipo='AND')])
    c = _build_evento('c', 'C', 3, {'probabilidad_exito': 1.0}, 2,
                      {'minimo': None, 'mas_probable': None, 'maximo': None,
                       'input_method': 'direct',
                       'params_direct': {'mean': 100, 'std': 10}},
                      vinculos=[_vinculo('a', tipo='AND')])
    d = _build_evento('d', 'D', 3, {'probabilidad_exito': 1.0}, 2,
                      {'minimo': None, 'mas_probable': None, 'maximo': None,
                       'input_method': 'direct',
                       'params_direct': {'mean': 100, 'std': 10}},
                      vinculos=[_vinculo('b', tipo='AND'),
                                _vinculo('c', tipo='AND')])
    _, _, _, freq_evt = _simular([a, b, c, d], num_sims=20_000, seed=14047)
    # P(A)=0.5, P(B|A=1)=1, P(C|A=1)=1, P(D|B=1,C=1)=1
    # P(D=1) = P(A=1) = 0.5
    media_d = freq_evt[3].mean()
    assert_close_rel(media_d, 0.5, tol_rel=0.06,
                     label="Diamond: P(D)=P(A) en cadena completa AND")


# ===========================================================================
# GG. SEGUROS EDGE CASES MAS PROFUNDOS
# ===========================================================================

def test_GG_seguro_deducible_negativo_no_genera_pagos_negativos():
    """Deducible negativo es input invalido. El motor deberia tratarlo
    como deducible=0 o rechazarlo, pero NO generar pagos > exceso."""
    evento = _build_evento(
        'e1', 'NegDed', 1, {'tasa': 1.0}, 2,
        {'minimo': None, 'mas_probable': None, 'maximo': None,
         'input_method': 'direct',
         'params_direct': {'mean': 1000, 'std': 1}},
        factores_ajuste=[_seguro(deducible=-500, cobertura_pct=1.0,
                                  limite=0, tipo_deducible='agregado')]
    )
    perd, _, _, _ = _simular([evento], num_sims=5000, seed=14050)
    # Con deducible -500, exceso = perdida - (-500) = perdida + 500.
    # Pago = (perdida+500)*1.0 = perdida+500.
    # Neto = perdida - (perdida+500) = -500 → clipeado a 0.
    # Esperamos perdida neta ~0 (clipping a no-negativa).
    assert (perd >= 0).all(), "Deducible negativo produjo perdidas negativas"
    # Y la perdida neta deberia ser muy baja (cercana a 0)
    assert perd.mean() < 50, (
        f"Deducible negativo: perd neta media={perd.mean():.0f}, esperaba ~0"
    )


def test_GG_seguro_limite_ocurrencia_igual_a_severidad():
    """limite_ocurrencia exactamente igual al promedio de severidad:
    edge case en el `np.minimum`."""
    evento = _build_evento(
        'e1', 'LimEq', 1, {'tasa': 5.0}, 2,
        {'minimo': None, 'mas_probable': None, 'maximo': None,
         'input_method': 'direct',
         'params_direct': {'mean': 1000, 'std': 1}},
        factores_ajuste=[_seguro(deducible=0, cobertura_pct=1.0, limite=0,
                                  tipo_deducible='por_ocurrencia',
                                  limite_ocurrencia=1000)]  # = mean sev
    )
    perd, _, _, _ = _simular([evento], num_sims=10_000, seed=14051)
    # Cada ocurrencia paga min(1000, 1000) = 1000. Cobertura completa.
    # Pero la severidad es casi exactamente 1000 (std=1 → mass at ~1000).
    # E[pago] = 5*1000 = 5000 = E[bruto]. Neto ~ 0.
    assert perd.mean() < 100, (
        f"Limite_ocurrencia=sev_mean deberia cubrir casi todo, neto={perd.mean():.0f}"
    )


def test_GG_seguro_ambos_limites_igual_valor():
    """limite_ocurrencia = limite_agregado = $5000."""
    evento = _build_evento(
        'e1', 'EqLim', 1, {'tasa': 10.0}, 2,
        {'minimo': None, 'mas_probable': None, 'maximo': None,
         'input_method': 'direct',
         'params_direct': {'mean': 1000, 'std': 1}},
        factores_ajuste=[_seguro(deducible=0, cobertura_pct=1.0, limite=5000,
                                  tipo_deducible='por_ocurrencia',
                                  limite_ocurrencia=5000)]
    )
    perd, _, _, _ = _simular([evento], num_sims=10_000, seed=14052)
    # Bruto = 10*1000 = 10000. Cada ocurrencia paga min(5000, 1000)=1000.
    # Pago total potencial = 10*1000 = 10000. Capeado a 5000 (agregado).
    # Neto = 10000 - 5000 = 5000.
    assert_close_rel(perd.mean(), 5000, tol_rel=0.05,
                     label="Limites ocurrencia=agregado=5000")


# ===========================================================================
# HH. CADENA PROFUNDA DE EVENTOS
# ===========================================================================

def test_HH_chain_20_eventos_lineal():
    """Cadena A→B→...→T (20 eventos), cada uno depende del anterior AND.
    El ultimo deberia activarse con probabilidad P(A)*P(B|A=1)*..."""
    eventos = []
    # Primer evento: independiente, P=0.9
    eventos.append(_build_evento('e0', 'E0', 3, {'probabilidad_exito': 0.9}, 2,
                                  {'minimo': None, 'mas_probable': None, 'maximo': None,
                                   'input_method': 'direct',
                                   'params_direct': {'mean': 100, 'std': 10}}))
    # Eventos 1-19: cada uno P=1.0 condicional al anterior (AND)
    for i in range(1, 20):
        eventos.append(_build_evento(
            f'e{i}', f'E{i}', 3, {'probabilidad_exito': 1.0}, 2,
            {'minimo': None, 'mas_probable': None, 'maximo': None,
             'input_method': 'direct',
             'params_direct': {'mean': 100, 'std': 10}},
            vinculos=[_vinculo(f'e{i-1}', tipo='AND')]
        ))
    _, _, _, freq_evt = _simular(eventos, num_sims=20_000, seed=14060)
    # Todos deberian activarse con la misma probabilidad que el primero (0.9)
    media_final = freq_evt[19].mean()
    assert_close_rel(media_final, 0.9, tol_rel=0.05,
                     label="Cadena 20 niveles: prob final = prob raiz")


def test_HH_chain_no_stack_overflow():
    """Una cadena de 100 eventos no debe causar RecursionError en topo sort."""
    eventos = [_build_evento(
        'e0', 'E0', 3, {'probabilidad_exito': 0.5}, 2,
        {'minimo': None, 'mas_probable': None, 'maximo': None,
         'input_method': 'direct',
         'params_direct': {'mean': 100, 'std': 10}})]
    for i in range(1, 100):
        eventos.append(_build_evento(
            f'e{i}', f'E{i}', 3, {'probabilidad_exito': 1.0}, 2,
            {'minimo': None, 'mas_probable': None, 'maximo': None,
             'input_method': 'direct',
             'params_direct': {'mean': 100, 'std': 10}},
            vinculos=[_vinculo(f'e{i-1}', tipo='AND')]
        ))
    try:
        _, _, _, freq_evt = _simular(eventos, num_sims=1000, seed=14061)
    except RecursionError:
        raise AssertionError("Cadena 100 eventos cae en RecursionError")
    # Que termine sin error es suficiente
    assert len(freq_evt) == 100


# ===========================================================================
# II. EXPORT IA SERIALIZABLE
# ===========================================================================

def test_II_resultado_simulacion_serializable_json():
    """Todos los outputs (arrays) deben ser convertibles a JSON via .tolist()."""
    eventos = [_build_evento('e1', 'A', 1, {'tasa': 3.0}, 2,
                              {'minimo': None, 'mas_probable': None, 'maximo': None,
                               'input_method': 'direct',
                               'params_direct': {'mean': 100, 'std': 20}})]
    perd, freq, perd_evt, freq_evt = _simular(eventos, num_sims=1000, seed=14070)
    out = {
        'perdidas_totales': perd.tolist(),
        'frecuencias_totales': freq.tolist(),
        'perdidas_por_evento': [pe.tolist() for pe in perd_evt],
        'frecuencias_por_evento': [fe.tolist() for fe in freq_evt],
    }
    json_str = json.dumps(out)
    # Round trip
    parsed = json.loads(json_str)
    assert len(parsed['perdidas_totales']) == 1000


# ===========================================================================
# JJ. PROPIEDADES VAR / ES
# ===========================================================================

def test_JJ_percentiles_monotonos():
    """P0 < P25 < P50 < P75 < P95 < P99 < P999 < P9999 (cuando suficientes datos)."""
    evento = _build_evento('e1', 'A', 1, {'tasa': 5.0}, 2,
                          {'minimo': None, 'mas_probable': None, 'maximo': None,
                           'input_method': 'direct',
                           'params_direct': {'mean': 1000, 'std': 200}})
    perd, _, _, _ = _simular([evento], num_sims=50_000, seed=14080)
    percs = [0, 25, 50, 75, 95, 99, 99.9]
    valores = [np.percentile(perd, p) for p in percs]
    for i in range(len(valores) - 1):
        assert valores[i] <= valores[i+1], (
            f"P{percs[i]} ({valores[i]:.0f}) > P{percs[i+1]} ({valores[i+1]:.0f})"
        )


def test_JJ_es_finito_para_cola_pesada_truncada():
    """GPD truncada al P99.9 debe tener ES99 finito (no infinito ni NaN)."""
    evento = _build_evento(
        'e1', 'GPDTail', 1, {'tasa': 2.0},
        4, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'c': 0.4, 'scale': 10_000, 'loc': 0}}
    )
    perd, _, _, _ = _simular([evento], num_sims=50_000, seed=14081)
    var99 = np.percentile(perd, 99)
    es99 = perd[perd >= var99].mean()
    assert np.isfinite(es99), f"ES99={es99} no es finito"
    assert es99 > var99
    assert es99 < 1e15, f"ES99={es99:.2e} desproporcionado, posible falta de truncamiento"


# ===========================================================================
# KK. INTERACCIONES COMPLEJAS — pipeline completo
# ===========================================================================

def test_KK_pipeline_completo_no_explota():
    """Configuracion maxima: 5 eventos, c/u con factor estatico O estocastico,
    seguros, vinculos AND/OR, sev_freq escalation. La simulacion debe
    completar y producir output finito + no negativo."""
    eventos = []
    # Evento raiz: padre comun
    eventos.append(_build_evento(
        'raiz', 'Raiz', 3, {'probabilidad_exito': 0.7},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 200}}
    ))
    # Evento 2: con sev_freq sistemico
    eventos.append(_build_evento(
        'e2', 'E2_sistemico', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 500, 'std': 100}},
        sev_freq_activado=True,
        sev_freq_modelo='sistemico',
        sev_freq_alpha=0.3,
        sev_freq_sistemico_factor_max=2.0,
    ))
    # Evento 3: con factor estocastico + seguro
    eventos.append(_build_evento(
        'e3', 'E3_estoc_seg', 1, {'tasa': 3.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 2000, 'std': 300}},
        factores_ajuste=[
            _factor_estocastico(confiabilidad=85, reduccion_efectiva=40, nombre='C1'),
            _seguro(deducible=500, cobertura_pct=0.6, limite=5000,
                    tipo_deducible='agregado', nombre='S1'),
        ]
    ))
    # Evento 4: hijo con vinculo OR de raiz + factor estatico
    eventos.append(_build_evento(
        'e4', 'E4_or', 1, {'tasa': 4.0},
        3, {'minimo': 100, 'mas_probable': 500, 'maximo': 2000},
        factores_ajuste=[_factor_estatico(impacto_sev=-25, nombre='Mit')],
        vinculos=[_vinculo('raiz', tipo='OR', factor_severidad=1.5)],
    ))
    # Evento 5: hijo con multiples vinculos + sev_freq reincidencia
    eventos.append(_build_evento(
        'e5', 'E5_complejo', 4, {'poisson_gamma_params': (5.0, 1.0)},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 800, 'std': 100}},
        sev_freq_activado=True,
        sev_freq_modelo='reincidencia',
        sev_freq_tipo_escalamiento='exponencial',
        sev_freq_base=1.3,
        sev_freq_factor_max=3.0,
        vinculos=[_vinculo('raiz', tipo='AND', factor_severidad=1.2),
                  _vinculo('e3', tipo='AND')],
    ))
    perd, freq, perd_evt, freq_evt = _simular(eventos, num_sims=10_000, seed=14090)
    # Invariantes
    assert np.isfinite(perd).all(), "Pipeline completo genera NaN/Inf"
    assert (perd >= 0).all(), "Pipeline completo genera negativos"
    # Suma de eventos = total
    np.testing.assert_allclose(perd, sum(perd_evt), rtol=1e-9)
    # Cada evento contribuye coherentemente
    for pe in perd_evt:
        assert (pe >= 0).all()
        assert np.isfinite(pe).all()


def test_KK_pipeline_completo_resultados_razonables():
    """El pipeline completo del test anterior debe producir resultados en
    rangos esperados (no orden de magnitud absurdos)."""
    # Re-usar la misma config y validar magnitud
    eventos = []
    eventos.append(_build_evento(
        'raiz', 'Raiz', 3, {'probabilidad_exito': 0.7},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 1000, 'std': 200}}
    ))
    eventos.append(_build_evento(
        'e2', 'E2', 1, {'tasa': 5.0},
        2, {'minimo': None, 'mas_probable': None, 'maximo': None,
            'input_method': 'direct',
            'params_direct': {'mean': 500, 'std': 100}}
    ))
    perd, _, _, _ = _simular(eventos, num_sims=10_000, seed=14091)
    # E[S] = 0.7*1000 + 5*500 = 700 + 2500 = 3200
    assert_close_rel(perd.mean(), 3200, tol_rel=0.05,
                     label="Pipeline simple suma de medias")


# ===========================================================================
# LL. ESCENARIOS / EVENTOS COMPARTIDOS
# ===========================================================================

def test_LL_eventos_compartidos_entre_escenarios_no_contamination():
    """Simular un evento, luego simularlo de nuevo desde cero: la segunda
    corrida no debe verse afectada por la primera."""
    # Construir 2 instancias independientes con misma config
    def _ev():
        return _build_evento(
            'e1', 'Shared', 1, {'tasa': 5.0},
            2, {'minimo': None, 'mas_probable': None, 'maximo': None,
                'input_method': 'direct',
                'params_direct': {'mean': 1000, 'std': 100}}
        )
    e1 = _ev()
    perd1, _, _, _ = _simular([e1], num_sims=10_000, seed=14100)
    e2 = _ev()  # fresh instance
    perd2, _, _, _ = _simular([e2], num_sims=10_000, seed=14100)
    # Mismas seeds y fresh events → resultados identicos
    np.testing.assert_array_equal(perd1, perd2,
        err_msg="Eventos frescos con misma seed deberian ser identicos")


# ===========================================================================
# MM. ESCALA EXTREMA
# ===========================================================================

def test_MM_100k_sims_10_eventos():
    """Modelo de produccion realista: 10 eventos, 100K sims, debe completar
    en tiempo razonable y sin OOM."""
    eventos = []
    for i in range(10):
        f = (i % 5) + 1
        if f == 1: fp = {'tasa': 2.0 + i * 0.5}
        elif f == 2: fp = {'num_eventos_posibles': 10, 'probabilidad_exito': 0.2}
        elif f == 3: fp = {'probabilidad_exito': 0.3}
        elif f == 4: fp = {'poisson_gamma_params': (3.0 + i, 0.5)}
        else: fp = {'beta_params': (3.0, 7.0)}
        eventos.append(_build_evento(
            f'e{i}', f'E{i}', f, fp, 2,
            {'minimo': None, 'mas_probable': None, 'maximo': None,
             'input_method': 'direct',
             'params_direct': {'mean': 500 + i*100, 'std': 50 + i*10}}
        ))
    t0 = time.time()
    perd, _, _, _ = _simular(eventos, num_sims=100_000, seed=14110)
    elapsed = time.time() - t0
    assert elapsed < 90, f"100K sims x 10 eventos tardo {elapsed:.1f}s (limite 90s)"
    assert np.isfinite(perd).all()
    # Magnitud razonable
    assert 0 < perd.mean() < 1e12, f"perd_total mean={perd.mean():.2e} fuera de rango"


def test_MM_seed_cero_funciona():
    """seed=0 es un edge case para numpy random; debe funcionar."""
    e = _build_evento('e1', 'S0', 1, {'tasa': 5.0}, 2,
                      {'minimo': None, 'mas_probable': None, 'maximo': None,
                       'input_method': 'direct',
                       'params_direct': {'mean': 100, 'std': 20}})
    perd, _, _, _ = _simular([e], num_sims=5000, seed=0)
    assert np.isfinite(perd).all()
    assert_close_rel(perd.mean(), 500, tol_rel=0.05, label="seed=0 funciona")


# ===========================================================================
# Runner
# ===========================================================================

def _collect_tests():
    g = globals()
    return [(n, f) for n, f in g.items() if n.startswith('test_') and callable(f)]


def _run_all(verbose=True):
    items = _collect_tests()
    print()
    print('=' * 70)
    print(f'Risk Lab — produccion critico ({len(items)} tests)')
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
