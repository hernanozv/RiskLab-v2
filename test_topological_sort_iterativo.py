"""
test_topological_sort_iterativo.py
=====================================

Regresion para bug #31: ordenar_eventos_por_dependencia() implementaba el
DFS del topological sort de forma recursiva (una llamada de función por
nivel de profundidad). Con una cadena de dependencia larga y VÁLIDA (sin
ciclos) — p.ej. ~1000+ eventos en serie A→B→C→...→Z, algo que puede surgir
de un modelo con muchos controles/mitigaciones encadenados — esto excedía
el límite de recursión de Python (RecursionError), haciendo que la
simulación completa fallara para un modelo perfectamente válido.

El test existente `test_HH_chain_no_stack_overflow` (test_produccion_
critico.py) solo probaba una cadena de 100 eventos, muy por debajo del
límite de recursión por defecto (~1000), por lo que nunca detectó el
problema real.

Esta suite prueba directamente ordenar_eventos_por_dependencia() (sin
pasar por la simulación completa, que sería más lento de construir a esta
escala) con:
  1. Una cadena de 5000 eventos en serie: no debe lanzar RecursionError y
     debe producir un orden topológico válido.
  2. Equivalencia de resultados con una implementación recursiva de
     referencia en grafos pequeños/variados (para confirmar que el cambio
     a iterativo no alteró el orden de desempate entre ramas).
"""
import ast
import os
import random
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


def _extraer_ordenar_eventos_por_dependencia():
    with open(ENGINE_FILE, 'r', encoding='utf-8') as f:
        src = f.read()
    tree = ast.parse(src)
    nodo = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == 'ordenar_eventos_por_dependencia'
    )
    modulo = ast.Module(body=[nodo], type_ignores=[])
    ns = {}
    exec(compile(modulo, ENGINE_FILE, 'exec'), ns)
    return ns['ordenar_eventos_por_dependencia']


def _dfs_recursivo_referencia(eventos_riesgo):
    """Reimplementacion de la version VIEJA (recursiva) para comparar
    equivalencia de resultados en grafos chicos (donde no crashea)."""
    hijos_map = {evento['id']: [] for evento in eventos_riesgo}
    for ev in eventos_riesgo:
        ev_id = ev['id']
        if 'vinculos' in ev:
            seen_padres = set()
            for vinculo in ev['vinculos']:
                padre_id = vinculo.get('id_padre')
                if padre_id in hijos_map and padre_id not in seen_padres:
                    hijos_map[padre_id].append(ev_id)
                    seen_padres.add(padre_id)
    visitados = set()
    stack = []

    def dfs(evento_id):
        visitados.add(evento_id)
        for hijo_id in hijos_map.get(evento_id, ()):
            if hijo_id not in visitados:
                dfs(hijo_id)
        stack.append(evento_id)

    for evento in eventos_riesgo:
        if evento['id'] not in visitados:
            dfs(evento['id'])
    stack.reverse()
    return stack


print("=" * 70)
print("BUG #31: Sort topológico iterativo (sin límite de recursión)")
print("=" * 70)

ordenar_eventos_por_dependencia = _extraer_ordenar_eventos_por_dependencia()

# --- 1. Cadena larga (5000 eventos): no debe lanzar RecursionError ---
N = 5000
eventos_cadena = []
for i in range(N):
    vinculos = [{'id_padre': f'e{i - 1}', 'tipo': 'AND'}] if i > 0 else []
    eventos_cadena.append({'id': f'e{i}', 'nombre': f'E{i}', 'vinculos': vinculos})

try:
    orden = ordenar_eventos_por_dependencia(eventos_cadena)
    check(True, f"Cadena de {N} eventos no lanza RecursionError")
except RecursionError:
    check(False, f"Cadena de {N} eventos no lanza RecursionError")
    orden = []

check(len(orden) == N, f"El orden resultante tiene los {N} eventos")

posiciones = {id_: idx for idx, id_ in enumerate(orden)}
orden_valido = all(posiciones[f'e{i - 1}'] < posiciones[f'e{i}'] for i in range(1, N))
check(orden_valido, "El orden respeta la cadena de dependencias (padre antes que hijo)")

# --- 2. Equivalencia con la implementación recursiva de referencia en
#        grafos aleatorios pequeños (branching, múltiples raíces, etc.) ---
random.seed(42)
todos_coinciden = True
for _ in range(200):
    n = random.randint(1, 30)
    ids = [f'e{i}' for i in range(n)]
    eventos = []
    for i, id_ in enumerate(ids):
        num_padres = random.randint(0, min(2, i))
        padres = random.sample(ids[:i], num_padres) if i > 0 else []
        vinculos = [{'id_padre': p, 'tipo': random.choice(['AND', 'OR', 'EXCLUYE'])} for p in padres]
        eventos.append({'id': id_, 'nombre': id_, 'vinculos': vinculos})
    random.shuffle(eventos)

    referencia = _dfs_recursivo_referencia(eventos)
    nuevo = ordenar_eventos_por_dependencia(eventos)
    if referencia != nuevo:
        todos_coinciden = False
        break

check(todos_coinciden,
      "200 grafos aleatorios: el orden iterativo es IDÉNTICO al de la versión recursiva original")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
