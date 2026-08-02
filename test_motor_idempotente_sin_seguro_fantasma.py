"""
test_motor_idempotente_sin_seguro_fantasma.py
=================================================

Regresion para bug medio #21 (QA ronda 3): generar_lda_con_secuencialidad
no era idempotente/reentrante sobre el MISMO dict de evento reutilizado
entre llamadas. Los campos internos '_seguros_aplicables'/
'_factores_vector'/etc. solo se (re)calculaban dentro del bloque
"if factores_activos:", que no se ejecuta si el evento ya no tiene
factores activos (lista vacía o el último factor se desactivó/eliminó).
Si una llamada anterior SÍ tenía un seguro activo sobre ese mismo dict,
'_seguros_aplicables' quedaba "fantasma" y se seguía aplicando en la
llamada siguiente, aunque el usuario ya lo hubiera quitado.

Nota: en la UI real esto está mitigado porque ejecutar_simulacion
siempre pasa copias frescas de los eventos (ver Agente 2, ronda 3), por
lo que el botón "Ejecutar Simulación" no dispara este problema hoy. Pero
es un invariante roto del motor que cualquier otro caller (tests, un
futuro modo batch, una optimización que reutilice objetos) podría
violar en silencio, sin excepción ni warning.

El fix limpia explícitamente los campos internos relacionados con
factores_ajuste cuando ya no hay ninguno activo, antes de decidir si
recalcularlos.

Este test corre el motor DOS veces sobre el MISMO dict de evento: primero
con un seguro 100% de cobertura (pérdida neta ≈0), después con
factores_ajuste vaciado (sin seguro) -- y verifica que la segunda corrida
refleje la pérdida BRUTA completa, no el seguro fantasma de la corrida
anterior.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np

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


print("=" * 70)
print("BUG MEDIO #21: motor debe ser idempotente sobre el mismo dict de evento")
print("=" * 70)

dist_frecuencia = RLB.generar_distribucion_frecuencia(3, probabilidad_exito=1.0)
dist_severidad = RLB.generar_distribucion_severidad(
    1, None, None, None, input_method='direct', params_direct={'mean': 100_000.0, 'std': 1.0}
)
seguro = {
    'nombre': 'SeguroTemporal', 'tipo_modelo': 'estatico', 'activo': True,
    'afecta_frecuencia': False, 'impacto_porcentual': 0,
    'afecta_severidad': True, 'tipo_severidad': 'seguro',
    'seguro_deducible': 0, 'seguro_cobertura_pct': 100.0,
    'seguro_limite': 0, 'seguro_tipo_deducible': 'agregado',
    'seguro_limite_ocurrencia': 0,
}
evento = {
    'id': 'e1', 'nombre': 'EventoReutilizado', 'activo': True,
    'freq_opcion': 3, 'prob_exito': 1.0,
    'dist_frecuencia': dist_frecuencia,
    'sev_opcion': 1, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 100_000.0, 'std': 1.0},
    'dist_severidad': dist_severidad,
    'factores_ajuste': [seguro],
}

# Run 1: CON seguro (100% cobertura) -> pérdida neta ≈0
rng1 = np.random.default_rng(31)
_, _, perd_evt_1, _ = RLB.generar_lda_con_secuencialidad([evento], num_simulaciones=2000, rng=rng1)
media_run1 = float(perd_evt_1[0].mean())
print(f"  Run 1 (con seguro 100%): pérdida neta media = {media_run1:.0f}")
check(media_run1 < 100,
      f"Precondición: con el seguro activo, la pérdida neta es ≈0 (obtenido: {media_run1:.2f})")

# Quitar el seguro del MISMO dict de evento (simula al usuario eliminando el
# control desde la UI, sin pasar por una copia fresca).
evento['factores_ajuste'] = []

# Run 2: SIN seguro, mismo dict reutilizado -> pérdida neta debería ser la
# BRUTA completa (~100.000), no seguir protegida por el seguro fantasma.
rng2 = np.random.default_rng(32)
_, _, perd_evt_2, _ = RLB.generar_lda_con_secuencialidad([evento], num_simulaciones=2000, rng=rng2)
media_run2 = float(perd_evt_2[0].mean())
print(f"  Run 2 (sin seguro, mismo dict reutilizado): pérdida neta media = {media_run2:.0f}")

check(media_run2 > 90_000,
      f"Bug medio #21: tras quitar el seguro del mismo dict, la pérdida neta "
      f"refleja la pérdida BRUTA completa (~100.000), no el seguro fantasma "
      f"de la corrida anterior (obtenido: {media_run2:.2f})")
check('_seguros_aplicables' not in evento or evento['_seguros_aplicables'] == [],
      f"El campo interno '_seguros_aplicables' queda vacío/limpio tras la corrida "
      f"sin factores activos (obtenido: {evento.get('_seguros_aplicables')!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
