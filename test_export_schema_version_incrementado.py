"""
test_export_schema_version_incrementado.py
==============================================

Regresion para bug bajo R4 #1 (QA ronda 4): EXPORT_SCHEMA_VERSION quedó
fijo en "1.0" a lo largo de rondas de QA que agregaron secciones/campos
nuevos al export IA (ai_agent_briefing, engine_limits, _meaning en
scenario_impacts, activo en factores_ajuste,
input_events_omitidos/input_scenarios_omitidos, etc.) y que incluso
cambiaron el SIGNIFICADO de un campo ya existente sin renombrarlo
(risk_map.importancia_score cambió de fórmula en R3 crítico #4). Ningún
consumidor externo (agente IA, script de análisis) podía detectar que
el formato había cambiado, ya que "$schema_version" siempre reportaba
el mismo valor.

El fix incrementó EXPORT_SCHEMA_VERSION (originalmente a "1.1") y actualiza
las referencias a la versión en EXPORT_SCHEMA.md (encabezado + ejemplos
JSON) para que queden consistentes con el código.

Actualización: al agregar las distribuciones nuevas (Burr sev=6, Weibull
sev=7, Log-t sev=8, Zero-Inflated Poisson freq=6) el schema del export IA
sumó los códigos/parámetros correspondientes, por lo que la versión se
incrementó nuevamente a "1.2". Este test se mantiene como guardián de que
código y documento nunca se desincronicen.

Este test verifica que:
1. EXPORT_SCHEMA_VERSION en el código sea "1.2", no una versión vieja.
2. El payload real construido por _construir_export_payload_ia refleje
   ese mismo valor en "$schema_version".
3. EXPORT_SCHEMA.md ya no mencione versiones viejas ("1.0"/"1.1") en
   ningún lugar donde documenta la versión del schema.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np
from PyQt5 import QtWidgets

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


app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

print("=" * 70)
print("BUG BAJO R4 #1: EXPORT_SCHEMA_VERSION debe incrementarse tras cambios de formato")
print("=" * 70)

check(RLB.EXPORT_SCHEMA_VERSION == "1.2",
      f"EXPORT_SCHEMA_VERSION es '1.2' (incrementado tras agregar las "
      f"distribuciones nuevas), no una versión vieja "
      f"(obtenido: {RLB.EXPORT_SCHEMA_VERSION!r})")

win = RLB.RiskLabApp()
win.eventos_riesgo = [{'id': 'e1', 'nombre': 'EventoA', 'activo': True}]
win.resultados_simulacion = {
    'perdidas_totales': np.array([1000.0]),
    'frecuencias_totales': np.array([1]),
    'perdidas_por_evento': [np.array([1000.0])],
    'frecuencias_por_evento': [np.array([1])],
    'eventos_riesgo': win.eventos_riesgo,
}
win.current_scenario = None

payload = win._construir_export_payload_ia({})
check(payload.get('$schema_version') == RLB.EXPORT_SCHEMA_VERSION,
      f"El payload real del export IA usa la misma versión que EXPORT_SCHEMA_VERSION "
      f"(obtenido: {payload.get('$schema_version')!r})")

with open(os.path.join(_THIS_DIR, 'EXPORT_SCHEMA.md'), encoding='utf-8') as f:
    schema_md = f.read()

check('`1.2`' in schema_md,
      "EXPORT_SCHEMA.md documenta la versión '1.2' en su encabezado")
check('"$schema_version": "1.0"' not in schema_md and '"$schema_version": "1.1"' not in schema_md,
      "EXPORT_SCHEMA.md ya NO menciona versiones viejas ('1.0'/'1.1') en sus ejemplos JSON")
check('`1.0`' not in schema_md and '`1.1`' not in schema_md,
      "EXPORT_SCHEMA.md ya NO menciona '1.0'/'1.1' como versión del schema")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
