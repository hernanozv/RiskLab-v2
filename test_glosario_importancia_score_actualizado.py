"""
test_glosario_importancia_score_actualizado.py
==================================================

Regresion para bug alto R4 #3 (QA ronda 4): la fórmula de
'importancia_score' fue cambiada de "ImpactoP90 x FrecuenciaModo" a
"ImpactoMedio" en R3 crítico #4 (porque la fórmula vieja colapsaba a 0
para eventos de baja frecuencia/alta severidad), y el propio campo
'importancia_formula' del payload ya refleja ese cambio -- pero el
glosario embebido ai_agent_briefing.glosario_metricas_clave.Importancia_score
(pensado justamente para que un agente IA no necesite contexto externo)
seguía describiendo la fórmula VIEJA, contradiciendo al propio payload
en el MISMO archivo. También se corrigió EXPORT_SCHEMA.md, que tenía el
mismo problema.

Este test verifica que el glosario embebido en Risk_Lab_Beta.py ya NO
mencione "FrecuenciaModo" (la fórmula vieja) para Importancia_score, y
que EXPORT_SCHEMA.md tampoco la mencione.
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
print("BUG ALTO R4 #3: glosario embebido de Importancia_score debe estar actualizado")
print("=" * 70)

texto_glosario = RLB._AI_BRIEFING_ES["glosario_metricas_clave"]["Importancia_score"]
print(f"  glosario: {texto_glosario!r}")

check('FrecuenciaModo' not in texto_glosario,
      f"Bug alto R4 #3: el glosario embebido ya NO menciona la fórmula vieja "
      f"'FrecuenciaModo' (obtenido: {texto_glosario!r})")
check('ImpactoMedio' in texto_glosario or 'pérdida media anual' in texto_glosario.lower(),
      f"El glosario menciona la fórmula real actual (ImpactoMedio) "
      f"(obtenido: {texto_glosario!r})")

with open(os.path.join(_THIS_DIR, 'EXPORT_SCHEMA.md'), encoding='utf-8') as f:
    schema_md = f.read()

check('ImpactoP90 x FrecuenciaModo' not in schema_md,
      "Bug alto R4 #3: EXPORT_SCHEMA.md ya NO menciona la fórmula vieja "
      "'ImpactoP90 x FrecuenciaModo'")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
