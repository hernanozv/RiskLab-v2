"""
test_vinculos_legacy_huerfanos.py
====================================

Regresion para bug #41 (QA ronda 2): la rama LEGACY de dependencias
('eventos_padres'/'tipo_dependencia', usada por eventos importados desde
un JSON en formato antiguo) no protegía contra referencias huérfanas de la
misma forma que la rama nueva ('vinculos'). Dos problemas relacionados:

  1. En generar_lda_con_secuencialidad, la rama legacy hacía
     `id_a_index[padre_id]` sin verificar que el padre existiera, a
     diferencia de la rama 'vinculos' (que sí hace
     `if id_padre not in id_a_index: continue`). Si el padre de un vínculo
     legacy no estaba en la lista de eventos simulados (p.ej. porque fue
     eliminado después de importar el JSON), esto lanzaba un KeyError SIN
     CAPTURAR que abortaba la simulación COMPLETA, no solo el evento
     afectado.

  2. limpiar_vinculos_huerfanos() (llamada al eliminar un evento desde la
     UI) solo limpiaba el campo 'vinculos', nunca 'eventos_padres'. Un
     evento en formato legacy quedaba con un id_padre apuntando a un
     evento ya borrado, sin que la limpieza de huérfanos lo detectara.

Este test verifica ambos fixes: (a) el motor de simulación ya no crashea
con un vínculo legacy huérfano, tratándolo como si no tuviera ese padre
(igual que hace la rama 'vinculos'); (b) limpiar_vinculos_huerfanos()
también limpia 'eventos_padres'.
"""
import ast
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

from test_robustez_simulacion import ENGINE, _build_evento, _simular

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


def _extraer_limpiar_vinculos_huerfanos():
    """Extrae el metodo limpiar_vinculos_huerfanos de RiskLabApp como
    funcion top-level (solo usa self.eventos_riesgo, no depende de Qt)."""
    engine_file = os.path.join(_THIS_DIR, 'Risk_Lab_Beta.py')
    with open(engine_file, 'r', encoding='utf-8') as f:
        src = f.read()
    tree = ast.parse(src)
    clase_app = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'RiskLabApp')
    metodo = next(
        n for n in clase_app.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'limpiar_vinculos_huerfanos'
    )
    modulo = ast.Module(body=[metodo], type_ignores=[])
    ns = {}
    exec(compile(modulo, engine_file, 'exec'), ns)
    return ns['limpiar_vinculos_huerfanos']


class _FakeApp:
    def __init__(self, eventos_riesgo):
        self.eventos_riesgo = eventos_riesgo


print("=" * 70)
print("BUG #41: Vínculos legacy (eventos_padres) huérfanos")
print("=" * 70)

# --- 1. El motor de simulación no debe crashear con un eventos_padres huérfano ---
evento_hijo = _build_evento(
    'hijo', 'Hijo', 1, {'tasa': 3.0}, 2,
    {'minimo': None, 'mas_probable': None, 'maximo': None, 'input_method': 'direct',
     'params_direct': {'mean': 500, 'std': 50}}
)
evento_hijo['eventos_padres'] = ['id-padre-que-no-existe']
evento_hijo['tipo_dependencia'] = 'AND'

try:
    perd, freq, _, _ = _simular([evento_hijo], num_sims=3000, seed=1)
    check(True, "El motor no lanza KeyError con un eventos_padres (legacy) huérfano")
except KeyError as e:
    check(False, f"El motor no lanza KeyError con un eventos_padres (legacy) huérfano (obtenido: {e!r})")
    perd = None

# El evento con padre huérfano debe comportarse como INDEPENDIENTE (mismo
# criterio que la rama 'vinculos' para referencias colgantes): su
# frecuencia esperada debe ser la de su propia distribución (tasa=3.0),
# sin restricción de ningún padre inexistente.
evento_independiente = _build_evento(
    'hijo', 'HijoIndep', 1, {'tasa': 3.0}, 2,
    {'minimo': None, 'mas_probable': None, 'maximo': None, 'input_method': 'direct',
     'params_direct': {'mean': 500, 'std': 50}}
)
perd_indep, freq_indep, _, _ = _simular([evento_independiente], num_sims=3000, seed=1)
if perd is not None:
    err = abs(perd.mean() - perd_indep.mean()) / perd_indep.mean()
    check(err < 0.10,
          f"El evento con padre huérfano se comporta como independiente "
          f"(perd={perd.mean():.1f} vs esperado≈{perd_indep.mean():.1f}, err={err:.1%})")

# --- 2. limpiar_vinculos_huerfanos() debe limpiar TANTO 'vinculos' como
#        'eventos_padres' ---
limpiar_vinculos_huerfanos = _extraer_limpiar_vinculos_huerfanos()

eventos = [
    {'id': 'A', 'nombre': 'A', 'vinculos': []},
    {
        'id': 'B', 'nombre': 'B',
        'vinculos': [{'id_padre': 'A', 'tipo': 'AND', 'probabilidad': 100,
                      'factor_severidad': 1.0, 'umbral_severidad': 0}],
    },
    {
        'id': 'C', 'nombre': 'C (formato legacy)',
        'eventos_padres': ['A'], 'tipo_dependencia': 'AND',
    },
]

app_fake = _FakeApp(eventos)
limpiar_vinculos_huerfanos(app_fake, ids_eliminados={'A'})

evento_b = next(e for e in app_fake.eventos_riesgo if e['id'] == 'B')
evento_c = next(e for e in app_fake.eventos_riesgo if e['id'] == 'C')

check(evento_b['vinculos'] == [],
      f"limpiar_vinculos_huerfanos limpia 'vinculos' (formato nuevo) como antes "
      f"(obtenido: {evento_b['vinculos']})")
check(evento_c.get('eventos_padres') == [],
      f"Bug #41: limpiar_vinculos_huerfanos también limpia 'eventos_padres' "
      f"(formato legacy) (obtenido: {evento_c.get('eventos_padres')})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
