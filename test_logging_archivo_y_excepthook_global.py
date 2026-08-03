"""
test_logging_archivo_y_excepthook_global.py
===============================================

Regresion para bug alto R4 #7 (QA ronda 4): Risk Lab no tenía logging a
archivo ni un sys.excepthook global. En una build empaquetada con la
consola oculta (PyInstaller --windowed/console=False), cualquier
excepción no capturada en el hilo principal (fuera de los try/except
explícitos de la UI, ej. dentro de un slot de Qt disparado por un botón)
simplemente cerraba la app sin dejar NINGÚN rastro: no hay consola donde
leer el traceback, y no existía ningún archivo de log en disco. Esto
hacía que un crash reportado por un usuario en producción fuera
efectivamente indiagnosticable a distancia.

El fix agrega, a nivel de módulo (se ejecuta al importar Risk_Lab_Beta):
1. Un logger raíz con un RotatingFileHandler escribiendo a
   ~/.risklab/risklab.log.
2. Un sys.excepthook que registra cualquier excepción no capturada del
   hilo principal en ese archivo antes de continuar con el
   comportamiento por defecto de Python (sys.__excepthook__).

Este test parchea os.path.expanduser ANTES de importar Risk_Lab_Beta
(para redirigir el directorio de log a uno temporal) y verifica que:
1. Se creó el archivo de log en el directorio esperado.
2. sys.excepthook fue reemplazado por uno propio de Risk Lab (no es el
   default de Python, sys.__excepthook__).
3. Invocar sys.excepthook con una excepción de prueba escribe su
   traceback en el archivo de log.
"""
import os
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

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


print("=" * 70)
print("BUG ALTO R4 #7: logging a archivo + excepthook global")
print("=" * 70)

_tmp_home = tempfile.mkdtemp(prefix="risklab_test_home_")
_real_expanduser = os.path.expanduser


def _fake_expanduser(path):
    if path == '~':
        return _tmp_home
    return _real_expanduser(path)


os.path.expanduser = _fake_expanduser
_excepthook_original_python = sys.excepthook

import Risk_Lab_Beta as RLB  # noqa: E402  (import diferido a propósito, tras el parche)

log_path = os.path.join(_tmp_home, '.risklab', 'risklab.log')

print(f"  directorio de log simulado: {_tmp_home}")
print(f"  archivo de log esperado: {log_path}")

check(os.path.isfile(log_path),
      f"Bug alto R4 #7: se crea un archivo de log en ~/.risklab/risklab.log "
      f"(obtenido: existe={os.path.isfile(log_path)})")

check(sys.excepthook is not _excepthook_original_python,
      "Bug alto R4 #7: sys.excepthook fue reemplazado por un hook propio de Risk Lab")

# Invocar el excepthook instalado con una excepción de prueba y verificar
# que quede registrada en el archivo de log.
try:
    raise RuntimeError("excepción de prueba R4-alto-7 marcador único 8f3c1a")
except RuntimeError:
    tipo, valor, tb = sys.exc_info()
    sys.excepthook(tipo, valor, tb)

for handler in RLB.logging.getLogger().handlers:
    try:
        handler.flush()
    except Exception:
        pass

with open(log_path, encoding='utf-8') as f:
    contenido_log = f.read()

check('8f3c1a' in contenido_log and 'RuntimeError' in contenido_log,
      "El excepthook instalado registra la excepción de prueba en el archivo de log")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
