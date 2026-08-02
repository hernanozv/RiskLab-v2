"""
test_limpieza_campos_internos_guardado.py
=============================================

Regresion para hallazgo medio #3: guardar_configuracion() removía una lista
explícita de campos internos temporales del motor de simulación
(_usa_estocastico, _factores_vector, _seguros_aplicables, etc.) antes de
serializar, pero esa lista NO incluía los campos '_cap_frecuencia_*' que el
motor agrega cuando reescala la frecuencia de un evento por exceder el
límite interno. Si alguno de esos campos llegaba a quedar en el dict del
evento (p.ej. por un cambio futuro que ya no proteja con shallow-copy antes
de simular), se guardaría en el JSON. Al recargar ese archivo más tarde, el
aviso de "resultados distorsionados" (bug #32) podría dispararse para una
corrida que en realidad no volvió a activar el cap — un falso positivo.

El fix centraliza TODOS los campos internos a limpiar en una única
constante (_CAMPOS_INTERNOS_SIMULACION) usada por ambas copias de limpieza
en guardar_configuracion (eventos principales y eventos de escenario), para
que agregar un campo nuevo no pueda "olvidarse" de una de las dos.

Este test instancia RiskLabApp de verdad (headless) y verifica que NINGÚN
campo interno — incluyendo una huella de cap de frecuencia "stale" puesta a
mano — sobrevive al guardado, tanto en la lista principal de eventos como
en los eventos de un escenario.
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
QtWidgets.QMessageBox.warning = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)


def _make_evento_con_flags_internos(nombre):
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
    # Simular que TODOS los campos internos conocidos quedaron pegados al
    # evento (huella "stale" de una corrida anterior).
    for campo in RLB._CAMPOS_INTERNOS_SIMULACION:
        evento[campo] = True
    return evento


print("=" * 70)
print("Hallazgo medio #3: limpieza completa de campos internos al guardar")
print("=" * 70)

check(len(RLB._CAMPOS_INTERNOS_SIMULACION) >= 14,
      "_CAMPOS_INTERNOS_SIMULACION incluye los campos de flags previos + los de cap de frecuencia")
for campo_cap in ('_cap_frecuencia_aplicado', '_cap_frecuencia_factor',
                  '_cap_frecuencia_suma_original', '_cap_frecuencia_suma_capeada',
                  '_cap_frecuencia_media_original', '_cap_frecuencia_media_capeada'):
    check(campo_cap in RLB._CAMPOS_INTERNOS_SIMULACION,
          f"'{campo_cap}' está en la lista de campos a limpiar")

win = RLB.RiskLabApp()
win.eventos_riesgo = [_make_evento_con_flags_internos('EventoPrincipal')]

escenario = RLB.Scenario('EscenarioTest', 'desc')
escenario.eventos_riesgo = [_make_evento_con_flags_internos('EventoEscenario')]
win.scenarios = [escenario]

win.num_simulaciones_var.setText('5000')

target = os.path.join(_THIS_DIR, '_tmp_limpieza_campos_internos.json')
QtWidgets.QFileDialog.getSaveFileName = staticmethod(lambda *a, **kw: (target, ''))

try:
    win.guardar_configuracion()

    with open(target, encoding='utf-8') as f:
        data = json.load(f)

    evento_principal_guardado = data['eventos_riesgo'][0]
    campos_internos_principal = [k for k in evento_principal_guardado if k.startswith('_')]
    check(campos_internos_principal == [],
          f"Bug medio #3: ningún campo interno sobrevive en el evento principal guardado "
          f"(encontrados: {campos_internos_principal})")

    evento_escenario_guardado = data['scenarios'][0]['eventos_riesgo'][0]
    campos_internos_escenario = [k for k in evento_escenario_guardado if k.startswith('_')]
    check(campos_internos_escenario == [],
          f"Bug medio #3: ningún campo interno sobrevive en el evento de escenario guardado "
          f"(encontrados: {campos_internos_escenario})")

    # Los campos normales del evento SI deben conservarse
    check(evento_principal_guardado.get('nombre') == 'EventoPrincipal',
          "Los campos normales del evento se conservan correctamente")
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
