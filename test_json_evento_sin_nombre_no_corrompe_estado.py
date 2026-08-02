"""
test_json_evento_sin_nombre_no_corrompe_estado.py
=====================================================

Regresion para bug critico #7 (QA ronda 3): cargar_configuracion (import
de JSON) se documenta a si misma como transaccional ("=== INICIO DE
TRANSACCIÓN: Procesar en variables temporales ===" / "=== COMMIT DE
TRANSACCIÓN ==="), pero el bloque de "commit" limpiaba
self.eventos_riesgo/self.scenarios y RECIEN DESPUES accedia a
evento_data['nombre'] sin proteccion (linea "...crear_table_item_con_wrap
(evento_data['nombre'])") para poblar la tabla de eventos.

Si un evento del archivo carecia de la clave 'nombre' (nunca se
validaba su presencia durante la fase de "procesamiento", solo se
usaba .get('nombre', 'N/A') para mensajes de error), el KeyError
ocurria DESPUES de que la configuracion previa (valida, en memoria) ya
habia sido destruida y reemplazada a medias -- violando por completo
el diseño transaccional que el propio codigo documenta. El dialogo de
error resultante sugeria que la carga habia "fallado", pero en
realidad el estado previo del usuario ya era irrecuperable.

El fix agrega una validacion explicita (todos los eventos de la
simulacion principal y de cada escenario deben tener 'nombre' no
vacio) ANTES del commit, junto a las demas validaciones pre-commit ya
existentes (deteccion de ciclos). Si falla, se lanza ValueError (que
cae en el except genero que muestra un dialogo, SIN haber tocado
self.eventos_riesgo/self.scenarios).

Este test precarga la app con un evento VALIDO en memoria, intenta
cargar un archivo JSON con un evento sin 'nombre', y verifica que:
  1. Se muestra un dialogo de error (critico).
  2. El evento previo valido SIGUE intacto en self.eventos_riesgo (el
     estado NO fue reemplazado a medias).
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

_criticals_mostrados = []


def _fake_critical(parent, titulo, texto, *a, **kw):
    _criticals_mostrados.append((titulo, texto))
    return QtWidgets.QMessageBox.Ok


QtWidgets.QMessageBox.critical = staticmethod(_fake_critical)
QtWidgets.QMessageBox.warning = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)


def _evento_base(id_, nombre, **extra):
    ev = {
        "id": id_, "nombre": nombre, "activo": True,
        "sev_opcion": 2, "sev_input_method": "direct",
        "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
        "sev_params_direct": {"mean": 10000, "std": 1000},
        "freq_opcion": 1, "tasa": 3.0,
        "num_eventos": None, "prob_exito": None,
        "pg_minimo": None, "pg_mas_probable": None, "pg_maximo": None,
        "pg_confianza": None, "pg_alpha": None, "pg_beta": None,
        "beta_minimo": None, "beta_mas_probable": None, "beta_maximo": None,
        "beta_confianza": None, "beta_alpha": None, "beta_beta": None,
        "sev_freq_activado": False,
        "vinculos": [], "factores_ajuste": [],
    }
    if 'nombre' in extra and extra['nombre'] is None:
        del ev['nombre']
        extra = {k: v for k, v in extra.items() if k != 'nombre'}
    ev.update(extra)
    return ev


print("=" * 70)
print("BUG CRÍTICO #7: evento sin 'nombre' no debe corromper el estado previo")
print("=" * 70)

evento_sin_nombre = _evento_base("evt-sin-nombre", "PLACEHOLDER")
del evento_sin_nombre['nombre']

config = {
    "num_simulaciones": 10000,
    "eventos_riesgo": [
        _evento_base("evt-A", "Evento Válido A"),
        evento_sin_nombre,
    ],
    "scenarios": [],
}

tmp_path = os.path.join(_THIS_DIR, '_tmp_test_evento_sin_nombre.json')
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config, f)

evento_previo = _evento_base("evt-previo", "Evento PREVIO (antes de cargar)")

try:
    win = RLB.RiskLabApp()
    # Precargar un evento VALIDO en memoria, como si el usuario ya
    # tuviera una configuración en curso antes de intentar importar el
    # archivo corrupto.
    win.eventos_riesgo = [evento_previo]
    for row, ev in enumerate([evento_previo]):
        win.eventos_table.insertRow(row)
        win.eventos_table.setCellWidget(row, 0, win.crear_checkbox_activo(row, activo=True))
        win.eventos_table.setItem(row, 1, win.crear_table_item_con_wrap(ev['nombre']))

    nombres_antes = [e.get('nombre') for e in win.eventos_riesgo]

    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    win.cargar_configuracion()

    check(len(_criticals_mostrados) >= 1,
          f"Bug crítico #7: se muestra un diálogo de error crítico al intentar "
          f"cargar un archivo con un evento sin 'nombre' (obtenido: {_criticals_mostrados})")

    nombres_despues = [e.get('nombre') for e in win.eventos_riesgo]
    check(nombres_despues == nombres_antes,
          f"Bug crítico #7: la configuración previa (válida) NO fue reemplazada "
          f"a medias por la carga fallida (antes: {nombres_antes!r}, "
          f"después: {nombres_despues!r})")
    check(len(win.eventos_riesgo) == 1 and win.eventos_riesgo[0] is evento_previo,
          "El objeto evento previo sigue siendo exactamente el mismo (misma identidad), "
          "confirmando que self.eventos_riesgo nunca fue tocado")
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
