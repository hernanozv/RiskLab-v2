"""
test_guardado_atomico.py
==========================

Regresion para bug #29: guardar_configuracion escribía directamente sobre
el archivo destino con `open(filepath, 'w')`, que trunca el archivo al
abrirlo. Si `json.dump` fallaba a mitad de camino (disco lleno, error de
serialización, proceso interrumpido), la configuración previa válida ya
había sido truncada y se perdía sin posibilidad de recuperación.

Ahora se escribe a un archivo temporal en el mismo directorio y solo se
reemplaza el archivo destino con os.replace() (atómico) una vez que la
escritura completa tuvo éxito.

Este test instancia RiskLabApp de verdad (headless) y ejercita
guardar_configuracion() en dos escenarios:
  1. Guardado exitoso: el archivo destino queda con el contenido correcto
     y no quedan archivos temporales huérfanos.
  2. Guardado que falla a mitad de camino (se simula fallando
     json.dump): el archivo destino preexistente NO debe alterarse, y no
     debe quedar ningún archivo temporal huérfano.
"""
import json
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


print("=" * 70)
print("BUG #29: Escritura atómica al guardar configuración")
print("=" * 70)

tmp_dir = os.path.join(_THIS_DIR, '_tmp_guardado_atomico')
os.makedirs(tmp_dir, exist_ok=True)
target_path = os.path.join(tmp_dir, 'config.json')

try:
    win = RLB.RiskLabApp()
    win.eventos_riesgo = [_make_evento('E1')]
    win.num_simulaciones_var.setText("5000")

    # --- 1. Guardado exitoso ---
    QtWidgets.QFileDialog.getSaveFileName = staticmethod(lambda *a, **kw: (target_path, ''))
    win.guardar_configuracion()

    check(len(_criticals_mostrados) == 0, "Guardado exitoso: no dispara ningún diálogo de error")
    check(os.path.exists(target_path), "Guardado exitoso: el archivo destino existe")
    with open(target_path, encoding='utf-8') as f:
        contenido = json.load(f)
    check(contenido.get('num_simulaciones') == 5000, "El contenido guardado es correcto")
    check(len(contenido.get('eventos_riesgo', [])) == 1, "El evento se guardó correctamente")

    archivos_temp = [f for f in os.listdir(tmp_dir) if f.startswith('.risklab_tmp_')]
    check(len(archivos_temp) == 0,
          f"No quedan archivos temporales huérfanos tras un guardado exitoso (encontrados: {archivos_temp})")

    # --- 2. Guardado que falla a mitad de camino: el archivo previo debe
    #        sobrevivir intacto ---
    contenido_original_bytes = open(target_path, 'rb').read()

    class _FakeJsonModule:
        """Actua como el modulo json real, pero .dump() falla (simula disco lleno)."""
        def dump(self, *a, **kw):
            raise OSError("Simulando disco lleno a mitad de la escritura")

        def __getattr__(self, nombre):
            return getattr(json, nombre)

    json_original = RLB.json
    RLB.json = _FakeJsonModule()
    try:
        win.num_simulaciones_var.setText("9999")  # cambio que NO deberia persistir
        win.guardar_configuracion()
    finally:
        RLB.json = json_original

    check(len(_criticals_mostrados) >= 1,
          "Guardado fallido: se reporta un error al usuario")

    contenido_tras_fallo_bytes = open(target_path, 'rb').read()
    check(contenido_tras_fallo_bytes == contenido_original_bytes,
          "Bug #29: el archivo destino preexistente NO se corrompe cuando falla la escritura")

    with open(target_path, encoding='utf-8') as f:
        contenido_tras_fallo = json.load(f)
    check(contenido_tras_fallo.get('num_simulaciones') == 5000,
          "El contenido previo (num_simulaciones=5000) sigue intacto, no el fallido (9999)")

    archivos_temp_tras_fallo = [f for f in os.listdir(tmp_dir) if f.startswith('.risklab_tmp_')]
    check(len(archivos_temp_tras_fallo) == 0,
          f"No queda ningún archivo temporal huérfano tras un guardado fallido "
          f"(encontrados: {archivos_temp_tras_fallo})")
finally:
    import shutil
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
