"""
test_export_ia_eventos_inactivos.py
=======================================

Regresion para bug critico #3 (QA ronda 3): _construir_export_payload_ia
obtenia la lista de eventos desde self.resultados_simulacion['eventos_riesgo'],
que ejecutar_simulacion ya pre-filtra a solo los eventos ACTIVOS antes de
simular (linea "eventos_activos_originales = [e for e in eventos if
e.get('activo', True)]"). Como consecuencia:

  - Los eventos DESACTIVADOS por el usuario nunca aparecian en
    payload['input_events'], como si no existieran en el modelo.
  - 'active_events_count' y 'total_events_count' se calculaban sobre esa
    misma lista ya filtrada, por lo que SIEMPRE eran iguales entre si,
    contradiciendo el propio EXPORT_SCHEMA.md (cuyo ejemplo documenta que
    pueden diferir) y ocultandole a cualquier agente IA consumidor del
    archivo que existen eventos desactivados en el modelo.

El fix resuelve la lista COMPLETA de eventos configurados (activos +
inactivos) desde self.eventos_riesgo (o self.current_scenario.eventos_riesgo
si la corrida fue de un escenario), y la usa para 'active_events_count',
'total_events_count' e 'input_events'. Las secciones de resultados
('results', 'topological_order', 'engine_limits') siguen basadas en los
eventos realmente simulados (activos), sin cambios.

Este test arma una app headless con 2 eventos configurados (uno activo,
uno inactivo) pero con self.resultados_simulacion ya pre-poblado como lo
dejaria una simulacion real (solo con el evento activo, replicando el
filtro de ejecutar_simulacion), y verifica que el payload de export:
  1. Reporta total_events_count=2 y active_events_count=1 (distintos).
  2. Incluye AMBOS eventos en input_events (activo e inactivo).
  3. El evento inactivo aparece marcado con 'activo': False.
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
print("BUG CRÍTICO #3: eventos inactivos ausentes del export IA")
print("=" * 70)

evento_activo = {
    'id': 'e1', 'nombre': 'EventoActivo', 'activo': True,
    'freq_opcion': 1, 'tasa': 5.0,
    'sev_opcion': 1, 'sev_input_method': 'min_mode_max',
    'sev_minimo': 100.0, 'sev_mas_probable': 500.0, 'sev_maximo': 1000.0,
}
evento_inactivo = {
    'id': 'e2', 'nombre': 'EventoInactivo', 'activo': False,
    'freq_opcion': 1, 'tasa': 3.0,
    'sev_opcion': 1, 'sev_input_method': 'min_mode_max',
    'sev_minimo': 50.0, 'sev_mas_probable': 200.0, 'sev_maximo': 500.0,
}

win = RLB.RiskLabApp()
# Configuracion completa del modelo: 2 eventos, uno inactivo.
win.eventos_riesgo = [evento_activo, evento_inactivo]

# Simular lo que deja ejecutar_simulacion en resultados_simulacion: SOLO
# el evento activo (mismo filtro que 'eventos_activos_originales').
N = 200
perdidas_totales = np.full(N, 1000.0)
frecuencias_totales = np.ones(N, dtype=int)
win.resultados_simulacion = {
    'perdidas_totales': perdidas_totales,
    'frecuencias_totales': frecuencias_totales,
    'perdidas_por_evento': [perdidas_totales.copy()],
    'frecuencias_por_evento': [frecuencias_totales.copy()],
    'eventos_riesgo': [evento_activo],  # ya pre-filtrado, como en produccion
}
win.current_scenario = None

payload = win._construir_export_payload_ia({})

total_events_count = payload['execution_metadata']['total_events_count']
active_events_count = payload['execution_metadata']['active_events_count']
print(f"  total_events_count={total_events_count}, active_events_count={active_events_count}")

check(total_events_count == 2,
      f"Bug crítico #3: total_events_count refleja TODOS los eventos configurados "
      f"(activos + inactivos), no solo los simulados (obtenido: {total_events_count})")
check(active_events_count == 1,
      f"active_events_count refleja solo los eventos activos (obtenido: {active_events_count})")
check(total_events_count != active_events_count,
      f"Bug crítico #3: total_events_count y active_events_count pueden diferir "
      f"(antes SIEMPRE eran iguales porque ambos se calculaban sobre la lista "
      f"ya pre-filtrada a activos)")

nombres_input_events = [e.get('nombre') for e in payload.get('input_events', [])]
print(f"  input_events: {nombres_input_events}")
check('EventoActivo' in nombres_input_events,
      "El evento activo aparece en input_events")
check('EventoInactivo' in nombres_input_events,
      f"Bug crítico #3: el evento INACTIVO también aparece en input_events "
      f"(antes desaparecía por completo del export) (obtenido: {nombres_input_events})")

evento_inactivo_export = next(
    (e for e in payload.get('input_events', []) if e.get('nombre') == 'EventoInactivo'), None
)
check(evento_inactivo_export is not None, "Se encontró el evento inactivo en input_events")
if evento_inactivo_export is not None:
    check(evento_inactivo_export.get('activo') is False,
          f"El evento inactivo queda marcado con 'activo': False en el export "
          f"(obtenido: {evento_inactivo_export.get('activo')!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
