"""
test_doc_comportamiento_error_escenario.py
=============================================

Regresion para hallazgo bajo #5: ESPECIFICACION_JSON_RISK_LAB.md (y
"Asistente GPT Risk Lab.md") documentaban que un error de severidad en un
evento DENTRO de un escenario NO omitía el evento, sino que lo agregaba
con severidad nula (pudiendo fallar al simular) — a diferencia de los
eventos principales, donde sí se omite. Esa documentación estaba
desactualizada: el código actual (cargar_configuracion, bloque de carga de
escenarios) omite el evento con severidad inválida exactamente igual que
para la lista principal (catch de la excepción + `continue`), reporta el
error, y sigue cargando el resto.

Se corrigió el texto de ambos documentos para reflejar el comportamiento
real. Este test verifica, de punta a punta (instanciando RiskLabApp de
verdad), que el comportamiento documentado hoy efectivamente ocurre: un
evento con severidad inválida dentro de un escenario se OMITE (no se
agrega con severidad nula), igual que en la lista principal.
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
_warnings_mostrados = []
QtWidgets.QMessageBox.warning = staticmethod(
    lambda parent, titulo, texto, *a, **kw: _warnings_mostrados.append((titulo, texto)) or QtWidgets.QMessageBox.Ok
)
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)


def _evento(id_, nombre, sev_valida=True):
    if sev_valida:
        sev = {"sev_opcion": 2, "sev_input_method": "direct",
               "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
               "sev_params_direct": {"mean": 1000, "std": 100}}
    else:
        # min_mode_max con 'mas_probable' fuera de [minimo, maximo] -> invalido
        sev = {"sev_opcion": 1, "sev_input_method": "min_mode_max",
               "sev_minimo": 100, "sev_mas_probable": 999999, "sev_maximo": 200,
               "sev_params_direct": {}}
    return {
        "id": id_, "nombre": nombre, "activo": True,
        "freq_opcion": 1, "tasa": 3.0,
        "vinculos": [], "factores_ajuste": [],
        **sev,
    }


print("=" * 70)
print("Hallazgo bajo #5: doc actualizada — error de severidad en escenarios")
print("=" * 70)

config = {
    "num_simulaciones": 5000,
    "eventos_riesgo": [],
    "scenarios": [{
        "nombre": "EscenarioTest", "descripcion": "",
        "eventos_riesgo": [
            _evento("x", "EventoSevInvalida", sev_valida=False),
            _evento("y", "EventoValido", sev_valida=True),
        ],
    }],
}

tmp_path = os.path.join(_THIS_DIR, '_tmp_doc_error_escenario.json')
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config, f)

try:
    win = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    win.cargar_configuracion()

    escenario = win.scenarios[0]
    nombres = [e['nombre'] for e in escenario.eventos_riesgo]

    check('EventoSevInvalida' not in nombres,
          f"El evento con severidad inválida se OMITE del escenario (comportamiento "
          f"documentado hoy), no se agrega con severidad nula (obtenido: {nombres})")
    check('EventoValido' in nombres,
          "El evento válido del mismo escenario sigue cargando correctamente")
    check(len(escenario.eventos_riesgo) == 1,
          f"El escenario queda con exactamente 1 evento (el válido), no 2 "
          f"(obtenido: {len(escenario.eventos_riesgo)})")
    check(len(_warnings_mostrados) >= 1,
          "Se reporta al usuario el evento omitido por severidad inválida")
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
