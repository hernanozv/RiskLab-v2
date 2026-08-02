"""
test_sin_ceros_tooltip_no_reordena_en_cada_hover.py
=======================================================

Regresion para bug bajo #31 (QA ronda 3): el formatter de tooltip del
gráfico "Sin Ceros" (formatter_distribucion_sin_ceros, dentro de
graficar_resultados) llamaba np.sort(perdidas_totales_sin_cero) EN CADA
INVOCACIÓN del tooltip (cada vez que el usuario mueve el mouse sobre el
gráfico), en vez de ordenar una sola vez y cachear el resultado -- el
mismo patrón que el gráfico 1 (formatter_distribucion) ya usaba
correctamente (ver comentario "Optimización: ordenar UNA SOLA VEZ...").
Con decenas de miles de simulaciones, ordenar en cada hover introduce una
latencia perceptible de la UI.

El fix aplica el mismo patrón de caché (_perdidas_sin_cero_sorted
calculado una sola vez fuera del closure) al formatter de "Sin Ceros".

NOTA sobre la técnica del test: en este entorno headless, la versión de
matplotlib/seaborn instalada no llena `ax.collections` para los parches
de sns.histplot (kde=False), por lo que add_tooltip_data nunca registra
el formatter en canvas.tooltip_labels (esto es una particularidad del
entorno de testing, no un bug de la app -- se reprodujo el mismo
comportamiento en el formatter de Gráfico 1, que es código no tocado por
este fix). Por eso este test verifica el CUERPO FUENTE de la función
(inspección estática) en vez de invocarla en vivo: confirma que la línea
`np.sort(...)` fue movida fuera del closure (a una variable cacheada) y
que dentro del cuerpo de la función solo se usa np.searchsorted sobre esa
variable ya ordenada.
"""
import os
import re
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

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
print("BUG BAJO #31: tooltip de 'Sin Ceros' no debe reordenar (np.sort) en cada hover")
print("=" * 70)

src = open(os.path.join(_THIS_DIR, 'Risk_Lab_Beta.py'), encoding='utf-8').read()

m = re.search(
    r'def formatter_distribucion_sin_ceros\(x, y\):\n((?:.*\n)*?)(?=\s*\n            #|            #)',
    src
)
check(m is not None, "Se encontró la definición de formatter_distribucion_sin_ceros")

if m is not None:
    cuerpo = m.group(1)
    print(f"  cuerpo de la función:\n{cuerpo}")
    check('np.sort(' not in cuerpo,
          "Bug bajo #31: el cuerpo del formatter ya NO llama a np.sort() "
          "directamente (debe usar una variable ya ordenada, cacheada fuera)")
    check('np.searchsorted(' in cuerpo,
          "El formatter sigue usando np.searchsorted para ubicar el percentil")

# Verificar que existe una variable cacheada (ordenada UNA sola vez) antes
# de la definición de la función, siguiendo el mismo patrón que Gráfico 1.
idx_def = src.find('def formatter_distribucion_sin_ceros(x, y):')
bloque_previo = src[max(0, idx_def - 600):idx_def]
check('np.sort(perdidas_totales_sin_cero)' in bloque_previo,
      "Existe una variable cacheada con np.sort(perdidas_totales_sin_cero) "
      "calculada ANTES (fuera) de la definición del formatter")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
