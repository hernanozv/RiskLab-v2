"""
test_vinculo_huerfano_import.py
=================================

Regresion para bug #28: cargar_configuracion (import de JSON) aceptaba
vinculos[].id_padre apuntando a un ID que no corresponde a ningún evento
del archivo, sin ningún aviso al usuario. El evento hijo se cargaba
correctamente, pero el vínculo quedaba con un ID que no existe en el
diccionario de eventos remapeados, y el motor de simulación lo ignora en
silencio (ver generar_lda_con_secuencialidad, "Vínculo ignorado: id_padre
no encontrado en id_a_index") — el evento termina comportándose como
independiente sin que el usuario se entere de que su configuración de
dependencias no se restauró como esperaba.

Este test instancia RiskLabApp de verdad (headless) y ejecuta
cargar_configuracion() sobre un archivo JSON real con un vínculo hacia un
ID inexistente, verificando que ahora se muestra un aviso explícito.
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


def _fake_question(*a, **kw):
    return QtWidgets.QMessageBox.Yes


QtWidgets.QMessageBox.warning = staticmethod(_fake_warning)
QtWidgets.QMessageBox.critical = staticmethod(_fake_critical)
QtWidgets.QMessageBox.question = staticmethod(_fake_question)


def _evento_base(id_, nombre, vinculos=None):
    return {
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
        "vinculos": vinculos or [],
        "factores_ajuste": [],
    }


print("=" * 70)
print("BUG #28: Vínculo con id_padre inexistente en import JSON")
print("=" * 70)

config = {
    "num_simulaciones": 10000,
    "eventos_riesgo": [
        _evento_base("evt-A", "Evento A (root, sin vinculos)"),
        _evento_base("evt-B", "Evento B (vinculo huérfano)", vinculos=[
            {"id_padre": "id-que-no-existe-en-el-archivo", "tipo": "AND",
             "probabilidad": 100, "factor_severidad": 1.0, "umbral_severidad": 0}
        ]),
    ],
    "scenarios": [],
}

tmp_path = os.path.join(_THIS_DIR, '_tmp_test_vinculo_huerfano.json')
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config, f)

try:
    win = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))

    win.cargar_configuracion()

    check(len(_criticals_mostrados) == 0,
          f"La carga no dispara ningún diálogo de error crítico (obtenido: {_criticals_mostrados})")
    check(len(win.eventos_riesgo) == 2,
          "Ambos eventos se cargan correctamente (el vínculo huérfano no descarta el evento)")

    check(len(_warnings_mostrados) >= 1,
          "Bug #28: se muestra al menos un aviso al usuario sobre el vínculo huérfano")
    if _warnings_mostrados:
        titulos = [t for t, _ in _warnings_mostrados]
        textos = " ".join(t for _, t in _warnings_mostrados)
        check(any("vínculo" in t.lower() or "vinculo" in t.lower() for t in titulos),
              f"El título del aviso menciona vínculos (obtenido: {titulos})")
        check("Evento B" in textos,
              "El aviso identifica el evento afectado (Evento B)")
        check("id-que-no-existe-en-el-archivo" in textos,
              "El aviso menciona el ID huérfano concreto")

    # El evento B debe seguir teniendo su vinculo (con el ID viejo, sin
    # remapear), que el motor de simulacion ignora de forma segura (no
    # rompe tiene_ciclo ni la simulacion).
    evento_b = next(e for e in win.eventos_riesgo if e['nombre'] == 'Evento B (vinculo huérfano)')
    check(len(evento_b.get('vinculos', [])) == 1,
          "El vínculo huérfano se conserva en el dict del evento (no crashea, el motor lo ignora)")
    check(win.tiene_ciclo(win.eventos_riesgo) is False,
          "tiene_ciclo() no falla ni detecta un falso ciclo por la referencia colgante")
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
