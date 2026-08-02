"""
test_normalizar_factor_unico_con_clip.py
============================================

Regresion para bug bajo #21 (QA ronda 2): editar_evento_popup tenía una
copia LOCAL de normalizar_factor, duplicando (y desincronizada de) la
versión canónica normalizar_factor_global (ya usada por el editor de
escenario y por el import de JSON). A diferencia de la versión
canónica, la copia local NO clipeaba impacto_porcentual/
reduccion_efectiva/confiabilidad a sus rangos válidos documentados
(p.ej. impacto_porcentual >= -99%). No era explotable hoy porque los
spinboxes de la UI ya clipean al mostrarse, pero era una trampa de
mantenimiento: dos implementaciones que podían divergir en silencio.

El fix elimina la copia local y usa normalizar_factor_global en su
lugar, igual que las otras rutas.

Este test abre el diálogo real "Editar Evento" (headless) sobre un
evento con un factor de ajuste fuera de rango
(impacto_porcentual=-150, un valor inválido según la documentación,
posible via import de un JSON antiguo/malformado) y verifica que la
tabla de factores muestra el valor YA CLIPEADO (-99%, mostrado como
"+99%" invertido), consistente con lo que ya hacía el editor de
escenario para el mismo caso.
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

print("=" * 70)
print("BUG BAJO #21: normalizar_factor único (sin duplicado), con clip de validación")
print("=" * 70)

check(hasattr(RLB, 'normalizar_factor_global'),
      "normalizar_factor_global (versión canónica) existe en el módulo")

# --- Verificación directa de la función canónica ---
factor_fuera_de_rango = {
    'nombre': 'ControlMalformado', 'tipo_modelo': 'estatico',
    'impacto_porcentual': -150,  # inválido: documentado como >= -99
    'afecta_frecuencia': True,
}
normalizado = RLB.normalizar_factor_global(factor_fuera_de_rango)
check(normalizado['impacto_porcentual'] == -99,
      f"normalizar_factor_global clipea impacto_porcentual a -99 "
      f"(obtenido: {normalizado['impacto_porcentual']})")

# --- Verificación end-to-end: el diálogo real usa esa misma función ---
evento = {
    'id': 'e1', 'nombre': 'EventoConFactorMalo', 'activo': True,
    'sev_opcion': 2, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 1000.0, 'std': 100.0},
    'freq_opcion': 1, 'tasa': 5.0,
    'factores_ajuste': [dict(factor_fuera_de_rango)],
}

win = RLB.RiskLabApp()
win.eventos_riesgo = [evento]

resultado = {}


def _fake_exec(self):
    ajustes_table = None
    for table in self.findChildren(QtWidgets.QTableWidget):
        headers = [table.horizontalHeaderItem(i).text() if table.horizontalHeaderItem(i) else ''
                   for i in range(table.columnCount())]
        if headers[:5] == ["Activo", "Nombre", "Tipo", "Configuración", "Eliminar"]:
            ajustes_table = table
            break
    assert ajustes_table is not None, "No se encontró la tabla de factores de ajuste"
    assert ajustes_table.rowCount() >= 1, "La tabla de factores no cargó el factor existente"
    item_config = ajustes_table.item(0, 3)
    resultado['texto_config'] = item_config.text() if item_config else None
    return QtWidgets.QDialog.Rejected


QtWidgets.QDialog.exec_ = _fake_exec
try:
    win.editar_evento_popup(new=False, row=0)
finally:
    del QtWidgets.QDialog.exec_

texto_config = resultado.get('texto_config')
check(texto_config is not None, f"Se encontró el texto de configuración del factor (obtenido: {texto_config!r})")
if texto_config is not None:
    check('+99%' in texto_config,
          f"Bug bajo #21: el diálogo muestra el valor clipeado (+99%), no el original "
          f"fuera de rango (+150%) (obtenido: {texto_config!r})")
    check('+150%' not in texto_config,
          f"El diálogo NO muestra el valor sin clipear +150% (obtenido: {texto_config!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
