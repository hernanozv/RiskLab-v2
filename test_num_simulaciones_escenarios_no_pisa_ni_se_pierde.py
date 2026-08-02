"""
test_num_simulaciones_escenarios_no_pisa_ni_se_pierde.py
============================================================

Regresion para bug alto #15 (QA ronda 3): dos problemas relacionados
con el campo "Número de simulaciones" de la pestaña Escenarios
(self.num_simulaciones_var_escenarios, independiente del de la pestaña
"Simulación", self.num_simulaciones_var):

  1. ejecutar_simulacion_escenario() sobreescribía
     self.num_simulaciones_var con el valor de la pestaña Escenarios de
     forma PERMANENTE (sin try/finally), a diferencia de
     self.eventos_riesgo, que sí se restauraba. El usuario perdía
     silenciosamente el valor que tenía configurado en "Simulación"
     cada vez que corría una simulación de escenario.

  2. guardar_configuracion/cargar_configuracion solo persistían
     self.num_simulaciones_var (pestaña Simulación); el de Escenarios
     nunca se guardaba, obligando a reconfigurarlo en cada sesión.

El fix: (1) restaura num_simulaciones_var en un finally, igual que ya
se hace con eventos_riesgo; (2) agrega 'num_simulaciones_escenarios' al
JSON guardado/cargado.

Este test verifica ambos aspectos: (a) llamando
ejecutar_simulacion_escenario con self.ejecutar_simulacion mockeado
(para no lanzar un QThread real) y comprobando que el campo de
Simulación vuelve a su valor original después; (b) guardando y
recargando la configuración y verificando que el campo de Escenarios
sobrevive el ciclo completo.
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
QtWidgets.QMessageBox.information = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)

print("=" * 70)
print("BUG ALTO #15: num_simulaciones de Escenarios no debe pisar ni perderse")
print("=" * 70)

# --- 1. ejecutar_simulacion_escenario restaura num_simulaciones_var ---
win = RLB.RiskLabApp()
evento = {
    'id': 'e1', 'nombre': 'EventoEsc', 'activo': True,
    'freq_opcion': 1, 'tasa': 5.0,
    'sev_opcion': 1, 'sev_input_method': 'min_mode_max',
    'sev_minimo': 100.0, 'sev_mas_probable': 500.0, 'sev_maximo': 1000.0,
}
escenario = RLB.Scenario("EscTest", "desc")
escenario.eventos_riesgo = [evento]
win.scenarios = [escenario]
win.current_scenario = escenario

win.num_simulaciones_var.setText("50000")
win.num_simulaciones_var_escenarios.setText("777")

win.ejecutar_simulacion = lambda: None  # evitar lanzar un QThread real
win.ejecutar_simulacion_escenario()

check(win.num_simulaciones_var.text() == "50000",
      f"Bug alto #15: num_simulaciones_var (pestaña Simulación) se RESTAURA a "
      f"su valor original tras ejecutar una simulación de escenario, igual que "
      f"ya hace eventos_riesgo (obtenido: {win.num_simulaciones_var.text()!r})")

# --- 2. num_simulaciones_var_escenarios se persiste en el JSON ---
win2 = RLB.RiskLabApp()
win2.eventos_riesgo = [dict(evento)]  # al menos un evento: evita el early-return de "sin datos para guardar"
win2.scenarios = []
win2.num_simulaciones_var.setText("10000")
win2.num_simulaciones_var_escenarios.setText("777")

tmp_path = os.path.join(_THIS_DIR, '_tmp_test_num_sim_escenarios.json')
QtWidgets.QFileDialog.getSaveFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))

try:
    win2.guardar_configuracion()
    with open(tmp_path, 'r', encoding='utf-8') as f:
        guardado = json.load(f)
    check(guardado.get('num_simulaciones_escenarios') == 777,
          f"Bug alto #15: 'num_simulaciones_escenarios' se persiste en el JSON guardado "
          f"(obtenido: {guardado.get('num_simulaciones_escenarios')!r})")

    win3 = RLB.RiskLabApp()
    win3.cargar_configuracion()
    check(win3.num_simulaciones_var_escenarios.text() == "777",
          f"Bug alto #15: al recargar, num_simulaciones_var_escenarios recupera "
          f"el valor guardado (obtenido: {win3.num_simulaciones_var_escenarios.text()!r})")
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
