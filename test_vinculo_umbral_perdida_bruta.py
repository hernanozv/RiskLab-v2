"""
test_vinculo_umbral_perdida_bruta.py
========================================

Regresion para bug alto #8 (QA ronda 3): 'umbral_severidad' de un vinculo
se evaluaba contra perdidas_por_evento[padre_idx], que YA es neta de
seguros (se le resta el pago del seguro antes de guardarse en ese
array). Un incidente real siempre grave en el padre podia no disparar
la cascada hacia el hijo simplemente porque el seguro redujo el valor
comparado contra el umbral -- inconsistente con la intuicion de negocio
(una cascada deberia dispararse por la magnitud REAL del incidente, no
por el remanente contable tras el reaseguro).

El fix agrega un array paralelo 'perdidas_brutas_por_evento' (pre-
seguros) usado exclusivamente para esta comparacion; 'perdidas_por_evento'
sigue siendo neta de seguros para las estadisticas reportadas.

Este test usa un padre con severidad casi determinista ($200.000) que
SIEMPRE ocurre, con un seguro por_ocurrencia (deducible $10.000,
cobertura 100%, sin limite) que reduce la perdida neta a ~$10.000. El
hijo tiene un vinculo AND con umbral_severidad=$100.000: el incidente
bruto ($200.000) supera el umbral, pero la perdida neta (~$10.000) NO.
Verifica que el hijo se activa (evaluando sobre la perdida BRUTA), no
que se quede inactivo (que es lo que pasaria evaluando sobre la neta).
"""
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

from test_robustez_simulacion import _build_evento, _simular, _vinculo, _seguro

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
print("BUG ALTO #8: umbral_severidad de vínculo debe evaluarse sobre la pérdida BRUTA del padre")
print("=" * 70)

padre = _build_evento(
    'pa', 'Padre', 3, {'probabilidad_exito': 1.0},  # Bernoulli p=1: SIEMPRE ocurre
    1, {'minimo': None, 'mas_probable': None, 'maximo': None,
        'input_method': 'direct',
        'params_direct': {'mean': 200_000.0, 'std': 1.0}},  # severidad ~determinista
    factores_ajuste=[_seguro(deducible=10_000, cobertura_pct=1.0, limite=0,
                              tipo_deducible='por_ocurrencia')]
)
hijo = _build_evento(
    'hi', 'Hijo', 1, {'tasa': 10.0},
    2, {'minimo': None, 'mas_probable': None, 'maximo': None,
        'input_method': 'direct',
        'params_direct': {'mean': 100, 'std': 10}},
    vinculos=[_vinculo('pa', tipo='AND', probabilidad=100, umbral_severidad=100_000)]
)

_, _, perd_evt, freq_evt = _simular([padre, hijo], num_sims=20_000, seed=700)

perdida_neta_padre = perd_evt[0].mean()
media_freq_hijo = freq_evt[1].mean()
print(f"  pérdida neta media del padre (post-seguro): {perdida_neta_padre:.0f}")
print(f"  frecuencia media del hijo (con vínculo AND, umbral=100.000): {media_freq_hijo:.3f}")

check(perdida_neta_padre < 100_000,
      f"Precondición: la pérdida NETA del padre (post-seguro) queda por debajo "
      f"del umbral de 100.000 (obtenido: {perdida_neta_padre:.0f})")

check(media_freq_hijo > 5.0,
      f"Bug alto #8: el hijo SÍ se activa (umbral evaluado sobre la pérdida BRUTA "
      f"del padre, ~200.000, que supera 100.000), aunque la pérdida neta post-seguro "
      f"esté por debajo del umbral (obtenido freq_hijo={media_freq_hijo:.3f}, "
      f"esperado ≈10.0 si el vínculo se activa siempre; antes del fix hubiera "
      f"dado ≈0 porque la pérdida neta no supera el umbral)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
