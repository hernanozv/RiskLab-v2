"""
test_scenario_sin_metodos_muertos.py
========================================

Regresion para bug bajo #36 (QA ronda 3): la clase Scenario definía
to_dict()/from_dict(), pero ningún sitio del código los invocaba -- la
serialización real de escenarios (guardar_configuracion) y su
deserialización (cargar_configuracion) duplican esa lógica de forma
independiente y ligeramente distinta (guardar_configuracion usa la
lista canónica _CAMPOS_INTERNOS_SIMULACION para limpiar campos
internos; Scenario.to_dict() usaba un criterio más laxo,
`key.startswith('_')`). Mantener dos implementaciones no usadas /
parcialmente inconsistentes es deuda técnica y una fuente de futuras
confusiones (alguien podría "arreglar" un bug editando el método
muerto, sin efecto real).

El fix elimina Scenario.to_dict()/from_dict() por completo. La
serialización real de escenarios sigue viviendo únicamente en
guardar_configuracion/cargar_configuracion.

Este test verifica que: (a) Scenario ya no expone to_dict/from_dict, y
(b) el ciclo real guardar→cargar de un escenario sigue funcionando
correctamente (para descartar que la eliminación haya roto algo).
"""
import json
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

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
QtWidgets.QMessageBox.warning = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)

print("=" * 70)
print("BUG BAJO #36: Scenario.to_dict()/from_dict() (código muerto) deben eliminarse")
print("=" * 70)

check(not hasattr(RLB.Scenario, 'to_dict'),
      "Bug bajo #36: Scenario ya NO expone to_dict() (código muerto eliminado)")
check(not hasattr(RLB.Scenario, 'from_dict'),
      "Bug bajo #36: Scenario ya NO expone from_dict() (código muerto eliminado)")

# Verificar que el ciclo REAL guardar -> cargar de un escenario sigue
# funcionando (la eliminación no rompió la serialización real).
win = RLB.RiskLabApp()
sc = RLB.Scenario("EscenarioReal", "Descripción de prueba")
sc.eventos_riesgo = [{
    "id": "evt-1", "nombre": "EventoEnEscenario", "activo": True,
    "sev_opcion": 2, "sev_input_method": "direct",
    "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
    "sev_params_direct": {"mean": 5000, "std": 500},
    "freq_opcion": 1, "tasa": 2.0, "vinculos": [], "factores_ajuste": [],
}]
win.scenarios = [sc]
win.eventos_riesgo = []

tmp_path = os.path.join(_THIS_DIR, '_tmp_test_scenario_sin_metodos_muertos.json')
try:
    QtWidgets.QFileDialog.getSaveFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    win.guardar_configuracion()
    check(os.path.exists(tmp_path), "guardar_configuracion() escribió el archivo JSON")

    with open(tmp_path, encoding='utf-8') as f:
        data = json.load(f)
    check(len(data.get('scenarios', [])) == 1 and data['scenarios'][0]['nombre'] == 'EscenarioReal',
          f"El JSON guardado contiene el escenario esperado (obtenido: {data.get('scenarios')})")

    win2 = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    win2.cargar_configuracion()
    check(len(win2.scenarios) == 1 and win2.scenarios[0].nombre == 'EscenarioReal',
          f"cargar_configuracion() reconstituyó el escenario correctamente "
          f"(obtenido: {[s.nombre for s in win2.scenarios]})")
    check(len(win2.scenarios[0].eventos_riesgo) == 1 and
          win2.scenarios[0].eventos_riesgo[0]['nombre'] == 'EventoEnEscenario',
          "El evento dentro del escenario cargado es correcto")
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
