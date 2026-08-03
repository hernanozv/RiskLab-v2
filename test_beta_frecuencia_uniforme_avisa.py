"""
test_beta_frecuencia_uniforme_avisa.py
==========================================

Regresion para bug critico R4 #6 (QA ronda 4): obtener_parametros_beta_frecuencia
puede converger a una Beta con alpha≈beta≈1 (practicamente
indistinguible de Uniforme(0,1)) con parametros de entrada NADA
extremos, SIN disparar ningun RiskLabAjusteImperfectoWarning -- el
chequeo de calidad existente solo compara la moda (via formula
numericamente inestable cerca de alpha=beta=1, forma 0/0) y dos
cuantiles puntuales, que pueden coincidir "por accidente" con los
valores pedidos sin que la FORMA global de la distribucion tenga
ninguna relacion real con lo solicitado.

Caso reproducido durante la auditoria: minimo=0.2082, mas_probable=0.5505,
maximo=0.6759, confianza=0.53 -> alpha≈1.0012, beta≈1.0010. Verificado
con 200.000 muestras reales: ~53% de las muestras caen FUERA del rango
[minimo, maximo] pedido -- el modelo de "probabilidad de ocurrencia
anual" (Bernoulli/Beta) termina siendo, en la practica, un sorteo
uniforme sobre TODO [0,1], invalidando el resultado de la simulacion
para ese evento, sin que el usuario se entere.

El fix detecta explicitamente cuando alpha y beta quedan ambos muy
cerca de 1 (la frontera numerica donde la formula de la moda es
inestable) y emite un RiskLabAjusteImperfectoWarning especifico en ese
caso, incluso cuando los chequeos puntuales existentes no lo detectan.

Este test llama obtener_parametros_beta_frecuencia con el caso exacto
de la auditoria y verifica que SI se emite el warning.
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
print("BUG CRÍTICO R4 #6: Beta de frecuencia cerca de Uniforme(0,1) debe avisar")
print("=" * 70)

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    alpha, beta = RLB.obtener_parametros_beta_frecuencia(0.2082, 0.5505, 0.6759, 0.53)

print(f"  alpha={alpha:.4f}, beta={beta:.4f}")

check(alpha < 1.05 and beta < 1.05,
      f"Precondición: el ajuste converge cerca de alpha=beta=1 (Uniforme) "
      f"(obtenido: alpha={alpha:.4f}, beta={beta:.4f})")

warnings_ajuste = [w for w in caught if issubclass(w.category, RLB.RiskLabAjusteImperfectoWarning)]
check(len(warnings_ajuste) >= 1,
      f"Bug crítico R4 #6: se emite RiskLabAjusteImperfectoWarning para el ajuste "
      f"degenerado cerca de Uniforme(0,1) (obtenido: {len(warnings_ajuste)} avisos)")

# Verificar empíricamente que el ajuste realmente produce una masa
# significativa fuera del rango pedido (confirmando que el aviso es
# informativo, no solo un falso positivo).
from scipy import stats as _stats
muestras = _stats.beta.rvs(alpha, beta, size=200_000, random_state=np.random.default_rng(3))
fuera_de_rango = float(np.mean((muestras < 0.2082) | (muestras > 0.6759)))
print(f"  fracción de muestras fuera de [0.2082, 0.6759]: {fuera_de_rango:.1%}")
check(fuera_de_rango > 0.30,
      f"El ajuste degenerado realmente produce una masa significativa fuera "
      f"del rango pedido (obtenido: {fuera_de_rango:.1%})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
