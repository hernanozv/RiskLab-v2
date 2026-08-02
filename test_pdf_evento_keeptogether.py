"""
test_pdf_evento_keeptogether.py
===================================

Regresion para bug medio #19 (QA ronda 2): en el reporte PDF
(ResultReport._create_pdf_internal), la sección "Estadísticas por Evento
de Riesgo" agregaba el título de cada evento, su texto de vínculos (si
existen) y su tabla de estadísticas como flowables SUELTOS a la lista
`elements`. Con 20+ eventos, reportlab puede insertar un salto de página
justo entre el título y su tabla (el título queda "huérfano" al final de
una página, la tabla recién en la siguiente), sin ninguna relación visual
entre ambos para el lector.

El fix agrupa el título + vínculos + tabla de cada evento en un único
flowable KeepTogether, que reportlab nunca parte entre dos páginas (si no
entra completo en el espacio restante, lo mueve entero a la página
siguiente).

Este test intercepta SimpleDocTemplate.build (para no renderizar un PDF
real, solo inspeccionar los flowables construidos) y verifica que, para
cada uno de 25 eventos, existe un KeepTogether que agrupa el título del
evento junto con su tabla de estadísticas.
"""
import os
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

import numpy as np
from reportlab.platypus import SimpleDocTemplate, KeepTogether, Paragraph, Table

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
print("BUG MEDIO #19: título de evento y su tabla deben viajar juntos (KeepTogether)")
print("=" * 70)

N = 500
rng = np.random.default_rng(0)
N_EVENTOS = 25

eventos = []
perdidas_por_evento = []
frecuencias_por_evento = []
perdidas_totales = np.zeros(N)
frecuencias_totales = np.ones(N, dtype=int) * N_EVENTOS

for i in range(N_EVENTOS):
    perd = rng.uniform(0, 100_000, N)
    perdidas_por_evento.append(perd)
    frecuencias_por_evento.append(np.ones(N, dtype=int))
    perdidas_totales = perdidas_totales + perd
    eventos.append({'id': f'e{i}', 'nombre': f'Evento {i:02d}', 'vinculos': []})

report = RLB.ResultReport(perdidas_totales, frecuencias_totales,
                          perdidas_por_evento, frecuencias_por_evento, eventos)

capturado = {}
_build_original = SimpleDocTemplate.build


def _fake_build(self, elements, *a, **kw):
    capturado['elements'] = elements


SimpleDocTemplate.build = _fake_build
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_pdf = os.path.join(tmpdir, 'reporte_test.pdf')
        report.create_pdf(ruta_pdf)
finally:
    SimpleDocTemplate.build = _build_original

elements = capturado.get('elements')
check(elements is not None, "Se capturó la lista de elementos del PDF")

bloques_keeptogether = [el for el in elements if isinstance(el, KeepTogether)]
check(len(bloques_keeptogether) >= N_EVENTOS,
      f"Bug medio #19: hay al menos un KeepTogether por evento "
      f"(obtenido: {len(bloques_keeptogether)}, esperado >= {N_EVENTOS})")


def _texto_parrafos(flowables):
    return " ".join(f.getPlainText() for f in flowables if isinstance(f, Paragraph))


nombres_encontrados = set()
for bloque in bloques_keeptogether:
    contenido = bloque._content
    texto = _texto_parrafos(contenido)
    tiene_tabla = any(isinstance(f, Table) for f in contenido)
    for i in range(N_EVENTOS):
        nombre = f'Evento {i:02d}'
        if nombre in texto:
            check(tiene_tabla,
                  f"El bloque KeepTogether de '{nombre}' incluye tanto su título "
                  f"como su tabla de estadísticas juntos")
            nombres_encontrados.add(nombre)
            break

check(len(nombres_encontrados) == N_EVENTOS,
      f"Se encontró un bloque KeepTogether título+tabla para los {N_EVENTOS} eventos "
      f"(obtenido: {len(nombres_encontrados)})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
