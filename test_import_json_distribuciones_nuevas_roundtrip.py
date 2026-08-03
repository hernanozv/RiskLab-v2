"""
test_import_json_distribuciones_nuevas_roundtrip.py
=====================================================

Feature: persistencia JSON de las 4 nuevas distribuciones (Burr XII sev=6,
Weibull sev=7, Log-t sev=8, Zero-Inflated Poisson freq=6).

Las severidades nuevas guardan sus parámetros en 'sev_params_direct' (que
cargar_configuracion ya lee genéricamente); ZIP usa campos propios
'zip_pi'/'zip_lambda' que requieren ramas de carga dedicadas en AMBOS
loops (eventos principales y eventos de escenario).

Verifica que un JSON con estas distribuciones (en un evento principal y en
un evento de escenario) se importa vía cargar_configuracion() y:
1. Reconstruye el objeto de distribución correcto (TruncatedBurr /
   weibull_min congelado / LogTDistribution / ZeroInflatedPoissonDistribution).
2. Preserva los parámetros exactos (incluyendo zip_pi/zip_lambda casteados
   a float aunque vengan como string en el JSON).
3. La simulación corre end-to-end produciendo pérdidas finitas no negativas.
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


app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
QtWidgets.QMessageBox.warning = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.information = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)

print("=" * 70)
print("FEATURE: round-trip JSON de las 4 distribuciones nuevas (main + escenario)")
print("=" * 70)


def _evento(nombre, id_, sev_opcion, sev_params, freq_opcion, freq_extra):
    ev = {
        "id": id_, "nombre": nombre, "activo": True,
        "sev_opcion": sev_opcion, "sev_input_method": "direct",
        "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
        "sev_params_direct": sev_params, "sev_limite_superior": None,
        "freq_opcion": freq_opcion,
        "tasa": None, "num_eventos": None, "prob_exito": None,
        "vinculos": [], "factores_ajuste": [],
    }
    ev.update(freq_extra)
    return ev


# Evento principal: Burr severidad + ZIP frecuencia (zip como STRING para probar casteo)
ev_main = _evento("BurrZIP", "id-main-1", 6, {"c": 2.0, "d": 1.5, "scale": 1_000_000, "loc": 0},
                  6, {"zip_pi": "0.6", "zip_lambda": "3.0"})
# Evento principal: Log-t severidad + Poisson
ev_main2 = _evento("LogtPoisson", "id-main-2", 8, {"df": 4, "mu": 13.0, "sigma": 0.7, "loc": 0},
                   1, {"tasa": 2.0})

# Evento de escenario: Weibull severidad + ZIP frecuencia
ev_esc = _evento("WeibullZIP", "id-esc-1", 7, {"c": 1.5, "scale": 500_000, "loc": 0},
                 6, {"zip_pi": 0.5, "zip_lambda": 2.5})

config = {
    "num_simulaciones": 4000,
    "eventos_riesgo": [ev_main, ev_main2],
    "scenarios": [
        {"nombre": "EscenarioNuevo", "descripcion": "x", "eventos_riesgo": [ev_esc]}
    ],
    "current_scenario_name": None,
}

tmp_path = os.path.join(_THIS_DIR, '_tmp_dist_nuevas.json')
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config, f)

try:
    win = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    win.cargar_configuracion()

    loaded = {e['nombre']: e for e in win.eventos_riesgo}
    check(set(loaded.keys()) == {"BurrZIP", "LogtPoisson"}, "Se cargaron los 2 eventos principales")

    b = loaded["BurrZIP"]
    check(type(b['dist_severidad']).__name__ == 'TruncatedBurr',
          f"Burr reconstruida como TruncatedBurr (obtenido {type(b['dist_severidad']).__name__})")
    check(type(b['dist_frecuencia']).__name__ == 'ZeroInflatedPoissonDistribution',
          f"ZIP reconstruida (obtenido {type(b['dist_frecuencia']).__name__})")
    check(isinstance(b.get('zip_pi'), float) and b['zip_pi'] == 0.6,
          f"zip_pi casteado a float 0.6 (obtenido {b.get('zip_pi')!r})")
    check(isinstance(b.get('zip_lambda'), float) and b['zip_lambda'] == 3.0,
          f"zip_lambda casteado a float 3.0 (obtenido {b.get('zip_lambda')!r})")
    check(b['sev_params_direct'].get('c') == 2.0 and b['sev_params_direct'].get('d') == 1.5,
          "params Burr preservados en sev_params_direct")

    lt = loaded["LogtPoisson"]
    check(type(lt['dist_severidad']).__name__ == 'LogTDistribution',
          f"Log-t reconstruida (obtenido {type(lt['dist_severidad']).__name__})")

    # Evento de escenario
    esc = win.scenarios[0]
    ev_e = esc.eventos_riesgo[0]
    check('frozen' in type(ev_e['dist_severidad']).__name__.lower(),
          f"Weibull de escenario reconstruida como distribución scipy congelada "
          f"(obtenido {type(ev_e['dist_severidad']).__name__})")
    check(type(ev_e['dist_frecuencia']).__name__ == 'ZeroInflatedPoissonDistribution',
          f"ZIP de escenario reconstruida (obtenido {type(ev_e['dist_frecuencia']).__name__})")
    check(isinstance(ev_e.get('zip_pi'), float) and ev_e['zip_pi'] == 0.5,
          f"zip_pi de escenario correcto (obtenido {ev_e.get('zip_pi')!r})")

    # Simulación end-to-end sobre eventos principales
    rng = np.random.default_rng(11)
    res = RLB.generar_lda_con_secuencialidad(win.eventos_riesgo, num_simulaciones=4000, rng=rng)
    perd = np.asarray(res[0])
    check(perd.shape == (4000,) and np.isfinite(perd).all() and (perd >= 0).all(),
          f"simulación produce pérdidas finitas no negativas (mean={perd.mean():.3e})")
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
