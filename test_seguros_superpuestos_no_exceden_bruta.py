"""
test_seguros_superpuestos_no_exceden_bruta.py
=================================================

Regresion para bug alto #9 (QA ronda 3): cada seguro (por_ocurrencia o
agregado) calculaba su pago de forma independiente sobre la misma base
(la perdida bruta del evento) y los pagos se sumaban sin ningun chequeo
de solapamiento entre polizas. Con dos polizas configuradas sobre la
MISMA capa (mismo deducible, ambas con 100% de cobertura -- una
configuracion perfectamente valida, aunque probablemente no intencional
por parte del usuario), el pago combinado reportado podia superar el
100% de la perdida bruta del evento (p.ej. pagar $200.000 de seguro por
una perdida de $100.000).

La perdida NETA final ya quedaba protegida por el np.maximum(...,0)
existente (nunca resulta negativa), pero el pago de seguro combinado en
si mismo -- usado en los mensajes de debug y potencialmente en futuros
reportes -- resultaba economicamente incoherente.

El fix aplica np.minimum(pago_combinado, perdida_bruta) tanto para
seguros por_ocurrencia como para seguros agregados, antes de restar del
total.

Este test dispara el mensaje de debug (monkeypatcheando _dbg para
capturarlo, evitando depender de la variable de entorno
RISKLAB_DEBUG_SIM) con 2 polizas por_ocurrencia identicas (deducible=0,
cobertura=100%, sin limite) sobre un evento con severidad casi
deterministica, y verifica que el "Pago medio seguro" reportado nunca
supera la perdida bruta media.
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
print("BUG ALTO #9: pago combinado de seguros superpuestos no debe superar la pérdida bruta")
print("=" * 70)

mensajes_debug = []
RLB._dbg = lambda *a, **kw: mensajes_debug.append(" ".join(str(x) for x in a))

dist_frecuencia = RLB.generar_distribucion_frecuencia(3, probabilidad_exito=1.0)  # Bernoulli p=1
dist_severidad = RLB.generar_distribucion_severidad(
    1, None, None, None, input_method='direct', params_direct={'mean': 100_000.0, 'std': 1.0}
)

seguro_a = {
    'nombre': 'SeguroA', 'tipo_modelo': 'estatico', 'activo': True,
    'afecta_frecuencia': False, 'impacto_porcentual': 0,
    'afecta_severidad': True, 'tipo_severidad': 'seguro',
    'seguro_deducible': 0, 'seguro_cobertura_pct': 100.0,
    'seguro_limite': 0, 'seguro_tipo_deducible': 'por_ocurrencia',
    'seguro_limite_ocurrencia': 0,
}
seguro_b = dict(seguro_a, nombre='SeguroB')  # misma capa, superpuesta

evento = {
    'id': 'e1', 'nombre': 'EventoSeguroSuperpuesto', 'activo': True,
    'freq_opcion': 3, 'prob_exito': 1.0,
    'dist_frecuencia': dist_frecuencia,
    'sev_opcion': 1, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 100_000.0, 'std': 1.0},
    'dist_severidad': dist_severidad,
    'factores_ajuste': [seguro_a, seguro_b],
}

rng = np.random.default_rng(11)
perd_tot, freq_tot, perd_evt, freq_evt = RLB.generar_lda_con_secuencialidad(
    [evento], num_simulaciones=5000, rng=rng
)

perdida_neta_media = float(perd_evt[0].mean())
print(f"  pérdida neta media reportada: {perdida_neta_media:.0f} (esperado ≈0, ya protegido por el floor)")
check(abs(perdida_neta_media) < 100,
      f"La pérdida neta reportada sigue siendo ≈0 (protegida por el floor existente) "
      f"(obtenido: {perdida_neta_media:.2f})")

msgs_ocurrencia = [m for m in mensajes_debug if 'SEGURO POR OCURRENCIA' in m and 'Pago medio seguro' in m]
check(len(msgs_ocurrencia) >= 1,
      f"Se capturó el mensaje de debug con el pago medio de seguro (obtenido: {len(msgs_ocurrencia)} mensajes)")

if msgs_ocurrencia:
    import re
    m = re.search(r"Pago medio seguro: \$([\d,]+)", msgs_ocurrencia[-1])
    check(m is not None, f"Se pudo parsear el pago medio del mensaje (obtenido: {msgs_ocurrencia[-1]!r})")
    if m:
        pago_medio = float(m.group(1).replace(',', ''))
        print(f"  Pago medio seguro combinado (2 pólizas superpuestas): ${pago_medio:,.0f}")
        check(pago_medio <= 100_000 + 100,
              f"Bug alto #9: el pago combinado de las 2 pólizas superpuestas NO supera "
              f"la pérdida bruta media (~$100.000) (obtenido: ${pago_medio:,.0f})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
