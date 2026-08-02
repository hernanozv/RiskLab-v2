"""
test_preview_probabilidad_ajustada_piso.py
=============================================

Regresion para bug alto #7 (QA ronda 2): el preview de "probabilidad/
frecuencia ajustada" que se muestra en tiempo real dentro del diálogo
"Editar Evento de Riesgo" (actualizar_probabilidad_ajustada, dentro de
editar_evento_popup) no aplicaba los mismos pisos de seguridad que el
motor de simulación real (modelo estático, generar_lda_con_secuencialidad):

  - El motor real clipea cada impacto individual a >= -99% antes de
    multiplicar, y el factor_multiplicativo final a >= 0.01 (mínimo 1% de
    la frecuencia/probabilidad original).
  - El preview multiplicaba los impactos SIN ningún piso.

Con 3 controles de -99% cada uno (una configuración perfectamente válida
desde la UI), el factor real sin clipear da (1-0.99)^3 = 1e-6. El motor
real lo clipea a 0.01 antes de usarlo (reduce la frecuencia real solo
100x), pero el preview mostraba una frecuencia ajustada calculada con el
1e-6 SIN clipear — 10.000 veces menor a la que el motor realmente simula.
Un analista viendo el preview creería haber "eliminado casi todo el
riesgo" cuando el motor retiene el piso del 1%.

Este test abre el diálogo real "Editar Evento" (headless, QT_QPA_PLATFORM=
offscreen) sobre un evento Poisson con 3 factores estáticos de -99% cada
uno, dispara el recálculo del preview, y compara el valor mostrado contra
el que el motor de simulación real efectivamente utiliza.
"""
import os
import re
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
print("BUG ALTO #7: preview de frecuencia ajustada no aplica el piso del motor")
print("=" * 70)

TASA_ORIGINAL = 12.0
FACTORES = [
    {'nombre': 'ControlA', 'impacto_porcentual': -99, 'activo': True},
    {'nombre': 'ControlB', 'impacto_porcentual': -99, 'activo': True},
    {'nombre': 'ControlC', 'impacto_porcentual': -99, 'activo': True},
]

evento = {
    'id': 'e1', 'nombre': 'EventoTest', 'activo': True,
    'sev_opcion': 2, 'sev_input_method': 'direct',
    'sev_params_direct': {'mean': 1000.0, 'std': 100.0},
    'freq_opcion': 1, 'tasa': TASA_ORIGINAL,
    'factores_ajuste': FACTORES,
}

win = RLB.RiskLabApp()
win.eventos_riesgo = [evento]

resultado = {}


def _fake_exec(self):
    # Encontrar el combobox de frecuencia (contiene las 5 opciones conocidas)
    freq_combobox = None
    for combo in self.findChildren(QtWidgets.QComboBox):
        items = [combo.itemText(i) for i in range(combo.count())]
        if items == ['Poisson', 'Binomial', 'Bernoulli', 'Poisson-Gamma', 'Beta']:
            freq_combobox = combo
            break
    assert freq_combobox is not None, "No se encontró el combobox de frecuencia"

    # Disparar manualmente el recálculo del preview (mismo signal que se
    # conecta a actualizar_probabilidad_ajustada en la app real).
    freq_combobox.currentIndexChanged.emit(freq_combobox.currentIndex())

    # Buscar el QLabel que muestra el preview de "λ base: ... Ajustada: ..."
    label_preview = None
    for label in self.findChildren(QtWidgets.QLabel):
        if 'λ base' in label.text():
            label_preview = label
            break
    resultado['texto'] = label_preview.text() if label_preview else None
    return QtWidgets.QDialog.Rejected


QtWidgets.QDialog.exec_ = _fake_exec
try:
    win.editar_evento_popup(new=False, row=0)
finally:
    del QtWidgets.QDialog.exec_

texto_preview = resultado.get('texto')
check(texto_preview is not None, f"El preview de λ se generó (obtenido: {texto_preview!r})")

m = re.search(r'Ajustada:\s*([\d.]+)', texto_preview or '')
check(m is not None, f"El texto del preview tiene el formato esperado (obtenido: {texto_preview!r})")
tasa_ajustada_preview = float(m.group(1)) if m else None

# Valor que el motor REAL usaría: factor_multiplicativo con el mismo piso
# que generar_lda_con_secuencialidad aplica en el modelo estático
# (cada impacto clipeado a >=-99%, factor final clipeado a >=0.01).
factor_esperado = 1.0
for f in FACTORES:
    impacto = max(f['impacto_porcentual'], -99)
    factor_esperado *= (1 + impacto / 100.0)
factor_esperado = max(factor_esperado, 0.01)
tasa_ajustada_motor_real = TASA_ORIGINAL * factor_esperado

check(abs(factor_esperado - 0.01) < 1e-9,
      f"Precondición: 3 factores de -99% dan factor sin piso 1e-6, "
      f"pero el motor real lo clipea a 0.01 (obtenido: {factor_esperado})")

if tasa_ajustada_preview is not None:
    ratio = tasa_ajustada_preview / tasa_ajustada_motor_real if tasa_ajustada_motor_real else None
    check(abs(tasa_ajustada_preview - tasa_ajustada_motor_real) < 1e-6,
          f"Bug alto #7: el preview ({tasa_ajustada_preview}) coincide con lo que el motor "
          f"real simula ({tasa_ajustada_motor_real}), en vez de mostrar un valor "
          f"~10.000x menor (ratio preview/motor_real: {ratio})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
