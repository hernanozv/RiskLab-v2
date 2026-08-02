"""
test_guardar_scenario_nombre_unico_y_resaltado.py
=====================================================

Regresion para bugs medio #25 y #26 (QA ronda 3), ambos en
RiskLabApp.guardar_scenario:

  #25: no había validación de nombre único de escenario. Dos escenarios
       podían llamarse igual, y la restauración del "escenario actual"
       tras cargar un JSON empareja por nombre (primer match en la
       lista) -- con nombres duplicados, podía seleccionar el escenario
       equivocado de forma silenciosa.

  #26: la rama de EDICIÓN de guardar_scenario no llamaba a
       actualizar_vista_escenarios() (a diferencia de la rama "nuevo"),
       por lo que los QTableWidgetItem nuevos creados en esa rama no
       tenían el resaltado (fondo verde + "✓") que esa función aplica.
       Si el escenario editado era el "escenario actual", su fila
       quedaba visualmente "des-resaltada" pese a seguir siendo el
       seleccionado internamente.

Este test crea dos escenarios ("A" y "B"), verifica que renombrar "B"
a "A" (duplicado) lanza un error y NO se aplica; luego selecciona "A"
como escenario actual, lo edita (cambiando solo la descripción) y
verifica que su fila sigue mostrando el resaltado tras guardar.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

from PyQt5 import QtWidgets, QtGui

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

_criticals = []
QtWidgets.QMessageBox.critical = staticmethod(lambda parent, t, m, *a, **kw: (_criticals.append((t, m)), QtWidgets.QMessageBox.Ok)[1])

print("=" * 70)
print("BUGS MEDIO #25/#26: nombre único de escenario y resaltado tras editar")
print("=" * 70)

win = RLB.RiskLabApp()
win.eventos_scenario = []


class _FakeDialog:
    def accept(self):
        pass


# --- Crear escenario "A" ---
nombre_var_a = QtWidgets.QLineEdit("A")
desc_var_a = QtWidgets.QLineEdit("desc A")
win.guardar_scenario(_FakeDialog(), True, None, nombre_var_a, desc_var_a)
check(len(win.scenarios) == 1 and win.scenarios[0].nombre == "A", "Escenario 'A' creado correctamente")

# --- Crear escenario "B" ---
nombre_var_b = QtWidgets.QLineEdit("B")
desc_var_b = QtWidgets.QLineEdit("desc B")
win.guardar_scenario(_FakeDialog(), True, None, nombre_var_b, desc_var_b)
check(len(win.scenarios) == 2 and win.scenarios[1].nombre == "B", "Escenario 'B' creado correctamente")

# --- Bug medio #25: intentar renombrar "B" (row=1) a "A" (duplicado) ---
nombre_var_dup = QtWidgets.QLineEdit("A")
desc_var_dup = QtWidgets.QLineEdit("desc B editada")
win.guardar_scenario(_FakeDialog(), False, 1, nombre_var_dup, desc_var_dup)

check(len(_criticals) >= 1,
      f"Bug medio #25: intentar renombrar 'B' a 'A' (duplicado) dispara un error "
      f"(obtenido: {_criticals})")
check(win.scenarios[1].nombre == "B",
      f"El escenario 'B' NO fue renombrado a 'A' (obtenido: {win.scenarios[1].nombre!r})")

# --- Bug medio #26: seleccionar "A" como actual, editarlo, verificar resaltado ---
win.select_scenario(0, 0)  # seleccionar fila 0 ("A") como escenario actual
check(win.current_scenario is win.scenarios[0], "El escenario 'A' quedó seleccionado como actual")

item_antes = win.scenarios_table.item(0, 0)
resaltado_antes = item_antes.background().color() == QtGui.QColor("#e8f5e9")
check(resaltado_antes, "Precondición: la fila de 'A' está resaltada (fondo verde) tras seleccionarlo")

nombre_var_edit = QtWidgets.QLineEdit("A")
desc_var_edit = QtWidgets.QLineEdit("descripción editada")
win.guardar_scenario(_FakeDialog(), False, 0, nombre_var_edit, desc_var_edit)

item_despues = win.scenarios_table.item(0, 0)
resaltado_despues = item_despues.background().color() == QtGui.QColor("#e8f5e9")
check(resaltado_despues,
      f"Bug medio #26: tras editar el escenario actual ('A'), su fila SIGUE resaltada "
      f"(fondo verde) (obtenido color: {item_despues.background().color().name()})")
check(item_despues.text().startswith("✓"),
      f"Bug medio #26: la fila editada conserva el indicador '✓' del escenario actual "
      f"(obtenido: {item_despues.text()!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
