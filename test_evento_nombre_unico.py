"""
test_evento_nombre_unico.py
==============================

Regresion para bug medio R4 #8 (QA ronda 4): a diferencia de los
escenarios (validados como únicos desde R3 medio #25), guardar_evento()
nunca validaba que el nombre de un evento fuera único, y duplicar_eventos()
tampoco garantizaba nombres únicos al agregar "(Copia)". Muchos reportes
y el export IA (tornado, contribución al total, resumen ejecutivo,
risk_map) identifican eventos por NOMBRE al mostrarlos a un usuario o a
un agente IA -- con dos eventos "Fraude" distintos (pero con 'id'
diferentes), un lector no puede saber cuál de los dos contribuyó qué.

El fix agrega:
1. En guardar_evento(): la misma validación de nombre único ya usada
   para escenarios (guardar_scenario, R3 medio #25).
2. En duplicar_eventos(): la misma búsqueda de nombre único ya usada
   para duplicar_scenario (R4 alto #6) -- "X (Copia)", "X (Copia) 2", etc.

Este test verifica que:
1. guardar_evento() rechaza un nombre que ya existe en otro evento (con
   un mensaje claro), y NO rechaza el mismo nombre al EDITAR ese mismo
   evento (caso negativo: no debe auto-rechazarse a sí mismo).
2. duplicar_eventos() invocado dos veces sobre el mismo evento produce
   dos copias con nombres DISTINTOS, no el mismo nombre repetido.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

from PyQt5 import QtCore, QtWidgets

import Risk_Lab_Beta as RLB


def _seleccionar_fila(tabla, row):
    """Selecciona una fila vía el selection model directamente (más
    confiable que .selectRow() en modo offscreen/headless tras
    insertRow(), donde la selección visual puede no reflejarse)."""
    sm = tabla.selectionModel()
    sm.clearSelection()
    sm.select(
        tabla.model().index(row, 0),
        QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows
    )

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
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)


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


def _kwargs_evento(nombre):
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


print("=" * 70)
print("BUG MEDIO R4 #8: eventos con el mismo nombre deben rechazarse/desambiguarse")
print("=" * 70)

# --- Caso 1: guardar_evento rechaza nombre duplicado ---
print("\n--- Caso 1: guardar_evento() rechaza un nombre ya usado ---")
win = RLB.RiskLabApp()
win.eventos_riesgo = []

criticals = []
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: criticals.append(a) or QtWidgets.QMessageBox.Ok)

win.guardar_evento(_FakeDialog(), True, None, **_kwargs_evento("EventoA"))
check(len(win.eventos_riesgo) == 1, "Primer evento 'EventoA' se guarda sin problema")

dialog2 = _FakeDialog()
win.guardar_evento(dialog2, True, None, **_kwargs_evento("EventoA"))

check(len(win.eventos_riesgo) == 1,
      f"Bug medio R4 #8: un segundo evento con el mismo nombre 'EventoA' NO se agrega "
      f"(obtenido: {len(win.eventos_riesgo)} eventos)")
check(len(criticals) >= 1 and 'nombre único' in str(criticals[-1]).lower(),
      f"Se muestra un error explicando que el nombre ya existe (obtenido: {criticals[-1:] if criticals else []})")

# --- Caso 2: editar un evento con su PROPIO nombre no debe fallar ---
print("\n--- Caso 2: editar un evento con su propio nombre (caso negativo) ---")
criticals.clear()
dialog3 = _FakeDialog()
win.guardar_evento(dialog3, False, 0, **_kwargs_evento("EventoA"))
check(len(criticals) == 0,
      f"Editar 'EventoA' manteniendo su propio nombre no dispara el error de duplicado "
      f"(obtenido: {len(criticals)} errores)")
check(dialog3.accepted, "La edición se acepta correctamente")

# --- Caso 3: duplicar_eventos() dos veces produce nombres distintos ---
print("\n--- Caso 3: duplicar_eventos() x2 produce nombres únicos ---")
win2 = RLB.RiskLabApp()
win2.eventos_riesgo = [
    {'id': 'e1', 'nombre': 'Base', 'activo': True, 'vinculos': []}
]
win2.eventos_table.setRowCount(1)
win2.eventos_table.setItem(0, 1, QtWidgets.QTableWidgetItem('Base'))
win2.actualizar_vista_eventos()
_seleccionar_fila(win2.eventos_table, 0)
win2.duplicar_eventos()

_seleccionar_fila(win2.eventos_table, 0)
win2.duplicar_eventos()

nombres = [e['nombre'] for e in win2.eventos_riesgo]
print(f"  eventos tras duplicar 'Base' dos veces: {nombres}")
check(len(win2.eventos_riesgo) == 3, "Se crearon 3 eventos en total (1 original + 2 copias)")
check(len(nombres) == len(set(nombres)),
      f"Bug medio R4 #8: no hay dos eventos con el mismo nombre tras duplicar dos veces "
      f"(obtenido: {nombres})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
