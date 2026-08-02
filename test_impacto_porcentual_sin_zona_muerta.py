"""
test_impacto_porcentual_sin_zona_muerta.py
==============================================

Regresion para bug medio #29 (QA ronda 3): los spinboxes de "impacto
porcentual" (frecuencia y severidad, en el diálogo "Agregar Control/
Factor de Riesgo") permitían un rango de [-200, 99], pero el motor
(generar_lda_con_secuencialidad) aplica un piso de -99% (factor mínimo
0.01) sin importar cuán más negativo sea el valor configurado -- un
control en -150% tenía EXACTAMENTE el mismo efecto que uno en -99%,
una "zona muerta" en la UI no comunicada al usuario, que podía hacerle
pensar que -150% era un control "más fuerte" que -99%.

El fix acota el rango del spinbox a [-99, 99], eliminando la zona
muerta directamente (en vez de solo documentarla).

Este test abre el diálogo real "Agregar Control/Factor de Riesgo"
(headless) y verifica que el rango mínimo de los spinboxes de impacto
porcentual (frecuencia y severidad) sea -99, no -200.
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
print("BUG MEDIO #29: spinbox de impacto porcentual no debe permitir la zona muerta < -99%")
print("=" * 70)

resultado = {}


def _fake_exec(self):
    titulo = self.windowTitle()
    if titulo == "Agregar Control/Factor de Riesgo":
        spinboxes = self.findChildren(QtWidgets.QSpinBox)
        # Sólo nos interesan impacto_var (frecuencia, modelo estático) e
        # impacto_severidad_var (severidad, modelo estático) -- se
        # identifican por su tooltip característico ("Positivo reduce...").
        # Los spinboxes del modelo ESTOCÁSTICO (reduccion_efectiva_var,
        # reduccion_sev_efectiva_var, reduccion_fallo_var,
        # reduccion_sev_fallo_var) usan un rango [-100, 99] distinto (fuera
        # del alcance de este bug: sólo -100 duplica -99, una superposición
        # de 1 punto, no la zona muerta de 101 puntos del bug original) y
        # deben excluirse explícitamente para no dar un falso positivo.
        rangos = [
            (sb.minimum(), sb.maximum()) for sb in spinboxes
            if sb.toolTip().startswith("Positivo reduce")
        ]
        resultado['rangos_impacto'] = rangos
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

rangos = resultado.get('rangos_impacto', [])
print(f"  rangos de impacto encontrados (min, max=99): {rangos}")
check(len(rangos) >= 1,
      f"Se encontraron spinboxes de impacto porcentual (obtenido: {rangos})")
check(all(r[0] == -99 for r in rangos),
      f"Bug medio #29: todos los spinboxes de impacto porcentual tienen "
      f"mínimo -99 (no -200, sin zona muerta) (obtenido: {rangos})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
