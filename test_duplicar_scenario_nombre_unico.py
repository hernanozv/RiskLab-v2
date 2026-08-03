"""
test_duplicar_scenario_nombre_unico.py
==========================================

Regresion para bug alto R4 #6 (QA ronda 4): guardar_scenario() valida
desde R3 medio #25 que no existan dos escenarios con el mismo nombre
(la restauración del "escenario actual" tras cargar un JSON empareja
por nombre, primer match, así que nombres duplicados hacen esa
restauración ambigua). Pero duplicar_scenario() no pasa por esa
validación: simplemente concatena " (Copia)" al nombre original sin
chequear colisiones contra self.scenarios. Duplicar el mismo escenario
dos veces (o duplicar un escenario que ya se llamaba "X (Copia)")
producía dos escenarios con nombres idénticos.

El fix agrega una búsqueda de nombre único en duplicar_scenario():
"X (Copia)", y si ya existe, "X (Copia) 2", "X (Copia) 3", etc.

Este test verifica que:
1. Duplicar un escenario "Base" dos veces produce "Base (Copia)" y
   "Base (Copia) 2" (nombres distintos), no dos escenarios "Base (Copia)".
2. Ningún par de escenarios en self.scenarios comparte nombre tras
   duplicar repetidamente.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

from PyQt5 import QtCore, QtWidgets

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


def _seleccionar_fila(tabla, row):
    # NOTA: QTableWidget.selectRow() no es confiable en modo headless/offscreen
    # tras un insertRow() previo cuando la tabla está en MultiSelection (queda
    # sin selección). Se usa selectionModel().select() explícitamente en su lugar.
    sm = tabla.selectionModel()
    sm.clearSelection()
    sm.select(tabla.model().index(row, 0),
              QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)


app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

QtWidgets.QMessageBox.warning = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)

print("=" * 70)
print("BUG ALTO R4 #6: duplicar_scenario() debe generar nombres únicos")
print("=" * 70)

win = RLB.RiskLabApp()

def agregar_fila_tabla(win, scenario):
    row = win.scenarios_table.rowCount()
    win.scenarios_table.insertRow(row)
    win.scenarios_table.setItem(row, 0, QtWidgets.QTableWidgetItem(scenario.nombre))
    win.scenarios_table.setItem(row, 1, QtWidgets.QTableWidgetItem(scenario.descripcion))


scenario_base = RLB.Scenario("Base", "Escenario original")
scenario_base.eventos_riesgo = []
win.scenarios = [scenario_base]
agregar_fila_tabla(win, scenario_base)
win.actualizar_vista_escenarios()

_seleccionar_fila(win.scenarios_table, 0)
win.duplicar_scenario()

print(f"  Escenarios tras 1ra duplicación: {[sc.nombre for sc in win.scenarios]}")
check(len(win.scenarios) == 2, "Se creó un segundo escenario")
check(win.scenarios[1].nombre == "Base (Copia)",
      f"Primera duplicación produce 'Base (Copia)' (obtenido: {win.scenarios[1].nombre!r})")

# Duplicar el escenario ORIGINAL "Base" de nuevo -- ahora ya existe "Base (Copia)".
_seleccionar_fila(win.scenarios_table, 0)
win.duplicar_scenario()

print(f"  Escenarios tras 2da duplicación: {[sc.nombre for sc in win.scenarios]}")
check(len(win.scenarios) == 3, "Se creó un tercer escenario")

nombres = [sc.nombre for sc in win.scenarios]
check(len(nombres) == len(set(nombres)),
      f"Bug alto R4 #6: no hay dos escenarios con el mismo nombre "
      f"(obtenido: {nombres})")
check(nombres[2] != "Base (Copia)",
      f"Bug alto R4 #6: la segunda duplicación de 'Base' NO reutiliza el nombre "
      f"'Base (Copia)' ya tomado (obtenido: {nombres[2]!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
