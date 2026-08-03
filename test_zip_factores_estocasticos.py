"""
test_zip_factores_estocasticos.py
===================================

Feature: la Zero-Inflated Poisson (freq_opcion=6) soporta factores de
ajuste estocásticos en el muestreo vectorizado
(_samplear_frecuencia_estocastica_vec). El factor escala λ de forma
multiplicativa (igual que Poisson), mientras que π (prob. de cero
estructural) se mantiene fijo.

Verifica que un evento ZIP con un factor estocástico que REDUCE la
frecuencia:
1. Corre la simulación sin errores (no cae al fallback de frecuencia=0).
2. Produce una frecuencia media menor que la del mismo evento sin el
   factor (λ efectivamente escalado hacia abajo).
3. Mantiene el exceso de ceros estructural (π sin cambios): la fracción de
   años en cero sigue siendo al menos π.
"""
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

print("=" * 70)
print("FEATURE: ZIP soporta factores de ajuste estocásticos (escala λ, π fijo)")
print("=" * 70)

PI, LAM = 0.5, 6.0


def _evento_zip(nombre, factores):
    ev = {
        "id": nombre, "nombre": nombre, "activo": True,
        "sev_opcion": 1, "sev_input_method": "direct",
        "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
        "sev_params_direct": {"mean": 1000.0, "std": 10.0}, "sev_limite_superior": None,
        "freq_opcion": 6, "zip_pi": PI, "zip_lambda": LAM,
        "tasa": None, "num_eventos": None, "prob_exito": None,
        "vinculos": [], "factores_ajuste": factores,
    }
    ev['dist_severidad'] = RLB.generar_distribucion_severidad(
        1, None, None, None, input_method='direct', params_direct={"mean": 1000.0, "std": 10.0})
    ev['dist_frecuencia'] = RLB.generar_distribucion_frecuencia(6, zip_params=(PI, LAM))
    return ev


# Factor estocástico que reduce la frecuencia de forma notable
factor_reductor = {
    "nombre": "ControlFuerte",
    "tipo_modelo": "estocastico",
    "activo": True,
    "confiabilidad": 100,
    "reduccion_efectiva": 60,   # -60% cuando el control funciona
    "reduccion_fallo": 60,
    "afecta_frecuencia": True,
}

ev_sin = _evento_zip("ZIP_sin_factor", [])
ev_con = _evento_zip("ZIP_con_factor", [factor_reductor])

rng1 = np.random.default_rng(123)
res_sin = RLB.generar_lda_con_secuencialidad([ev_sin], num_simulaciones=20000, rng=rng1)
rng2 = np.random.default_rng(123)
res_con = RLB.generar_lda_con_secuencialidad([ev_con], num_simulaciones=20000, rng=rng2)

freq_sin = np.asarray(res_sin[3][0])
freq_con = np.asarray(res_con[3][0])

media_sin = float(freq_sin.mean())
media_con = float(freq_con.mean())
print(f"  frecuencia media sin factor: {media_sin:.3f} (esperada ~{(1-PI)*LAM:.2f})")
print(f"  frecuencia media con factor reductor: {media_con:.3f}")

check(media_sin > (1 - PI) * LAM * 0.8,
      f"sin factor: frecuencia media coherente con (1-π)·λ={(1-PI)*LAM:.2f} (obtenido {media_sin:.3f}); "
      f"no colapsó a 0")
check(media_con < media_sin * 0.85,
      f"con factor reductor: frecuencia media claramente menor (λ escalado hacia abajo) "
      f"({media_con:.3f} < {media_sin:.3f})")
check(media_con > 0.1,
      f"con factor: la frecuencia NO se fuerza a 0 por error (obtenido {media_con:.3f})")

frac_ceros_con = float((freq_con == 0).mean())
check(frac_ceros_con >= PI - 0.02,
      f"con factor: se preserva el exceso de ceros estructural π={PI} "
      f"(fracción ceros observada {frac_ceros_con:.3f})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
