"""
test_guardar_encoder_personalizado.py
========================================

Regresion para hallazgo medio #4: guardar_configuracion() llamaba a
json.dump(configuracion, f, ...) SIN el parámetro default=, a diferencia
del export para análisis IA (_escribir_export_json), que sí usa
default=self._json_default. Esto funcionaba "por casualidad" para
np.float64 (subclase de float, el encoder estándar lo maneja nativamente),
pero:
  1. Cualquier OTRO tipo numpy que el evento pudiera contener y que NO sea
     subclase de un tipo nativo de Python (np.int64, np.bool_, np.ndarray)
     hacía fallar json.dump con un TypeError crudo, abortando TODO el
     guardado — incluso si esos valores eran perfectamente serializables
     con el encoder ya existente en la clase.
  2. Un NaN/Infinity (p.ej. un CV con media≈0) se guardaba como token
     NO estándar (NaN/Infinity), rompiendo parsers JSON estrictos, igual
     que el bug #27 ya corregido en el export.

El fix agrega el mismo default=self._json_default Y el mismo saneo
_sanear_nan_inf_recursivo que ya usa el export, logrando paridad entre
ambos caminos de serialización.

Este test instancia RiskLabApp de verdad (headless) y guarda una
configuración cuyo evento contiene deliberadamente tipos numpy no-nativos
(np.int64, np.bool_) y un NaN, verificando que el guardado no falla y que
el archivo resultante es JSON válido y estricto.
"""
import json
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


def _parse_constant_estricto(token):
    raise ValueError(f"Token no válido en JSON estándar: {token}")


app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

_criticals_mostrados = []
QtWidgets.QMessageBox.warning = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.critical = staticmethod(
    lambda parent, titulo, texto, *a, **kw: _criticals_mostrados.append((titulo, texto)) or QtWidgets.QMessageBox.Ok
)


print("=" * 70)
print("Hallazgo medio #4: encoder personalizado en guardar_configuracion")
print("=" * 70)

win = RLB.RiskLabApp()

dist_freq = RLB.generar_distribucion_frecuencia(1, tasa=5.0)
dist_sev = RLB.generar_distribucion_severidad(
    2, None, None, None, input_method='direct', params_direct={'mean': 1000.0, 'std': 100.0}
)
evento = {
    'id': 'e1', 'nombre': 'E1', 'freq_opcion': 1, 'sev_opcion': 2,
    'dist_frecuencia': dist_freq, 'dist_severidad': dist_sev, 'activo': True,
    'tasa': 5.0,
    # Tipos numpy no-nativos que ANTES no tenian encoder para manejarlos:
    'num_eventos': np.int64(12),
    'algun_flag_numpy': np.bool_(True),
    # Valor degenerado que produce NaN (p.ej. de un CV con media 0):
    'coeficiente_variacion_ejemplo': float('nan'),
    'limite_superior_ejemplo': float('inf'),
}
win.eventos_riesgo = [evento]
win.num_simulaciones_var.setText('5000')

target = os.path.join(_THIS_DIR, '_tmp_guardar_encoder.json')
QtWidgets.QFileDialog.getSaveFileName = staticmethod(lambda *a, **kw: (target, ''))

try:
    win.guardar_configuracion()

    check(len(_criticals_mostrados) == 0,
          f"El guardado con tipos numpy no-nativos y NaN/Infinity NO falla "
          f"(obtenido: {_criticals_mostrados})")
    check(os.path.exists(target), "El archivo destino existe")

    with open(target, encoding='utf-8') as f:
        contenido_crudo = f.read()

    check('NaN' not in contenido_crudo and 'Infinity' not in contenido_crudo,
          "El JSON guardado no contiene tokens NaN/Infinity no estándar")

    try:
        data = json.loads(contenido_crudo, parse_constant=_parse_constant_estricto)
        check(True, "El JSON guardado es parseable con un parser estricto")
    except ValueError as e:
        check(False, f"El JSON guardado debería ser estrictamente válido: {e}")
        data = json.loads(contenido_crudo)

    ev_guardado = data['eventos_riesgo'][0]
    check(ev_guardado.get('num_eventos') == 12,
          "np.int64 se serializa correctamente (via encoder)")
    check(ev_guardado.get('algun_flag_numpy') is True,
          "np.bool_ se serializa correctamente (via encoder)")
    check(ev_guardado.get('coeficiente_variacion_ejemplo') is None,
          "NaN se serializa como null")
    check(ev_guardado.get('limite_superior_ejemplo') == 'inf',
          "Infinity se serializa como 'inf'")
finally:
    if os.path.exists(target):
        os.remove(target)


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
