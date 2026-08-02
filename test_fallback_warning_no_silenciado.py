"""
test_fallback_warning_no_silenciado.py
=========================================

Regresion para bug #43 (QA ronda 2): el módulo aplica, al importarse,
`warnings.filterwarnings("ignore", category=RuntimeWarning)` (línea ~296)
para suprimir warnings ruidosos de numpy/scipy. Las 9 alertas propias de
Risk Lab que avisan cuando el motor no puede generar la
frecuencia/severidad de un evento y cae al fallback de "pérdidas = 0"
usaban esa MISMA categoría (RuntimeWarning), quedando también silenciadas
desde el arranque — sin que nadie lo notara, ni siquiera capturándolas con
`catch_warnings(record=True)` sin resetear los filtros (que es exactamente
cómo se comportan en la app real, donde nada llama a
`simplefilter('always')`).

El fix introduce una categoría propia, `RiskLabFallbackWarning` (subclase
de UserWarning, igual que las otras alertas de Risk Lab), usada en los 9
lugares donde antes se emitía RuntimeWarning para este propósito. El
filtro global de RuntimeWarning se mantiene intacto (sigue suprimiendo el
ruido genérico de numpy/scipy), pero ya no afecta a estas alertas.

Este test verifica:
  1. RiskLabFallbackWarning existe y NO es subclase de RuntimeWarning (así
     el filtro global no la alcanza).
  2. Tras importar el módulo (que aplica el filtro), un RuntimeWarning
     genérico sigue silenciado (el filtro conserva su propósito original).
  3. Una RiskLabFallbackWarning SÍ se captura bajo las mismas condiciones.
  4. Disparo real end-to-end: forzar una excepción real dentro de
     BetaFrequencyDistribution.pmf() (uno de los 9 sitios) y confirmar que
     el warning emitido es visible y de la categoría correcta.
  5. Por inspección de código: ninguno de los 9 sitios conocidos sigue
     usando RuntimeWarning.
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
print("BUG #43: RiskLabFallbackWarning no queda silenciado por el filtro global")
print("=" * 70)

check(hasattr(RLB, 'RiskLabFallbackWarning'), "RiskLabFallbackWarning está definida")
check(issubclass(RLB.RiskLabFallbackWarning, UserWarning),
      "RiskLabFallbackWarning hereda de UserWarning (igual que las otras alertas de Risk Lab)")
check(not issubclass(RLB.RiskLabFallbackWarning, RuntimeWarning),
      "RiskLabFallbackWarning NO es subclase de RuntimeWarning "
      "(así el filtro global de RuntimeWarning no la alcanza)")

# --- El filtro global sigue funcionando para RuntimeWarning genéricos
#     (no debe reactivarse por accidente el ruido de numpy/scipy) ---
with warnings.catch_warnings(record=True) as w:
    warnings.warn("ruido generico de numpy", RuntimeWarning)
    check(len(w) == 0,
          "Un RuntimeWarning genérico sigue silenciado (el filtro conserva su propósito original)")

# --- RiskLabFallbackWarning SÍ se captura bajo las mismas condiciones ---
with warnings.catch_warnings(record=True) as w:
    warnings.warn("alerta propia de Risk Lab", RLB.RiskLabFallbackWarning)
    check(len(w) == 1 and issubclass(w[0].category, RLB.RiskLabFallbackWarning),
          "Bug #43: una RiskLabFallbackWarning SÍ se captura (ya no queda invisible)")

# --- Disparo real end-to-end: forzar una excepción real dentro de un
#     sitio real del motor (BetaFrequencyDistribution.pmf) ---
dist = RLB.BetaFrequencyDistribution(alpha='no-es-un-numero', beta=1)
with warnings.catch_warnings(record=True) as w:
    resultado = dist.pmf(np.array([0, 1, 0, 1]))
    check(len(w) == 1, f"pmf() con alpha inválido emite exactamente un warning (obtenido: {len(w)})")
    if w:
        check(issubclass(w[0].category, RLB.RiskLabFallbackWarning),
              f"El warning disparado end-to-end es RiskLabFallbackWarning (obtenido: {w[0].category.__name__})")
    check(np.array_equal(resultado, np.zeros(4)),
          "El fallback sigue devolviendo ceros como antes (mismo comportamiento numérico)")

# --- Verificación por inspección de código: ninguno de los 9 sitios
#     conocidos de "fallback a cero" sigue usando RuntimeWarning ---
engine_file = os.path.join(_THIS_DIR, 'Risk_Lab_Beta.py')
with open(engine_file, 'r', encoding='utf-8') as f:
    lineas = f.readlines()

lineas_runtimewarning_activas = [
    (i + 1, l) for i, l in enumerate(lineas)
    if l.strip() == 'RuntimeWarning,'
]
check(len(lineas_runtimewarning_activas) == 0,
      f"Ningún warnings.warn(...) sigue usando RuntimeWarning como categoría "
      f"(encontrados: {lineas_runtimewarning_activas})")

lineas_fallback_warning = [l for l in lineas if l.strip() == 'RiskLabFallbackWarning,']
check(len(lineas_fallback_warning) >= 9,
      f"Se encuentran al menos 9 sitios usando RiskLabFallbackWarning "
      f"(encontrados: {len(lineas_fallback_warning)})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
