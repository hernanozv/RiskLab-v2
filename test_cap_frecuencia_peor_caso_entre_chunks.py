"""
test_cap_frecuencia_peor_caso_entre_chunks.py
=================================================

Regresion para bug alto #14 (QA ronda 3): SimulacionThread divide una
corrida en 10 chunks, llamando a generar_lda_con_secuencialidad 10
veces con el MISMO dict de evento (mutable, compartido). Los campos de
diagnostico '_cap_frecuencia_factor'/'_cap_frecuencia_suma_original'/etc.
se sobreescribian en CADA chunk que disparara el cap de frecuencia, sin
acumular el peor caso. Si el cap se disparaba muy fuerte en un chunk
temprano (factor pequeño = distorsion severa) pero solo levemente en el
ULTIMO chunk (factor cercano a 1 = distorsion minima), el reporte final
mostraba el factor del ultimo chunk -- dando la falsa impresion de una
distorsion minima cuando en realidad una porcion sustancial de las
simulaciones sufrio una distorsion mucho mas severa.

El fix conserva el PEOR caso (factor mas chico) de todos los chunks de
la corrida, no el ultimo.

Este test llama al motor DOS veces sobre el MISMO dict de evento (Poisson
tasa=3000, MAX_EVENTOS_POR_EVENTO_POR_CHUNK monkeypatcheado a un valor
bajo para poder disparar el cap con pocas simulaciones): primero con un
chunk SEVERO (factor pequeño), despues con un chunk LEVE (factor cercano
a 1) -- exactamente el orden que expone el bug -- y verifica que el
factor final registrado sea el SEVERO (peor caso), no el leve (ultimo).
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
print("BUG ALTO #14: campos de diagnóstico de cap de frecuencia deben reflejar el PEOR caso")
print("=" * 70)

RLB.MAX_EVENTOS_POR_EVENTO_POR_CHUNK = 50_000

dist_frecuencia = RLB.generar_distribucion_frecuencia(1, tasa=3000.0)
dist_severidad = RLB.generar_distribucion_severidad(
    1, None, None, None, input_method='direct', params_direct={'mean': 100.0, 'std': 10.0}
)
evento = {
    'id': 'e1', 'nombre': 'EventoCapChunks', 'activo': True,
    'freq_opcion': 1, 'tasa': 3000.0,
    'dist_frecuencia': dist_frecuencia,
    'sev_opcion': 1, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 100.0, 'std': 10.0},
    'dist_severidad': dist_severidad,
}

# Chunk "severo" primero: 100 sims * tasa=3000 -> suma ~300.000 vs cap 50.000
# -> factor ~0.1667 (distorsión fuerte).
rng1 = np.random.default_rng(1)
RLB.generar_lda_con_secuencialidad([evento], num_simulaciones=100, rng=rng1)
factor_tras_chunk_severo = evento.get('_cap_frecuencia_factor')
print(f"  factor tras chunk SEVERO: {factor_tras_chunk_severo}")
check(factor_tras_chunk_severo is not None and factor_tras_chunk_severo < 0.3,
      f"Precondición: el chunk severo dispara el cap con un factor pequeño "
      f"(obtenido: {factor_tras_chunk_severo})")

# Chunk "leve" después, MISMO dict de evento: 20 sims * tasa=3000 -> suma
# ~60.000 vs cap 50.000 -> factor ~0.833 (distorsión mínima).
rng2 = np.random.default_rng(2)
RLB.generar_lda_con_secuencialidad([evento], num_simulaciones=20, rng=rng2)
factor_final = evento.get('_cap_frecuencia_factor')
print(f"  factor tras chunk LEVE (mismo evento, corrida 'completa'): {factor_final}")

check(factor_final is not None and factor_final < 0.3,
      f"Bug alto #14: el factor final registrado sigue siendo el del chunk SEVERO "
      f"(peor caso), no el del último chunk (leve) "
      f"(obtenido: {factor_final}, antes del fix hubiera dado ≈0.83)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
