"""
test_preview_sev_freq_aplica_pisos_motor.py
===============================================

Regresion para bug medio #19 (QA ronda 3): la vista previa de
"Escalamiento de Severidad por Frecuencia" (_actualizar_preview, dentro
de _crear_seccion_escalamiento_ui) calculaba los multiplicadores SIN
aplicar los mismos pisos que el motor real
(generar_lda_con_secuencialidad): paso >= 0, base >= 1, factor_max >= 1
(fixes de rondas anteriores para que valores fuera de rango no inviertan
o anulen el escalamiento).

Con "Incremento por ocurrencia" (paso) = -0.5, la vista previa mostraba
una curva DECRECIENDO hasta valores negativos (×1.0 → ×0.5 → ×0.0 →
×-0.5 → ...), pero el motor real, al aplicar paso=max(0.0,-0.5)=0.0,
usa multiplicador ×1.0 FIJO para todas las ocurrencias (sin ningún
escalamiento) -- el usuario ve una preview que no corresponde a lo que
realmente va a pasar en la simulación.

Este test construye la sección de UI real (headless, sin diálogo
completo), fuerza paso=-0.5 en el modo Lineal, y verifica que la
vista previa muestre multiplicadores constantes en ×1.0 (el piso real
del motor), no una curva decreciente/negativa.
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
print("BUG MEDIO #19: preview de escalamiento debe usar los mismos pisos que el motor")
print("=" * 70)

host = QtWidgets.QWidget()
layout = QtWidgets.QVBoxLayout(host)

evento_data = {
    'sev_freq_activado': True,
    'sev_freq_modelo': 'reincidencia',
    'sev_freq_tipo_escalamiento': 'lineal',
    'sev_freq_paso': 0.5,
    'sev_freq_factor_max': 5.0,
    # Valores distintos de '0.5' para no confundir la búsqueda de paso_var
    # (por texto pre-cargado) con alpha_var, que por default también es 0.5.
    'sev_freq_alpha': 0.777,
    'sev_freq_base': 1.234,
}
config, on_freq_changed = RLB._crear_seccion_escalamiento_ui(layout, evento_data)
on_freq_changed(1)  # Poisson: el escalamiento por frecuencia SI aplica

activar_check = next(w for w in host.findChildren(QtWidgets.QCheckBox)
                     if 'activar' in w.objectName().lower() or True)
# Buscar por texto pre-cargado en vez de objectName (no seteado explicitamente)
line_edits = host.findChildren(QtWidgets.QLineEdit)
paso_var = next(w for w in line_edits if w.text() == '0.5')
preview_label = next(w for w in host.findChildren(QtWidgets.QLabel) if w.text().startswith('📊'))

texto_antes = preview_label.text()
print(f"  preview con paso=0.5 (válido): {texto_antes!r}")
check('×1.5' in texto_antes and '×3.0' in texto_antes,
      f"Precondición: con paso=0.5 válido, la preview muestra un escalamiento creciente real "
      f"(obtenido: {texto_antes!r})")

# Forzar paso=-0.5 (fuera de rango): dispara textChanged -> _sync_config -> _actualizar_preview
paso_var.setText('-0.5')
texto_despues = preview_label.text()
print(f"  preview con paso=-0.5 (fuera de rango): {texto_despues!r}")

check(texto_despues != texto_antes,
      f"Precondición: el cambio de paso_var efectivamente disparó una actualización "
      f"de la preview (obtenido: antes={texto_antes!r}, después={texto_despues!r})")
check(texto_despues.count('×1.0') == 7,
      f"Bug medio #19: con paso=-0.5 (fuera de rango, motor aplica piso 0.0), "
      f"la preview muestra multiplicador CONSTANTE ×1.0 en las 7 ocurrencias, "
      f"no una curva decreciente/negativa (obtenido: {texto_despues!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
