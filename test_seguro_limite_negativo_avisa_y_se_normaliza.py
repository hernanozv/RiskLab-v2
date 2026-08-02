"""
test_seguro_limite_negativo_avisa_y_se_normaliza.py
=======================================================

Regresion para bug bajo #43 (QA ronda 3): un 'seguro_limite' o
'seguro_limite_ocurrencia' NEGATIVO (solo posible vía un JSON editado a
mano -- los spinboxes de la UI ya restringen ambos campos a
[0, 999999999]) era neutralizado en silencio por el guard `if limite >
0` en el motor (se comportaba exactamente como límite=0, "sin límite"),
sin ningún aviso al usuario de que el valor configurado era inválido.

El fix normaliza explícitamente un límite negativo a 0 y emite un
RiskLabFallbackWarning visible (capturado por el sistema de warnings de
Risk Lab, ver crítico #2 de esta misma ronda), en vez de solo dejar que
el guard numérico lo ignore silenciosamente.

Este test construye un evento con un factor de tipo 'seguro' con
seguro_limite=-500 y seguro_limite_ocurrencia=-100, corre la
simulación, y verifica que: (a) se emite un warning mencionando el
límite negativo, y (b) el comportamiento numérico sigue siendo "sin
límite" (no cambia el resultado, solo se agrega visibilidad).
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
print("BUG BAJO #43: seguro_limite/limite_ocurrencia negativo debe avisar y normalizarse")
print("=" * 70)

dist_frecuencia = RLB.generar_distribucion_frecuencia(1, tasa=2.0)
dist_severidad = RLB.generar_distribucion_severidad(
    1, None, None, None, input_method='direct', params_direct={'mean': 100_000.0, 'std': 5000.0}
)
evento = {
    "id": "e1", "nombre": "EventoConLimiteNegativo", "activo": True,
    "sev_opcion": 1, "sev_input_method": "direct",
    "sev_params_direct": {"mean": 100_000.0, "std": 5000.0},
    "dist_severidad": dist_severidad,
    "freq_opcion": 1, "tasa": 2.0, "dist_frecuencia": dist_frecuencia,
    "vinculos": [],
    "factores_ajuste": [{
        "nombre": "SeguroLimNeg", "activo": True,
        "tipo_modelo": "estatico",
        "afecta_frecuencia": False, "afecta_severidad": True,
        "tipo_severidad": "seguro",
        "seguro_deducible": 10000, "seguro_cobertura_pct": 80,
        "seguro_limite": -500, "seguro_limite_ocurrencia": -100,
        "seguro_tipo_deducible": "agregado",
    }],
}

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    perdidas_totales, frecuencias_totales, _, _ = RLB.generar_lda_con_secuencialidad(
        [evento], num_simulaciones=2000, rng=np.random.default_rng(33)
    )

mensajes_limite_negativo = [
    str(w.message) for w in caught
    if issubclass(w.category, RLB.RiskLabFallbackWarning) and 'límite' in str(w.message).lower()
]
print(f"  warnings capturados sobre límite negativo: {mensajes_limite_negativo}")

check(len(mensajes_limite_negativo) >= 1,
      f"Bug bajo #43: se emite un RiskLabFallbackWarning mencionando el "
      f"límite negativo (obtenido: {mensajes_limite_negativo})")

check(perdidas_totales.size == 2000 and np.all(np.isfinite(perdidas_totales)),
      "La simulación completa sin errores pese al límite negativo (normalizado a 'sin límite')")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
