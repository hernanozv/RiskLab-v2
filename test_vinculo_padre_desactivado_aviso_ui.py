"""
test_vinculo_padre_desactivado_aviso_ui.py
==============================================

Regresion para bug medio #17 (QA ronda 2): en ejecutar_simulacion (usado
tanto por la pestaña "Simulación" como por "Escenarios", que reutiliza el
mismo flujo vía ejecutar_simulacion_escenario), cuando un vínculo apunta a
un evento padre DESACTIVADO, ese vínculo se filtra silenciosamente antes
de simular (el evento hijo pasa a comportarse como independiente para ese
vínculo). El único aviso de esto era un `print()` a consola — invisible
en un build de producción con consola oculta — sin ningún aviso visible
en la UI.

El fix recolecta los eventos cuyos vínculos fueron ignorados por esta
razón y muestra un QMessageBox.warning visible antes de iniciar la
simulación.

Este test arma un escenario con un evento padre desactivado y un evento
hijo con un vínculo hacia él, llama a ejecutar_simulacion() (headless,
interceptando QMessageBox.warning) y verifica que se muestra el aviso
mencionando el evento hijo afectado.
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

avisos_mostrados = []


def _fake_warning(parent, titulo, texto, *a, **kw):
    avisos_mostrados.append((titulo, texto))
    return QtWidgets.QMessageBox.Ok


QtWidgets.QMessageBox.warning = staticmethod(_fake_warning)
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)

print("=" * 70)
print("BUG MEDIO #17: vínculo a padre desactivado debe avisar en la UI")
print("=" * 70)

evento_padre = {
    'id': 'padre', 'nombre': 'EventoPadreDesactivado', 'activo': False,  # DESACTIVADO
    'sev_opcion': 2, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 1000.0, 'std': 100.0},
    'freq_opcion': 1, 'tasa': 5.0,
}
evento_hijo = {
    'id': 'hijo', 'nombre': 'EventoHijoConVinculo', 'activo': True,
    'sev_opcion': 2, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 500.0, 'std': 50.0},
    'freq_opcion': 1, 'tasa': 2.0,
    'vinculos': [
        {'id_padre': 'padre', 'tipo': 'AND', 'probabilidad': 100,
         'factor_severidad': 1.0, 'umbral_severidad': 0},
    ],
}

win = RLB.RiskLabApp()
win.eventos_riesgo = [evento_padre, evento_hijo]
win.num_simulaciones_var.setText("2000")

win.ejecutar_simulacion()

check(len(avisos_mostrados) == 1,
      f"Se muestra exactamente un aviso al ejecutar la simulación (obtenido: {len(avisos_mostrados)})")

if avisos_mostrados:
    titulo, texto = avisos_mostrados[0]
    check('vínculo' in titulo.lower() or 'vinculo' in titulo.lower(),
          f"El título del aviso menciona 'vínculos' (obtenido: {titulo!r})")
    check('EventoHijoConVinculo' in texto,
          f"Bug medio #17: el aviso menciona el evento hijo afectado "
          f"(obtenido: {texto!r})")

# Dejar que el hilo de simulación (ya lanzado) termine antes de salir, para
# no dejar un QThread colgando al finalizar el proceso.
if getattr(win, 'simulation_thread', None) is not None:
    win.simulation_thread.wait(5000)


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
