"""
test_scenarios_table_multiseleccion_habilitada.py
=====================================================

Regresion para bug bajo R4 #6 (QA ronda 4): eliminar_scenario() siempre
estuvo escrito para soportar borrado múltiple -- confirma "¿eliminar N
escenario(s)?" con la cantidad real de filas seleccionadas, e itera
sobre TODAS las filas seleccionadas (en orden descendente) borrándolas
una por una. Pero self.scenarios_table estaba configurada con
QAbstractItemView.SingleSelection, haciendo ese código de borrado
múltiple completamente inalcanzable: nunca podía haber más de una fila
seleccionada a la vez. eventos_table (con el mismo patrón para
eliminar_evento) sí usa MultiSelection.

El fix cambia scenarios_table a MultiSelection, alineándola con
eventos_table, para que la funcionalidad de borrado múltiple ya escrita
en eliminar_scenario() funcione de verdad.

Este test verifica que:
1. scenarios_table tenga selectionMode() == MultiSelection (no
   SingleSelection).
2. Seleccionando DOS escenarios y llamando a eliminar_scenario(), AMBOS
   se borren (no solo uno), demostrando que el borrado múltiple
   realmente funciona de punta a punta.
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


app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)


print("=" * 70)
print("BUG BAJO R4 #6: scenarios_table debe permitir selección múltiple para borrado")
print("=" * 70)

win = RLB.RiskLabApp()

check(win.scenarios_table.selectionMode() == QtWidgets.QAbstractItemView.MultiSelection,
      f"Bug bajo R4 #6: scenarios_table tiene selectionMode MultiSelection "
      f"(obtenido: {win.scenarios_table.selectionMode()})")

# Preparar 3 escenarios y seleccionar 2 de ellos para borrar.
escenarios = [RLB.Scenario(f"Escenario{i}", "") for i in range(3)]
for e in escenarios:
    e.eventos_riesgo = []
win.scenarios = escenarios
for i, e in enumerate(escenarios):
    win.scenarios_table.insertRow(i)
    win.scenarios_table.setItem(i, 0, QtWidgets.QTableWidgetItem(e.nombre))
    win.scenarios_table.setItem(i, 1, QtWidgets.QTableWidgetItem(""))
win.current_scenario = None

sm = win.scenarios_table.selectionModel()
sm.clearSelection()
sm.select(win.scenarios_table.model().index(0, 0), QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)
sm.select(win.scenarios_table.model().index(2, 0), QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)

seleccionados = win.scenarios_table.selectionModel().selectedRows()
check(len(seleccionados) == 2,
      f"Se pueden seleccionar 2 filas simultáneamente en scenarios_table "
      f"(obtenido: {len(seleccionados)} filas seleccionadas)")

win.eliminar_scenario()

nombres_restantes = [sc.nombre for sc in win.scenarios]
print(f"  escenarios restantes tras eliminar 2 de 3: {nombres_restantes}")
check(len(win.scenarios) == 1,
      f"Bug bajo R4 #6: se eliminaron AMBOS escenarios seleccionados, no solo uno "
      f"(obtenido: {len(win.scenarios)} restante(s): {nombres_restantes})")
check(nombres_restantes == ["Escenario1"],
      f"El escenario NO seleccionado ('Escenario1') es el único que sobrevive "
      f"(obtenido: {nombres_restantes})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
