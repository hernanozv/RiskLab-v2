"""
test_vinculos_spinboxes_no_scroll.py
========================================

Regresion para bug alto #9 (QA ronda 2): los spinboxes de la tabla de
vínculos (columnas "Prob.(%)", "Sev.(x)" y "Umbral($)" dentro de
editar_evento_popup) usaban QSpinBox/QDoubleSpinBox crudos en vez de las
clases NoScrollSpinBox/NoScrollDoubleSpinBox que el proyecto ya define
justamente para este caso (ver clase NoScrollSpinBox, ~línea 249). Como
estos spinboxes viven embebidos en una tabla scrolleable, un scroll del
mouse sin hacer clic sobre la celda cambia su valor — y el cambio se
persiste silenciosamente en el vínculo, sin que el usuario se dé cuenta.

Este test abre el diálogo real "Editar Evento" (headless, QT_QPA_PLATFORM=
offscreen) sobre un evento con un vínculo ya cargado, ubica los 3
spinboxes de la fila de la tabla de vínculos y verifica: (a) son instancias
de NoScrollSpinBox/NoScrollDoubleSpinBox (no QSpinBox/QDoubleSpinBox
crudos); (b) un QWheelEvent enviado directamente al widget NO cambia su
valor (comportamiento funcional, no solo el nombre de la clase).
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

from PyQt5 import QtCore, QtGui, QtWidgets

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

print("=" * 70)
print("BUG ALTO #9: spinboxes de la tabla de vínculos ignoran scroll del mouse")
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
        {'id_padre': 'padre', 'tipo': 'AND', 'probabilidad': 80,
         'factor_severidad': 1.5, 'umbral_severidad': 1000},
    ],
}

win = RLB.RiskLabApp()
win.eventos_riesgo = [evento_padre, evento_hijo]

resultado = {}


def _fake_exec(self):
    vinculos_table = None
    for table in self.findChildren(QtWidgets.QTableWidget):
        headers = [table.horizontalHeaderItem(i).text() if table.horizontalHeaderItem(i) else ''
                   for i in range(table.columnCount())]
        if headers[:5] == ["Evento", "Tipo", "Prob.(%)", "Sev.(x)", "Umbral($)"]:
            vinculos_table = table
            break
    assert vinculos_table is not None, "No se encontró la tabla de vínculos"
    assert vinculos_table.rowCount() >= 1, "La tabla de vínculos no cargó el vínculo existente"

    resultado['prob_spin'] = vinculos_table.cellWidget(0, 2)
    resultado['factor_sev_spin'] = vinculos_table.cellWidget(0, 3)
    resultado['umbral_spin'] = vinculos_table.cellWidget(0, 4)
    return QtWidgets.QDialog.Rejected


QtWidgets.QDialog.exec_ = _fake_exec
try:
    win.editar_evento_popup(new=False, row=1)  # editar 'EventoHijo' (índice 1)
finally:
    del QtWidgets.QDialog.exec_

prob_spin = resultado.get('prob_spin')
factor_sev_spin = resultado.get('factor_sev_spin')
umbral_spin = resultado.get('umbral_spin')

check(prob_spin is not None and factor_sev_spin is not None and umbral_spin is not None,
      "Los 3 spinboxes de la fila de vínculo se encontraron en la tabla")

check(isinstance(prob_spin, RLB.NoScrollSpinBox),
      f"Bug alto #9: el spinbox de Probabilidad es NoScrollSpinBox (obtenido: {type(prob_spin).__name__})")
check(isinstance(factor_sev_spin, RLB.NoScrollDoubleSpinBox),
      f"Bug alto #9: el spinbox de Factor de severidad es NoScrollDoubleSpinBox (obtenido: {type(factor_sev_spin).__name__})")
check(isinstance(umbral_spin, RLB.NoScrollSpinBox),
      f"Bug alto #9: el spinbox de Umbral es NoScrollSpinBox (obtenido: {type(umbral_spin).__name__})")


def _simular_scroll_y_verificar_sin_cambio(spin, nombre):
    valor_antes = spin.value()
    evento_wheel = QtGui.QWheelEvent(
        QtCore.QPointF(5, 5), QtCore.QPointF(5, 5),
        QtCore.QPoint(0, 120), QtCore.QPoint(0, 120),
        QtCore.Qt.NoButton, QtCore.Qt.NoModifier,
        QtCore.Qt.ScrollUpdate, False
    )
    QtWidgets.QApplication.sendEvent(spin, evento_wheel)
    valor_despues = spin.value()
    check(valor_despues == valor_antes,
          f"Bug alto #9: un scroll del mouse sobre '{nombre}' NO cambia su valor "
          f"(antes={valor_antes}, después={valor_despues})")


_simular_scroll_y_verificar_sin_cambio(prob_spin, "Probabilidad")
_simular_scroll_y_verificar_sin_cambio(factor_sev_spin, "Factor de severidad")
_simular_scroll_y_verificar_sin_cambio(umbral_spin, "Umbral de severidad")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
