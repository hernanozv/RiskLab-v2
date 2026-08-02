"""
test_cap_frecuencia_warning_ui.py
====================================

Regresion para bug #32: cuando el motor de simulación reescala hacia abajo
la frecuencia de un evento porque excede el límite interno del motor
(MAX_EVENTOS_POR_EVENTO_POR_CHUNK), emite un warning de Python
(RiskLabFrequencyCapWarning) y marca el evento con
'_cap_frecuencia_aplicado'. Pero nada en la UI leía esa marca: el warning de
Python solo se ve si hay una consola visible (en un build de producción con
consola oculta, no llega a ningún lado), y la única forma de enterarse era
abrir el export JSON opcional (fuera del flujo normal) y buscar el campo.
Los resultados quedaban silenciosamente subestimados sin que el usuario lo
supiera.

La lógica que efectivamente DISPARA el cap dentro del motor de simulación
ya está cubierta por test_cap_dispara_warning_en_freq_muy_alta
(test_robustez_simulacion.py). Este test cubre la pieza que faltaba: que
simulacion_completada() (el slot de la UI que recibe los resultados)
efectivamente revisa los eventos en busca de '_cap_frecuencia_aplicado' y
avisa al usuario con un QMessageBox visible.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np
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

_warnings_mostrados = []


def _fake_warning(parent, titulo, texto, *a, **kw):
    _warnings_mostrados.append((titulo, texto))
    return QtWidgets.QMessageBox.Ok


QtWidgets.QMessageBox.warning = staticmethod(_fake_warning)


def _make_evento(nombre, capeado=False):
    dist_freq = RLB.generar_distribucion_frecuencia(1, tasa=5.0)
    dist_sev = RLB.generar_distribucion_severidad(
        2, None, None, None, input_method='direct',
        params_direct={'mean': 1000.0, 'std': 100.0}
    )
    evento = {
        'id': nombre, 'nombre': nombre, 'freq_opcion': 1, 'sev_opcion': 2,
        'dist_frecuencia': dist_freq, 'dist_severidad': dist_sev,
        'activo': True, 'tasa': 5.0,
    }
    if capeado:
        # Huella que el motor deja cuando se activa el cap de frecuencia
        # (ver Risk_Lab_Beta.py, bloque "Fix bug #1" / sum_final_event_frequencies).
        evento['_cap_frecuencia_aplicado'] = True
        evento['_cap_frecuencia_factor'] = 0.001
        evento['_cap_frecuencia_suma_original'] = 600_000_000
        evento['_cap_frecuencia_suma_capeada'] = 500_000_000
        evento['_cap_frecuencia_media_original'] = 60_000.0
        evento['_cap_frecuencia_media_capeada'] = 50_000.0
    return evento


def _resultados_dummy(eventos, num_sims=1000):
    n_ev = len(eventos)
    perdidas_totales = np.random.default_rng(0).random(num_sims) * 1000
    frecuencias_totales = np.random.default_rng(1).integers(0, 5, size=num_sims)
    perdidas_por_evento = [perdidas_totales / n_ev for _ in range(n_ev)]
    frecuencias_por_evento = [frecuencias_totales for _ in range(n_ev)]
    return perdidas_totales, frecuencias_totales, perdidas_por_evento, frecuencias_por_evento


print("=" * 70)
print("BUG #32: Warning visible en UI cuando se aplica el cap de frecuencia")
print("=" * 70)

win = RLB.RiskLabApp()

# --- 1. Caso normal (ningún evento capeado): no debe aparecer ningún aviso ---
_warnings_mostrados.clear()
eventos_normales = [_make_evento('E1'), _make_evento('E2')]
resultados = _resultados_dummy(eventos_normales)
win.simulacion_completada(*resultados, eventos_normales)
check(len(_warnings_mostrados) == 0,
      "Sin eventos capeados: no se muestra ningún aviso de distorsión")

# --- 2. Un evento capeado: debe mostrarse un aviso explícito ---
_warnings_mostrados.clear()
eventos_con_cap = [_make_evento('E1'), _make_evento('EventoCapeado', capeado=True)]
resultados = _resultados_dummy(eventos_con_cap)
win.simulacion_completada(*resultados, eventos_con_cap)

check(len(_warnings_mostrados) == 1,
      f"Bug #32: se muestra exactamente un aviso cuando hay un evento capeado "
      f"(obtenido: {len(_warnings_mostrados)})")
if _warnings_mostrados:
    titulo, texto = _warnings_mostrados[0]
    check("frecuencia" in titulo.lower() or "recescal" in titulo.lower() or "distorsion" in titulo.lower(),
          f"El título del aviso refleja el problema (obtenido: '{titulo}')")
    check("EventoCapeado" in texto, "El aviso identifica el evento afectado")
    check("60,000.0" in texto or "60000.0" in texto or "60.000,0" in texto or "60,000" in texto,
          f"El aviso menciona la media original de frecuencia (texto: {texto!r})")
    check("50,000.0" in texto or "50000.0" in texto or "50.000,0" in texto or "50,000" in texto,
          f"El aviso menciona la media capeada de frecuencia (texto: {texto!r})")

print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
