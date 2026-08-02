"""
test_guardar_evento_escenario_sin_duplicar_por_doble_click.py
==================================================================

Regresion para bug medio R4 #4 (QA ronda 4): guardar_evento() y
guardar_scenario() (los handlers conectados a la señal 'accepted' de los
QDialogButtonBox de "Agregar/Editar Evento" y "Agregar/Editar Escenario")
no tenían ninguna guardia de re-entrancy. Un doble-click (o Enter +
click casi simultáneos) sobre el botón Guardar puede disparar 'accepted'
dos veces antes de que el diálogo termine de cerrarse, ejecutando el
handler dos veces en secuencia:

- guardar_evento(): como 'new' sigue siendo True en ambas invocaciones y
  los nombres de evento NO se validan como únicos, la segunda invocación
  agrega el MISMO evento otra vez -- dos eventos idénticos en
  self.eventos_riesgo tras un solo click del usuario.
- guardar_scenario(): SÍ tiene una validación de nombre único (R3 medio
  #25), así que la segunda invocación no duplica el escenario -- pero
  falla con un mensaje de error confuso ("ya existe un escenario llamado
  'X'") para un usuario que solo hizo un click, ya que la primera
  invocación acaba de crear ese escenario exitosamente.

El fix guarda un flag en el propio objeto 'dialog' (persiste entre
llamadas sucesivas, ya que es el mismo objeto) para que solo la primera
invocación exitosa tenga efecto; cualquier invocación posterior es un
no-op inmediato.

Este test invoca guardar_evento()/guardar_scenario() DOS VECES seguidas
con los mismos argumentos (simulando la re-entrancy de un doble-click) y
verifica que:
1. Solo se agregue UN evento (no dos) a win.eventos_riesgo.
2. Solo se agregue UN escenario (no dos) a win.scenarios, y la segunda
   invocación NO dispare ningún QMessageBox.critical de "nombre
   duplicado" (ya que fue un no-op, no un intento real de duplicar).
"""
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
        self.accept_calls = 0

    def accept(self):
        self.accept_calls += 1


print("=" * 70)
print("BUG MEDIO R4 #4: doble-click en Guardar no debe duplicar evento/escenario")
print("=" * 70)

# --- Caso 1: guardar_evento invocado dos veces (simulando doble-click) ---
print("\n--- Caso 1: guardar_evento() x2 ---")
win = RLB.RiskLabApp()
win.eventos_riesgo = []

criticals = []
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: criticals.append(a) or QtWidgets.QMessageBox.Ok)

dialog = _FakeDialog()
kwargs = dict(
    nombre_var=_FakeText("EventoDobleClick"),
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
    freq_combobox=_FakeCombo(0, "Poisson"),
    tasa_var=_FakeText("5"),
    num_eventos_var=_FakeText(""),
    prob_exito_var=_FakeText(""),
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

# Simular el doble-click: invocar el handler DOS veces seguidas con el
# mismo dialog (idéntico a lo que ocurriría si 'accepted' se disparó dos
# veces antes de que el diálogo cerrara).
win.guardar_evento(dialog, True, None, **kwargs)
win.guardar_evento(dialog, True, None, **kwargs)

nombres_eventos = [e['nombre'] for e in win.eventos_riesgo]
print(f"  eventos tras invocar guardar_evento() dos veces: {nombres_eventos}")
check(len(win.eventos_riesgo) == 1,
      f"Bug medio R4 #4: solo se agrega UN evento pese a invocar guardar_evento() "
      f"dos veces seguidas (obtenido: {len(win.eventos_riesgo)} eventos)")
check(dialog.accept_calls == 1,
      f"dialog.accept() solo se llama una vez (obtenido: {dialog.accept_calls})")

# --- Caso 2: guardar_scenario invocado dos veces (simulando doble-click) ---
print("\n--- Caso 2: guardar_scenario() x2 ---")
win2 = RLB.RiskLabApp()
win2.scenarios = []
win2.eventos_scenario = []

criticals2 = []
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: criticals2.append(a) or QtWidgets.QMessageBox.Ok)

dialog2 = _FakeDialog()
nombre_var = _FakeText("EscenarioDobleClick")
descripcion_var = _FakeText("desc")

win2.guardar_scenario(dialog2, True, None, nombre_var, descripcion_var)
win2.guardar_scenario(dialog2, True, None, nombre_var, descripcion_var)

nombres_escenarios = [sc.nombre for sc in win2.scenarios]
print(f"  escenarios tras invocar guardar_scenario() dos veces: {nombres_escenarios}")
check(len(win2.scenarios) == 1,
      f"Bug medio R4 #4: solo se agrega UN escenario pese a invocar guardar_scenario() "
      f"dos veces seguidas (obtenido: {len(win2.scenarios)} escenarios)")
check(len(criticals2) == 0,
      f"Bug medio R4 #4: la segunda invocación (redundante) NO dispara un error de "
      f"'nombre duplicado' confuso para el usuario (obtenido: {len(criticals2)} diálogos)")
check(dialog2.accept_calls == 1,
      f"dialog.accept() solo se llama una vez (obtenido: {dialog2.accept_calls})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
