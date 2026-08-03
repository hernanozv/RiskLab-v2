"""
test_frecuencia_zip_directo.py
================================

Feature: nueva distribución de frecuencia Zero-Inflated Poisson (ZIP,
freq_opcion=6), agregada en la revisión de suficiencia de distribuciones
para Meli (eventos raros pero agrupados, ej. sanciones regulatorias).

Verifica que:
1. generar_distribucion_frecuencia(6, zip_params=(pi, lam)) construye la
   distribución y expone .rvs(size, random_state) / .mean() / .var().
2. La media analítica y empírica coinciden con E[N] = (1-pi)*lam.
3. Con pi alto, la fracción de años en cero es >= pi (exceso de ceros
   estructural, imposible de modelar con una Poisson pura).
4. Cuando el evento SÍ ocurre, admite conteos > 1 (a diferencia de
   Bernoulli/Beta que son binarios).
5. Parámetros inválidos (pi fuera de [0,1), lam <= 0) se rechazan.
6. Los diccionarios de nombres del motor incluyen la opción 6.
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
print("FEATURE: frecuencia Zero-Inflated Poisson (freq_opcion=6)")
print("=" * 70)

rng = np.random.default_rng(7)
PI, LAM = 0.7, 4.0
dist = RLB.generar_distribucion_frecuencia(6, zip_params=(PI, LAM))
N = 400000
muestras = np.asarray(dist.rvs(size=N, random_state=rng))

media_esperada = (1 - PI) * LAM
check(muestras.shape == (N,), f".rvs(N) devuelve array de tamaño N (obtenido {muestras.shape})")
check(abs(dist.mean() - media_esperada) < 1e-9,
      f"mean() analítica = (1-π)·λ = {media_esperada:.3f} (obtenido {dist.mean():.3f})")
check(abs(muestras.mean() - media_esperada) < 0.05,
      f"media empírica ≈ (1-π)·λ (obtenido {muestras.mean():.3f}, esperado {media_esperada:.3f})")

frac_ceros = float((muestras == 0).mean())
check(frac_ceros >= PI - 0.02,
      f"fracción de años en cero ({frac_ceros:.3f}) >= π ({PI}) — exceso de ceros estructural")

check(muestras.max() >= 2,
      f"admite conteos > 1 cuando el evento ocurre (max observado = {int(muestras.max())})")

# Validaciones
print("\n-- validaciones de parámetros inválidos --")
invalidos = [
    ("pi >= 1", (1.0, 3.0)),
    ("pi < 0", (-0.1, 3.0)),
    ("lam <= 0", (0.5, 0.0)),
    ("lam negativo", (0.5, -2.0)),
]
for nombre, zp in invalidos:
    try:
        RLB.generar_distribucion_frecuencia(6, zip_params=zp)
        check(False, f"ZIP {nombre}: debería lanzar ValueError")
    except (ValueError, Exception):
        check(True, f"ZIP {nombre}: rechazado correctamente")

# pi = 0 debe ser válido (colapsa a Poisson)
try:
    d0 = RLB.generar_distribucion_frecuencia(6, zip_params=(0.0, 3.0))
    m0 = np.asarray(d0.rvs(size=50000, random_state=rng))
    check(abs(m0.mean() - 3.0) < 0.1, f"ZIP con π=0 colapsa a Poisson(λ) (media {m0.mean():.3f} ≈ 3.0)")
except Exception as e:
    check(False, f"ZIP con π=0 debería ser válido (error: {e})")

# Diccionarios
print("\n-- diccionarios de nombres --")
check(6 in RLB._FREQ_DIST_NAMES and "Zero-Inflated Poisson" in RLB._FREQ_DIST_NAMES[6],
      f"_FREQ_DIST_NAMES[6] = {RLB._FREQ_DIST_NAMES.get(6)!r}")
check(6 in RLB._FREQ_DIST_DESCRIPTIONS, "_FREQ_DIST_DESCRIPTIONS[6] existe")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
