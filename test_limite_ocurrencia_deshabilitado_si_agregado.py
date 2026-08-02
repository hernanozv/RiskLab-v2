"""
test_limite_ocurrencia_deshabilitado_si_agregado.py
=======================================================

Regresion para bug medio #20 (QA ronda 3): en el diálogo "Agregar
Control/Factor de Riesgo" (tipo Seguro/Transferencia), el spinbox
"Límite por siniestro" (seguro_limite_ocurrencia) quedaba siempre
habilitado sin importar el tipo de deducible seleccionado. El motor
(generar_lda_con_secuencialidad) SOLO lee este campo para pólizas
'por_ocurrencia'; para 'agregado' (el default) lo ignora por completo.
Un usuario que configurara "Agregado anual" + un límite por siniestro
> 0 esperando que se respetara no recibía ningún aviso de que ese valor
es letra muerta.

El fix deshabilita el spinbox (y su etiqueta) cuando el tipo de
deducible es "Agregado anual", habilitándolo solo para "Por
ocurrencia".

Este test abre el diálogo real "Agregar Evento" (headless), dispara el
diálogo anidado "Agregar Control/Factor de Riesgo", activa el modo
Seguro/Transferencia, y verifica que el spinbox de límite por siniestro
está deshabilitado con el default ("Agregado anual") y se habilita al
seleccionar "Por ocurrencia".
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

print("=" * 70)
print("BUG MEDIO #20: 'Límite por siniestro' debe deshabilitarse para seguros 'agregado'")
print("=" * 70)

resultado = {}


def _fake_exec(self):
    titulo = self.windowTitle()
    if titulo == "Agregar Control/Factor de Riesgo":
        afecta_severidad_check = next(
            w for w in self.findChildren(QtWidgets.QCheckBox)
            if 'severidad' in w.text().lower()
        )
        afecta_severidad_check.setChecked(True)
        tipo_sev_seguro = next(
            w for w in self.findChildren(QtWidgets.QRadioButton)
            if 'seguro' in w.text().lower()
        )
        tipo_sev_seguro.setChecked(True)

        tipo_ded_agregado = next(
            w for w in self.findChildren(QtWidgets.QRadioButton)
            if 'agregado' in w.text().lower()
        )
        tipo_ded_ocurrencia = next(
            w for w in self.findChildren(QtWidgets.QRadioButton)
            if 'ocurrencia' in w.text().lower()
        )
        limite_spin = next(
            w for w in self.findChildren(QtWidgets.QDoubleSpinBox) + self.findChildren(QtWidgets.QSpinBox)
            if w.toolTip().startswith("Máximo que paga el seguro por siniestro") or
               'agregado' in w.toolTip().lower()
        )

        resultado['agregado_checked_default'] = tipo_ded_agregado.isChecked()
        resultado['limite_habilitado_con_agregado'] = limite_spin.isEnabled()

        tipo_ded_ocurrencia.setChecked(True)
        resultado['limite_habilitado_con_ocurrencia'] = limite_spin.isEnabled()

        tipo_ded_agregado.setChecked(True)
        resultado['limite_habilitado_al_volver_a_agregado'] = limite_spin.isEnabled()
        return QtWidgets.QDialog.Rejected

    elif titulo in ("Agregar Evento de Riesgo", "Editar Evento de Riesgo"):
        add_btn = next(
            w for w in self.findChildren(QtWidgets.QPushButton)
            if 'agregar factor' in w.text().lower() or 'agregar control' in w.text().lower()
        )
        add_btn.click()
        return QtWidgets.QDialog.Rejected
    return QtWidgets.QDialog.Rejected


QtWidgets.QDialog.exec_ = _fake_exec
try:
    win = RLB.RiskLabApp()
    win.eventos_riesgo = []
    win.editar_evento_popup(new=True, row=None)
finally:
    del QtWidgets.QDialog.exec_

check(resultado.get('agregado_checked_default') is True,
      "Precondición: 'Agregado anual' es el tipo de deducible por default")
check(resultado.get('limite_habilitado_con_agregado') is False,
      f"Bug medio #20: el límite por siniestro está DESHABILITADO con el default "
      f"'Agregado anual' (obtenido: {resultado.get('limite_habilitado_con_agregado')})")
check(resultado.get('limite_habilitado_con_ocurrencia') is True,
      f"El límite por siniestro se HABILITA al seleccionar 'Por ocurrencia' "
      f"(obtenido: {resultado.get('limite_habilitado_con_ocurrencia')})")
check(resultado.get('limite_habilitado_al_volver_a_agregado') is False,
      f"El límite por siniestro vuelve a deshabilitarse al volver a 'Agregado anual' "
      f"(obtenido: {resultado.get('limite_habilitado_al_volver_a_agregado')})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
