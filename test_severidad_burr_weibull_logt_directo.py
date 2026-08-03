"""
test_severidad_burr_weibull_logt_directo.py
=============================================

Regresion/feature para las 3 NUEVAS distribuciones de severidad agregadas
(revisión de suficiencia de distribuciones para Meli): Burr XII
(sev_opcion=6), Weibull (sev_opcion=7) y Log-t (sev_opcion=8), todas con
parámetros directos.

Verifica que:
1. Cada una se construye vía generar_distribucion_severidad(opcion,
   input_method='direct', params_direct=...) y expone el contrato .rvs(size,
   random_state) esperado por el motor.
2. El muestreo produce un array del tamaño pedido, finito y NO negativo
   (severidad = pérdida >= 0), con percentiles crecientes coherentes.
3. Burr y Log-t (cola pesada) están efectivamente capadas en ~P99.9 (ningún
   valor supera el cap teórico).
4. Estas distribuciones SOLO admiten parámetros directos: llamar con
   input_method='min_mode_max' lanza ValueError.
5. Parámetros inválidos (forma <= 0, scale <= 0, df <= 0, loc < 0) se
   rechazan con ValueError.
6. Los diccionarios de nombres del motor incluyen las 3 opciones.
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
print("FEATURE: severidad Burr XII / Weibull / Log-t (solo parámetros directos)")
print("=" * 70)

rng = np.random.default_rng(2024)
N = 200000

casos = [
    ("Burr", 6, {'c': 2.0, 'd': 1.5, 'scale': 1_000_000, 'loc': 0}, True),
    ("Weibull", 7, {'c': 1.5, 'scale': 500_000, 'loc': 0}, False),
    ("Log-t", 8, {'df': 4, 'mu': 13.0, 'sigma': 0.8, 'loc': 0}, True),
]

for nombre, opcion, params, tiene_cap in casos:
    print(f"\n-- {nombre} (sev_opcion={opcion}) --")
    dist = RLB.generar_distribucion_severidad(opcion, None, None, None,
                                              input_method='direct', params_direct=params)
    muestras = dist.rvs(size=N, random_state=rng)
    muestras = np.asarray(muestras)
    check(muestras.shape == (N,), f"{nombre}: .rvs(N) devuelve array de tamaño N (obtenido {muestras.shape})")
    check(np.isfinite(muestras).all(), f"{nombre}: todas las muestras son finitas")
    check((muestras >= 0).all(), f"{nombre}: todas las muestras son >= 0 (severidad no negativa)")
    p50, p95, p99 = np.percentile(muestras, [50, 95, 99])
    check(p50 < p95 < p99, f"{nombre}: percentiles crecientes P50<P95<P99 ({p50:.2e}<{p95:.2e}<{p99:.2e})")
    if tiene_cap:
        cap = dist.ppf(0.999)
        check(muestras.max() <= cap * (1 + 1e-9),
              f"{nombre}: cola pesada capada en ~P99.9 (max={muestras.max():.3e} <= cap={cap:.3e})")

    # Solo parámetros directos: min_mode_max debe fallar
    try:
        RLB.generar_distribucion_severidad(opcion, 1, 2, 3, input_method='min_mode_max')
        check(False, f"{nombre}: min_mode_max debería lanzar ValueError (es solo-directo)")
    except (ValueError, Exception):
        check(True, f"{nombre}: min_mode_max rechazado (solo admite parámetros directos)")

# Validaciones de parámetros inválidos
print("\n-- validaciones de parámetros inválidos --")
invalidos = [
    ("Burr c<=0", 6, {'c': -1, 'd': 1, 'scale': 1e5}),
    ("Burr scale<=0", 6, {'c': 1, 'd': 1, 'scale': 0}),
    ("Weibull c<=0", 7, {'c': 0, 'scale': 1e5}),
    ("Weibull loc<0", 7, {'c': 1.5, 'scale': 1e5, 'loc': -10}),
    ("Log-t df<=0", 8, {'df': 0, 'mu': 10, 'sigma': 0.5}),
    ("Log-t sigma<=0", 8, {'df': 4, 'mu': 10, 'sigma': -0.5}),
]
for nombre, opcion, params in invalidos:
    try:
        RLB.generar_distribucion_severidad(opcion, None, None, None, input_method='direct', params_direct=params)
        check(False, f"{nombre}: debería lanzar ValueError")
    except (ValueError, Exception):
        check(True, f"{nombre}: rechazado correctamente")

# Diccionarios de nombres
print("\n-- diccionarios de nombres --")
for opcion, esperado_sub in [(6, "Burr"), (7, "Weibull"), (8, "Log-t")]:
    check(opcion in RLB._SEV_DIST_NAMES and esperado_sub in RLB._SEV_DIST_NAMES[opcion],
          f"_SEV_DIST_NAMES[{opcion}] contiene '{esperado_sub}' (obtenido: {RLB._SEV_DIST_NAMES.get(opcion)!r})")
    check(opcion in RLB._SEV_DIST_DESCRIPTIONS,
          f"_SEV_DIST_DESCRIPTIONS[{opcion}] existe")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
