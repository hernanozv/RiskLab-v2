"""
test_poliza_compartida_entre_eventos_avisa.py
=================================================

Regresion para bug critico R4 #4 (QA ronda 4): el motor calcula el
limite agregado anual (y el deducible) de una poliza de seguro POR
EVENTO de riesgo, de forma totalmente independiente entre eventos -- no
existe ningun mecanismo de "pooling" cruzado. Si el usuario configura la
MISMA poliza real (identificada por 'nombre', p.ej. "Poliza Crimen XL")
como factor de ajuste tipo 'seguro' en 2+ eventos distintos (patron de
modelado comun: una poliza que cubre varias categorias de riesgo, como
Fraude Interno y Fraude Externo), esa poliza puede terminar pagando
hasta N veces su limite nominal en la misma simulacion, subestimando
sistematicamente la perdida neta agregada, sin ningun aviso.

Implementar el pooling cruzado real requeriria rediseñar el pipeline de
seguros (hoy procesa cada evento de forma aislada), con alto riesgo de
regresion sobre logica extensamente testeada. El fix agrega una
deteccion explicita en ejecutar_simulacion: si el mismo nombre de
poliza aparece en 2+ eventos activos, se muestra un QMessageBox.warning
detallando cuales eventos comparten esa poliza, para que el usuario
pueda evaluar si es un problema real de modelado (misma poliza real) o
una coincidencia de nombre inocua.

Este test construye 2 eventos activos que comparten el mismo nombre de
poliza de seguro y verifica que ejecutar_simulacion muestre el aviso
correspondiente, mencionando ambos eventos. Tambien verifica que 2
eventos con polizas de NOMBRES DISTINTOS no disparen el aviso.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

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
print("BUG CRÍTICO R4 #4: póliza de seguro compartida entre eventos debe avisar")
print("=" * 70)


def _evento_con_seguro(id_, nombre, nombre_poliza):
    return {
        "id": id_, "nombre": nombre, "activo": True,
        "sev_opcion": 2, "sev_input_method": "direct",
        "sev_minimo": None, "sev_mas_probable": None, "sev_maximo": None,
        "sev_params_direct": {"mean": 100_000, "std": 5000},
        "freq_opcion": 1, "tasa": 2.0, "vinculos": [],
        "factores_ajuste": [{
            "nombre": nombre_poliza, "activo": True, "tipo_modelo": "estatico",
            "afecta_frecuencia": False, "afecta_severidad": True,
            "tipo_severidad": "seguro",
            "seguro_deducible": 10000, "seguro_cobertura_pct": 100,
            "seguro_limite": 1_000_000, "seguro_limite_ocurrencia": 0,
            "seguro_tipo_deducible": "agregado",
        }],
    }


class _ThreadFalso:
    def __init__(self, *a, **kw):
        self.progreso_actualizado = _SignalFalsa()
        self.simulacion_completada = _SignalFalsa()
        self.error_ocurrido = _SignalFalsa()

    def start(self):
        pass


class _SignalFalsa:
    def connect(self, *a, **kw):
        pass


RLB.SimulacionThread = _ThreadFalso

# --- Caso 1: 2 eventos comparten la MISMA póliza (mismo nombre) ---
print("\n--- Caso 1: póliza compartida entre 2 eventos ---")
win1 = RLB.RiskLabApp()
win1.eventos_riesgo = [
    _evento_con_seguro("e1", "FraudeInterno", "PolizaCrimenXL"),
    _evento_con_seguro("e2", "FraudeExterno", "PolizaCrimenXL"),
]
win1.num_simulaciones_var.setText("2000")

warnings_capturados = []
QtWidgets.QMessageBox.warning = staticmethod(
    lambda *a, **kw: warnings_capturados.append(a) or QtWidgets.QMessageBox.Ok
)

win1.ejecutar_simulacion()

texto_avisos = " ".join(str(a) for a in warnings_capturados)
check(any('PolizaCrimenXL' in str(a) and 'compartida' in str(a).lower() for a in warnings_capturados),
      f"Bug crítico R4 #4: se muestra un aviso mencionando la póliza compartida "
      f"(obtenido: {len(warnings_capturados)} avisos)")
check('FraudeInterno' in texto_avisos and 'FraudeExterno' in texto_avisos,
      "El aviso menciona AMBOS eventos que comparten la póliza")

# --- Caso 2: 2 eventos con pólizas de NOMBRES DISTINTOS (sin problema) ---
print("\n--- Caso 2: pólizas con nombres distintos (sin aviso) ---")
win2 = RLB.RiskLabApp()
win2.eventos_riesgo = [
    _evento_con_seguro("e1", "FraudeInterno", "PolizaA"),
    _evento_con_seguro("e2", "FraudeExterno", "PolizaB"),
]
win2.num_simulaciones_var.setText("2000")

warnings_capturados2 = []
QtWidgets.QMessageBox.warning = staticmethod(
    lambda *a, **kw: warnings_capturados2.append(a) or QtWidgets.QMessageBox.Ok
)

win2.ejecutar_simulacion()

check(not any('compartida' in str(a).lower() for a in warnings_capturados2),
      f"Pólizas con nombres distintos NO disparan el aviso de póliza compartida "
      f"(obtenido: {len(warnings_capturados2)} avisos)")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
