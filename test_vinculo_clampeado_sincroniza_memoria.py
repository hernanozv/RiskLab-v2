"""
test_vinculo_clampeado_sincroniza_memoria.py
================================================

Regresion para bug medio #16 (QA ronda 2): en la tabla de vínculos del
diálogo "Editar Evento", cada spinbox se construye llamando primero a
`.setValue(valor_clampeado)` y RECIÉN DESPUÉS a `.valueChanged.connect(...)`.
Como la señal todavía no está conectada cuando se llama a setValue(), el
clampeo inicial (p.ej. un vínculo con probabilidad=150 importado de un
JSON antiguo, mostrado como 100% porque el spinbox tiene rango [1,100])
nunca disparaba el callback que sincroniza `vinculos_existentes[idx]` con
el valor mostrado. Si el usuario guardaba el evento SIN tocar ese
control, se persistía el valor NO mostrado (150), distinto al 100% que
realmente vio en pantalla — hasta que el usuario tocaba el control
(lo que sí dispara valueChanged y sincroniza).

El fix escribe el valor clampeado de vuelta al dict del vínculo
inmediatamente al construir la fila de la tabla, sin depender del orden
de conexión de señales.

Este test abre el diálogo real "Editar Evento" (headless) sobre un
evento con un vínculo cuyos 3 valores están fuera de rango
(probabilidad=150, factor_severidad=10.0, umbral_severidad=-50), hace
clic en "Guardar" SIN tocar ningún spinbox, y verifica que lo persistido
en self.eventos_riesgo coincide con los valores clampeados que se
mostraron en pantalla (100%, 5.0x, 0), no con los valores originales
fuera de rango.
"""
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

print("=" * 70)
print("BUG MEDIO #16: vínculo fuera de rango debe guardar el valor clampeado mostrado")
print("=" * 70)

evento_padre = {
    'id': 'padre', 'nombre': 'EventoPadre', 'activo': True,
    'sev_opcion': 2, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 1000.0, 'std': 100.0},
    'freq_opcion': 1, 'tasa': 5.0,
}
evento_hijo = {
    'id': 'hijo', 'nombre': 'EventoHijo', 'activo': True,
    'sev_opcion': 2, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 500.0, 'std': 50.0},
    'freq_opcion': 1, 'tasa': 2.0,
    'vinculos': [
        # Los 3 valores están fuera del rango que impone el spinbox
        # (probabilidad: [1,100], factor_severidad: [0.10,5.00],
        # umbral_severidad: [0, inf)).
        {'id_padre': 'padre', 'tipo': 'AND', 'probabilidad': 150,
         'factor_severidad': 10.0, 'umbral_severidad': -50},
    ],
}

win = RLB.RiskLabApp()
win.eventos_riesgo = [evento_padre, evento_hijo]


def _fake_exec(self):
    vinculos_table = None
    for table in self.findChildren(QtWidgets.QTableWidget):
        headers = [table.horizontalHeaderItem(i).text() if table.horizontalHeaderItem(i) else ''
                   for i in range(table.columnCount())]
        if headers[:5] == ["Evento", "Tipo", "Prob.(%)", "Sev.(x)", "Umbral($)"]:
            vinculos_table = table
            break
    assert vinculos_table is not None, "No se encontró la tabla de vínculos"

    prob_spin = vinculos_table.cellWidget(0, 2)
    factor_sev_spin = vinculos_table.cellWidget(0, 3)
    umbral_spin = vinculos_table.cellWidget(0, 4)

    check(prob_spin.value() == 100,
          f"El spinbox de Probabilidad muestra el valor clampeado 100 (obtenido: {prob_spin.value()})")
    check(factor_sev_spin.value() == 5.0,
          f"El spinbox de Factor de severidad muestra el valor clampeado 5.0 (obtenido: {factor_sev_spin.value()})")
    check(umbral_spin.value() == 0,
          f"El spinbox de Umbral muestra el valor clampeado 0 (obtenido: {umbral_spin.value()})")

    # Hacer clic en "Guardar" SIN tocar ningún spinbox.
    button_box = None
    for bb in self.findChildren(QtWidgets.QDialogButtonBox):
        if bb.button(QtWidgets.QDialogButtonBox.Ok) is not None:
            button_box = bb
            break
    assert button_box is not None, "No se encontró el QDialogButtonBox de Guardar/Cancelar"
    button_box.button(QtWidgets.QDialogButtonBox.Ok).click()

    return QtWidgets.QDialog.Rejected


QtWidgets.QDialog.exec_ = _fake_exec
try:
    win.editar_evento_popup(new=False, row=1)  # editar 'EventoHijo' (índice 1)
finally:
    del QtWidgets.QDialog.exec_

evento_hijo_guardado = next(e for e in win.eventos_riesgo if e['nombre'] == 'EventoHijo')
vinculo_guardado = evento_hijo_guardado['vinculos'][0]

check(vinculo_guardado['probabilidad'] == 100,
      f"Bug medio #16: se guarda la probabilidad clampeada mostrada (100), no el valor "
      f"original fuera de rango (150) (obtenido: {vinculo_guardado['probabilidad']})")
check(vinculo_guardado['factor_severidad'] == 5.0,
      f"Bug medio #16: se guarda el factor de severidad clampeado mostrado (5.0), no el "
      f"valor original fuera de rango (10.0) (obtenido: {vinculo_guardado['factor_severidad']})")
check(vinculo_guardado['umbral_severidad'] == 0,
      f"Bug medio #16: se guarda el umbral clampeado mostrado (0), no el valor original "
      f"fuera de rango (-50) (obtenido: {vinculo_guardado['umbral_severidad']})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
