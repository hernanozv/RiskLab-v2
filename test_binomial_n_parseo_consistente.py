"""
test_binomial_n_parseo_consistente.py
=========================================

Regresion para bug bajo #22 (QA ronda 2): el campo "n" (número de
eventos posibles) de la distribución Binomial se parseaba de forma
distinta entre el diálogo principal ("Editar Evento", guardar_evento)
y el editor de eventos dentro de un Escenario (editar_scenario_popup):

  - Diálogo principal: n = int(float(num_eventos_var.text()))
  - Editor de escenario: n = int(n_var.text())  (SIN el float() intermedio)

Ambos campos se precargan con str(evento.get('num_eventos')). Si ese
valor fue guardado como float (p.ej. 5.0, algo que puede ocurrir tras un
ciclo de guardar/cargar), el texto queda "5.0". int("5.0") lanza
ValueError ("invalid literal for int() with base 10: '5.0'"), mientras
que int(float("5.0")) funciona correctamente. El editor de escenario
mostraba un error de guardado genérico y NO aplicaba los cambios,
mientras que el diálogo principal manejaba el mismo caso sin problema.

Este test abre el editor de Escenario real (headless), sobre un evento
Binomial cuyo num_eventos está guardado como FLOAT (5.0, precargando el
campo con el texto "5.0"), dispara el doble clic que abre el editor de
parámetros del evento, hace clic en "Guardar" sin tocar el campo n, y
verifica que el cambio se aplica sin error (num_eventos queda en 5),
igual que ya funciona en el diálogo principal.
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

errores_criticos = []


def _fake_critical(parent, titulo, texto, *a, **kw):
    errores_criticos.append((titulo, texto))
    return QtWidgets.QMessageBox.Ok


QtWidgets.QMessageBox.critical = staticmethod(_fake_critical)
QtWidgets.QMessageBox.warning = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)

print("=" * 70)
print("BUG BAJO #22: parseo de 'n' (Binomial) consistente entre diálogos")
print("=" * 70)

evento_binomial = {
    'id': 'e1', 'nombre': 'EventoBinomialFloat', 'activo': True,
    'sev_opcion': 2, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 1000.0, 'std': 100.0},
    'freq_opcion': 2,  # Binomial
    'num_eventos': 5.0,  # Guardado como FLOAT: el campo se precarga con "5.0"
    'prob_exito': 0.5,
    'factores_ajuste': [],
}

win = RLB.RiskLabApp()
escenario = RLB.Scenario("EscenarioTest", "desc")
escenario.eventos_riesgo = [evento_binomial]
win.scenarios = [escenario]

resultado = {}


def _fake_exec(self):
    titulo = self.windowTitle()
    if titulo.startswith("Editar Parámetros del Evento"):
        n_var = None
        campos_n = []
        for label_texto in ("Número de Eventos (n):",):
            pass  # (buscamos por posición del formulario, ver abajo)
        # Buscar los QLineEdit del formulario de frecuencia: el primero
        # editable con texto "5.0" es n_var (el segundo, "0.5", es p_var).
        line_edits = [w for w in self.findChildren(QtWidgets.QLineEdit)]
        for w in line_edits:
            if w.text() == "5.0":
                n_var = w
                break
        assert n_var is not None, "No se encontró el campo 'n' precargado con '5.0'"
        resultado['texto_n_precargado'] = n_var.text()

        button_box = None
        for bb in self.findChildren(QtWidgets.QDialogButtonBox):
            if bb.button(QtWidgets.QDialogButtonBox.Save) is not None:
                button_box = bb
                break
        assert button_box is not None, "No se encontró el QDialogButtonBox de Guardar/Cancelar"
        button_box.button(QtWidgets.QDialogButtonBox.Save).click()
        return QtWidgets.QDialog.Accepted

    elif titulo in ("Editar Escenario", "Agregar Escenario"):
        eventos_table = None
        for table in self.findChildren(QtWidgets.QTableWidget):
            headers = [table.horizontalHeaderItem(i).text() if table.horizontalHeaderItem(i) else ''
                       for i in range(table.columnCount())]
            if headers == ["", "Evento de Riesgo", "Fact."]:
                eventos_table = table
                break
        assert eventos_table is not None, "No se encontró la tabla de eventos del escenario"
        assert eventos_table.rowCount() >= 1, "La tabla de eventos del escenario está vacía"
        # Disparar el doble clic que abre el editor de parámetros del evento
        eventos_table.cellDoubleClicked.emit(0, 0)
        return QtWidgets.QDialog.Rejected

    return QtWidgets.QDialog.Rejected


QtWidgets.QDialog.exec_ = _fake_exec
try:
    win.editar_scenario_popup(new=False, row=0)
finally:
    del QtWidgets.QDialog.exec_

check(resultado.get('texto_n_precargado') == '5.0',
      f"Precondición: el campo 'n' se precarga con el texto '5.0' (num_eventos guardado "
      f"como float) (obtenido: {resultado.get('texto_n_precargado')!r})")

check(len(errores_criticos) == 0,
      f"Bug bajo #22: guardar no dispara un QMessageBox.critical al parsear 'n'=5.0 "
      f"(obtenido: {errores_criticos})")

num_eventos_final = win.eventos_scenario[0].get('num_eventos')
check(num_eventos_final == 5,
      f"Bug bajo #22: el cambio se aplica correctamente (num_eventos=5), consistente "
      f"con el diálogo principal (obtenido: {num_eventos_final!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
