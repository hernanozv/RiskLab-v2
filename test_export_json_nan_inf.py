"""
test_export_json_nan_inf.py
=============================

Regresion para bug #27: en el export JSON para análisis IA
(_escribir_export_json), el parámetro `default=self._json_default` de
json.dumps nunca llegaba a ejecutarse para valores NaN/Infinity, porque
`np.float64` es subclase de `float` y el encoder JSON estándar sabe
serializar `float` (incluidos NaN/Infinity, como los tokens NO estándar
`NaN`/`Infinity`/`-Infinity`) de forma nativa ANTES de recurrir a
`default=`. El resultado: cualquier NaN/Infinity en las estadísticas
exportadas (p.ej. de un cálculo degenerado) terminaba en el archivo como
un token literal `NaN`/`Infinity`, que no es JSON válido según el
estándar y rompe parsers estrictos (la mayoría de los lenguajes/librerías
fuera de Python/JS).

Este test verifica que, tras sanear el payload con
_sanear_nan_inf_recursivo antes de serializar, el JSON resultante:
  1. No contiene los tokens NaN/Infinity/-Infinity.
  2. Es parseable con un parser JSON estricto (que rechaza esos tokens).
  3. Preserva la intención original (NaN -> null, Infinity -> "inf",
     -Infinity -> "-inf"), incluyendo para np.float32 (que NO es
     subclase de float) via _json_default.
"""
import os
import sys
import json

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


def _parse_constant_estricto(token):
    raise ValueError(f"Token no válido en JSON estándar: {token}")


print("=" * 70)
print("BUG #27: NaN/Infinity como tokens literales en export JSON")
print("=" * 70)

sanear = RLB.RiskLabApp._sanear_nan_inf_recursivo
json_default = RLB.RiskLabApp._json_default

payload = {
    "nan_python": float('nan'),
    "inf_python": float('inf'),
    "neg_inf_python": float('-inf'),
    "nan_np64": np.float64('nan'),
    "inf_np64": np.float64('inf'),
    "inf_np32": np.float32('inf'),  # np.float32 NO es subclase de float
    "valor_normal": 1234.5,
    "entero_np": np.int64(42),
    "anidado": {
        "lista": [1.0, float('nan'), np.float64('-inf')],
    },
}

# --- 1. Sin el fix (solo default=_json_default, sin sanear primero):
#        reproduce el bug para los valores basados en 'float' nativo/np.float64 ---
json_str_bug = json.dumps(payload, default=json_default)
check('NaN' in json_str_bug or 'Infinity' in json_str_bug,
      "Reproduccion del bug: sin sanear, el JSON crudo SI contiene tokens NaN/Infinity")
try:
    json.loads(json_str_bug, parse_constant=_parse_constant_estricto)
    check(False, "El JSON sin sanear deberia fallar con un parser estricto")
except ValueError:
    check(True, "Confirmado: el JSON sin sanear rompe un parser JSON estricto")

# --- 2. Con el fix: sanear ANTES de dumps ---
payload_saneado = sanear(payload)
json_str_fix = json.dumps(payload_saneado, default=json_default)

check('NaN' not in json_str_fix and 'Infinity' not in json_str_fix,
      "Fix bug #27: el JSON saneado NO contiene tokens NaN/Infinity")

try:
    parsed = json.loads(json_str_fix, parse_constant=_parse_constant_estricto)
    check(True, "El JSON saneado es parseable con un parser JSON estricto")
except ValueError as e:
    check(False, f"El JSON saneado deberia ser estrictamente valido: {e}")
    parsed = json.loads(json_str_fix)

check(parsed["nan_python"] is None, "NaN (float nativo) -> null")
check(parsed["inf_python"] == "inf", "Infinity (float nativo) -> 'inf'")
check(parsed["neg_inf_python"] == "-inf", "-Infinity (float nativo) -> '-inf'")
check(parsed["nan_np64"] is None, "NaN (np.float64) -> null")
check(parsed["inf_np64"] == "inf", "Infinity (np.float64) -> 'inf'")
check(parsed["inf_np32"] == "inf", "Infinity (np.float32, no-subclase de float) -> 'inf'")
check(parsed["valor_normal"] == 1234.5, "Valores normales no se alteran")
check(parsed["entero_np"] == 42, "Enteros numpy se preservan")
check(parsed["anidado"]["lista"] == [1.0, None, "-inf"],
      "El saneo recorre estructuras anidadas (dicts/listas)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
