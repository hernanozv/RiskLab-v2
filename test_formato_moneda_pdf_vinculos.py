"""
test_formato_moneda_pdf_vinculos.py
=====================================

Regresion para hallazgo bajo #2: en la descripción de vínculos dentro del
PDF de resultados, el umbral de severidad se formateaba con un f-string
crudo (f"${umbral:,}", formato en inglés "$1,234,567"), en vez de usar
currency_format() (formato "$1.234.567", el que usa el resto de la
aplicación y del mismo PDF, incluida la tabla de estadísticas del evento
apenas debajo de esa misma línea). El resultado era un PDF con dos
convenciones de separador de miles/decimales mezcladas en la misma página.

No se genera un PDF completo en este test (es costoso: requiere reportlab
+ matplotlib + datos de simulación reales); en cambio se verifica, por
inspección del código fuente, que la línea que compone el texto del umbral
usa currency_format() y no un f-string crudo con separador de miles.
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
print("Hallazgo bajo #2: formato de moneda consistente en PDF (vínculos)")
print("=" * 70)

# --- 1. currency_format produce el formato Latinoamericano usado en toda
#        la app (separador de miles '.', sin separador de decimales aca) ---
check(RLB.currency_format(1234567) == '$1.234.567',
      f"currency_format(1234567) produce '$1.234.567' (obtenido: {RLB.currency_format(1234567)!r})")

# --- 2. La linea que arma el texto del umbral en la descripcion de
#        vinculos del PDF usa currency_format(), no un f-string crudo con
#        separador de miles en ingles ---
ENGINE_FILE = os.path.join(_THIS_DIR, 'Risk_Lab_Beta.py')
with open(ENGINE_FILE, 'r', encoding='utf-8') as f:
    lineas = f.readlines()

lineas_umbral = [l for l in lineas if 'umbral:' in l and 'desc +=' in l]
check(len(lineas_umbral) == 1,
      f"Se encuentra exactamente una línea que arma el texto del umbral (encontradas: {len(lineas_umbral)})")

if lineas_umbral:
    linea = lineas_umbral[0]
    check('currency_format(' in linea,
          f"La línea usa currency_format() (línea: {linea.strip()!r})")
    check(':,}' not in linea and ':,}"' not in linea,
          f"La línea NO usa un f-string crudo con separador de miles en inglés "
          f"(línea: {linea.strip()!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
