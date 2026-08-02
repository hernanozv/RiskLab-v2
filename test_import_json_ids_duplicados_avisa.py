"""
test_import_json_ids_duplicados_avisa.py
============================================

Regresion para bug medio R4 #2 (QA ronda 4): tanto id_a_index (dentro
del motor de simulación, generar_lda_con_secuencialidad) como id_mapeo
(dentro de cargar_configuracion) resuelven eventos por su campo 'id'
usando un diccionario Python. Si el archivo JSON trae dos eventos con el
MISMO id (algo que solo puede ocurrir con un archivo editado a mano o
generado externamente, ya que la app siempre genera ids con uuid4), el
segundo evento pisa silenciosamente al primero en ese diccionario -- y
cualquier vínculo que apunte a ese id termina enlazado al evento
equivocado, sin ningún aviso al usuario.

El fix detecta ids duplicados ANTES de procesar el archivo (tanto en los
eventos principales como dentro de cada escenario, ya que cada lista es
su propio espacio de ids) y muestra un QMessageBox.warning explicando
cuáles ids están duplicados y con qué eventos, para que el usuario pueda
revisar y corregir el archivo.

Este test construye un JSON con dos eventos principales que comparten el
mismo 'id' (uno de ellos con un vínculo a un tercer evento) y verifica
que cargar_configuracion:
1. Muestre un QMessageBox.warning mencionando el id duplicado.
2. El mensaje incluya los nombres de ambos eventos involucrados.
3. Un archivo SIN ids duplicados NO dispare esta advertencia (caso
   negativo, para evitar falsos positivos).
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
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)


def _evento_base(id_, nombre, vinculos=None):
    return {
        "id": id_, "nombre": nombre, "activo": True,
        "sev_opcion": 1, "sev_input_method": "direct",
        "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
        "sev_params_direct": {"mean": 1000.0, "std": 10.0},
        "freq_opcion": 3, "tasa": None, "num_eventos": None, "prob_exito": 0.5,
        "pg_minimo": None, "pg_mas_probable": None, "pg_maximo": None, "pg_confianza": None,
        "pg_alpha": None, "pg_beta": None,
        "beta_minimo": None, "beta_mas_probable": None, "beta_maximo": None, "beta_confianza": None,
        "beta_alpha": None, "beta_beta": None,
        "sev_freq_activado": False, "sev_freq_modelo": "reincidencia",
        "sev_freq_tipo_escalamiento": "lineal", "sev_freq_paso": 0.5, "sev_freq_base": 1.5,
        "sev_freq_factor_max": 5.0, "sev_freq_tabla": [], "sev_freq_alpha": 0.5,
        "sev_freq_solo_aumento": True, "sev_freq_sistemico_factor_max": 3.0,
        "vinculos": vinculos or [],
        "factores_ajuste": [],
    }


print("=" * 70)
print("BUG MEDIO R4 #2: ids de evento duplicados en el JSON deben avisarse")
print("=" * 70)

# --- Caso 1: dos eventos principales con el MISMO id ---
print("\n--- Caso 1: id duplicado entre dos eventos principales ---")
ID_DUPLICADO = "id-repetido-0001"
config_con_duplicado = {
    "num_simulaciones": 5000,
    "eventos_riesgo": [
        _evento_base(ID_DUPLICADO, "EventoA_original"),
        _evento_base(ID_DUPLICADO, "EventoB_conflicto"),
    ],
    "scenarios": [],
    "current_scenario_name": None,
}

tmp_path = os.path.join(_THIS_DIR, '_tmp_test_ids_duplicados.json')
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config_con_duplicado, f)

try:
    win = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    warnings_capturados = []
    QtWidgets.QMessageBox.warning = staticmethod(
        lambda *a, **kw: warnings_capturados.append(a) or QtWidgets.QMessageBox.Ok
    )

    win.cargar_configuracion()

    check(len(win.eventos_riesgo) == 2, "Ambos eventos se cargaron (cada uno con un id nuevo)")

    texto_completo = " ".join(str(a) for a in warnings_capturados)
    check('duplicad' in texto_completo.lower(),
          f"Bug medio R4 #2: se muestra un aviso mencionando ids duplicados "
          f"(obtenido: {len(warnings_capturados)} avisos)")
    check('EventoA_original' in texto_completo and 'EventoB_conflicto' in texto_completo,
          "El aviso incluye los nombres de AMBOS eventos involucrados en el conflicto")
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

# --- Caso 2: sin ids duplicados, no debe dispararse el aviso ---
print("\n--- Caso 2: sin ids duplicados (caso negativo) ---")
config_sin_duplicado = {
    "num_simulaciones": 5000,
    "eventos_riesgo": [
        _evento_base("id-unico-0001", "EventoA"),
        _evento_base("id-unico-0002", "EventoB"),
    ],
    "scenarios": [],
    "current_scenario_name": None,
}
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config_sin_duplicado, f)

try:
    win2 = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    warnings_negativo = []
    QtWidgets.QMessageBox.warning = staticmethod(
        lambda *a, **kw: warnings_negativo.append(a) or QtWidgets.QMessageBox.Ok
    )

    win2.cargar_configuracion()

    texto_negativo = " ".join(str(a) for a in warnings_negativo)
    check('duplicad' not in texto_negativo.lower(),
          f"Un archivo SIN ids duplicados no dispara el aviso de duplicados "
          f"(obtenido: {len(warnings_negativo)} avisos: {texto_negativo[:150]!r})")
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
