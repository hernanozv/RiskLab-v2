"""
test_umbrales_riesgo_unicos.py
===============================

Regresion para bug #24: los umbrales de riesgo (bajo/moderado/alto) estaban
definidos en un dict compartido (_UMBRALES_RIESGO_USD) pero los gráficos
Termómetro, Semáforo y Calendario de Riesgo los hardcodeaban por separado
como literales ($3M/$32M/$110M), en vez de leer el dict. Si alguien
actualizaba el dict (p.ej. para recalibrar los umbrales de negocio) sin
tocar los 3 lugares hardcodeados, los gráficos quedaban desincronizados
entre sí y con el resto de la app sin ningún error visible.

Este test verifica, por inspección del código fuente, que los valores
numéricos de los umbrales aparecen EXCLUSIVAMENTE en la definición del
dict compartido y en ningún otro lugar del archivo.
"""
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
ENGINE_FILE = os.path.join(_THIS_DIR, 'Risk_Lab_Beta.py')

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
print("BUG #24: Umbrales de riesgo con fuente única")
print("=" * 70)

with open(ENGINE_FILE, 'r', encoding='utf-8') as f:
    lineas = f.readlines()

VALORES = ["3_000_000", "32_000_000", "110_000_000"]

for valor in VALORES:
    lineas_con_valor = [
        (i + 1, l) for i, l in enumerate(lineas)
        if valor in l and not l.strip().startswith('#')
    ]
    # La única línea permitida es la definición del dict _UMBRALES_RIESGO_USD
    lineas_fuera_del_dict = [
        (n, l) for n, l in lineas_con_valor
        if '_UMBRALES_RIESGO_USD' not in "".join(lineas[max(0, n - 4):n])
    ]
    check(len(lineas_fuera_del_dict) == 0,
          f"'{valor}' no aparece hardcodeado fuera de _UMBRALES_RIESGO_USD "
          f"(encontrado en líneas: {[n for n, _ in lineas_fuera_del_dict]})")

# Y que los 3 gráficos efectivamente LEEN del dict compartido
import Risk_Lab_Beta as RLB  # noqa: E402

src = "".join(lineas)
idx_dict = src.find('_UMBRALES_RIESGO_USD = {')
check(idx_dict != -1, "Se encuentra la definición del dict _UMBRALES_RIESGO_USD")

usos_del_dict = src.count('_UMBRALES_RIESGO_USD["bajo"]') + src.count("_UMBRALES_RIESGO_USD['bajo']")
check(usos_del_dict >= 3,
      f"El dict compartido se lee en al menos 3 lugares (encontrado: {usos_del_dict})")

check(RLB._UMBRALES_RIESGO_USD == {"bajo": 3_000_000, "moderado": 32_000_000, "alto": 110_000_000},
      "Los valores del dict compartido son los esperados")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
