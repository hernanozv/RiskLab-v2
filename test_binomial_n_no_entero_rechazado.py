"""
test_binomial_n_no_entero_rechazado.py
==========================================

Regresion para bug medio R4 #3 (QA ronda 4): tanto guardar_evento()
(diálogo "Agregar/Editar Evento de Riesgo") como el diálogo de edición
rápida usan `int(float(texto))` para parsear "n" (número de eventos
posibles) en la distribución Binomial. Ese patrón fue introducido a
propósito en R2 bajo #22 para manejar bien texto como "5.0" (evita que
int("5.0") lance ValueError) -- pero como efecto secundario, TRUNCA en
silencio cualquier valor genuinamente fraccionario: "10.7" se convertía
en 10 sin ningún aviso ni error, aunque "n" es un conteo de ensayos y
debe ser un entero exacto.

El fix valida explícitamente que el valor parseado como float sea (casi)
igual a su propio redondeo antes de truncar, y si no lo es, lanza un
ValueError pidiendo un número entero -- preservando el comportamiento
correcto para "5.0" (sigue funcionando) pero rechazando "10.7" en vez de
aceptarlo silenciosamente.

Este test llama win.guardar_evento(...) DIRECTAMENTE con objetos "fake"
que imitan la interfaz mínima de los widgets Qt reales (.text(),
.currentIndex(), .currentText()), simulando un evento Binomial con
n="10.7", y verifica que:
1. Se muestre un QMessageBox.critical explicando que "n" debe ser entero.
2. El evento NO se agregue a win.eventos_riesgo.
3. Un valor "10.0" (equivalente a un entero, formateado como float)
   SIGA funcionando correctamente (caso negativo, preserva R2 bajo #22).
"""
import os
import sys
import uuid

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


class _FakeText:
    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text


class _FakeCombo:
    def __init__(self, index=0, text=""):
        self._index = index
        self._text = text

    def currentIndex(self):
        return self._index

    def currentText(self):
        return self._text


class _FakeDialog:
    def __init__(self):
        self.accepted = False

    def accept(self):
        self.accepted = True


def _construir_kwargs_evento(nombre="EventoBinomialTest", num_eventos_texto="10.7", prob_exito_texto="0.5"):
    return dict(
        nombre_var=_FakeText(nombre),
        sev_combobox=_FakeCombo(0, "Normal"),
        sev_input_method_combo=_FakeCombo(0, ""),
        sev_min_var=_FakeText("100"),
        sev_mas_probable_var=_FakeText("500"),
        sev_max_var=_FakeText("1000"),
        sev_norm_mean_var=_FakeText(""),
        sev_norm_std_var=_FakeText(""),
        sev_ln_param_mode_combo=_FakeCombo(0, ""),
        sev_ln_s_var=_FakeText(""),
        sev_ln_scale_var=_FakeText(""),
        sev_ln_mean_var=_FakeText(""),
        sev_ln_std_var=_FakeText(""),
        sev_ln_mu_var=_FakeText(""),
        sev_ln_sigma_var=_FakeText(""),
        sev_ln_loc_var=_FakeText(""),
        sev_gpd_c_var=_FakeText(""),
        sev_gpd_scale_var=_FakeText(""),
        sev_gpd_loc_var=_FakeText(""),
        freq_combobox=_FakeCombo(1, "Binomial"),  # freq_opcion = index+1 = 2
        tasa_var=_FakeText(""),
        num_eventos_var=_FakeText(num_eventos_texto),
        prob_exito_var=_FakeText(prob_exito_texto),
        prob_exito_var_bern=_FakeText(""),
        pg_minimo_var=_FakeText(""),
        pg_mas_probable_var=_FakeText(""),
        pg_maximo_var=_FakeText(""),
        pg_confianza_var=_FakeText(""),
        beta_minimo_var=_FakeText(""),
        beta_mas_probable_var=_FakeText(""),
        beta_maximo_var=_FakeText(""),
        beta_confianza_var=_FakeText(""),
        vinculos_existentes=[],
        factores_ajuste_existentes=[],
        sev_freq_config=None,
        sev_limite_var=_FakeText(""),
        freq_limite_var=_FakeText(""),
    )


print("=" * 70)
print("BUG MEDIO R4 #3: 'n' fraccionario en Binomial debe rechazarse, no truncarse")
print("=" * 70)

# --- Caso 1: n fraccionario (10.7) debe rechazarse ---
print("\n--- Caso 1: n='10.7' (fraccionario) ---")
win = RLB.RiskLabApp()
win.eventos_riesgo = []

criticals = []
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: criticals.append(a) or QtWidgets.QMessageBox.Ok)

dialog = _FakeDialog()
kwargs = _construir_kwargs_evento(num_eventos_texto="10.7")
win.guardar_evento(dialog, True, None, **kwargs)

texto_criticals = " ".join(str(a) for a in criticals)
check(len(criticals) >= 1,
      f"Bug medio R4 #3: se muestra un error al guardar Binomial con n='10.7' "
      f"(obtenido: {len(criticals)} diálogos)")
check('entero' in texto_criticals.lower(),
      f"El mensaje de error menciona que 'n' debe ser un número entero "
      f"(obtenido: {texto_criticals[:200]!r})")
check(len(win.eventos_riesgo) == 0,
      f"Bug medio R4 #3: el evento NO se agrega con n fraccionario "
      f"(obtenido: {len(win.eventos_riesgo)} eventos)")
check(not dialog.accepted, "El diálogo no se cierra con 'accept' (el error impide guardar)")

# --- Caso 2: n="10.0" (entero formateado como float) sigue funcionando ---
print("\n--- Caso 2: n='10.0' (entero, caso negativo -- preserva R2 bajo #22) ---")
win2 = RLB.RiskLabApp()
win2.eventos_riesgo = []
criticals2 = []
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: criticals2.append(a) or QtWidgets.QMessageBox.Ok)

dialog2 = _FakeDialog()
kwargs2 = _construir_kwargs_evento(nombre="EventoBinomialValido", num_eventos_texto="10.0")
win2.guardar_evento(dialog2, True, None, **kwargs2)

check(len(criticals2) == 0,
      f"n='10.0' (entero formateado como float) NO dispara ningún error "
      f"(obtenido: {len(criticals2)} diálogos: {[str(a) for a in criticals2]})")
check(len(win2.eventos_riesgo) == 1 and win2.eventos_riesgo[0].get('num_eventos') == 10,
      f"El evento se guarda correctamente con num_eventos=10 (obtenido: "
      f"{len(win2.eventos_riesgo)} eventos, "
      f"num_eventos={win2.eventos_riesgo[0].get('num_eventos') if win2.eventos_riesgo else 'N/A'})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
