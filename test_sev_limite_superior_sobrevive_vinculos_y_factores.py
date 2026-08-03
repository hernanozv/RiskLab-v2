"""
test_sev_limite_superior_sobrevive_vinculos_y_factores.py
=============================================================

Regresion para bug critico R4 #5 (QA ronda 4): sev_limite_superior (el
cap de severidad "máximo posible por ocurrencia") se re-aplicaba
correctamente DESPUÉS del escalamiento sev_freq (fix R3 medio #22), pero
NO después de aplicar el factor de severidad de VÍNCULOS/cascada (que
puede llegar hasta 5.0x por cada vínculo AND, y se COMPONE
MULTIPLICATIVAMENTE entre vínculos -- 5^N con N vínculos, sin ningún
techo) ni después de un factor de ajuste de severidad (estático o
estocástico, sin techo superior vía import JSON). Con solo 2 vínculos
AND de factor_severidad=5.0 cada uno, el bypass observado durante la
auditoría fue de 25x (no 5x), llevando una severidad configurada con
sev_limite_superior=1200 a ~$28.750 con una sola ocurrencia.

El fix re-aplica el clip directo (np.minimum) sobre sev_limite_superior
una vez más, justo después de aplicar TODOS los factores multiplicativos
de severidad (vínculos y factor de ajuste), antes de que los seguros
procesen la pérdida.

Este test construye un hijo con sev_limite_superior=1200, severidad
fija (mockeada) de 1150 (justo debajo del cap), y 2 vínculos AND a 2
padres que SIEMPRE ocurren (Bernoulli con prob_exito=1.0), cada uno con
factor_severidad=5.0. Sin el fix, la severidad final del hijo sería
~1150*5*5=28.750; con el fix, debe quedar acotada a 1200.
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
print("BUG CRÍTICO R4 #5: sev_limite_superior debe sobrevivir a la cascada de vínculos")
print("=" * 70)


class _SeveridadFija:
    def __init__(self, valor):
        self.valor = valor

    def rvs(self, size=1, random_state=None):
        return np.full(size, self.valor)


def _padre_siempre_activo(id_):
    return {
        'id': id_, 'nombre': f'Padre_{id_}', 'activo': True,
        'freq_opcion': 3, 'prob_exito': 1.0,
        'dist_frecuencia': RLB.generar_distribucion_frecuencia(3, probabilidad_exito=1.0),
        'sev_opcion': 1, 'sev_input_method': 'direct',
        'sev_params_direct': {'mean': 100.0, 'std': 10.0},
        'dist_severidad': RLB.generar_distribucion_severidad(
            1, None, None, None, input_method='direct', params_direct={'mean': 100.0, 'std': 10.0}
        ),
    }


hijo = {
    'id': 'hijo', 'nombre': 'EventoConCapYVinculos', 'activo': True,
    'freq_opcion': 1, 'tasa': 3.0,
    'dist_frecuencia': RLB.generar_distribucion_frecuencia(1, tasa=3.0),
    'sev_opcion': 1, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 1150.0, 'std': 10.0},
    'dist_severidad': _SeveridadFija(1150.0),
    'sev_limite_superior': 1200.0,
    'vinculos': [
        {'id_padre': 'p1', 'tipo': 'AND', 'probabilidad': 100, 'factor_severidad': 5.0, 'umbral_severidad': 0},
        {'id_padre': 'p2', 'tipo': 'AND', 'probabilidad': 100, 'factor_severidad': 5.0, 'umbral_severidad': 0},
    ],
}

eventos = [_padre_siempre_activo('p1'), _padre_siempre_activo('p2'), hijo]

rng = np.random.default_rng(77)
_, freq_tot, perd_evt, freq_evt = RLB.generar_lda_con_secuencialidad(eventos, num_simulaciones=3000, rng=rng)

idx_hijo = [e['id'] for e in eventos].index('hijo')
idx_1_occ = np.flatnonzero(freq_evt[idx_hijo] == 1)
check(idx_1_occ.size > 0, "Precondición: hay simulaciones con exactamente 1 ocurrencia del hijo")

if idx_1_occ.size > 0:
    perdidas_1_occ = perd_evt[idx_hijo][idx_1_occ]
    maximo_observado = float(perdidas_1_occ.max())
    print(f"  máxima severidad observada (1 ocurrencia): {maximo_observado:,.2f}")
    check(maximo_observado <= 1200.0 + 1e-6,
          f"Bug crítico R4 #5: la severidad del hijo respeta sev_limite_superior=1200 "
          f"pese a 2 vínculos AND de factor_severidad=5.0 cada uno "
          f"(obtenido: {maximo_observado:,.2f}; sin el fix sería ~28.750)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
