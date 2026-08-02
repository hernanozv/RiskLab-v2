"""
test_risk_map_cuadrante_importancia_consistentes.py
=======================================================

Regresion para bug medio #24 (QA ronda 3): en 'results.risk_map'
(export IA), el cuadrante (Alto/Bajo Impacto x Alta/Baja Frecuencia) se
calculaba sobre impacto_medio, mientras que 'importancia_score' (antes
del fix crítico #4 de esta misma ronda) se calculaba sobre impacto_p90.
Esto permitía que un evento quedara clasificado "Alto Impacto" en el
cuadrante mientras 'importancia_score' fuera ≈0 (para eventos de baja
frecuencia/alta severidad, donde el P90 de la pérdida agregada es 0),
generando mensajes contradictorios dentro del mismo bloque.

El fix crítico #4 (mismo archivo, ronda 3) ya resolvió esto de forma
indirecta: 'importancia_score' pasó a basarse en impacto_medio (la
MISMA base que usa el cuadrante para su eje X), por lo que ambos
quedan consistentes automáticamente. Este test verifica explícitamente
que la consistencia se mantiene: un evento "Alto Impacto" según el
cuadrante debe tener mayor importancia_score que uno "Bajo Impacto",
usando el mismo escenario catastrófico-raro vs. frecuente-menor que
expone el caso extremo (P90=0 para el evento raro).
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
print("BUG MEDIO #24: cuadrante e importancia_score no deben contradecirse")
print("=" * 70)

rng = np.random.default_rng(123)
N = 100_000
ocurre = rng.random(N) < 0.02  # ocurre en el 2% de los años: P90=0
perdida_catastrofico = np.where(ocurre, rng.uniform(30_000_000, 70_000_000, N), 0.0)
freq_catastrofico = ocurre.astype(int)

perdida_frecuente = rng.uniform(10_000, 20_000, N)
freq_frecuente = np.full(N, 5, dtype=int)

eventos = [
    {"id": "e1", "nombre": "Catastrófico raro"},
    {"id": "e2", "nombre": "Frecuente menor"},
]
risk_map = RLB.RiskLabApp._build_risk_map(
    None, eventos, [perdida_catastrofico, perdida_frecuente], [freq_catastrofico, freq_frecuente]
)
registros = {r["event_name"]: r for r in risk_map["events"]}
r_cat = registros["Catastrófico raro"]
r_frec = registros["Frecuente menor"]

print(f"  Catastrófico raro: cuadrante={r_cat['cuadrante']!r}, importancia={r_cat['importancia_score']:.2f}")
print(f"  Frecuente menor:   cuadrante={r_frec['cuadrante']!r}, importancia={r_frec['importancia_score']:.2f}")

check(r_cat['cuadrante'].startswith("Alto Impacto"),
      f"El evento catastrófico-raro queda clasificado 'Alto Impacto' en el cuadrante "
      f"(obtenido: {r_cat['cuadrante']!r})")
check(r_cat['importancia_score'] > r_frec['importancia_score'],
      f"Bug medio #24: el evento 'Alto Impacto' tiene MAYOR importancia_score que el "
      f"evento 'Bajo Impacto', sin contradicción entre ambos campos (obtenido: "
      f"cat={r_cat['importancia_score']:.2f} vs frec={r_frec['importancia_score']:.2f})")
check(r_cat['importancia_score'] > 1000,
      f"El importancia_score del evento 'Alto Impacto' no colapsa a ≈0 pese a que su "
      f"P90 (impacto_p90={r_cat['impacto_p90']:.2f}) sí es 0 (obtenido: "
      f"{r_cat['importancia_score']:.2f})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
