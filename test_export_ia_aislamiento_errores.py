"""
test_export_ia_aislamiento_errores.py
=========================================

Regresion para bug alto #12 (QA ronda 3): manejo de errores inconsistente
entre 'input_events' e 'input_scenarios' en el export IA.

Antes del fix: un solo evento que hiciera fallar
_decodificar_evento_para_export (por cualquier motivo no previsto)
abortaba la exportación COMPLETA (list comprehension sin try/except),
incluso si el resto de los eventos y escenarios eran válidos. Un
escenario que fallara, en cambio, se descartaba ENTERO y en silencio
(except/continue sin ningún registro), sin dejar ningún rastro en el
payload -- un agente IA no tenía forma de saber que faltaban uno o más
escenarios.

El fix aísla el error por evento (para 'input_events') y por escenario
(para 'input_scenarios'), dejando constancia explícita de lo omitido en
'input_events_omitidos'/'input_scenarios_omitidos', en vez de abortar
todo o descartar en silencio.

Este test arma una app headless con:
  - eventos_todos = [evento_valido, "no-es-un-dict"] (el segundo dispara
    un AttributeError real al llamar .get() sobre un string).
  - un escenario cuyo único evento también es "no-es-un-dict".
Y verifica que el evento/escenario válido se exporta igual, y que los
inválidos quedan registrados explícitamente (no silenciosamente
perdidos, no abortando toda la exportación).
"""
import os
import sys
import types

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
print("BUG ALTO #12: aislamiento de errores en input_events / input_scenarios")
print("=" * 70)

evento_valido = {
    'id': 'e1', 'nombre': 'EventoValido', 'activo': True,
    'freq_opcion': 1, 'tasa': 5.0,
    'sev_opcion': 1, 'sev_input_method': 'min_mode_max',
    'sev_minimo': 100.0, 'sev_mas_probable': 500.0, 'sev_maximo': 1000.0,
}
# Dict bien formado (no rompe mapa_nombres ni el resto de la construcción
# del payload), pero con un campo que revienta DENTRO de
# _decodificar_evento_para_export: freq_opcion no numérico -> int(...) falla
# con ValueError. Reproduce una falla de decodificación aislada realista,
# a diferencia de un tipo completamente ajeno (que rompería código anterior
# a _decodificar_evento_para_export, no lo que este test quiere aislar).
evento_roto = {
    'id': 'e2', 'nombre': 'EventoRoto', 'activo': True,
    'freq_opcion': 'no-es-un-numero',
}

win = RLB.RiskLabApp()
win.eventos_riesgo = [evento_valido, evento_roto]

N = 100
perdidas_totales = np.full(N, 1000.0)
frecuencias_totales = np.ones(N, dtype=int)
win.resultados_simulacion = {
    'perdidas_totales': perdidas_totales,
    'frecuencias_totales': frecuencias_totales,
    'perdidas_por_evento': [perdidas_totales.copy()],
    'frecuencias_por_evento': [frecuencias_totales.copy()],
    'eventos_riesgo': [evento_valido],
}
win.current_scenario = None

escenario_roto = types.SimpleNamespace(
    nombre='EscenarioRoto', descripcion='desc', eventos_riesgo=[evento_roto]
)
win.scenarios = [escenario_roto]

payload = win._construir_export_payload_ia({})

nombres_input_events = [e.get('nombre') for e in payload.get('input_events', [])]
print(f"  input_events: {nombres_input_events}")
check('EventoValido' in nombres_input_events,
      f"Bug alto #12: el evento VÁLIDO se exporta igual, pese a que otro evento "
      f"en la misma lista es inválido (obtenido: {nombres_input_events})")

omitidos_eventos = payload.get('input_events_omitidos', [])
check(len(omitidos_eventos) >= 1,
      f"Bug alto #12: el evento inválido queda registrado explícitamente en "
      f"'input_events_omitidos', no silenciosamente perdido ni aborta toda la "
      f"exportación (obtenido: {omitidos_eventos})")

omitidos_escenarios = payload.get('input_scenarios_omitidos', [])
print(f"  input_scenarios_omitidos: {omitidos_escenarios}")
check(len(omitidos_escenarios) >= 1,
      f"Bug alto #12: el escenario inválido queda registrado explícitamente en "
      f"'input_scenarios_omitidos', no descartado en silencio "
      f"(obtenido: {omitidos_escenarios})")
if omitidos_escenarios:
    check(omitidos_escenarios[0].get('nombre') == 'EscenarioRoto',
          f"El registro identifica el escenario afectado por nombre "
          f"(obtenido: {omitidos_escenarios[0]!r})")

check(payload.get('input_scenarios') == [],
      f"El escenario roto no aparece en input_scenarios (lista vacía) "
      f"(obtenido: {payload.get('input_scenarios')!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
