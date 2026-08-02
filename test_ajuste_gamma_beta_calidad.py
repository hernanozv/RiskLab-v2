"""
test_ajuste_gamma_beta_calidad.py
====================================

Regresion para bug #44 (QA ronda 2): obtener_parametros_gamma_para_poisson y
obtener_parametros_beta_frecuencia ajustan una distribucion Gamma/Beta a 3
objetivos (moda + 2 cuantiles) usando solo 2 parametros libres (forma/tasa).
Ese sistema esta SOBRE-DETERMINADO: en general no existe una solucion que
reproduzca los 3 valores exactamente, y antes del fix el objetivo de
optimizacion no estaba normalizado (los terminos de error de los cuantiles
dominaban numericamente cuando maximo >> mas_probable, por pura escala,
haciendo que el optimizador ignorara la moda pedida por el usuario). Ademas,
la funcion nunca validaba result.success ni la calidad real del ajuste, a
diferencia de obtener_parametros_lognormal/obtener_parametros_gpd.

Un primer intento de fix (normalizar + exigir que el error de la moda no
supere 25%) resulto ser demasiado estricto: en una bateria de 300 casos
aleatorios razonables, el 100% fue rechazado con ValueError, porque el
sistema sobre-determinado simplemente no admite ese nivel de precision en
la mayoria de los casos. El fix final:
  1. Normaliza los terminos de error (relativos al valor pedido) y usa
     multi-arranque en la optimizacion (evita quedar atrapado en el limite
     inferior del bound).
  2. Valida calidad usando el PEOR error relativo entre moda y los 2
     cuantiles (no solo la moda). Se rechaza con ValueError solo si el
     optimizador no convergio, o si ese peor error satura cerca del 100%
     (senal de que ninguna Gamma/Beta razonable puede aproximar lo pedido).
  3. Un desajuste moderado (peor error > 30%), esperable dado el
     sobre-ajuste, se informa con un warning propio
     (RiskLabAjusteImperfectoWarning) en vez de bloquear al usuario.

Este test verifica: (a) casos razonables (incluso con desajuste notable)
ya NO se rechazan; (b) casos genuinamente patologicos SI se rechazan; (c)
la bateria de 300 casos aleatorios que antes tenia 100% de rechazo ahora
tiene una tasa de rechazo baja; (d) el warning se emite en la categoria
correcta cuando el ajuste es imperfecto pero aceptable.
"""
import os
import sys
import warnings

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
print("BUG #44: Ajuste Gamma/Beta - validación de calidad sin sobre-rechazo")
print("=" * 70)

check(hasattr(RLB, 'RiskLabAjusteImperfectoWarning'),
      "RiskLabAjusteImperfectoWarning está definida")
check(issubclass(RLB.RiskLabAjusteImperfectoWarning, UserWarning),
      "RiskLabAjusteImperfectoWarning hereda de UserWarning")

# --- 1. Casos razonables (aunque con desajuste notable) NO deben rechazarse ---
casos_razonables = [
    ("simple", 1, 5, 20, 0.8),
    ("agente_original (caso extremo de la ronda de QA)", 0.2, 0.5, 50, 0.8),
    ("freq_tipica", 1, 3, 10, 0.9),
    ("rango_angosto", 4, 5, 6, 0.8),
]
for nombre, mn, mp, mx, c in casos_razonables:
    try:
        alpha, beta = RLB.obtener_parametros_gamma_para_poisson(mn, mp, mx, c)
        check(alpha > 1 and beta > 0,
              f"Gamma '{nombre}' (min={mn}, moda={mp}, max={mx}, conf={c}) "
              f"se ajusta sin ser rechazado (alpha={alpha:.4g}, beta={beta:.4g})")
    except ValueError as e:
        check(False, f"Gamma '{nombre}' NO debería rechazarse (obtenido: {e})")

# --- 2. Casos genuinamente patológicos SÍ deben rechazarse ---
casos_patologicos = [
    ("moda casi pegada al mínimo, máximo 6 órdenes de magnitud mayor",
     0.001, 0.002, 1000, 0.99),
    ("máximo un millón de veces la moda con confianza muy alta",
     1, 1.01, 1_000_000, 0.98),
]
for nombre, mn, mp, mx, c in casos_patologicos:
    try:
        alpha, beta = RLB.obtener_parametros_gamma_para_poisson(mn, mp, mx, c)
        check(False,
              f"Gamma patológico ({nombre}) debería rechazarse "
              f"(obtenido: alpha={alpha:.4g}, beta={beta:.4g})")
    except ValueError:
        check(True, f"Gamma patológico ({nombre}) se rechaza correctamente")

# --- 3. Bateria de 300 casos aleatorios: la tasa de rechazo debe ser baja
#        (el bug original hacía que el 100% de estos casos se rechazara) ---
rng = np.random.default_rng(42)
n_ok, n_reject = 0, 0
for _ in range(300):
    minimo = rng.uniform(0.01, 10)
    mas_probable = minimo + rng.uniform(0.01, 10)
    maximo = mas_probable + rng.uniform(0.01, 50)
    confianza = rng.uniform(0.5, 0.95)
    try:
        RLB.obtener_parametros_gamma_para_poisson(minimo, mas_probable, maximo, confianza)
        n_ok += 1
    except ValueError:
        n_reject += 1

tasa_rechazo = n_reject / 300
check(tasa_rechazo < 0.20,
      f"Bug #44: la tasa de rechazo en 300 casos aleatorios razonables es "
      f"baja (obtenido: {tasa_rechazo:.0%} rechazados, {n_ok} aceptados) — "
      f"antes del fix era 100%")

# --- 4. El warning se emite (categoría correcta) para un ajuste imperfecto,
#        y NO se emite para un caso de buen ajuste ---
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always')
    RLB.obtener_parametros_gamma_para_poisson(1, 5, 20, 0.8)  # caso "simple": desajuste notable
    check(len(w) == 1 and issubclass(w[0].category, RLB.RiskLabAjusteImperfectoWarning),
          f"Warning RiskLabAjusteImperfectoWarning se emite para un ajuste imperfecto "
          f"pero aceptable (obtenido: {[x.category.__name__ for x in w]})")

with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always')
    RLB.obtener_parametros_gamma_para_poisson(4, 5, 6, 0.8)  # caso "rango_angosto": buen ajuste
    check(len(w) == 0,
          f"Ningún warning se emite para un caso de buen ajuste "
          f"(obtenido: {[x.category.__name__ for x in w]})")

# --- 5. Lo mismo para obtener_parametros_beta_frecuencia ---
try:
    alpha, beta = RLB.obtener_parametros_beta_frecuencia(0.05, 0.15, 0.60, 0.8)
    check(alpha > 1 and beta > 1,
          f"Beta razonable (0.05, 0.15, 0.60, conf=0.8) se ajusta sin rechazo "
          f"(alpha={alpha:.4g}, beta={beta:.4g})")
except ValueError as e:
    check(False, f"Beta razonable no debería rechazarse (obtenido: {e})")

try:
    alpha, beta = RLB.obtener_parametros_beta_frecuencia(0.001, 0.998, 0.999, 0.99)
    check(False,
          f"Beta patológico (moda pegada al máximo, mínimo muy lejano) debería "
          f"rechazarse (obtenido: alpha={alpha:.4g}, beta={beta:.4g})")
except ValueError:
    check(True, "Beta patológico (moda pegada al máximo, mínimo muy lejano) se rechaza correctamente")

# Caso de regresión adicional: un intervalo MUY angosto con confianza casi 1
# (0.4999, 0.5, 0.5001, conf=0.999999) es en realidad un buen ajuste (error
# de punto flotante, ~1e-16), pero Nelder-Mead reporta result.success=False
# por tolerancias de paso demasiado finas para esa escala numérica. Antes de
# corregir esto, la función lo rechazaba igual (por confiar en
# result.success), aunque el ajuste real fuera casi perfecto.
try:
    alpha, beta = RLB.obtener_parametros_beta_frecuencia(0.4999, 0.5, 0.5001, 0.999999)
    check(True,
          f"Un ajuste casi perfecto no se rechaza aunque Nelder-Mead reporte "
          f"'no convergió' por tolerancias numéricas (alpha={alpha:.4g}, beta={beta:.4g})")
except ValueError as e:
    check(False,
          f"Un ajuste casi perfecto NO debería rechazarse solo porque "
          f"result.success sea False (obtenido: {e})")

rng = np.random.default_rng(7)
n_ok, n_reject = 0, 0
for _ in range(300):
    minimo = rng.uniform(0.0, 0.3)
    mas_probable = minimo + rng.uniform(0.01, 0.3)
    maximo = min(mas_probable + rng.uniform(0.01, 0.6), 0.999)
    if not (minimo < mas_probable < maximo):
        continue
    confianza = rng.uniform(0.5, 0.95)
    try:
        RLB.obtener_parametros_beta_frecuencia(minimo, mas_probable, maximo, confianza)
        n_ok += 1
    except ValueError:
        n_reject += 1

tasa_rechazo_beta = n_reject / (n_ok + n_reject)
check(tasa_rechazo_beta < 0.20,
      f"Bug #44 (Beta): la tasa de rechazo en ~300 casos aleatorios razonables "
      f"es baja (obtenido: {tasa_rechazo_beta:.0%} rechazados, {n_ok} aceptados)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
