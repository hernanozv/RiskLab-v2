"""
test_menu_archivo_bloqueado_durante_simulacion.py
=====================================================

Regresion para bug alto R4 #4 (QA ronda 4): set_interfaz_activa (el
guard de re-entrancy, fix #22) solo deshabilita config_tab,
scenarios_tab, num_simulaciones_var y eventos_table -- el menuBar()
NUNCA se deshabilita mientras una simulación corre en background.
"Nueva Simulación" limpiaba self.eventos_riesgo/self.scenarios in-place
sin chequear si el hilo seguía corriendo, y "Cargar Simulación"
reemplazaba el modelo completo desde otro archivo, también sin
chequeo -- desincronizando la UI de los resultados que esa simulación
en curso termine mostrando.

El fix agrega el mismo guard de re-entrancy usado en ejecutar_simulacion
(chequear self.simulation_thread.isRunning()) al inicio de
nueva_simulacion() y cargar_configuracion(), rechazando la acción con un
aviso claro si hay una simulación corriendo.

Este test simula un hilo "en ejecución" (isRunning()=True) y verifica
que: (a) nueva_simulacion() NO limpia eventos_riesgo/scenarios y muestra
un aviso, (b) cargar_configuracion() NO abre el diálogo de archivo (ni
modifica nada) y muestra un aviso, ambos mientras el hilo simulado sigue
"corriendo".
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


class _HiloFalsoCorriendo:
    def isRunning(self):
        return True


print("=" * 70)
print("BUG ALTO R4 #4: menú Archivo debe respetar el guard de re-entrancy")
print("=" * 70)

# --- Caso 1: Nueva Simulación mientras hay una simulación corriendo ---
print("\n--- Caso 1: Nueva Simulación ---")
win1 = RLB.RiskLabApp()
win1.eventos_riesgo = [{'id': 'e1', 'nombre': 'EventoA', 'activo': True}]
win1.simulation_thread = _HiloFalsoCorriendo()

preguntas1 = []
QtWidgets.QMessageBox.question = staticmethod(
    lambda *a, **kw: preguntas1.append(1) or QtWidgets.QMessageBox.Yes
)
warnings1 = []
QtWidgets.QMessageBox.warning = staticmethod(
    lambda *a, **kw: warnings1.append(a) or QtWidgets.QMessageBox.Ok
)

win1.nueva_simulacion()

check(len(win1.eventos_riesgo) == 1,
      f"Bug alto R4 #4: nueva_simulacion() NO limpia eventos_riesgo mientras hay "
      f"una simulación corriendo (obtenido: {len(win1.eventos_riesgo)} eventos)")
check(len(preguntas1) == 0,
      "nueva_simulacion() ni siquiera pregunta 'está seguro' si hay una simulación corriendo")
check(len(warnings1) >= 1,
      f"Se muestra un aviso explicando que hay una simulación en curso "
      f"(obtenido: {len(warnings1)} avisos)")

# --- Caso 2: Cargar Simulación mientras hay una simulación corriendo ---
print("\n--- Caso 2: Cargar Simulación ---")
win2 = RLB.RiskLabApp()
win2.eventos_riesgo = [{'id': 'e1', 'nombre': 'EventoOriginal', 'activo': True}]
win2.simulation_thread = _HiloFalsoCorriendo()

dialogo_abierto = []
QtWidgets.QFileDialog.getOpenFileName = staticmethod(
    lambda *a, **kw: dialogo_abierto.append(1) or ("", "")
)
warnings2 = []
QtWidgets.QMessageBox.warning = staticmethod(
    lambda *a, **kw: warnings2.append(a) or QtWidgets.QMessageBox.Ok
)

win2.cargar_configuracion()

check(len(dialogo_abierto) == 0,
      f"Bug alto R4 #4: cargar_configuracion() NO abre el diálogo de archivo "
      f"mientras hay una simulación corriendo (obtenido: {len(dialogo_abierto)} aperturas)")
check(len(win2.eventos_riesgo) == 1 and win2.eventos_riesgo[0]['nombre'] == 'EventoOriginal',
      "El modelo original permanece intacto")
check(len(warnings2) >= 1,
      f"Se muestra un aviso explicando que hay una simulación en curso "
      f"(obtenido: {len(warnings2)} avisos)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
