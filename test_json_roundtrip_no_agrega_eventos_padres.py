"""
test_json_roundtrip_no_agrega_eventos_padres.py
===================================================

Regresion para bug medio #27 (QA ronda 3): cargar_configuracion asignaba
incondicionalmente evento_data['eventos_padres'] = [...] (incluso una
lista VACÍA) a todo evento cargado, sin importar si el evento original
tenía esa clave. Un evento en formato moderno (solo con 'vinculos', sin
'eventos_padres' legado) terminaba con esa clave agregada tras cargar
un archivo JSON -- una violación de fidelidad round-trip (el dict
cargado no era idéntico al que se había guardado), que además se
repetía/acumulaba en cada ciclo guardar→cargar.

El fix solo reasigna 'eventos_padres' si esa clave YA estaba presente
en el evento original.

Este test construye un archivo JSON con un evento SIN 'eventos_padres'
(solo 'vinculos', formato moderno) y verifica que, tras cargarlo, el
evento en memoria NO tiene esa clave agregada.
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
print("BUG MEDIO #27: carga de JSON no debe agregar 'eventos_padres' si no existía")
print("=" * 70)


def _evento_moderno(id_, nombre, vinculos=None):
    return {
        "id": id_, "nombre": nombre, "activo": True,
        "sev_opcion": 2, "sev_input_method": "direct",
        "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
        "sev_params_direct": {"mean": 10000, "std": 1000},
        "freq_opcion": 1, "tasa": 3.0,
        "vinculos": vinculos or [], "factores_ajuste": [],
        # NOTA: sin 'eventos_padres' -- formato moderno, solo 'vinculos'.
    }


config = {
    "num_simulaciones": 5000,
    "eventos_riesgo": [_evento_moderno("evt-A", "Evento Moderno")],
    "scenarios": [
        {"nombre": "EscModerno", "descripcion": "",
         "eventos_riesgo": [_evento_moderno("evt-B", "Evento Escenario Moderno")]}
    ],
}

tmp_path = os.path.join(_THIS_DIR, '_tmp_test_roundtrip_eventos_padres.json')
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config, f)

try:
    win = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    win.cargar_configuracion()

    check(len(win.eventos_riesgo) == 1, "El evento principal se cargó correctamente")
    if win.eventos_riesgo:
        check('eventos_padres' not in win.eventos_riesgo[0],
              f"Bug medio #27: el evento principal cargado NO tiene 'eventos_padres' "
              f"agregado (obtenido claves: {sorted(win.eventos_riesgo[0].keys())})")

    check(len(win.scenarios) == 1, "El escenario se cargó correctamente")
    if win.scenarios:
        evento_esc = win.scenarios[0].eventos_riesgo[0]
        check('eventos_padres' not in evento_esc,
              f"Bug medio #27: el evento del escenario cargado NO tiene "
              f"'eventos_padres' agregado (obtenido claves: {sorted(evento_esc.keys())})")
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
