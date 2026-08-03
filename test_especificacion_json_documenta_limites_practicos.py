"""
test_especificacion_json_documenta_limites_practicos.py
============================================================

Regresion para bug bajo R4 #7 (QA ronda 4): ESPECIFICACION_JSON_RISK_LAB.md
(el documento fuente de verdad para que un agente IA genere archivos JSON
válidos para Risk Lab) nunca documentaba ningún límite práctico sobre la
cantidad de eventos/escenarios permitidos en un archivo, ni sobre el
tamaño del archivo en sí -- solo mencionaba el máximo recomendado de
`num_simulaciones`. Un agente generando un archivo muy grande (miles de
eventos, por ejemplo) no tenía ninguna guía sobre las implicancias
prácticas de rendimiento/memoria.

El fix agrega una sección "Límites Prácticos (Eventos, Escenarios y
Tamaño del Archivo)" que documenta explícitamente que no hay límites
duros, pero sí guías prácticas de rendimiento, incluyendo los dos
umbrales reales del motor (OCURRENCIAS_TOTALES_UMBRAL_AVISO_MEMORIA y
MAX_EVENTOS_POR_EVENTO_POR_CHUNK, ya introducidos en R4 crítico #1).

Este test verifica que:
1. El documento mencione la nueva sección de límites prácticos.
2. Los valores numéricos documentados coincidan EXACTAMENTE con las
   constantes reales del motor (para que esta documentación no se
   desincronice si esas constantes cambian en el futuro).
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


def _con_puntos_miles(n):
    return f"{n:,}".replace(",", ".")


print("=" * 70)
print("BUG BAJO R4 #7: la especificación JSON debe documentar límites prácticos")
print("=" * 70)

with open(os.path.join(_THIS_DIR, 'ESPECIFICACION_JSON_RISK_LAB.md'), encoding='utf-8') as f:
    spec_md = f.read()

check('Límites Prácticos' in spec_md,
      "El documento incluye la sección 'Límites Prácticos (Eventos, Escenarios y Tamaño del Archivo)'")
check('eventos_riesgo' in spec_md.split('Límites Prácticos', 1)[1][:2000],
      "La sección menciona explícitamente 'eventos_riesgo'")
check('scenarios' in spec_md.split('Límites Prácticos', 1)[1][:2000],
      "La sección menciona explícitamente 'scenarios'")

umbral_memoria_doc = _con_puntos_miles(RLB.OCURRENCIAS_TOTALES_UMBRAL_AVISO_MEMORIA)
umbral_chunk_doc = _con_puntos_miles(RLB.MAX_EVENTOS_POR_EVENTO_POR_CHUNK)
print(f"  umbral de aviso de memoria (código): {RLB.OCURRENCIAS_TOTALES_UMBRAL_AVISO_MEMORIA:,} -> doc: {umbral_memoria_doc!r}")
print(f"  umbral máximo por chunk (código): {RLB.MAX_EVENTOS_POR_EVENTO_POR_CHUNK:,} -> doc: {umbral_chunk_doc!r}")

check(umbral_memoria_doc in spec_md,
      f"El documento cita el umbral REAL de aviso de memoria del código "
      f"(esperado: {umbral_memoria_doc!r})")
check(umbral_chunk_doc in spec_md,
      f"El documento cita el umbral REAL de reescalado por chunk del código "
      f"(esperado: {umbral_chunk_doc!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
