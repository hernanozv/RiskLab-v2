"""
test_json_aislamiento_errores_por_item.py
=============================================

Regresion para bug alto #16 (QA ronda 3): cargar_configuracion (import
de JSON) tenia una infraestructura explicita para tolerar eventos
individuales invalidos (eventos_con_error, con try/except SOLO alrededor
de generar_distribucion_severidad), pero muchos otros accesos ocurrian
FUERA de ese try y aterrizaban en el except generico de toda la funcion,
abortando la importacion COMPLETA -- incluso si el resto del archivo
(otros eventos validos, escenarios validos) era perfecto:

  - evento_data['freq_opcion'] accedido con [] directo, fuera del try.
  - escenario_data['eventos_riesgo'] accedido con [] directo.
  - vinculo['tipo'] accedido con [] directo al reconstruir vinculos.

El fix: (1) envuelve TODO el procesamiento de cada evento (no solo la
generacion de severidad) en un try/except que descarta SOLO ese evento;
(2) envuelve TODO el procesamiento de cada escenario en un try/except
que descarta SOLO ese escenario (revirtiendo cualquier escenario
parcialmente agregado); (3) usa vinculo.get('tipo', 'AND') en vez de
vinculo['tipo'] (mismo default que ya usan el motor y el export IA para
este campo opcional).

Este test verifica los 3 casos con un archivo JSON real:
  1. Un evento sin 'freq_opcion' junto a un evento válido: solo se
     descarta el evento roto, el válido se carga igual.
  2. Un escenario sin 'eventos_riesgo' junto a la simulación principal
     válida: el escenario roto se descarta, la simulación principal
     igual se carga.
  3. Un vínculo sin 'tipo': no crashea, se trata como 'AND' (default).
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

_criticals = []
QtWidgets.QMessageBox.critical = staticmethod(lambda parent, t, m, *a, **kw: (_criticals.append((t, m)), QtWidgets.QMessageBox.Ok)[1])
QtWidgets.QMessageBox.warning = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)


def _evento_base(id_, nombre, vinculos=None, **extra):
    ev = {
        "id": id_, "nombre": nombre, "activo": True,
        "sev_opcion": 2, "sev_input_method": "direct",
        "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
        "sev_params_direct": {"mean": 10000, "std": 1000},
        "freq_opcion": 1, "tasa": 3.0,
        "vinculos": vinculos or [], "factores_ajuste": [],
    }
    ev.update(extra)
    return ev


print("=" * 70)
print("BUG ALTO #16: aislamiento de errores por evento/escenario/vínculo en import JSON")
print("=" * 70)

evento_valido = _evento_base("evt-A", "Evento Válido")
evento_sin_freq_opcion = _evento_base("evt-B", "Evento Sin FreqOpcion")
del evento_sin_freq_opcion["freq_opcion"]

evento_con_vinculo_sin_tipo = _evento_base(
    "evt-C", "Evento Vínculo Sin Tipo",
    vinculos=[{"id_padre": "evt-A", "probabilidad": 100, "factor_severidad": 1.0, "umbral_severidad": 0}]
)

config = {
    "num_simulaciones": 5000,
    "eventos_riesgo": [evento_valido, evento_sin_freq_opcion, evento_con_vinculo_sin_tipo],
    "scenarios": [
        {"nombre": "EscenarioRoto"},  # sin 'eventos_riesgo'
    ],
}

tmp_path = os.path.join(_THIS_DIR, '_tmp_test_aislamiento_errores.json')
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config, f)

try:
    win = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    win.cargar_configuracion()

    check(len(_criticals) == 0,
          f"Bug alto #16: la carga NO aborta con un error crítico general "
          f"(obtenido: {_criticals})")

    nombres_cargados = [e.get('nombre') for e in win.eventos_riesgo]
    print(f"  eventos cargados: {nombres_cargados}")
    check('Evento Válido' in nombres_cargados,
          "El evento válido se carga correctamente")
    check('Evento Sin FreqOpcion' not in nombres_cargados,
          f"Bug alto #16: el evento SIN freq_opcion se descarta (no crashea toda "
          f"la carga) (obtenido: {nombres_cargados})")
    check('Evento Vínculo Sin Tipo' in nombres_cargados,
          f"Bug alto #16: el evento con un vínculo SIN 'tipo' se carga igual "
          f"(no crashea) (obtenido: {nombres_cargados})")

    evento_c = next((e for e in win.eventos_riesgo if e.get('nombre') == 'Evento Vínculo Sin Tipo'), None)
    if evento_c is not None:
        vinc = evento_c.get('vinculos', [{}])[0] if evento_c.get('vinculos') else {}
        check(vinc.get('tipo') == 'AND',
              f"Bug alto #16: el vínculo sin 'tipo' toma el default 'AND' "
              f"(obtenido: {vinc.get('tipo')!r})")

    check(win.scenarios == [] or 'EscenarioRoto' not in [s.nombre for s in win.scenarios],
          f"Bug alto #16: el escenario SIN 'eventos_riesgo' se descarta, no aborta "
          f"la carga de la simulación principal (obtenido escenarios: "
          f"{[s.nombre for s in win.scenarios]})")
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
