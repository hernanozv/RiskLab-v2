"""
test_chart_validator_codigo_muerto_eliminado.py
===================================================

Regresion para bug bajo R4 #4 (QA ronda 4): RiskLabApp.verificar_graficos_interactivos()
importaba un módulo `chart_validator` que nunca existió en el repositorio
(no hay ningún archivo chart_validator.py) y llamaba a
`chart_validator.ChartValidator()`, una clase que tampoco existe. El
método además nunca estaba conectado a ningún botón/menú de la UI --
código completamente muerto e inalcanzable que, de haberse ejecutado
alguna vez, habría fallado con "No se pudo verificar: No module named
'chart_validator'".

El fix elimina el método muerto por completo (no se implementó el
módulo faltante, ya que la funcionalidad nunca estuvo conectada a
ningún punto real de la UI -- no había ningún requisito funcional que
cumplir, solo código inalcanzable referenciando una dependencia
inexistente).

Este test verifica que:
1. RiskLabApp ya no tiene el método verificar_graficos_interactivos.
2. El código fuente ya no contiene ninguna referencia a 'chart_validator'.
3. El módulo Risk_Lab_Beta se importa sin error (nada se rompió al
   eliminar el método).
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
print("BUG BAJO R4 #4: código muerto que referencia el módulo 'chart_validator' inexistente")
print("=" * 70)

check(not hasattr(RLB.RiskLabApp, 'verificar_graficos_interactivos'),
      "Bug bajo R4 #4: RiskLabApp ya NO tiene el método muerto verificar_graficos_interactivos")

with open(os.path.join(_THIS_DIR, 'Risk_Lab_Beta.py'), encoding='utf-8') as f:
    codigo = f.read()

check('chart_validator' not in codigo,
      "Bug bajo R4 #4: el código fuente ya no contiene ninguna referencia a 'chart_validator'")

check(not os.path.isfile(os.path.join(_THIS_DIR, 'chart_validator.py')),
      "Precondición: el archivo chart_validator.py nunca existió en el repo")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
