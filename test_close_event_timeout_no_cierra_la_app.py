"""
test_close_event_timeout_no_cierra_la_app.py
================================================

Regresion para bug critico R4 #3 (QA ronda 4): en closeEvent, is_running
(seteado por hilo.stop()) solo se revisa ENTRE chunks dentro de
SimulacionThread.run() -- la llamada al motor de un chunk individual NO
es interrumpible. Si ese chunk tarda mas de 10 segundos (alcanzable con
num_simulaciones grande o eventos con muchos vinculos/factores),
hilo.wait(10_000) hace TIMEOUT y retorna False, pero el codigo anterior
no comprobaba ese retorno: llamaba a event.accept() de todas formas,
permitiendo que la aplicacion (y el interprete de Python, via
sys.exit(app.exec_())) termine MIENTRAS el QThread real sigue vivo en
otro hilo del sistema operativo -- exactamente el escenario de
"QThread: Destroyed while thread is still running" que el fix original
del bug #30 (que agrego closeEvent) buscaba eliminar por completo.

El fix comprueba el valor de retorno de hilo.wait(10_000): si es False
(timeout), se avisa al usuario y se ignora el evento de cierre (la
aplicacion NO se cierra) en vez de aceptar el cierre igual.

Este test fuerza a SimulacionThread.wait() a simular un timeout (retorna
False) mientras el hilo sigue genuinamente corriendo (bloqueado), y
verifica que closeEvent: (a) NO acepta el cierre, (b) avisa al usuario
con un QMessageBox.warning, (c) igual llama a hilo.stop() (is_running
pasa a False) antes de detectar el timeout.
"""
import os
import sys
import threading
import time

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

print("=" * 70)
print("BUG CRÍTICO R4 #3: closeEvent no debe cerrar la app si hilo.wait() hace timeout")
print("=" * 70)


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


win = RLB.RiskLabApp()
win.eventos_riesgo = [_make_evento('E1')]
win.num_simulaciones_var.setText("2000")

_bloqueo_liberado = threading.Event()
_entro_al_motor = threading.Event()
_original_generar_lda = RLB.generar_lda_con_secuencialidad
_original_wait = RLB.SimulacionThread.wait


def _generar_lda_bloqueante(*args, **kwargs):
    _entro_al_motor.set()
    _bloqueo_liberado.wait(timeout=30)
    return _original_generar_lda(*args, **kwargs)


def _wait_timeout(self, ms=None):
    # Simula que el chunk actual (no interrumpible) todavía no terminó
    # dentro del plazo, sin esperar el timeout real de 10s.
    return False


RLB.generar_lda_con_secuencialidad = _generar_lda_bloqueante
RLB.SimulacionThread.wait = _wait_timeout
try:
    win.ejecutar_simulacion()
    hilo = win.simulation_thread
    check(_entro_al_motor.wait(timeout=10) and hilo.isRunning(),
          "Precondición: la simulación queda corriendo (bloqueada en el motor)")

    QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)
    warnings_capturados = []
    QtWidgets.QMessageBox.warning = staticmethod(
        lambda *a, **kw: warnings_capturados.append(a) or QtWidgets.QMessageBox.Ok
    )

    evento_close = QtGui.QCloseEvent()
    win.closeEvent(evento_close)

    check(not evento_close.isAccepted(),
          "Bug crítico R4 #3: si hilo.wait() hace timeout, el cierre se IGNORA "
          "(la app no se cierra)")
    check(len(warnings_capturados) >= 1,
          f"Bug crítico R4 #3: se avisa al usuario que la simulación sigue en curso "
          f"(obtenido: {len(warnings_capturados)} avisos)")
    check(hilo.is_running is False,
          "hilo.stop() se llamó igual antes de detectar el timeout (is_running=False)")

finally:
    RLB.generar_lda_con_secuencialidad = _original_generar_lda
    RLB.SimulacionThread.wait = _original_wait
    _bloqueo_liberado.set()
    try:
        from PyQt5 import QtCore
        QtCore.QThread.wait(hilo, 5000)
    except Exception:
        pass


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
