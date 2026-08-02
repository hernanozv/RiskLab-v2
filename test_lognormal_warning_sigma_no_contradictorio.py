"""
test_lognormal_warning_sigma_no_contradictorio.py
=====================================================

Regresion para bug bajo R4 #5 (QA ronda 4): cuando obtener_parametros_lognormal()
detecta que el ajuste por MODA da sigma > 1.0 (la moda pierde
significado con tanta dispersión), reintenta un ajuste alternativo
interpretando 'más probable' como MEDIANA en vez de moda -- un sistema
de ecuaciones totalmente distinto, que puede converger a un sigma_alt
con un valor completamente diferente (incluso <= 1.0). El warning que
explica este cambio de método citaba `sigma_alt` (el sigma del ajuste
NUEVO/alternativo) como si fuera la razón ("debido a alta dispersión
σ=... > 1.0") -- pero la condición que realmente disparó el cambio usa
el sigma del ajuste ORIGINAL (por moda), no sigma_alt. Con ciertos
min/mas_probable/maximo, sigma_alt termina siendo <= 1.0, haciendo que
el mensaje se auto-contradiga: afirma "σ=0.02 > 1.0", una afirmación
matemáticamente falsa.

El fix usa la variable 'sigma' (el valor del ajuste original que
efectivamente cumple sigma > 1.0, la condición que dispara este
branch) en el mensaje, en vez de 'sigma_alt'.

Este test usa parámetros concretos (encontrados por búsqueda) donde el
ajuste por moda da sigma≈1.26 (>1.0, dispara el cambio de método) pero
el ajuste alternativo por mediana converge a sigma_alt≈0.018 (<1.0) --
y verifica que el warning emitido cite un sigma consistente con su
propia afirmación "> 1.0", no el sigma_alt contradictorio.
"""
import os
import sys
import warnings

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import re

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
print("BUG BAJO R4 #5: warning de LogNormal no debe citar un sigma contradictorio")
print("=" * 70)

MINIMO, MAS_PROBABLE, MAXIMO = 204.4, 209.1, 1398493.5

with warnings.catch_warnings(record=True) as capturados:
    warnings.simplefilter('always')
    mu, sigma_final = RLB.obtener_parametros_lognormal(MINIMO, MAS_PROBABLE, MAXIMO)

mensajes_mediana = [str(w.message) for w in capturados if 'MEDIANA' in str(w.message)]
print(f"  sigma final devuelto (sigma_alt, del ajuste por mediana): {sigma_final:.4f}")
print(f"  mensajes capturados: {mensajes_mediana}")

check(len(mensajes_mediana) == 1,
      f"Se dispara el warning de cambio a método por mediana (obtenido: {len(mensajes_mediana)})")
check(sigma_final <= 1.0,
      f"Precondición: sigma_alt (el sigma final devuelto) es <= 1.0 en este caso "
      f"(obtenido: {sigma_final:.4f})")

if mensajes_mediana:
    match = re.search(r"σ=([\d.]+)", mensajes_mediana[0])
    check(match is not None, "El mensaje incluye un valor numérico de sigma")
    if match:
        sigma_en_mensaje = float(match.group(1))
        print(f"  sigma citado en el mensaje: {sigma_en_mensaje}")
        check(sigma_en_mensaje > 1.0,
              f"Bug bajo R4 #5: el sigma citado en el mensaje ES > 1.0, consistente con la "
              f"propia afirmación del mensaje ('> 1.0') (obtenido: σ={sigma_en_mensaje}, "
              f"sin el fix habría sido el sigma_alt contradictorio ≈{sigma_final:.2f})")
        check(abs(sigma_en_mensaje - sigma_final) > 0.5,
              f"El sigma citado en el mensaje es claramente DISTINTO de sigma_alt "
              f"(obtenido: mensaje={sigma_en_mensaje}, sigma_alt={sigma_final:.4f})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
