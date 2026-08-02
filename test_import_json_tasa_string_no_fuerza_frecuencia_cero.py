"""
test_import_json_tasa_string_no_fuerza_frecuencia_cero.py
=============================================================

Regresion para bug alto R4 #9 (QA ronda 4): cargar_configuracion casteaba
'tasa'/'num_eventos'/'prob_exito' a float/int SOLO en variables locales,
usadas exclusivamente para reconstruir el objeto dist_frecuencia cacheado
-- pero NUNCA escribia esos valores casteados de vuelta en evento_data.
Si el JSON traia estos campos como STRING (ej. "tasa": "6.0", algo que
ocurre con exportaciones de hojas de calculo o JSON editado a mano),
evento_data['tasa'] quedaba siendo un string en memoria para siempre.

dist_frecuencia (ya construido con el valor casteado) funciona bien para
un evento SIN factores estocasticos activos. Pero si el evento SI tiene
al menos un factor de ajuste con tipo_modelo='estocastico' (algo comun en
configuraciones de produccion), el motor usa
_samplear_frecuencia_estocastica_vec, que lee evento['tasa'] DIRECTAMENTE
del dict (sin castear) para escalar el lambda de Poisson:
`lambdas = tasa_original * factores_subset`. Multiplicar un string por un
array de numpy lanza un TypeError, capturado por el except generico de
generar_lda_con_secuencialidad, que fuerza la frecuencia de ESE evento a
0 para TODAS las simulaciones -- silenciosamente, en el sentido de que la
causa raiz (un JSON con tipos de datos inconsistentes) nunca se hace
evidente para el usuario.

El fix escribe 'tasa'/'num_eventos'/'prob_exito' YA CASTEADOS de vuelta en
evento_data, en las dos rutas de cargar_configuracion (eventos
principales y eventos de escenario).

Este test construye un JSON con un evento Poisson (tasa="6.0", como
STRING) que tiene un factor de ajuste estocastico activo (pero neutral:
confiabilidad=100%, reduccion_efectiva=0, reduccion_fallo=0, para que NO
cambie el resultado esperado -- solo fuerza el camino de codigo
_samplear_frecuencia_estocastica_vec). Carga el JSON via
cargar_configuracion() y verifica que:
1. win.eventos_riesgo[0]['tasa'] sea un float (no un string) tras cargar.
2. Correr generar_lda_con_secuencialidad sobre el evento cargado NO
   fuerce su frecuencia a 0 -- la frecuencia media observada debe
   acercarse a la tasa real (6.0), no colapsar a 0.0.
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
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)

print("=" * 70)
print("BUG ALTO R4 #9: JSON con 'tasa' como string no debe forzar frecuencia=0")
print("=" * 70)

TASA_REAL = 6.0

evento = {
    "id": "00000000-0000-0000-0000-000000000001",
    "nombre": "EventoTasaString",
    "activo": True,
    "sev_opcion": 1,
    "sev_input_method": "direct",
    "sev_minimo": None,
    "sev_mas_probable": None,
    "sev_maximo": None,
    "sev_params_direct": {"mean": 1000.0, "std": 10.0},
    "freq_opcion": 1,
    "tasa": str(TASA_REAL),  # <-- BUG: string en vez de número, como vendría de un import externo
    "num_eventos": None,
    "prob_exito": None,
    "pg_minimo": None, "pg_mas_probable": None, "pg_maximo": None, "pg_confianza": None,
    "pg_alpha": None, "pg_beta": None,
    "beta_minimo": None, "beta_mas_probable": None, "beta_maximo": None, "beta_confianza": None,
    "beta_alpha": None, "beta_beta": None,
    "sev_freq_activado": False,
    "sev_freq_modelo": "reincidencia",
    "sev_freq_tipo_escalamiento": "lineal",
    "sev_freq_paso": 0.5, "sev_freq_base": 1.5, "sev_freq_factor_max": 5.0,
    "sev_freq_tabla": [], "sev_freq_alpha": 0.5, "sev_freq_solo_aumento": True,
    "sev_freq_sistemico_factor_max": 3.0,
    "vinculos": [],
    "factores_ajuste": [
        {
            "nombre": "ControlNeutral",
            "tipo_modelo": "estocastico",
            "activo": True,
            "confiabilidad": 100,
            "reduccion_efectiva": 0,
            "reduccion_fallo": 0,
            "afecta_frecuencia": True,
        }
    ],
}

config = {
    "num_simulaciones": 5000,
    "eventos_riesgo": [evento],
    "scenarios": [],
    "current_scenario_name": None,
}

tmp_path = os.path.join(_THIS_DIR, '_tmp_test_tasa_string.json')
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config, f)

try:
    win = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    win.cargar_configuracion()

    check(len(win.eventos_riesgo) == 1, "El evento se cargó correctamente")

    tasa_cargada = win.eventos_riesgo[0].get('tasa')
    print(f"  tipo de evento_data['tasa'] tras cargar: {type(tasa_cargada).__name__} (valor: {tasa_cargada!r})")
    check(isinstance(tasa_cargada, float) and not isinstance(tasa_cargada, str),
          f"Bug alto R4 #9: evento_data['tasa'] queda como float tras cargar_configuracion, "
          f"no como el string original del JSON (obtenido: {type(tasa_cargada).__name__})")

    rng = np.random.default_rng(99)
    _, freq_tot, perd_evt, freq_evt = RLB.generar_lda_con_secuencialidad(
        win.eventos_riesgo, num_simulaciones=5000, rng=rng
    )
    freq_media_observada = float(freq_evt[0].mean())
    print(f"  frecuencia media observada tras simular: {freq_media_observada:.3f} (esperada ~{TASA_REAL})")
    check(freq_media_observada > TASA_REAL * 0.5,
          f"Bug alto R4 #9: la frecuencia del evento NO queda forzada a 0 pese al factor "
          f"estocástico activo y 'tasa' importada como string (obtenido: media="
          f"{freq_media_observada:.3f}; con el bug sería ~0.0)")
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
