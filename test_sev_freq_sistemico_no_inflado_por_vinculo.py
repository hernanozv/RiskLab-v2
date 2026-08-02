"""
test_sev_freq_sistemico_no_inflado_por_vinculo.py
=====================================================

Regresion para bug alto R4 #8 (QA ronda 4): el modelo de escalamiento
sev_freq "sistémico" calcula un z-score de la frecuencia de CADA
simulación-año contra una referencia (media/desvío) tomada de
final_event_frequencies -- el array de frecuencia del evento en TODAS
las simulaciones. Cuando el evento depende de un vínculo (AND/OR/EXCLUYE
a un padre), las simulaciones donde el vínculo NO se activó quedan en
frecuencia 0 por ESTRUCTURA, no por variabilidad propia del evento. Si
el padre es raro (ej. prob_exito=0.05), la enorme mayoría del array de
referencia son estos ceros "estructurales", lo que arrastra la media
hacia abajo y sesga el desvío estándar -- inflando artificialmente el
z-score (y por lo tanto el multiplicador de severidad) de las
simulaciones donde el evento SÍ ocurrió, incluso si esa ocurrencia fue
perfectamente "normal" dentro de la distribución del evento cuando está
activo.

El fix cachea la máscara de elegibilidad del vínculo
(evento['_condicion_vinculo_final']) y, si existe, calcula freq_mean/
freq_std del modelo sistémico SOLO sobre las simulaciones elegibles
(donde el vínculo se activó), no sobre el array completo.

Este test construye un padre Bernoulli con prob_exito=0.05 (rara
activación) y un hijo con severidad fija ($1000), vínculo AND a ese
padre, frecuencia Poisson(tasa=5) cuando el vínculo se activa, y
escalamiento sev_freq "sistémico" (alpha=1.0, solo_aumento=True,
factor_max=5.0). Verifica que, en simulaciones donde el hijo tuvo
EXACTAMENTE su frecuencia media condicional (5 ocurrencias -- un año
"normal" dado que el evento está activo), el multiplicador de severidad
efectivo (perdida_total / (frecuencia * severidad_base)) quede cerca de
1.0x (neutral), en vez de inflado artificialmente hacia el factor_max=5.0
por los ceros estructurales del vínculo.
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
print("BUG ALTO R4 #8: sev_freq sistémico no debe inflarse por ceros de vínculo")
print("=" * 70)


class _SeveridadFija:
    def __init__(self, valor):
        self.valor = valor

    def rvs(self, size=1, random_state=None):
        return np.full(size, self.valor)


padre = {
    'id': 'p1', 'nombre': 'PadreRaro', 'activo': True,
    'freq_opcion': 3, 'prob_exito': 0.05,
    'dist_frecuencia': RLB.generar_distribucion_frecuencia(3, probabilidad_exito=0.05),
    'sev_opcion': 1, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 100.0, 'std': 10.0},
    'dist_severidad': RLB.generar_distribucion_severidad(
        1, None, None, None, input_method='direct', params_direct={'mean': 100.0, 'std': 10.0}
    ),
}

SEVERIDAD_BASE = 1000.0

hijo = {
    'id': 'hijo', 'nombre': 'HijoSistemicoConVinculo', 'activo': True,
    'freq_opcion': 1, 'tasa': 5.0,
    'dist_frecuencia': RLB.generar_distribucion_frecuencia(1, tasa=5.0),
    'sev_opcion': 1, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': SEVERIDAD_BASE, 'std': 10.0},
    'dist_severidad': _SeveridadFija(SEVERIDAD_BASE),
    'sev_freq_activado': True,
    'sev_freq_modelo': 'sistemico',
    'sev_freq_alpha': 1.0,
    'sev_freq_solo_aumento': True,
    'sev_freq_sistemico_factor_max': 5.0,
    'vinculos': [
        {'id_padre': 'p1', 'tipo': 'AND', 'probabilidad': 100, 'factor_severidad': 1.0, 'umbral_severidad': 0},
    ],
}

eventos = [padre, hijo]

rng = np.random.default_rng(2024)
NUM_SIM = 20000
_, freq_tot, perd_evt, freq_evt = RLB.generar_lda_con_secuencialidad(eventos, num_simulaciones=NUM_SIM, rng=rng)

idx_hijo = [e['id'] for e in eventos].index('hijo')
freq_hijo = freq_evt[idx_hijo]
perd_hijo = perd_evt[idx_hijo]

n_activos = int(np.sum(freq_hijo > 0))
print(f"  simulaciones donde el vínculo se activó y hubo >=1 ocurrencia: {n_activos} / {NUM_SIM}")
check(0 < n_activos < NUM_SIM * 0.2,
      f"Precondición: el padre es raro, la mayoría de simulaciones quedan en freq=0 por vínculo "
      f"(obtenido: {n_activos} activas de {NUM_SIM})")

mask_freq_media = freq_hijo == 5
n_en_media = int(np.sum(mask_freq_media))
print(f"  simulaciones con frecuencia EXACTA = 5 (media condicional del hijo activo): {n_en_media}")
check(n_en_media >= 20,
      f"Precondición: hay suficientes simulaciones con frecuencia=5 para medir el multiplicador "
      f"(obtenido: {n_en_media})")

if n_en_media >= 20:
    multiplicadores = perd_hijo[mask_freq_media] / (5.0 * SEVERIDAD_BASE)
    mult_medio = float(multiplicadores.mean())
    print(f"  multiplicador sev_freq medio en años con frecuencia=5 (la media condicional): {mult_medio:.3f}")
    check(mult_medio < 2.5,
          f"Bug alto R4 #8: el multiplicador para años con la frecuencia EXACTAMENTE en la media "
          f"condicional del evento activo debe quedar cerca de 1.0x (neutral), no inflado hacia "
          f"factor_max=5.0 por los ceros estructurales del vínculo (obtenido: {mult_medio:.3f}x; "
          f"sin el fix sería cercano a ~5.0x)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
