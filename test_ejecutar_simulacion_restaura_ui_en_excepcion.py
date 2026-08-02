"""
test_ejecutar_simulacion_restaura_ui_en_excepcion.py
========================================================

Regresion para bug bajo #39 (QA ronda 3): en ejecutar_simulacion(), si
ocurre una excepción DESPUÉS de self.set_interfaz_activa(False) pero
ANTES de que el hilo (SimulacionThread) arranque con éxito (p.ej. el
constructor de SimulacionThread lanza una excepción, o .start() falla),
los bloques except (ValueError / Exception genérica) mostraban el error
pero NO reactivaban la interfaz -- ni self.simulacion_completada ni
self.simulacion_error se disparan nunca (el hilo nunca llegó a correr),
por lo que la UI quedaba deshabilitada permanentemente. Baja
probabilidad de ocurrir en la práctica, pero real.

El fix agrega self.set_interfaz_activa(True) en ambos bloques except.
Como set_interfaz_activa es idempotente (solo llama setEnabled en
widgets), es seguro llamarla incluso si la interfaz nunca llegó a
deshabilitarse (p.ej. si la excepción ocurre antes, por validación de
num_simulaciones).

Este test fuerza una excepción en la construcción de SimulacionThread
(monkeypatch) -- que ocurre DESPUÉS de set_interfaz_activa(False) en el
código real -- y verifica que, tras la excepción, los widgets de la
interfaz principal queden habilitados (no deshabilitados para siempre).
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
print("BUG BAJO #39: ejecutar_simulacion debe restaurar la UI si falla tras desactivarla")
print("=" * 70)

win = RLB.RiskLabApp()
win.eventos_riesgo = [{
    "id": "evt-1", "nombre": "EventoA", "activo": True,
    "sev_opcion": 2, "sev_input_method": "direct",
    "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
    "sev_params_direct": {"mean": 5000, "std": 500},
    "freq_opcion": 1, "tasa": 2.0, "vinculos": [], "factores_ajuste": [],
}]
win.num_simulaciones_var.setText("1000")

# Precondición: la interfaz arranca habilitada.
check(win.num_simulaciones_var.isEnabled(), "Precondición: num_simulaciones_var está habilitado antes de simular")

# Forzar que SimulacionThread (construido DESPUÉS de set_interfaz_activa(False)
# en el código real) lance una excepción al instanciarse.
_orig_thread_cls = RLB.SimulacionThread


class _ThreadQueFalla:
    def __init__(self, *a, **kw):
        raise RuntimeError("fallo simulado en la construcción del hilo")


RLB.SimulacionThread = _ThreadQueFalla
try:
    win.ejecutar_simulacion()
finally:
    RLB.SimulacionThread = _orig_thread_cls

print(f"  num_simulaciones_var.isEnabled() tras la excepción: {win.num_simulaciones_var.isEnabled()}")
print(f"  eventos_table.isEnabled() tras la excepción: {win.eventos_table.isEnabled()}")

check(win.num_simulaciones_var.isEnabled(),
      "Bug bajo #39: num_simulaciones_var sigue/vuelve a estar habilitado tras la excepción")
check(win.eventos_table.isEnabled(),
      "Bug bajo #39: eventos_table sigue/vuelve a estar habilitado tras la excepción")
check(win.central_widget.isTabEnabled(win.central_widget.indexOf(win.config_tab)),
      "Bug bajo #39: la pestaña de configuración sigue/vuelve a estar habilitada tras la excepción")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
