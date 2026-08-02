"""
test_avisos_riesgo_buffer_global.py
=======================================

Regresion para bug critico #2 (QA ronda 3): en un ejecutable empaquetado
con PyInstaller en modo "windowed" (Risk_Lab_Beta.spec con console=False),
sys.stderr puede ser None. El modulo warnings de la libreria estandar
maneja ese caso de forma EXPLICITA: si sys.stderr is None,
warnings.warn() descarta el aviso en silencio (sin excepcion, sin ningun
rastro). Esto volvia invisibles en produccion a TODOS los avisos de las
categorias RiskLab* (cap de frecuencia, fallback de rejection sampling,
fallback generico, ajuste imperfecto de Gamma/Beta), aunque el motor
siguiera aplicando correctamente sus salvaguardas matematicas.

El fix instala un warnings.showwarning propio que:
  1. Nunca depende exclusivamente de sys.stderr: siempre deja un rastro
     en un buffer en memoria (_riesgo_warnings_buffer), aunque
     sys.stderr sea None o cualquier objeto sin soporte para .write().
  2. SimulacionThread.run() y los 2 puntos donde el dialogo de
     evento/escenario calcula el ajuste Gamma/Beta ahora leen ese buffer
     (via _drenar_avisos_riesgo_desde) y muestran un QMessageBox.warning
     al usuario, sin depender de que warnings.warn() haya llegado a la
     consola.

Este test verifica, sin necesidad de un build empaquetado real:
  A. Con sys.stderr=None, un warnings.warn(RiskLabFallbackWarning) NO
     lanza excepcion (antes de este fix, el modulo warnings SI logueaba
     silenciosamente sin excepcion, pero SIN dejar ningun rastro
     recuperable; ahora ademas queda en el buffer).
  B. El mensaje queda efectivamente recuperable via
     _drenar_avisos_riesgo_desde, incluso con sys.stderr=None.
  C. generar_lda_con_secuencialidad, al disparar
     RiskLabRejectionFallbackWarning (freq_limite_superior muy bajo
     frente a una tasa alta), deja ese aviso en el buffer global,
     recuperable con una marca de indice tomada antes de la llamada
     (el mismo patron que usa SimulacionThread.run()).
"""
import os
import sys
import warnings
import numpy as np

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
print("BUG CRÍTICO #2 (R3): warnings invisibles con sys.stderr=None")
print("=" * 70)

# --- A y B: sys.stderr=None no debe hacer que el aviso desaparezca sin rastro ---
stderr_original = sys.stderr
idx_inicio = RLB._indice_actual_avisos_riesgo()
excepcion_lanzada = None
try:
    sys.stderr = None
    warnings.warn(
        "Mensaje de prueba con sys.stderr=None",
        RLB.RiskLabFallbackWarning,
        stacklevel=2
    )
except Exception as e:
    excepcion_lanzada = e
finally:
    sys.stderr = stderr_original

check(excepcion_lanzada is None,
      f"Bug crítico #2: warnings.warn con sys.stderr=None no lanza excepción "
      f"(obtenido: {excepcion_lanzada!r})")

avisos_nuevos, _ = RLB._drenar_avisos_riesgo_desde(idx_inicio)
mensajes = [m for c, m in avisos_nuevos if c == 'RiskLabFallbackWarning']
check(any("Mensaje de prueba con sys.stderr=None" in m for m in mensajes),
      f"Bug crítico #2: el aviso queda recuperable en el buffer global aunque "
      f"sys.stderr fuera None en el momento de emitirlo "
      f"(obtenido: {mensajes})")

# --- C: RiskLabRejectionFallbackWarning durante la simulación real queda en el buffer ---
dist_frecuencia = RLB.generar_distribucion_frecuencia(1, tasa=1000.0)
dist_severidad = RLB.generar_distribucion_severidad(
    1, 100.0, 500.0, 1000.0, input_method='min_mode_max'
)
evento = {
    'id': 'e1', 'nombre': 'EventoRejectionFallback', 'activo': True,
    'freq_opcion': 1, 'tasa': 1000.0,
    'freq_limite_superior': 1,  # cap absurdamente bajo frente a tasa=1000
    'dist_frecuencia': dist_frecuencia,
    'sev_opcion': 1,
    'sev_minimo': 100.0, 'sev_mas_probable': 500.0, 'sev_maximo': 1000.0,
    'dist_severidad': dist_severidad,
}

idx_inicio_2 = RLB._indice_actual_avisos_riesgo()
rng = np.random.default_rng(7)
# NOTA: no usar simplefilter("ignore") aca -- eso suprime el warning ANTES de
# que llegue a showwarning (y por lo tanto antes de que nuestro buffer lo
# capture), que es exactamente lo opuesto de lo que este test necesita
# verificar.
RLB.generar_lda_con_secuencialidad([evento], num_simulaciones=500, rng=rng)

avisos_rejection, _ = RLB._drenar_avisos_riesgo_desde(idx_inicio_2)
mensajes_rejection = [m for c, m in avisos_rejection if c == 'RiskLabRejectionFallbackWarning']
check(len(mensajes_rejection) > 0,
      f"Bug crítico #2: RiskLabRejectionFallbackWarning (freq_limite_superior=1 "
      f"con tasa=1000) queda en el buffer global, recuperable con una marca de "
      f"índice tomada antes de la llamada (obtenido: {len(mensajes_rejection)} avisos)")

# --- Verificar que SimulacionThread.run() efectivamente toma esa marca de índice ---
import inspect
src_run = inspect.getsource(RLB.SimulacionThread.run)
check("_indice_actual_avisos_riesgo" in src_run and "avisos_riesgo_indice_inicio" in src_run,
      "SimulacionThread.run() toma una marca de índice del buffer de avisos "
      "al iniciar (self.avisos_riesgo_indice_inicio)")

src_completada = inspect.getsource(RLB.RiskLabApp.simulacion_completada)
check("_drenar_avisos_riesgo_desde" in src_completada,
      "simulacion_completada lee el buffer de avisos acumulados durante la corrida "
      "y los muestra al usuario")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
