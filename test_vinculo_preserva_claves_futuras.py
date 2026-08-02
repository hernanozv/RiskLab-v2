"""
test_vinculo_preserva_claves_futuras.py
==========================================

Regresion para hallazgo bajo #4: al reconstruir los vínculos durante el
import de configuración JSON (cargar_configuracion), el código armaba un
dict COMPLETAMENTE NUEVO con exactamente 5 claves fijas
(id_padre, tipo, probabilidad, factor_severidad, umbral_severidad),
descartando silenciosamente cualquier otra clave que el vínculo original
pudiera traer — ya sea metadata de una versión futura del esquema, o
cualquier campo agregado por otra herramienta que genere el JSON.

El fix parte de una COPIA del vínculo original (preservando cualquier
clave desconocida) y solo actualiza encima las 5 claves conocidas/
validadas, tanto para la lista principal de eventos como para los eventos
de escenario.

Este test instancia RiskLabApp de verdad (headless) y carga un archivo
JSON cuyo vínculo trae claves adicionales no reconocidas por el esquema
actual, verificando que sobreviven al round-trip de import — tanto en la
lista principal como en un escenario.
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


def _evento_base(id_, nombre, vinculos=None):
    return {
        "id": id_, "nombre": nombre, "activo": True,
        "sev_opcion": 2, "sev_input_method": "direct",
        "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
        "sev_params_direct": {"mean": 1000, "std": 100},
        "freq_opcion": 1, "tasa": 3.0,
        "vinculos": vinculos or [],
        "factores_ajuste": [],
    }


VINCULO_CON_CLAVES_FUTURAS = {
    "id_padre": "evt-A", "tipo": "AND",
    "probabilidad": 100, "factor_severidad": 1.0, "umbral_severidad": 0,
    "campo_futuro_desconocido": "valor_importante",
    "otra_clave_de_una_version_mas_nueva": 42,
}


print("=" * 70)
print("Hallazgo bajo #4: preservar claves desconocidas de vínculos al importar")
print("=" * 70)

config = {
    "num_simulaciones": 5000,
    "eventos_riesgo": [
        _evento_base("evt-A", "Evento A (root)"),
        _evento_base("evt-B", "Evento B (vinculo con claves futuras)",
                     vinculos=[dict(VINCULO_CON_CLAVES_FUTURAS)]),
    ],
    "scenarios": [
        {
            "nombre": "EscenarioTest", "descripcion": "desc",
            "eventos_riesgo": [
                _evento_base("evt-C", "Evento C escenario (root)"),
                _evento_base("evt-D", "Evento D escenario (vinculo con claves futuras)",
                             vinculos=[{**VINCULO_CON_CLAVES_FUTURAS, "id_padre": "evt-C"}]),
            ],
        }
    ],
}

tmp_path = os.path.join(_THIS_DIR, '_tmp_vinculo_claves_futuras.json')
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(config, f)

try:
    win = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    win.cargar_configuracion()

    evento_b = next(e for e in win.eventos_riesgo if e['nombre'] == 'Evento B (vinculo con claves futuras)')
    vinculo_b = evento_b['vinculos'][0]

    check(vinculo_b.get('campo_futuro_desconocido') == 'valor_importante',
          "Lista principal: clave desconocida 'campo_futuro_desconocido' sobrevive al import")
    check(vinculo_b.get('otra_clave_de_una_version_mas_nueva') == 42,
          "Lista principal: clave desconocida 'otra_clave_de_una_version_mas_nueva' sobrevive al import")
    check(vinculo_b.get('tipo') == 'AND' and vinculo_b.get('probabilidad') == 100,
          "Lista principal: las claves conocidas/validadas siguen presentes y correctas")

    escenario = next(s for s in win.scenarios if s.nombre == 'EscenarioTest')
    evento_d = next(e for e in escenario.eventos_riesgo if e['nombre'] == 'Evento D escenario (vinculo con claves futuras)')
    vinculo_d = evento_d['vinculos'][0]

    check(vinculo_d.get('campo_futuro_desconocido') == 'valor_importante',
          "Escenario: clave desconocida 'campo_futuro_desconocido' sobrevive al import")
    check(vinculo_d.get('otra_clave_de_una_version_mas_nueva') == 42,
          "Escenario: clave desconocida 'otra_clave_de_una_version_mas_nueva' sobrevive al import")
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
