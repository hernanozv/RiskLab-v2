"""
test_sev_limite_superior_sobrevive_escalamiento.py
======================================================

Regresion para bug medio #22 (QA ronda 3): el rejection sampling que
fuerza severidad <= sev_limite_superior corria ANTES del escalamiento
de severidad por frecuencia (reincidencia/sistémico, que multiplica esa
misma pérdida hasta por sev_freq_factor_max). El resultado final podía
terminar bien por encima del cap declarado, contradiciendo la promesa
de que ninguna severidad individual supera sev_limite_superior.

El fix re-aplica el cap (clip directo) sobre el resultado YA escalado,
inmediatamente después del bloque de escalamiento.

Este test configura un evento con sev_limite_superior=1200 y
escalamiento lineal con factor_max=5 (activado, occurrence-based), de
forma que sin el fix una pérdida individual pudiera llegar hasta
~6.000 (1200 * 5). Verifica que, tras simular, NINGUNA pérdida
individual por evento supera 1200.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np

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
print("BUG MEDIO #22: sev_limite_superior debe sobrevivir al escalamiento sev_freq")
print("=" * 70)

dist_frecuencia = RLB.generar_distribucion_frecuencia(1, tasa=5.0)  # Poisson, varias ocurrencias/año
dist_severidad = RLB.generar_distribucion_severidad(
    1, None, None, None, input_method='direct', params_direct={'mean': 1100.0, 'std': 50.0}
)
evento = {
    'id': 'e1', 'nombre': 'EventoConCap', 'activo': True,
    'freq_opcion': 1, 'tasa': 5.0,
    'dist_frecuencia': dist_frecuencia,
    'sev_opcion': 1, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 1100.0, 'std': 50.0},
    'dist_severidad': dist_severidad,
    'sev_limite_superior': 1200.0,
    'sev_freq_activado': True,
    'sev_freq_modelo': 'reincidencia',
    'sev_freq_tipo_escalamiento': 'lineal',
    'sev_freq_paso': 1.0,        # se duplica cada ocurrencia adicional
    'sev_freq_factor_max': 5.0,  # hasta 5x -> ~5.500-6.000 sin el fix
}

# Truco: para observar severidades individuales (no solo la pérdida
# agregada), corremos con pocas simulaciones pero forzamos varias
# ocurrencias/año (tasa=5), y accedemos a la pérdida TOTAL del evento por
# simulación como proxy: si escala sin cap, la pérdida total para
# simulaciones con >=2 ocurrencias puede superar comodamente 1200*2=2400
# incluso con el cap "funcionando" a nivel de la primera ocurrencia.
# Para una verificación mas directa, monkeypatcheamos dist_severidad.rvs
# para devolver SIEMPRE el mismo valor justo por debajo del cap, aislando
# el efecto del escalamiento.
class _SeveridadFija:
    def rvs(self, size=1, random_state=None):
        return np.full(size, 1150.0)  # justo debajo del cap de 1200


evento['dist_severidad'] = _SeveridadFija()

rng = np.random.default_rng(41)
_, freq_tot, perd_evt, freq_evt = RLB.generar_lda_con_secuencialidad([evento], num_simulaciones=3000, rng=rng)

# Para simulaciones con exactamente 1 ocurrencia, perdida_evento == severidad
# individual (sin escalamiento, ya que occurrence_idx=1 -> multiplicador=1).
# Para simulaciones con >=2 ocurrencias, el escalamiento se activa en la 2da+
# y la pérdida total ya no es directamente comparable a una severidad
# individual -- por eso construimos el caso con severidad fija y verificamos
# que threshold*maximo_multiplicador nunca se exprese sin capear.
idx_una_ocurrencia = np.flatnonzero(freq_evt[0] == 1)
check(idx_una_ocurrencia.size > 0, "Precondición: hay simulaciones con exactamente 1 ocurrencia")
if idx_una_ocurrencia.size > 0:
    perdidas_1_occ = perd_evt[0][idx_una_ocurrencia]
    check(np.all(perdidas_1_occ <= 1200.0 + 1e-6),
          f"Con 1 ocurrencia (sin escalamiento), la severidad respeta el cap "
          f"(obtenido max: {perdidas_1_occ.max():.1f})")

idx_multi_ocurrencia = np.flatnonzero(freq_evt[0] >= 2)
check(idx_multi_ocurrencia.size > 0,
      "Precondición: hay simulaciones con >=2 ocurrencias (donde se activa el escalamiento)")
if idx_multi_ocurrencia.size > 0:
    # Con severidad fija en 1150 y factor_max=5 (paso=1.0: mult=1,2,3,4,5...),
    # sin el fix la SEGUNDA ocurrencia de cada simulación multi-occurrencia
    # tendría severidad_individual=1150*2=2300 > cap=1200. La pérdida TOTAL
    # de una simulación con 2 ocurrencias, sin fix, sería >= 1150+2300=3450;
    # con el fix (cada severidad individual capeada a 1200), sería <= 2400.
    perdida_max_multi = perd_evt[0][idx_multi_ocurrencia].max()
    freq_max_en_ese_grupo = int(freq_evt[0][idx_multi_ocurrencia].max())
    print(f"  pérdida total máxima con >=2 ocurrencias: {perdida_max_multi:.1f} "
          f"(máx ocurrencias en una sim: {freq_max_en_ese_grupo})")
    check(perdida_max_multi <= 1200.0 * freq_max_en_ese_grupo + 1e-3,
          f"Bug medio #22: la pérdida total nunca supera cap*num_ocurrencias "
          f"(cada severidad individual quedó capeada tras el escalamiento) "
          f"(obtenido: {perdida_max_multi:.1f}, límite: {1200.0 * freq_max_en_ese_grupo:.1f})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
