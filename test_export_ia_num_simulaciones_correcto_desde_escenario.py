"""
test_export_ia_num_simulaciones_correcto_desde_escenario.py
===============================================================

Regresion para bug alto R4 #2 (QA ronda 4): configuration.num_simulaciones
en el export IA podia NO corresponder a la corrida real cuando se
ejecuto desde la pestaña Escenarios. ejecutar_simulacion_escenario()
sincroniza temporalmente self.num_simulaciones_var (pestaña
"Simulacion") con el valor de la pestaña "Escenarios", lanza el hilo
ASINCRONO via self.ejecutar_simulacion(), y en su bloque `finally`
RESTAURA self.num_simulaciones_var al valor original de "Simulacion"
ANTES de que el hilo termine. Cuando el usuario exporta mas tarde (con
self.resultados_simulacion ya poblado por el hilo), _construir_export_payload_ia
leia self.num_simulaciones_var.text(), que ya habia vuelto al valor de
"Simulacion", no al usado realmente para el escenario.

El fix usa directamente `n_sim` (= perdidas_totales.size, el conteo REAL
de simulaciones de esta corrida) en vez de leer el textbox de la UI, que
puede estar desincronizado del resultado real en cualquier momento.

Este test simula el escenario exacto reportado: pestaña "Simulacion"
con un valor, pero resultados_simulacion con una cantidad DISTINTA de
simulaciones (como quedaria tras ejecutar_simulacion_escenario), y
verifica que el export IA reporte el conteo REAL, no el de la pestaña
"Simulacion".
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np
from PyQt5 import QtWidgets

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


app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

print("=" * 70)
print("BUG ALTO R4 #2: num_simulaciones del export IA debe reflejar la corrida real")
print("=" * 70)

evento = {'id': 'e1', 'nombre': 'EventoA', 'activo': True}

win = RLB.RiskLabApp()
win.eventos_riesgo = [evento]

# Pestaña "Simulación" quedó en 5000 (valor YA restaurado por el finally
# de ejecutar_simulacion_escenario, distinto del realmente usado).
win.num_simulaciones_var.setText("5000")

# La corrida REAL (desde la pestaña Escenarios) usó 12000 simulaciones.
N_REAL = 12000
perdidas_totales = np.full(N_REAL, 1000.0)
frecuencias_totales = np.ones(N_REAL, dtype=int)
win.resultados_simulacion = {
    'perdidas_totales': perdidas_totales,
    'frecuencias_totales': frecuencias_totales,
    'perdidas_por_evento': [perdidas_totales.copy()],
    'frecuencias_por_evento': [frecuencias_totales.copy()],
    'eventos_riesgo': [evento],
}
win.current_scenario = None

payload = win._construir_export_payload_ia({})

num_sim_reportado = payload['configuration']['num_simulaciones']
n_real_en_resultados = payload['results']['aggregate']['perdidas_totales']['n']

print(f"  pestaña 'Simulación': 5000 | corrida real: {N_REAL} | "
      f"configuration.num_simulaciones reportado: {num_sim_reportado}")

check(n_real_en_resultados == N_REAL,
      f"Precondición: results.aggregate...n refleja la corrida real "
      f"(obtenido: {n_real_en_resultados})")
check(num_sim_reportado == N_REAL,
      f"Bug alto R4 #2: configuration.num_simulaciones coincide con la corrida "
      f"real ({N_REAL}), no con el valor desincronizado de la pestaña Simulación "
      f"(5000) (obtenido: {num_sim_reportado})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
