"""
test_aviso_memoria_antes_de_simular.py
==========================================

Regresion para bug critico R4 #1 (QA ronda 4): la simulacion podia agotar
toda la RAM disponible y ser matada por el sistema operativo (OOM kill,
SIGKILL no interceptable) con parametros de entrada perfectamente
normales -- un evento con frecuencia alta (ej. tasa=500/año) combinado con
un numero de simulaciones moderado (ej. 200.000) generaba arrays de
tamaño num_simulaciones x tasa sin ningun control real de memoria.
MAX_EVENTOS_POR_EVENTO_POR_CHUNK (500M) solo protegia contra distorsion
estadistica, no contra memoria real -- el OOM ya ocurria muy por debajo
de ese umbral.

El fix agrega una estimacion previa de "ocurrencias totales" (num.
simulaciones x frecuencia esperada por evento, sumada entre todos los
eventos activos) justo antes de arrancar el hilo de simulacion. Si supera
un umbral empirico (OCURRENCIAS_TOTALES_UMBRAL_AVISO_MEMORIA), se muestra
una confirmacion visible (QMessageBox.question, default "No") en vez de
dejar que el proceso sea matado en silencio.

Este test verifica: (a) una configuracion de bajo riesgo NO dispara
ninguna confirmacion y la simulacion arranca normalmente; (b) una
configuracion de alto riesgo SI dispara la confirmacion, y si el usuario
responde "No" (o cierra el dialogo), la simulacion NO arranca (no se
crea self.simulation_thread, la interfaz permanece activa); (c) si el
usuario responde "Si", la simulacion arranca normalmente pese al aviso.
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
print("BUG CRÍTICO R4 #1: aviso de memoria antes de arrancar una simulación de riesgo")
print("=" * 70)


def _evento_poisson(tasa):
    return {
        "id": "evt-1", "nombre": "EventoAltaFrecuencia", "activo": True,
        "sev_opcion": 2, "sev_input_method": "direct",
        "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
        "sev_params_direct": {"mean": 1000, "std": 100},
        "freq_opcion": 1, "tasa": tasa, "vinculos": [], "factores_ajuste": [],
    }


class _ThreadFalso:
    instancias_creadas = 0

    def __init__(self, *a, **kw):
        _ThreadFalso.instancias_creadas += 1
        self.progreso_actualizado = _SignalFalsa()
        self.simulacion_completada = _SignalFalsa()
        self.error_ocurrido = _SignalFalsa()

    def start(self):
        pass


class _SignalFalsa:
    def connect(self, *a, **kw):
        pass


# --- Caso 1: configuración de BAJO riesgo (pocas ocurrencias estimadas) ---
print("\n--- Caso 1: configuración de bajo riesgo ---")
win1 = RLB.RiskLabApp()
win1.eventos_riesgo = [_evento_poisson(tasa=2.0)]
win1.num_simulaciones_var.setText("5000")

preguntas_capturadas = []
QtWidgets.QMessageBox.question = staticmethod(
    lambda *a, **kw: preguntas_capturadas.append(a) or QtWidgets.QMessageBox.Yes
)

_ThreadFalso.instancias_creadas = 0
RLB.SimulacionThread = _ThreadFalso
win1.ejecutar_simulacion()

check(len(preguntas_capturadas) == 0,
      f"Bug crítico R4 #1: config de bajo riesgo NO dispara ningún aviso de memoria "
      f"(obtenido: {len(preguntas_capturadas)} preguntas)")
check(_ThreadFalso.instancias_creadas == 1,
      f"La simulación arranca normalmente sin aviso (obtenido: {_ThreadFalso.instancias_creadas} hilos creados)")

# --- Caso 2: configuración de ALTO riesgo, usuario responde "No" ---
print("\n--- Caso 2: configuración de alto riesgo, usuario cancela ---")
win2 = RLB.RiskLabApp()
win2.eventos_riesgo = [_evento_poisson(tasa=2000.0)]
win2.num_simulaciones_var.setText("10000")

preguntas_capturadas2 = []
QtWidgets.QMessageBox.question = staticmethod(
    lambda *a, **kw: preguntas_capturadas2.append(a) or QtWidgets.QMessageBox.No
)

_ThreadFalso.instancias_creadas = 0
win2.ejecutar_simulacion()

check(len(preguntas_capturadas2) == 1,
      f"Bug crítico R4 #1: config de alto riesgo SÍ dispara la confirmación de memoria "
      f"(obtenido: {len(preguntas_capturadas2)} preguntas)")
check(_ThreadFalso.instancias_creadas == 0,
      f"Bug crítico R4 #1: si el usuario responde 'No', la simulación NO arranca "
      f"(obtenido: {_ThreadFalso.instancias_creadas} hilos creados)")
check(win2.num_simulaciones_var.isEnabled(),
      "La interfaz permanece activa/habilitada tras cancelar por memoria")

# --- Caso 3: configuración de ALTO riesgo, usuario responde "Sí" ---
print("\n--- Caso 3: configuración de alto riesgo, usuario confirma ---")
win3 = RLB.RiskLabApp()
win3.eventos_riesgo = [_evento_poisson(tasa=2000.0)]
win3.num_simulaciones_var.setText("10000")

QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)

_ThreadFalso.instancias_creadas = 0
win3.ejecutar_simulacion()

check(_ThreadFalso.instancias_creadas == 1,
      f"Si el usuario confirma pese al aviso, la simulación arranca normalmente "
      f"(obtenido: {_ThreadFalso.instancias_creadas} hilos creados)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
