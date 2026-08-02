"""
test_ciclos_dependencia_import.py
==================================

Regresión para bug #21: el detector de ciclos de dependencia
(RiskLabApp.tiene_ciclo) ya existía y estaba correctamente conectado al
diálogo manual de eventos y a "duplicar escenario", pero el import de
configuración desde JSON (cargar_configuracion) lo saltaba por completo.

Un archivo JSON con un ciclo de vínculos (p.ej. dos eventos con EXCLUYE
mutuo, o un evento vinculado a sí mismo) se cargaba sin ningún aviso,
dejando el grafo de dependencias en un estado que el ordenamiento
topológico (ordenar_eventos_por_dependencia) no puede resolver de forma
determinística — el evento que "gana" pasa a depender silenciosamente
del orden de la lista en el archivo en vez de la lógica de negocio
declarada.

Esta suite:
  1. Extrae `tiene_ciclo` directamente del código fuente de
     Risk_Lab_Beta.py vía AST (sin instanciar QApplication/RiskLabApp,
     que requiere una GUI Qt completa) y valida su comportamiento en
     varios grafos (cíclicos, acíclicos, auto-referencia, referencia
     colgante).
  2. Verifica, también por inspección del código fuente, que
     `cargar_configuracion` efectivamente invoca `tiene_ciclo` sobre la
     lista principal de eventos y sobre cada escenario, y que la
     validación ocurre ANTES del commit de la transacción (para que un
     archivo inválido no modifique el estado de la app).
"""
import ast
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


def _extraer_tiene_ciclo():
    """Extrae el metodo tiene_ciclo de la clase RiskLabApp como funcion
    top-level, sin ejecutar el resto del modulo (que importa PyQt y
    construye la UI)."""
    with open(ENGINE_FILE, 'r', encoding='utf-8') as f:
        src = f.read()
    tree = ast.parse(src)

    clase_app = next(
        n for n in tree.body
        if isinstance(n, ast.ClassDef) and n.name == 'RiskLabApp'
    )
    metodo = next(
        n for n in clase_app.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'tiene_ciclo'
    )
    modulo = ast.Module(body=[metodo], type_ignores=[])
    ns = {}
    exec(compile(modulo, ENGINE_FILE, 'exec'), ns)
    return ns['tiene_ciclo']


def _ev(id_, vinculos=None):
    return {'id': id_, 'nombre': id_, 'vinculos': vinculos or []}


def _vinc(id_padre):
    return {'id_padre': id_padre, 'tipo': 'AND', 'probabilidad': 100,
            'factor_severidad': 1.0, 'umbral_severidad': 0}


print("=" * 70)
print("BUG #21: Deteccion de ciclos de dependencia")
print("=" * 70)

tiene_ciclo = _extraer_tiene_ciclo()

# --- 1. DAG valido: A -> B -> C (sin ciclo) ---
eventos_dag = [
    _ev('A'),
    _ev('B', [_vinc('A')]),
    _ev('C', [_vinc('B')]),
]
check(tiene_ciclo(None, eventos_dag) is False,
      "DAG lineal valido A->B->C: NO detecta ciclo")

# --- 2. EXCLUYE mutuo: A depende de B, B depende de A ---
eventos_mutuo = [
    _ev('A', [_vinc('B')]),
    _ev('B', [_vinc('A')]),
]
check(tiene_ciclo(None, eventos_mutuo) is True,
      "EXCLUYE mutuo A<->B: SI detecta ciclo (antes se cargaba sin aviso via JSON)")

# --- 3. Auto-referencia: A depende de si mismo ---
eventos_auto = [_ev('A', [_vinc('A')])]
check(tiene_ciclo(None, eventos_auto) is True,
      "Auto-referencia A->A: SI detecta ciclo")

# --- 4. Ciclo largo: A -> B -> C -> A ---
eventos_ciclo_largo = [
    _ev('A', [_vinc('C')]),
    _ev('B', [_vinc('A')]),
    _ev('C', [_vinc('B')]),
]
check(tiene_ciclo(None, eventos_ciclo_largo) is True,
      "Ciclo de 3 eventos A->B->C->A: SI detecta ciclo")

# --- 5. Referencia colgante (id_padre sin evento correspondiente): no debe
#        crashear con KeyError, y el motor la trata como si no hubiera padre. ---
eventos_colgante = [_ev('B', [_vinc('id-inexistente')])]
try:
    resultado = tiene_ciclo(None, eventos_colgante)
    check(resultado is False,
          "Referencia colgante a id inexistente: no crashea y no se reporta como ciclo")
except KeyError:
    check(False, "Referencia colgante a id inexistente: no crashea y no se reporta como ciclo")

# --- 6. Formato legado 'eventos_padres' ---
eventos_legado_ciclo = [
    {'id': 'A', 'nombre': 'A', 'eventos_padres': ['B']},
    {'id': 'B', 'nombre': 'B', 'eventos_padres': ['A']},
]
check(tiene_ciclo(None, eventos_legado_ciclo) is True,
      "Formato legado 'eventos_padres' con ciclo mutuo: SI detecta ciclo")


# ==============================================================================
# Verificar que cargar_configuracion (import JSON) efectivamente llama a
# tiene_ciclo() ANTES de comprometer la transaccion.
# ==============================================================================
print("\n" + "=" * 70)
print("Wiring: cargar_configuracion invoca tiene_ciclo() antes del commit")
print("=" * 70)

with open(ENGINE_FILE, 'r', encoding='utf-8') as f:
    _src = f.read()

_tree = ast.parse(_src)
_clase_app = next(n for n in _tree.body if isinstance(n, ast.ClassDef) and n.name == 'RiskLabApp')
_metodo_cargar = next(
    n for n in _clase_app.body
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'cargar_configuracion'
)
_inicio, _fin = _metodo_cargar.lineno, _metodo_cargar.end_lineno
_lineas = _src.splitlines()[_inicio - 1:_fin]
_cuerpo_metodo = "\n".join(_lineas)

idx_ciclo_principal = _cuerpo_metodo.find("self.tiene_ciclo(eventos_riesgo_temp)")
idx_ciclo_escenario = _cuerpo_metodo.find("self.tiene_ciclo(scenario.eventos_riesgo)")
idx_commit = _cuerpo_metodo.find("COMMIT DE TRANSACCIÓN")

check(idx_ciclo_principal != -1,
      "cargar_configuracion llama a tiene_ciclo() sobre eventos_riesgo_temp (lista principal)")
check(idx_ciclo_escenario != -1,
      "cargar_configuracion llama a tiene_ciclo() sobre cada escenario")
check(idx_commit != -1, "Se encuentra el marcador de COMMIT DE TRANSACCIÓN")
if idx_ciclo_principal != -1 and idx_commit != -1:
    check(idx_ciclo_principal < idx_commit,
          "La validacion de ciclos (principal) ocurre ANTES del commit de la transaccion")
if idx_ciclo_escenario != -1 and idx_commit != -1:
    check(idx_ciclo_escenario < idx_commit,
          "La validacion de ciclos (escenarios) ocurre ANTES del commit de la transaccion")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
