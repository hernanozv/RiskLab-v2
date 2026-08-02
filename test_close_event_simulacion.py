"""
test_close_event_simulacion.py
================================

Regresion para bug #30: SimulacionThread tiene un método stop() (que pone
is_running=False para que el hilo termine cooperativamente en el próximo
límite de chunk) pero nada en la aplicación lo llamaba jamás. RiskLabApp
(QMainWindow) no sobreescribía closeEvent, así que cerrar la ventana
mientras una simulación corría en background dejaba el QThread huérfano:
podía seguir corriendo después de que la ventana se destruyera y, al
intentar emitir sus señales (progreso, resultado) hacia slots de una
ventana ya destruida, arriesgar un crash o comportamiento indefinido.

Este test instancia RiskLabApp de verdad (headless) y verifica:
  1. Sin simulación corriendo, cerrar la ventana no pregunta nada y
     acepta el cierre inmediatamente.
  2. Con una simulación corriendo, cerrar la ventana pregunta al usuario;
     si el usuario cancela, el cierre se ignora y el hilo sigue vivo.
  3. Si el usuario confirma, se llama a stop() (is_running=False) y se
     espera al hilo antes de aceptar el cierre.
"""
import os
import sys
import threading
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

from PyQt5 import QtWidgets, QtGui, QtCore

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

_preguntas_mostradas = []


def _make_evento(nombre):
    dist_freq = RLB.generar_distribucion_frecuencia(1, tasa=5.0)
    dist_sev = RLB.generar_distribucion_severidad(
        2, None, None, None, input_method='direct',
        params_direct={'mean': 1000.0, 'std': 100.0}
    )
    return {
        'id': nombre, 'nombre': nombre, 'freq_opcion': 1, 'sev_opcion': 2,
        'dist_frecuencia': dist_freq, 'dist_severidad': dist_sev,
        'activo': True, 'tasa': 5.0,
    }


def _pump(seconds):
    t0 = time.time()
    while time.time() - t0 < seconds:
        app.processEvents()
        time.sleep(0.005)


print("=" * 70)
print("BUG #30: closeEvent detiene la simulación en curso al cerrar la app")
print("=" * 70)

win = RLB.RiskLabApp()
win.eventos_riesgo = [_make_evento('E1')]
win.num_simulaciones_var.setText("2000")

# --- 1. Sin simulacion corriendo: cerrar no debe preguntar nada ---
_preguntas_mostradas.clear()
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: _preguntas_mostradas.append(1) or QtWidgets.QMessageBox.Yes)
evento_close = QtGui.QCloseEvent()
win.closeEvent(evento_close)
check(len(_preguntas_mostradas) == 0,
      "Sin simulación corriendo: closeEvent no pregunta nada al usuario")
check(evento_close.isAccepted(), "Sin simulación corriendo: el cierre se acepta de inmediato")

# --- Preparar una simulacion bloqueada de forma determinista ---
_bloqueo_liberado = threading.Event()
_entro_al_motor = threading.Event()
_original_generar_lda = RLB.generar_lda_con_secuencialidad


def _generar_lda_bloqueante(*args, **kwargs):
    _entro_al_motor.set()
    _bloqueo_liberado.wait(timeout=30)
    return _original_generar_lda(*args, **kwargs)


RLB.generar_lda_con_secuencialidad = _generar_lda_bloqueante
try:
    # --- 2. Con simulacion corriendo, el usuario CANCELA el cierre ---
    win.ejecutar_simulacion()
    hilo = win.simulation_thread
    check(_entro_al_motor.wait(timeout=10) and hilo.isRunning(),
          "Precondición: la simulación queda corriendo (bloqueada)")

    _preguntas_mostradas.clear()
    QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: _preguntas_mostradas.append(1) or QtWidgets.QMessageBox.No)
    evento_close_cancel = QtGui.QCloseEvent()
    win.closeEvent(evento_close_cancel)

    check(len(_preguntas_mostradas) == 1,
          "Con simulación corriendo: closeEvent SI pregunta al usuario")
    check(not evento_close_cancel.isAccepted(),
          "Bug #30: si el usuario cancela, el cierre se ignora (event.ignore())")
    check(hilo.isRunning(), "Si el usuario cancela, el hilo de simulación sigue corriendo")

    # --- 3. El usuario CONFIRMA el cierre: se detiene el hilo cooperativamente ---
    QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)
    evento_close_confirm = QtGui.QCloseEvent()

    check(hilo.is_running is True, "Precondición: el flag is_running del hilo sigue en True")
    _bloqueo_liberado.set()  # liberar el motor para que el hilo pueda terminar tras stop()
    win.closeEvent(evento_close_confirm)

    check(hilo.is_running is False,
          "Bug #30: al confirmar el cierre, se llama a hilo.stop() (is_running=False)")
    check(evento_close_confirm.isAccepted(),
          "Al confirmar el cierre (y tras esperar el hilo), el cierre se acepta")
    check(not hilo.isRunning(), "El hilo ya terminó cuando closeEvent acepta el cierre")
finally:
    RLB.generar_lda_con_secuencialidad = _original_generar_lda


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
