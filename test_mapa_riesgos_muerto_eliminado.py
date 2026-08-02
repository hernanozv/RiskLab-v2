"""
test_mapa_riesgos_muerto_eliminado.py
========================================

Regresion para hallazgo medio #1: el bloque "Mapa de Riesgos Mejorado"
(scatterplot jerárquico con cuadrantes, tooltips y anotaciones por evento)
se recalculaba en CADA simulación dentro de graficar_resultados, pero
nunca se agregaba una pestaña (self.graficos_tab_widget.addTab) para
mostrarlo — a diferencia de los demás gráficos de esa misma función, que
sí se agregan (Tail Risk, Termómetro, Semáforo, Calendario, etc.). Era
trabajo puro desperdiciado en cada corrida (construcción de DataFrame,
scatterplot con seaborn, tooltips por evento, anotaciones, etc.) sin
ningún beneficio para el usuario.

Se eliminó el bloque completo (nunca fue alcanzable desde la UI). Este
test verifica que no se reintroduzca sin conectarlo a una pestaña.
"""
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
ENGINE_FILE = os.path.join(_THIS_DIR, 'Risk_Lab_Beta.py')

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


print("=" * 70)
print("Hallazgo medio #1: Mapa de Riesgos Mejorado (código muerto eliminado)")
print("=" * 70)

with open(ENGINE_FILE, 'r', encoding='utf-8') as f:
    src = f.read()

for identificador in ('df_riesgos', 'canvas_mapa', 'fig_mapa', 'ax_mapa'):
    check(identificador not in src,
          f"'{identificador}' (del bloque muerto Mapa de Riesgos Mejorado) ya no existe en el código")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
