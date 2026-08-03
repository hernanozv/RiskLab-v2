"""
test_tooltip_umbral_severidad_semantica_correcta.py
=======================================================

Regresion para bug medio R4 #10 (QA ronda 4): R3 alto #8 cambió el motor
(generar_lda_con_secuencialidad) para evaluar el "umbral de severidad del
padre" de un vínculo contra la pérdida BRUTA del padre
(perdidas_brutas_por_evento, ANTES de aplicar seguros) -- justamente
para que un incidente realmente grave no dejara de disparar la cascada
solo porque un seguro redujo el monto neto por debajo del umbral. Pero
los dos tooltips de la UI que explican este campo (uno en el diálogo
"Añadir Vínculo", otro en el spinbox por-fila de la tabla de vínculos
dentro de "Agregar/Editar Evento") nunca se actualizaron: seguían
describiendo la semántica VIEJA ("pérdida NETA del padre, post-controles
y seguros"), contradiciendo el comportamiento real ya corregido del
motor -- un usuario leyendo el tooltip entendería exactamente lo
contrario de lo que realmente hace el campo.

El fix actualiza ambos tooltips para decir "pérdida BRUTA... antes de
aplicar seguros", consistente con el comentario ya existente en el
motor (generar_lda_con_secuencialidad, línea ~3221) que documenta este
mismo fix de R3 alto #8.

Este test lee el código fuente y verifica que ningún tooltip de
"umbral de severidad"/"umbral... del padre" mencione la semántica vieja
("NETA"/"post-controles"), y que ambos mencionen la semántica real
("BRUTA"/"antes de aplicar seguros"), consistente con lo que el motor
realmente evalúa (perdidas_brutas_por_evento).
"""
import os
import re
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

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
print("BUG MEDIO R4 #10: tooltips de 'umbral de severidad del padre' deben describir BRUTA, no NETA")
print("=" * 70)

with open(os.path.join(_THIS_DIR, 'Risk_Lab_Beta.py'), encoding='utf-8') as f:
    codigo = f.read()

# Localizar las líneas setToolTip(...) que hablan de "umbral" y "padre".
tooltips_umbral = [
    linea for linea in codigo.splitlines()
    if '.setToolTip(' in linea and 'padre' in linea.lower() and
    ('umbral' in linea.lower() or 'pérdida' in linea.lower() or 'perdida' in linea.lower())
]

print(f"  tooltips encontrados ({len(tooltips_umbral)}):")
for t in tooltips_umbral:
    print(f"    {t.strip()!r}")

check(len(tooltips_umbral) >= 2,
      f"Se encontraron al menos 2 tooltips relacionados con el umbral del padre "
      f"(obtenido: {len(tooltips_umbral)})")

check(all('neta' not in t.lower() for t in tooltips_umbral),
      "Bug medio R4 #10: ningún tooltip menciona la semántica vieja 'NETA'")
check(all('post-controles' not in t.lower() and 'post-seguros' not in t.lower() for t in tooltips_umbral),
      "Bug medio R4 #10: ningún tooltip menciona 'post-controles'/'post-seguros' (semántica vieja)")
check(all('bruta' in t.lower() for t in tooltips_umbral),
      "Todos los tooltips mencionan la semántica real 'BRUTA'")
check(all('antes de aplicar seguros' in t.lower() for t in tooltips_umbral),
      "Todos los tooltips aclaran explícitamente 'antes de aplicar seguros'")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
