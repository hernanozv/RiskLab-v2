"""
test_carga_json_malformado_no_muestra_traceback.py
======================================================

Regresion para bug alto R4 #1 (QA ronda 4): cargar_configuracion no
validaba la ESTRUCTURA raiz del archivo JSON antes de asumir que era un
dict con listas en 'eventos_riesgo'/'scenarios'. Un JSON sintacticamente
valido pero mal formado (la raiz es un array/string, o 'eventos_riesgo'
es un string/dict/null explicito en vez de una lista) rompia el propio
mecanismo de aislamiento de errores por-evento: al iterar un string
caracter por caracter, `evento_data.get(...)` dentro del handler de
excepcion tambien fallaba (AttributeError), escapando hasta el
catch-all generico, que mostraba un TRACEBACK CRUDO de Python (rutas de
archivo, numeros de linea, jerga tecnica) directamente al usuario.

El fix agrega validacion explicita de tipo para la raiz y para
'eventos_riesgo'/'scenarios' (deben ser listas o estar ausentes/null),
usa `or []` en vez de `.get(clave, [])` para manejar el caso de null
explicito, hace defensivo el handler de aislamiento por-evento
(isinstance check), y reemplaza el traceback.format_exc() del catch-all
final por un mensaje traducido/amigable (mismo helper traducir_error ya
usado en el resto del metodo).

Este test construye varios archivos JSON malformados (raiz=lista,
eventos_riesgo=string, eventos_riesgo=null explicito, eventos_riesgo=dict)
y verifica que cargar_configuracion SIEMPRE termine mostrando un
QMessageBox.critical con un mensaje SIN trazas de Python (sin "Traceback",
sin rutas de archivo .py, sin "line "), en vez de crashear o mostrar
jerga tecnica cruda.
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
QtWidgets.QMessageBox.question = staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.Yes)

print("=" * 70)
print("BUG ALTO R4 #1: JSON malformado no debe mostrar traceback crudo")
print("=" * 70)

casos_con_error = {
    "raiz_es_lista": ["esto", "no", "es", "un", "objeto"],
    "eventos_riesgo_es_string": {"eventos_riesgo": "no soy una lista", "scenarios": []},
    "eventos_riesgo_es_dict": {"eventos_riesgo": {"a": 1}, "scenarios": []},
}

tmp_path = os.path.join(_THIS_DIR, '_tmp_test_json_malformado.json')

for nombre_caso, contenido in casos_con_error.items():
    print(f"\n--- Caso: {nombre_caso} ---")
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(contenido, f)

    try:
        win = RLB.RiskLabApp()
        QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))

        criticals_capturados = []
        QtWidgets.QMessageBox.critical = staticmethod(
            lambda *a, **kw: criticals_capturados.append(a) or QtWidgets.QMessageBox.Ok
        )

        excepcion_escapo = None
        try:
            win.cargar_configuracion()
        except Exception as e:
            excepcion_escapo = e

        check(excepcion_escapo is None,
              f"[{nombre_caso}] cargar_configuracion NO deja escapar ninguna excepción "
              f"(obtenido: {excepcion_escapo!r})")

        texto_completo = " ".join(str(a) for a in criticals_capturados)
        check(len(criticals_capturados) >= 1,
              f"[{nombre_caso}] se muestra un QMessageBox.critical (obtenido: "
              f"{len(criticals_capturados)} diálogos)")
        check('Traceback' not in texto_completo and '.py' not in texto_completo and ', line ' not in texto_completo,
              f"[{nombre_caso}] Bug alto R4 #1: el mensaje NO contiene traceback crudo de Python "
              f"(obtenido: {texto_completo[:200]!r})")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- Caso adicional: 'eventos_riesgo'/'scenarios' con null EXPLÍCITO ---
# (clave presente con valor null) debe cargar una config vacía sin error,
# no ser tratado como un caso "malformado" -- confirma que `or []` (en vez
# de `.get(clave, [])`, que solo aplica el default si la clave está
# AUSENTE) maneja este caso con gracia.
print("\n--- Caso: eventos_riesgo/scenarios con null explícito (config vacía válida) ---")
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump({"eventos_riesgo": None, "scenarios": None}, f)
try:
    win = RLB.RiskLabApp()
    QtWidgets.QFileDialog.getOpenFileName = staticmethod(lambda *a, **kw: (tmp_path, ''))
    criticals_null = []
    QtWidgets.QMessageBox.critical = staticmethod(
        lambda *a, **kw: criticals_null.append(a) or QtWidgets.QMessageBox.Ok
    )
    win.cargar_configuracion()
    check(len(criticals_null) == 0,
          f"null explícito en eventos_riesgo/scenarios carga una config vacía "
          f"SIN error (obtenido: {len(criticals_null)} diálogos de error)")
    check(win.eventos_riesgo == [] and win.scenarios == [],
          f"La config queda vacía correctamente (obtenido: "
          f"{len(win.eventos_riesgo)} eventos, {len(win.scenarios)} escenarios)")
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
