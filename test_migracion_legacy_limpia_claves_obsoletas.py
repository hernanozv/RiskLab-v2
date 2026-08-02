"""
test_migracion_legacy_limpia_claves_obsoletas.py
====================================================

Regresion para bug bajo #41 (QA ronda 3): al cargar un archivo JSON con
eventos en formato LEGACY (claves 'eventos_padres'/'tipo_dependencia',
anteriores al esquema actual de 'vinculos'), cargar_configuracion
migraba correctamente esas claves a una lista 'vinculos' equivalente,
pero NO eliminaba las claves legacy del evento en memoria. Esto dejaba
'eventos_padres'/'tipo_dependencia' colgando de forma redundante junto
a 'vinculos' (que es la única representación que el motor
(generar_lda_con_secuencialidad) realmente usa) -- si el usuario volvía
a guardar, esas claves obsoletas se persistían indefinidamente en el
nuevo JSON, y cualquier código que solo chequeara `'eventos_padres' in
evento` (p.ej. el propio fix de fidelidad round-trip de medio #27)
seguiría viéndolas como si el evento aún estuviera en formato legacy.

El fix elimina ('pop') 'eventos_padres' y 'tipo_dependencia' del evento
inmediatamente después de migrarlos a 'vinculos', tanto para eventos de
la simulación principal como para eventos dentro de un escenario.

Este test construye un archivo JSON con un evento legacy (sin
'vinculos', con 'eventos_padres'+'tipo_dependencia') en la simulación
principal Y en un escenario, lo carga, y verifica que en memoria: (a)
'vinculos' se construyó correctamente a partir de los datos legacy, y
(b) las claves legacy ya NO están presentes.
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
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)

print("=" * 70)
print("BUG BAJO #41: migración legacy debe limpiar 'eventos_padres'/'tipo_dependencia'")
print("=" * 70)


def _evento_legacy(id_, nombre, padres=None):
    return {
        "id": id_, "nombre": nombre, "activo": True,
        "sev_opcion": 2, "sev_input_method": "direct",
        "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
        "sev_params_direct": {"mean": 10000, "std": 1000},
        "freq_opcion": 1, "tasa": 3.0,
        "factores_ajuste": [],
        "eventos_padres": padres or [],
        "tipo_dependencia": "AND",
        # NOTA: sin 'vinculos' -- formato legacy puro.
    }


config = {
    "num_simulaciones": 5000,
    "eventos_riesgo": [
        _evento_legacy("evt-padre", "EventoPadre"),
        _evento_legacy("evt-hijo", "EventoHijo", padres=["evt-padre"]),
    ],
    "scenarios": [
        {"nombre": "EscLegacy", "descripcion": "", "eventos_riesgo": [
            _evento_legacy("evt-padre-esc", "EventoPadreEsc"),
            _evento_legacy("evt-hijo-esc", "EventoHijoEsc", padres=["evt-padre-esc"]),
        ]}
    ],
}

tmp_path = os.path.join(_THIS_DIR, '_tmp_test_migracion_legacy.json')
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config, f)

try:
    win = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    win.cargar_configuracion()

    check(len(win.eventos_riesgo) == 2, "Los 2 eventos principales se cargaron correctamente")
    evento_hijo = next((e for e in win.eventos_riesgo if e.get('nombre') == 'EventoHijo'), None)
    check(evento_hijo is not None, "El evento hijo (con eventos_padres legacy) se encontró")

    if evento_hijo is not None:
        check('vinculos' in evento_hijo and len(evento_hijo['vinculos']) == 1,
              f"Bug bajo #41: 'vinculos' se construyó correctamente a partir de "
              f"'eventos_padres' legacy (obtenido: {evento_hijo.get('vinculos')})")
        check('eventos_padres' not in evento_hijo,
              f"Bug bajo #41: la clave legacy 'eventos_padres' ya NO está presente "
              f"tras la migración (obtenido claves: {sorted(evento_hijo.keys())})")
        check('tipo_dependencia' not in evento_hijo,
              f"Bug bajo #41: la clave legacy 'tipo_dependencia' ya NO está presente "
              f"tras la migración (obtenido claves: {sorted(evento_hijo.keys())})")

    check(len(win.scenarios) == 1, "El escenario se cargó correctamente")
    if win.scenarios:
        evento_hijo_esc = next(
            (e for e in win.scenarios[0].eventos_riesgo if e.get('nombre') == 'EventoHijoEsc'), None
        )
        check(evento_hijo_esc is not None, "El evento hijo del escenario se encontró")
        if evento_hijo_esc is not None:
            check('vinculos' in evento_hijo_esc and len(evento_hijo_esc['vinculos']) == 1,
                  f"Bug bajo #41 (escenario): 'vinculos' se construyó correctamente "
                  f"(obtenido: {evento_hijo_esc.get('vinculos')})")
            check('eventos_padres' not in evento_hijo_esc,
                  f"Bug bajo #41 (escenario): 'eventos_padres' ya NO está presente "
                  f"(obtenido claves: {sorted(evento_hijo_esc.keys())})")
            check('tipo_dependencia' not in evento_hijo_esc,
                  f"Bug bajo #41 (escenario): 'tipo_dependencia' ya NO está presente "
                  f"(obtenido claves: {sorted(evento_hijo_esc.keys())})")
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
