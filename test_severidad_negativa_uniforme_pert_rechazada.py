"""
test_severidad_negativa_uniforme_pert_rechazada.py
======================================================

Regresion para bug alto R4 #5 (QA ronda 4): obtener_parametros_uniforme()
y obtener_parametros_pert() solo validaban el ORDEN de minimo/mas_probable/
maximo, pero no que el rango fuera al menos parcialmente positivo. Si un
usuario configuraba un evento con severidad Uniforme o PERT completamente
en rango negativo (ej. minimo=-1000, maximo=-10), el evento se guardaba
SIN error -- pero el motor de simulación clippea toda severidad negativa a
$0 inmediatamente después de muestrear (np.maximum(..., 0), línea ~3600),
por lo que ese evento contribuiría SIEMPRE $0 de pérdida, silenciosamente,
para siempre: un "riesgo fantasma" que aparenta estar modelado pero nunca
impacta un resultado.

El fix agrega una validación explícita: si maximo <= 0 (rango
completamente no-positivo), obtener_parametros_uniforme/obtener_parametros_pert
lanzan ValueError con un mensaje claro, en vez de aceptar la configuración
en silencio.

Este test verifica que:
1. obtener_parametros_uniforme(minimo=-1000, maximo=-10) lance ValueError.
2. obtener_parametros_pert(minimo=-1000, mas_probable=-500, maximo=-10) lance
   ValueError.
3. Rangos válidos (incluyendo parcialmente negativos, ej. minimo=-50,
   maximo=100, consistente con cómo ya se comporta Normal vía truncnorm)
   siguen funcionando sin error.
4. generar_distribucion_severidad(opcion=5, ...) y (opcion=3, ...) propagan
   el ValueError con un mensaje que menciona el problema real.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

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
print("BUG ALTO R4 #5: rango de severidad completamente negativo debe rechazarse")
print("=" * 70)

# --- Caso 1: Uniforme completamente negativa ---
print("\n--- Caso 1: obtener_parametros_uniforme completamente negativo ---")
try:
    RLB.obtener_parametros_uniforme(-1000, -10)
    check(False, "Bug alto R4 #5: obtener_parametros_uniforme(-1000, -10) debería lanzar ValueError")
except ValueError as e:
    check(True, f"obtener_parametros_uniforme(-1000, -10) lanza ValueError (mensaje: {e})")
except Exception as e:
    check(False, f"Se esperaba ValueError, se obtuvo {type(e).__name__}: {e}")

# --- Caso 2: PERT completamente negativa ---
print("\n--- Caso 2: obtener_parametros_pert completamente negativo ---")
try:
    RLB.obtener_parametros_pert(-1000, -500, -10)
    check(False, "Bug alto R4 #5: obtener_parametros_pert(-1000, -500, -10) debería lanzar ValueError")
except ValueError as e:
    check(True, f"obtener_parametros_pert(-1000, -500, -10) lanza ValueError (mensaje: {e})")
except Exception as e:
    check(False, f"Se esperaba ValueError, se obtuvo {type(e).__name__}: {e}")

# --- Caso 3: rangos válidos siguen funcionando ---
print("\n--- Caso 3: rangos válidos (incluyendo maximo=0 exacto rechazado, maximo>0 aceptado) ---")
try:
    loc, scale = RLB.obtener_parametros_uniforme(10, 100)
    check(loc == 10 and scale == 90, "Uniforme(10, 100) totalmente positivo sigue funcionando")
except Exception as e:
    check(False, f"Uniforme(10, 100) no debería lanzar error (obtenido: {e})")

try:
    loc, scale = RLB.obtener_parametros_uniforme(-50, 100)
    check(loc == -50 and scale == 150,
          "Uniforme(-50, 100) parcialmente negativo (maximo>0) sigue funcionando, "
          "consistente con cómo Normal ya trunca en 0")
except Exception as e:
    check(False, f"Uniforme(-50, 100) no debería lanzar error (obtenido: {e})")

try:
    a, b = RLB.obtener_parametros_pert(-50, 0, 100)
    check(True, "PERT(-50, 0, 100) parcialmente negativo (maximo>0) sigue funcionando")
except Exception as e:
    check(False, f"PERT(-50, 0, 100) no debería lanzar error (obtenido: {e})")

# --- Caso 4: maximo == 0 exacto (rango completamente no-positivo) también rechazado ---
print("\n--- Caso 4: maximo == 0 exacto también se rechaza ---")
try:
    RLB.obtener_parametros_uniforme(-100, 0)
    check(False, "Bug alto R4 #5: obtener_parametros_uniforme(-100, 0) debería lanzar ValueError (maximo=0)")
except ValueError:
    check(True, "obtener_parametros_uniforme(-100, 0) lanza ValueError (maximo=0 sigue siendo fantasma)")

# --- Caso 5: el error se propaga a través de generar_distribucion_severidad ---
print("\n--- Caso 5: generar_distribucion_severidad propaga el error ---")
try:
    RLB.generar_distribucion_severidad(5, minimo=-1000, mas_probable=None, maximo=-10, input_method='min_mode_max')
    check(False, "Bug alto R4 #5: generar_distribucion_severidad(Uniforme completamente negativa) debería fallar")
except ValueError as e:
    check('fantasma' in str(e).lower() or 'mayor a 0' in str(e).lower(),
          f"generar_distribucion_severidad propaga el mensaje explicando el problema real (obtenido: {e})")

try:
    RLB.generar_distribucion_severidad(3, minimo=-1000, mas_probable=-500, maximo=-10, input_method='min_mode_max')
    check(False, "Bug alto R4 #5: generar_distribucion_severidad(PERT completamente negativa) debería fallar")
except ValueError as e:
    check('fantasma' in str(e).lower() or 'mayor a 0' in str(e).lower(),
          f"generar_distribucion_severidad propaga el mensaje explicando el problema real (obtenido: {e})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
