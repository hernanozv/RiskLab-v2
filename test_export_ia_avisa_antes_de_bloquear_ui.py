"""
test_export_ia_avisa_antes_de_bloquear_ui.py
================================================

Regresion para bug medio R4 #5 (QA ronda 4): exportar_para_ia() llama a
_construir_export_payload_ia() y _escribir_export_json() de forma
SÍNCRONA en el hilo principal -- a diferencia de ejecutar_simulacion()
(que usa un QThread), no hay ningún mecanismo de background aquí. Con
"incluir arrays raw" activado, la interfaz queda sin responder durante
toda la generación, y convertir los arrays numpy a listas de Python
nativas (necesario para serializar a JSON) puede usar varias veces la
memoria del tamaño final del archivo -- sin ningún aviso previo al
usuario, que solo ve la app "colgada" sin explicación.

El fix agrega un aviso explícito (QMessageBox.question) ANTES de iniciar
el trabajo pesado, cuando el usuario activó "incluir arrays raw" y el
tamaño estimado supera un umbral (50 MB): explica que la UI quedará sin
responder y que la memoria usada puede ser varias veces mayor al tamaño
final, dándole la oportunidad de cancelar. También fuerza
QApplication.processEvents() tras activar el cursor de espera, para que
al menos el indicio visual de "ocupado" llegue a pintarse antes de
bloquear el hilo principal.

Este test mockea _dialogo_export_ia, _construir_export_payload_ia y
_escribir_export_json (evitando construir un export real) y verifica:
1. Con incluir_raw_arrays=True y mb_raw_estimado grande (100 MB): se
   muestra el aviso, y si el usuario responde "No", NI
   _construir_export_payload_ia NI _escribir_export_json se llegan a
   invocar (la exportación se cancela sin hacer el trabajo pesado).
2. Con el mismo escenario pero respondiendo "Sí": el export SÍ procede
   (_construir_export_payload_ia se invoca).
3. Con incluir_raw_arrays=False (o tamaño pequeño): NO se muestra
   ningún aviso, y el export procede directo (caso negativo).
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
QtWidgets.QMessageBox.information = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Ok)
QtWidgets.QFileDialog.getSaveFileName = staticmethod(lambda *a, **kw: ("/tmp/_fake_export_ia.json", ""))

print("=" * 70)
print("BUG MEDIO R4 #5: exportar_para_ia debe avisar antes de bloquear la UI")
print("=" * 70)


def _preparar_win():
    win = RLB.RiskLabApp()
    win.resultados_simulacion = {
        'perdidas_totales': [0.0],
        'frecuencias_totales': [0],
        'perdidas_por_evento': [],
        'frecuencias_por_evento': [],
        'eventos_riesgo': [],
    }
    llamadas = {'payload': 0, 'escribir': 0}
    win._construir_export_payload_ia = lambda opciones: (llamadas.__setitem__('payload', llamadas['payload'] + 1) or {})
    win._escribir_export_json = lambda filepath, payload, comprimir=False: llamadas.__setitem__('escribir', llamadas['escribir'] + 1)
    return win, llamadas


# --- Caso 1: raw grande + usuario cancela ---
print("\n--- Caso 1: incluir_raw_arrays=True, 100 MB, usuario responde No ---")
win1, llamadas1 = _preparar_win()
win1._dialogo_export_ia = lambda: {
    "incluir_resumen_ejecutivo": True, "incluir_estadisticas": True,
    "incluir_histogramas": True, "incluir_por_evento": True,
    "incluir_contribucion_marginal": True, "incluir_text_snapshot": True,
    "incluir_raw_arrays": True, "comprimir": False,
    "mb_raw_estimado": 100.0,
}
preguntas1 = []
QtWidgets.QMessageBox.question = staticmethod(
    lambda *a, **kw: preguntas1.append(a) or QtWidgets.QMessageBox.No
)

win1.exportar_para_ia()

texto1 = " ".join(str(a) for a in preguntas1)
check(len(preguntas1) >= 1,
      f"Bug medio R4 #5: se muestra un aviso antes de iniciar una exportación grande "
      f"(obtenido: {len(preguntas1)} preguntas)")
check('sin responder' in texto1.lower() or 'responder' in texto1.lower(),
      f"El aviso menciona que la UI quedará sin responder (obtenido: {texto1[:200]!r})")
check(llamadas1['payload'] == 0 and llamadas1['escribir'] == 0,
      f"Bug medio R4 #5: si el usuario cancela, NO se construye el payload ni se "
      f"escribe el archivo (obtenido: payload={llamadas1['payload']}, escribir={llamadas1['escribir']})")

# --- Caso 2: raw grande + usuario confirma ---
print("\n--- Caso 2: incluir_raw_arrays=True, 100 MB, usuario responde Sí ---")
win2, llamadas2 = _preparar_win()
win2._dialogo_export_ia = lambda: {
    "incluir_resumen_ejecutivo": True, "incluir_estadisticas": True,
    "incluir_histogramas": True, "incluir_por_evento": True,
    "incluir_contribucion_marginal": True, "incluir_text_snapshot": True,
    "incluir_raw_arrays": True, "comprimir": False,
    "mb_raw_estimado": 100.0,
}
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)

win2.exportar_para_ia()

check(llamadas2['payload'] == 1 and llamadas2['escribir'] == 1,
      f"Si el usuario confirma, el export SÍ procede normalmente "
      f"(obtenido: payload={llamadas2['payload']}, escribir={llamadas2['escribir']})")

# --- Caso 3: sin raw arrays (caso negativo, no debe avisar) ---
print("\n--- Caso 3: incluir_raw_arrays=False (caso negativo) ---")
win3, llamadas3 = _preparar_win()
win3._dialogo_export_ia = lambda: {
    "incluir_resumen_ejecutivo": True, "incluir_estadisticas": True,
    "incluir_histogramas": True, "incluir_por_evento": True,
    "incluir_contribucion_marginal": True, "incluir_text_snapshot": True,
    "incluir_raw_arrays": False, "comprimir": False,
    "mb_raw_estimado": 100.0,
}
preguntas3 = []
QtWidgets.QMessageBox.question = staticmethod(
    lambda *a, **kw: preguntas3.append(a) or QtWidgets.QMessageBox.Yes
)

win3.exportar_para_ia()

check(len(preguntas3) == 0,
      f"Sin arrays raw incluidos, no se muestra el aviso de exportación grande "
      f"(obtenido: {len(preguntas3)} preguntas)")
check(llamadas3['payload'] == 1 and llamadas3['escribir'] == 1,
      f"El export procede normalmente sin arrays raw "
      f"(obtenido: payload={llamadas3['payload']}, escribir={llamadas3['escribir']})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
