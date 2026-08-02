"""
test_marginal_contribution_cvar.py
====================================

Regresion para bug #26: recurrencia del bug de CVaR/media_cola_condicional
(ya corregido en otro lugar del código) dentro de
RiskLabApp._build_marginal_contribution.

Para calcular la "contribución marginal en el percentil X", la función
construye una ventana [percentil(pct-2.5), percentil(pct+2.5)] y toma las
simulaciones cuya pérdida total cae en ese rango. Cuando hay una masa
puntual grande en 0 (p.ej. 97% de los años sin pérdida, algo común en
riesgo operacional de baja frecuencia), el límite inferior de la ventana
para percentiles altos (P99, etc.) puede caer dentro de esa masa y quedar
en 0. Como las pérdidas nunca son negativas, la máscara ">= 0" termina
incluyendo TODAS las simulaciones (no solo las cercanas al percentil
objetivo), y la "contribución marginal en P99" colapsa a ser idéntica a la
contribución promedio general — exactamente el mismo patrón del bug de
CVaR ya corregido en `media_cola_condicional` (uso de `>=` en vez de `>`
cuando el umbral es degenerado).

Este test construye un escenario con 97% de años sin pérdida y 3% con
pérdida (dominada por un evento en la cola y por otro evento en el resto),
y verifica que P99 ya NO sea idéntico a la Media.
"""
import ast
import os
import sys

import numpy as np

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


def _extraer_build_marginal_contribution():
    with open(ENGINE_FILE, 'r', encoding='utf-8') as f:
        src = f.read()
    tree = ast.parse(src)
    clase_app = next(
        n for n in tree.body
        if isinstance(n, ast.ClassDef) and n.name == 'RiskLabApp'
    )
    metodo = next(
        n for n in clase_app.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == '_build_marginal_contribution'
    )
    modulo = ast.Module(body=[metodo], type_ignores=[])
    ns = {'np': np}
    exec(compile(modulo, ENGINE_FILE, 'exec'), ns)
    return ns['_build_marginal_contribution']


print("=" * 70)
print("BUG #26: Recurrencia del bug de CVaR en _build_marginal_contribution")
print("=" * 70)

_build_marginal_contribution = _extraer_build_marginal_contribution()

rng = np.random.default_rng(42)
N = 100_000
tail_idx = rng.choice(N, size=int(0.03 * N), replace=False)

perdidas_evento_A = np.zeros(N)
perdidas_evento_B = np.zeros(N)
# En la cola (3% de los años), el Evento A domina la perdida; el Evento B
# aporta una fraccion menor pero tambien presente.
perdidas_evento_A[tail_idx] = rng.uniform(1_000_000, 5_000_000, size=len(tail_idx))
perdidas_evento_B[tail_idx] = rng.uniform(10_000, 50_000, size=len(tail_idx))
perdidas_totales = perdidas_evento_A + perdidas_evento_B

eventos = [{'nombre': 'EventoA'}, {'nombre': 'EventoB'}]
perdidas_por_evento = [perdidas_evento_A, perdidas_evento_B]

resultado = _build_marginal_contribution(None, eventos, perdidas_totales, perdidas_por_evento)

check(resultado is not None, "_build_marginal_contribution no retorna None")

contrib_media = {f['evento']: f['contribucion'] for f in resultado['contribuciones_por_percentil']['Media']}
contrib_p99 = {f['evento']: f['contribucion'] for f in resultado['contribuciones_por_percentil']['P99']}

check(contrib_p99 != contrib_media,
      f"Bug #26: la contribución en P99 ya NO es idéntica a la Media "
      f"(Media={contrib_media}, P99={contrib_p99})")

# La contribución de EventoA en P99 debe ser sustancialmente mayor que en
# Media (ya que la cola está dominada por sus pérdidas de $1M-$5M, mientras
# que la media incluye el 97% de años en cero).
check(contrib_p99['EventoA'] > contrib_media['EventoA'] * 10,
      f"La contribución de EventoA en P99 (${contrib_p99['EventoA']:,.0f}) es "
      f"muy superior a la de la Media (${contrib_media['EventoA']:,.0f})")

# P99 deberia estar en el orden de magnitud de las perdidas reales de la cola
# (millones), no en el orden de la media general (decenas/cientos de miles).
check(contrib_p99['EventoA'] > 500_000,
      f"La contribución de EventoA en P99 (${contrib_p99['EventoA']:,.0f}) refleja "
      f"la magnitud real de la cola (millones), no la media diluida por el 97% en cero")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
