"""
test_risk_map_importancia_score.py
======================================

Regresion para bugs criticos #4 y #5 (QA ronda 3), ambos en
_build_risk_map (seccion 'results.risk_map' del export IA):

  #4: 'importancia_score' se calculaba como impacto_p90 * frecuencia_modo.
      Para un evento de baja frecuencia/alta severidad (el perfil de
      riesgo que Risk Lab esta pensado para modelar: fraude catastrofico,
      eventos sistemicos, etc.), tanto el percentil 90 de la perdida
      agregada (0 si el evento ocurre en menos del 10% de las
      simulaciones) como la frecuencia_modo (0 si ocurre en menos del
      50%) colapsaban a 0, dando importancia_score=0.0 -- el minimo
      posible -- exactamente para el evento que mas deberia importar.
      Esto contradecia al 'executive_summary' del MISMO export, que
      calcula la contribucion al riesgo sobre la MEDIA y puede reportar
      a ese mismo evento como el que domina el riesgo agregado.
      El fix usa impacto_medio (perdida esperada anual, que SI incorpora
      la frecuencia real de ocurrencia) como score de importancia,
      consistente con esa otra seccion del mismo export.

  #5: cuando la frecuencia maxima de un evento superaba 100.000 (guard
      de memoria de np.bincount), 'frecuencia_modo' se fijaba en 0 (un
      dato FALSO, no un "N/A"), en vez de usar el fallback correcto
      (scipy.stats.mode) que ya usan otras partes de la app para el
      mismo caso. Esto distorsionaba tanto 'frecuencia_modo' como el
      cuadrante Alto/Bajo Impacto x Alta/Baja Frecuencia.

Este test construye escenarios sinteticos que reproducen ambos casos
directamente sobre _build_risk_map (que no depende de mas estado que sus
parametros), sin necesidad de correr una simulacion completa.
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
print("BUGS CRÍTICOS #4 y #5: risk_map.importancia_score / frecuencia_modo")
print("=" * 70)

# ---------------------------------------------------------------------
# Bug crítico #4: evento raro-catastrófico no debe colapsar a
# importancia_score=0, y debe superar en importancia a un evento
# frecuente pero de impacto medio mucho menor (consistente con
# executive_summary, que rankearía al catastrófico como dominante).
# ---------------------------------------------------------------------
rng = np.random.default_rng(123)
N = 100_000

# Evento raro: ocurre en 2% de los años, pérdida grande cuando ocurre.
ocurre = rng.random(N) < 0.02
perdida_catastrofico = np.where(ocurre, rng.uniform(30_000_000, 70_000_000, N), 0.0)
freq_catastrofico = ocurre.astype(int)

# Evento frecuente: ocurre siempre, pérdida chica.
perdida_frecuente = rng.uniform(10_000, 20_000, N)
freq_frecuente = np.full(N, 5, dtype=int)

eventos = [
    {"id": "e1", "nombre": "Catastrófico raro"},
    {"id": "e2", "nombre": "Frecuente menor"},
]
perdidas_por_evento = [perdida_catastrofico, perdida_frecuente]
frecuencias_por_evento = [freq_catastrofico, freq_frecuente]

risk_map = RLB.RiskLabApp._build_risk_map(None, eventos, perdidas_por_evento, frecuencias_por_evento)
check(risk_map is not None, "_build_risk_map devuelve un resultado no nulo")

registros = {r["event_name"]: r for r in risk_map["events"]} if risk_map else {}
r_cat = registros.get("Catastrófico raro")
r_frec = registros.get("Frecuente menor")
check(r_cat is not None and r_frec is not None, "Ambos eventos aparecen en risk_map.events")

if r_cat is not None:
    print(f"  Catastrófico raro: impacto_medio={r_cat['impacto_medio']:.0f}, "
          f"impacto_p90={r_cat['impacto_p90']:.0f}, frecuencia_modo={r_cat['frecuencia_modo']}, "
          f"importancia_score={r_cat['importancia_score']:.2f}")
    check(r_cat["importancia_score"] > 1000,
          f"Bug crítico #4: el evento catastrófico-raro NO colapsa a "
          f"importancia_score≈0 (obtenido: {r_cat['importancia_score']:.2f})")

if r_frec is not None:
    print(f"  Frecuente menor: impacto_medio={r_frec['impacto_medio']:.0f}, "
          f"importancia_score={r_frec['importancia_score']:.2f}")

if r_cat is not None and r_frec is not None:
    check(r_cat["importancia_score"] > r_frec["importancia_score"],
          f"Bug crítico #4: el evento catastrófico-raro (domina el riesgo agregado "
          f"medio) tiene mayor importancia_score que el evento frecuente-menor, "
          f"consistente con executive_summary (obtenido: cat={r_cat['importancia_score']:.2f} "
          f"vs frec={r_frec['importancia_score']:.2f})")
    check(abs(r_cat["importancia_score"] - r_cat["impacto_medio"]) < 1e-6,
          "importancia_score coincide con impacto_medio (misma base que executive_summary)")

# ---------------------------------------------------------------------
# Bug crítico #5: frecuencia_modo con max(f_arr) > 100.000 debe usar el
# fallback de scipy.stats.mode, no fijarse falsamente en 0.
# ---------------------------------------------------------------------
freq_alta = rng.integers(199_000, 201_000, N)  # todos > 100_000, moda real ~200_000
perdida_alta = rng.uniform(1.0, 2.0, N)

eventos2 = [{"id": "e3", "nombre": "AltaFrecuencia"}]
risk_map2 = RLB.RiskLabApp._build_risk_map(None, eventos2, [perdida_alta], [freq_alta])
check(risk_map2 is not None, "_build_risk_map (caso alta frecuencia) devuelve un resultado no nulo")
if risk_map2:
    r_alta = risk_map2["events"][0]
    print(f"  AltaFrecuencia: frecuencia_modo={r_alta['frecuencia_modo']} "
          f"(máximo real de la muestra: {int(np.max(freq_alta))})")
    check(r_alta["frecuencia_modo"] > 100000,
          f"Bug crítico #5: frecuencia_modo usa el fallback correcto (scipy.stats.mode) "
          f"para frecuencias > 100.000, no se fija falsamente en 0 "
          f"(obtenido: {r_alta['frecuencia_modo']})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
