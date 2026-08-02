"""
test_reentrancy_simulacion.py
==============================

Regresion para bug #22: re-entrancy de simulaciones concurrentes.

set_interfaz_activa(False) solo deshabilitaba la pestaña "Simulación"
(config_tab). La pestaña "Escenarios" (y su botón "Ejecutar Simulación",
que redirige a ejecutar_simulacion_escenario -> ejecutar_simulacion) seguía
totalmente operativa mientras una simulación ya estaba corriendo. Sin
ningún guard de re-entrancy (isRunning()), un doble-click en el botón, o
iniciar una simulación desde una pestaña mientras la otra ya tenía una en
curso, creaba un SEGUNDO SimulacionThread que sobreescribía
self.simulation_thread mientras el primero seguía corriendo: ambos quedaban
conectados a los mismos slots (actualizar_progreso, simulacion_completada,
error_ocurrido) y el que terminara último "ganaba" silenciosamente, sin
ningún aviso al usuario.

Esta suite instancia RiskLabApp de verdad (headless, QT_QPA_PLATFORM=
offscreen) porque el bug vive en la interaccion entre metodos de la clase
Qt (ejecutar_simulacion, set_interfaz_activa) y el QThread real — no es
reproducible extrayendo funciones puras por AST.

Para que la ventana de "simulación en curso" sea determinística (y no
depender de una carrera de wall-clock contra un numero grande de
simulaciones, que ademas dispararia graficos pesados sobre datasets
enormes), se intercepta generar_lda_con_secuencialidad para que el hilo de
fondo quede bloqueado en un threading.Event hasta que el test decida
liberarlo.
"""
import os
import sys
import threading
import time

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

# Los dialogos modales (QMessageBox.warning/critical) bloquearian el test en
# un entorno headless sin loop de eventos real corriendo via app.exec_().
# Los interceptamos para registrar la llamada en vez de mostrarlos.
_warnings_mostrados = []
_criticals_mostrados = []


def _fake_warning(parent, titulo, texto, *a, **kw):
    _warnings_mostrados.append((titulo, texto))
    return QtWidgets.QMessageBox.Ok


def _fake_critical(parent, titulo, texto, *a, **kw):
    _criticals_mostrados.append((titulo, texto))
    return QtWidgets.QMessageBox.Ok


QtWidgets.QMessageBox.warning = staticmethod(_fake_warning)
QtWidgets.QMessageBox.critical = staticmethod(_fake_critical)


def _make_evento(nombre, tasa=5.0, mean=1000.0, std=100.0):
    dist_freq = RLB.generar_distribucion_frecuencia(1, tasa=tasa)
    dist_sev = RLB.generar_distribucion_severidad(
        2, None, None, None, input_method='direct',
        params_direct={'mean': mean, 'std': std}
    )
    return {
        'id': nombre, 'nombre': nombre, 'freq_opcion': 1, 'sev_opcion': 2,
        'dist_frecuencia': dist_freq, 'dist_severidad': dist_sev,
        'activo': True, 'tasa': tasa,
    }


def _pump(seconds):
    t0 = time.time()
    while time.time() - t0 < seconds:
        app.processEvents()
        time.sleep(0.005)


# --- Interceptar el motor de simulacion para bloquear el hilo de forma
#     determinista (en vez de una carrera de wall-clock contra un N enorme) ---
_bloqueo_liberado = threading.Event()
_entro_al_motor = threading.Event()
_original_generar_lda = RLB.generar_lda_con_secuencialidad


def _generar_lda_bloqueante(*args, **kwargs):
    _entro_al_motor.set()
    _bloqueo_liberado.wait(timeout=30)
    return _original_generar_lda(*args, **kwargs)


print("=" * 70)
print("BUG #22: Re-entrancy de simulaciones concurrentes")
print("=" * 70)

win = RLB.RiskLabApp()
win.eventos_riesgo = [_make_evento('E1')]
win.num_simulaciones_var.setText("2000")

RLB.generar_lda_con_secuencialidad = _generar_lda_bloqueante
try:
    # --- 1. Primer click: arranca la simulacion; el motor queda bloqueado
    #        esperando la señal de liberacion, asi que el hilo sigue "vivo"
    #        de forma determinista mientras dure el test. ---
    win.ejecutar_simulacion()
    primer_hilo = getattr(win, 'simulation_thread', None)
    check(primer_hilo is not None and primer_hilo.isRunning(),
          "Primer click: se crea y arranca un SimulacionThread")
    check(len(_criticals_mostrados) == 0,
          "Primer click: no dispara ningun dialogo de error")

    check(_entro_al_motor.wait(timeout=10),
          "Precondicion: el hilo de fondo llego a ejecutar el motor de simulación")
    check(primer_hilo.isRunning(),
          "Precondicion: el primer hilo sigue corriendo (bloqueado) al hacer el segundo click")

    # --- 2. Segundo click MIENTRAS el primero sigue corriendo (simula
    #        doble-click o iniciar desde la otra pestaña) ---
    win.ejecutar_simulacion()
    segundo_hilo = getattr(win, 'simulation_thread', None)

    check(segundo_hilo is primer_hilo,
          "Bug #22: el segundo click NO reemplaza self.simulation_thread mientras el primero corre")
    check(len(_warnings_mostrados) >= 1,
          "Bug #22: el segundo click muestra un aviso de 'simulación en curso' al usuario")
    if _warnings_mostrados:
        texto_aviso = _warnings_mostrados[-1][1].lower()
        check("curso" in texto_aviso or "espere" in texto_aviso,
              "El aviso menciona que ya hay una simulación en curso")

    # --- 3. La pestaña Escenarios tambien debe quedar deshabilitada mientras
    #        corre la simulacion (defensa adicional, no solo el guard) ---
    idx_escenarios = win.central_widget.indexOf(win.scenarios_tab)
    check(win.central_widget.isTabEnabled(idx_escenarios) is False,
          "Mientras corre la simulación, la pestaña Escenarios queda deshabilitada")

    # --- 4. Liberar el hilo bloqueado y esperar a que termine la corrida real ---
    _bloqueo_liberado.set()
    _pump(seconds=0.2)
    primer_hilo.wait(15_000)
    _pump(seconds=2.0)  # drenar señales encoladas (simulacion_completada, plots)

    check(not primer_hilo.isRunning(), "El hilo original termina correctamente")
    check(win.central_widget.isTabEnabled(idx_escenarios) is True,
          "Al terminar, la pestaña Escenarios se reactiva")
    check(len(_criticals_mostrados) == 0,
          "Ninguna corrida disparo un dialogo de error inesperado")

    # --- 5. Tras finalizar, un nuevo click SI debe poder arrancar una nueva
    #        simulacion normalmente (el guard no debe quedar "trabado") ---
    _bloqueo_liberado.clear()
    _entro_al_motor.clear()
    win.ejecutar_simulacion()
    tercer_hilo = getattr(win, 'simulation_thread', None)
    check(tercer_hilo is not primer_hilo,
          "Tras terminar la corrida anterior, un nuevo click SI arranca un hilo nuevo")
    check(_entro_al_motor.wait(timeout=10), "La tercera corrida llega a ejecutar el motor")
    _bloqueo_liberado.set()
    tercer_hilo.wait(15_000)
    _pump(seconds=2.0)
    check(not tercer_hilo.isRunning(), "La tercera corrida tambien termina correctamente")
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
