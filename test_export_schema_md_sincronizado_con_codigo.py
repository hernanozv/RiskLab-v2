"""
test_export_schema_md_sincronizado_con_codigo.py
====================================================

Regresion para bug medio R4 #6 (QA ronda 4): EXPORT_SCHEMA.md (la
documentación del formato JSON del export para IA) se había desactualizado
respecto al código real en varios campos, encontrados por una revisión
sistemática comparando cada sección documentada contra
_construir_export_payload_ia y sus helpers:

1. La tabla de `freq_opcion` documentaba `distribucion="Beta de
   probabilidad"` para freq_opcion=5, pero el código (_FREQ_DIST_NAMES[5])
   produce literalmente `"Beta"` -- un agente filtrando por el string
   documentado nunca matchearía.
2. `results.scenario_impacts.escenarios[]` siempre incluye un campo
   `_meaning` (explicación en lenguaje natural) que no estaba documentado.
3. `execution_metadata.engine_limits` (límites internos del motor y
   eventos con cap de frecuencia aplicado) no aparecía en el ejemplo ni
   se mencionaba en absoluto.
4. Los campos raíz condicionales `input_events_omitidos`/
   `input_scenarios_omitidos` no se mencionaban en la estructura raíz.
5. Cada factor de ajuste (`factores_ajuste[]`) siempre incluye un campo
   `"activo"` que faltaba en los tres ejemplos (estático/estocástico/
   seguro) del documento.
6. `escalamiento_severidad_por_frecuencia` siempre incluye TODOS los
   campos de ambos modelos (paso/base/tabla + alpha/solo_aumento/
   sistemico_factor_max), no solo los relevantes al modelo activo -- el
   ejemplo del doc solo mostraba un subconjunto.
7. `per_event[].contribucion_al_total`/`comportamiento_observado` se
   documentaban como si fueran siempre presentes, pero son condicionales.
8. `risk_map.umbrales_cuadrantes.criterio` decía `"mediana × 1.2"` en el
   doc pero el código produce `"mediana × 1.2 (calculado dinámicamente)"`.

Este test lee EXPORT_SCHEMA.md y verifica que cada una de estas 8
correcciones esté presente (y que el contenido viejo/incorrecto ya no
aparezca), y además que el string documentado para freq_opcion=5
coincida EXACTAMENTE con _FREQ_DIST_NAMES[5] real del código (para que
esta regresión no pueda volver a desincronizarse sin que el test lo note).
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

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
print("BUG MEDIO R4 #6: EXPORT_SCHEMA.md debe estar sincronizado con el código")
print("=" * 70)

with open(os.path.join(_THIS_DIR, 'EXPORT_SCHEMA.md'), encoding='utf-8') as f:
    schema_md = f.read()

# 1. freq_opcion=5 distribucion: "Beta", no "Beta de probabilidad"
nombre_real_freq5 = RLB._FREQ_DIST_NAMES[5]
check(nombre_real_freq5 == "Beta",
      f"Precondición: _FREQ_DIST_NAMES[5] es 'Beta' en el código (obtenido: {nombre_real_freq5!r})")
check('Beta de probabilidad' not in schema_md,
      "El doc ya NO usa 'Beta de probabilidad' como valor de 'distribucion' para freq_opcion=5")
check('| 5 | Beta |' in schema_md,
      "El doc documenta correctamente 'Beta' (no 'Beta de probabilidad') para freq_opcion=5")

# 2. scenario_impacts._meaning
check('_meaning' in schema_md,
      "El doc menciona el campo '_meaning' de scenario_impacts.escenarios[]")

# 3. engine_limits
check('engine_limits' in schema_md,
      "El doc menciona el bloque 'engine_limits' de execution_metadata")
check('eventos_con_cap_aplicado' in schema_md,
      "El doc menciona 'eventos_con_cap_aplicado' dentro de engine_limits")

# 4. input_events_omitidos / input_scenarios_omitidos
check('input_events_omitidos' in schema_md and 'input_scenarios_omitidos' in schema_md,
      "El doc menciona los campos raíz condicionales input_events_omitidos/input_scenarios_omitidos")

# 5. factores_ajuste[].activo
count_activo = schema_md.count('"activo": true')
check(count_activo >= 3,
      f"El doc incluye la clave 'activo' en los 3 ejemplos de factores_ajuste "
      f"(obtenido: {count_activo} ocurrencias)")

# 6. escalamiento_severidad_por_frecuencia: campos de ambos modelos
for campo in ('"base"', '"tabla"', '"alpha"', '"solo_aumento"', '"sistemico_factor_max"'):
    check(campo in schema_md,
          f"El doc incluye el campo {campo} en el ejemplo de escalamiento_severidad_por_frecuencia")

# 7. contribucion_al_total / comportamiento_observado condicionales
check('condicional' in schema_md.lower() and 'contribucion_al_total' in schema_md,
      "El doc aclara que contribucion_al_total/comportamiento_observado son condicionales")

# 8. criterio del risk_map
check('mediana × 1.2 (calculado dinámicamente)' in schema_md,
      "El doc documenta el texto EXACTO de 'criterio' que produce el código")
check(schema_md.count('"criterio": "mediana × 1.2"') == 0,
      "El doc ya NO tiene el texto viejo/incompleto de 'criterio' (sin el sufijo)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
