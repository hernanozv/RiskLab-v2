"""
test_version_info_sincronizado_con_app_version.py
=====================================================

Regresion para bug bajo R4 #3 (QA ronda 4): version_info.txt (usado por
PyInstaller para incrustar los metadatos de versión del ejecutable de
Windows -- FileVersion/ProductVersion visibles en las propiedades del
.exe) seguía en "1.0.0.0" mientras self.APP_VERSION (mostrado dentro de
la propia app, en el diálogo "Acerca de" y en la barra de estado) ya
había avanzado a "1.10.0". Un build empaquetado mostraría una versión
distinta en las propiedades de Windows Explorer que la que la app
reporta internamente, confundiendo a soporte/usuarios al reportar bugs.

El fix actualiza version_info.txt (filevers/prodvers y los strings
FileVersion/ProductVersion) para reflejar la misma versión que
self.APP_VERSION.

Este test parsea self.APP_VERSION del código y version_info.txt, y
verifica que ambos coincidan (permitiendo que version_info.txt use el
formato de 4 componentes con un componente de build final en 0, que es
la convención estándar de Windows para FileVersion/ProductVersion).
"""
import os
import re
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

print("=" * 70)
print("BUG BAJO R4 #3: version_info.txt debe coincidir con self.APP_VERSION")
print("=" * 70)

win = RLB.RiskLabApp()
app_version = win.APP_VERSION
print(f"  self.APP_VERSION: {app_version!r}")

with open(os.path.join(_THIS_DIR, 'version_info.txt'), encoding='utf-8') as f:
    version_info_txt = f.read()

version_info_esperada = app_version + '.0'  # convención de 4 componentes de Windows
print(f"  versión de 4 componentes esperada en version_info.txt: {version_info_esperada!r}")

check(f"u'FileVersion', u'{version_info_esperada}'" in version_info_txt,
      f"Bug bajo R4 #3: FileVersion en version_info.txt coincide con APP_VERSION "
      f"(esperado: {version_info_esperada!r})")
check(f"u'ProductVersion', u'{version_info_esperada}'" in version_info_txt,
      f"Bug bajo R4 #3: ProductVersion en version_info.txt coincide con APP_VERSION "
      f"(esperado: {version_info_esperada!r})")

partes = [int(p) for p in app_version.split('.')] + [0]
tupla_esperada = f"({partes[0]}, {partes[1]}, {partes[2]}, {partes[3]})"
check(version_info_txt.count(tupla_esperada) == 2,
      f"Bug bajo R4 #3: filevers y prodvers usan la tupla correcta {tupla_esperada} "
      f"(obtenido: {version_info_txt.count(tupla_esperada)} ocurrencias)")

check('1.0.0.0' not in version_info_txt,
      "Bug bajo R4 #3: version_info.txt ya no contiene la versión vieja '1.0.0.0'")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
