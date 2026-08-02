"""
test_duplicar_preserva_claves_vinculos.py
=============================================

Regresion para bug medio #14 (QA ronda 2): duplicar_eventos() y
duplicar_scenario() reconstruían los vínculos de los eventos duplicados
armando un dict COMPLETAMENTE NUEVO con exactamente 5 claves fijas
(id_padre, tipo, probabilidad, factor_severidad, umbral_severidad),
descartando silenciosamente cualquier otra clave que el vínculo original
pudiera traer. Es exactamente la misma regresión que el bug #39 de la
Ronda 1 corrigió para el import de configuración JSON — pero ese fix
nunca se aplicó a estas dos rutas de duplicación.

El fix parte de una COPIA del vínculo original (preservando cualquier
clave desconocida/futura) y solo actualiza encima 'id_padre' (remapeado
al nuevo ID si el padre también fue duplicado).

Este test instancia RiskLabApp de verdad (headless), agrega dos eventos
con un vínculo que trae una clave adicional no reconocida por el esquema
actual, duplica el evento hijo (duplicar_eventos) y un escenario completo
(duplicar_scenario), y verifica que esa clave desconocida sobrevive en
ambos casos.
"""
import os
import sys
import copy
import uuid

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


def _evento_base(id_, nombre, vinculos=None):
    return {
        "id": id_, "nombre": nombre, "activo": True,
        "sev_opcion": 2, "sev_input_method": "direct",
        "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
        "sev_params_direct": {"mean": 1000, "std": 100},
        "freq_opcion": 1, "tasa": 3.0,
        "vinculos": vinculos or [],
        "factores_ajuste": [],
    }


VINCULO_CON_CLAVE_FUTURA = {
    "id_padre": "evt-A", "tipo": "AND",
    "probabilidad": 100, "factor_severidad": 1.0, "umbral_severidad": 0,
    "campo_futuro_desconocido": "valor_importante",
}


print("=" * 70)
print("BUG MEDIO #14: duplicar_eventos/duplicar_scenario preservan claves de vínculos")
print("=" * 70)

# --- 1. duplicar_eventos() ---
win = RLB.RiskLabApp()
evento_a = _evento_base("evt-A", "Evento A (root)")
evento_b = _evento_base("evt-B", "Evento B (con vinculo)", vinculos=[dict(VINCULO_CON_CLAVE_FUTURA)])
win.eventos_riesgo = [evento_a, evento_b]
win.eventos_table.setRowCount(2)
win.eventos_table.setItem(0, 1, QtWidgets.QTableWidgetItem("Evento A (root)"))
win.eventos_table.setItem(1, 1, QtWidgets.QTableWidgetItem("Evento B (con vinculo)"))
win.eventos_table.selectRow(1)  # Seleccionar 'Evento B' (el que tiene el vínculo)

win.duplicar_eventos()

evento_b_copia = next(e for e in win.eventos_riesgo if e['nombre'] == 'Evento B (con vinculo) (Copia)')
vinculo_copia = evento_b_copia['vinculos'][0]

check(vinculo_copia.get('campo_futuro_desconocido') == 'valor_importante',
      f"duplicar_eventos(): la clave desconocida 'campo_futuro_desconocido' sobrevive "
      f"a la duplicación (obtenido: {vinculo_copia})")
check(vinculo_copia.get('tipo') == 'AND' and vinculo_copia.get('probabilidad') == 100,
      "duplicar_eventos(): las claves conocidas siguen presentes y correctas")
check(vinculo_copia.get('id_padre') == 'evt-A',
      f"duplicar_eventos(): el id_padre se mantiene igual al original ya que el padre "
      f"('evt-A') NO fue duplicado (obtenido: {vinculo_copia.get('id_padre')})")

# --- 2. duplicar_scenario() ---
win2 = RLB.RiskLabApp()
evento_c = _evento_base("evt-C", "Evento C escenario (root)")
evento_d = _evento_base("evt-D", "Evento D escenario (con vinculo)",
                        vinculos=[{**VINCULO_CON_CLAVE_FUTURA, "id_padre": "evt-C"}])
escenario = RLB.Scenario("EscenarioTest", "desc")
escenario.eventos_riesgo = [evento_c, evento_d]
win2.scenarios = [escenario]
win2.scenarios_table.setRowCount(1)
win2.scenarios_table.setItem(0, 0, QtWidgets.QTableWidgetItem("EscenarioTest"))
win2.scenarios_table.selectRow(0)

win2.duplicar_scenario()

escenario_copia = next(s for s in win2.scenarios if s.nombre == 'EscenarioTest (Copia)')
evento_d_copia = next(e for e in escenario_copia.eventos_riesgo if e['nombre'] == 'Evento D escenario (con vinculo)')
vinculo_d_copia = evento_d_copia['vinculos'][0]

check(vinculo_d_copia.get('campo_futuro_desconocido') == 'valor_importante',
      f"duplicar_scenario(): la clave desconocida 'campo_futuro_desconocido' sobrevive "
      f"a la duplicación (obtenido: {vinculo_d_copia})")
check(vinculo_d_copia.get('tipo') == 'AND' and vinculo_d_copia.get('probabilidad') == 100,
      "duplicar_scenario(): las claves conocidas siguen presentes y correctas")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
