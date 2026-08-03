"""
test_import_json_nombres_escenario_duplicados_avisa.py
===========================================================

Regresion para bug medio R4 #11 (QA ronda 4): guardar_scenario() valida
que el nombre de un escenario sea único al crearlo/editarlo a mano (R3
medio #25), pero cargar_configuracion() nunca validaba lo mismo para
los escenarios que vienen de un archivo JSON importado. Si el archivo
trae dos escenarios con el mismo 'nombre' (archivo editado a mano o
generado externamente), la restauración de 'current_scenario_name' --
que empareja por nombre, tomando el PRIMER match -- selecciona
ambiguamente cualquiera de los dos, no necesariamente el que estaba
realmente seleccionado cuando se guardó el archivo.

El fix detecta nombres de escenario duplicados dentro del archivo ANTES
de procesar, y muestra un QMessageBox.warning explicando cuáles nombres
están duplicados, para que el usuario pueda revisar y corregir el
archivo.

Este test construye un JSON con dos escenarios que comparten el mismo
'nombre' y verifica que cargar_configuracion:
1. Muestre un QMessageBox.warning mencionando el nombre duplicado.
2. Ambos escenarios se carguen igual (no se pierden datos).
3. Un archivo SIN nombres duplicados NO dispare esta advertencia (caso
   negativo, para evitar falsos positivos).
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
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)


def _escenario(nombre, descripcion=""):
    return {"nombre": nombre, "descripcion": descripcion, "eventos_riesgo": []}


print("=" * 70)
print("BUG MEDIO R4 #11: nombres de escenario duplicados en el JSON deben avisarse")
print("=" * 70)

# --- Caso 1: dos escenarios con el MISMO nombre ---
print("\n--- Caso 1: nombre duplicado entre dos escenarios ---")
NOMBRE_DUPLICADO = "EscenarioConflicto"
config_con_duplicado = {
    "num_simulaciones": 5000,
    "eventos_riesgo": [],
    "scenarios": [
        _escenario(NOMBRE_DUPLICADO, "Primera versión"),
        _escenario(NOMBRE_DUPLICADO, "Segunda versión"),
    ],
    "current_scenario_name": None,
}

tmp_path = os.path.join(_THIS_DIR, '_tmp_test_nombres_escenario_duplicados.json')
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config_con_duplicado, f)

try:
    win = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    warnings_capturados = []
    QtWidgets.QMessageBox.warning = staticmethod(
        lambda *a, **kw: warnings_capturados.append(a) or QtWidgets.QMessageBox.Ok
    )

    win.cargar_configuracion()

    check(len(win.scenarios) == 2, "Ambos escenarios se cargaron correctamente")

    texto_completo = " ".join(str(a) for a in warnings_capturados)
    check('duplicad' in texto_completo.lower(),
          f"Bug medio R4 #11: se muestra un aviso mencionando nombres de escenario "
          f"duplicados (obtenido: {len(warnings_capturados)} avisos)")
    check(NOMBRE_DUPLICADO in texto_completo,
          f"El aviso incluye el nombre de escenario duplicado en cuestión")
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

# --- Caso 2: sin nombres duplicados, no debe dispararse el aviso ---
print("\n--- Caso 2: sin nombres duplicados (caso negativo) ---")
config_sin_duplicado = {
    "num_simulaciones": 5000,
    "eventos_riesgo": [],
    "scenarios": [
        _escenario("EscenarioA"),
        _escenario("EscenarioB"),
    ],
    "current_scenario_name": None,
}
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config_sin_duplicado, f)

try:
    win2 = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    warnings_negativo = []
    QtWidgets.QMessageBox.warning = staticmethod(
        lambda *a, **kw: warnings_negativo.append(a) or QtWidgets.QMessageBox.Ok
    )

    win2.cargar_configuracion()

    texto_negativo = " ".join(str(a) for a in warnings_negativo)
    check('duplicad' not in texto_negativo.lower(),
          f"Un archivo SIN nombres de escenario duplicados no dispara el aviso "
          f"(obtenido: {len(warnings_negativo)} avisos: {texto_negativo[:150]!r})")
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
