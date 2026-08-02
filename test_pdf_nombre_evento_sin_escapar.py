"""
test_pdf_nombre_evento_sin_escapar.py
========================================

Regresion para bug alto #12 (QA ronda 2): ResultReport inserta el nombre
del evento (y el nombre del evento padre en la descripción de vínculos)
directamente dentro del markup de reportlab (Paragraph). Paragraph
interpreta el texto como XML/HTML simplificado (soporta <b>, <i>, etc.);
un nombre de evento con un patrón como "<br" sin cerrar (plausible si se
copia desde Excel/HTML) generaba un error de parseo que abortaba
doc.build() COMPLETO — el PDF entero fallaba a generarse, sin ninguna
pista de qué evento o carácter lo causó.

El fix escapa (xml.sax.saxutils.escape) el nombre del evento, el nombre
del evento padre en vínculos, y el título de cada gráfico antes de
insertarlos en el markup de reportlab.

Este test construye un ResultReport con eventos cuyos nombres contienen
patrones que rompen el parser XML de reportlab (una etiqueta sin cerrar y
un '&' crudo) y verifica que create_pdf() ya NO lanza una excepción.
"""
import os
import sys
import tempfile

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


print("=" * 70)
print("BUG ALTO #12: nombres de eventos con markup roto no deben abortar el PDF")
print("=" * 70)

N = 2000
rng = np.random.default_rng(0)

perdidas_A = rng.uniform(0, 100_000, N)
perdidas_B = rng.uniform(0, 50_000, N)
perdidas_totales = perdidas_A + perdidas_B
frecuencias_totales = np.ones(N, dtype=int)

eventos = [
    # Patrón exacto del hallazgo original: una etiqueta "<br" sin cerrar,
    # plausible si el nombre se pegó desde una celda de Excel/HTML.
    {'id': 'a', 'nombre': 'Fraude interno <br importante', 'vinculos': []},
    # Un '&' crudo (otro caracter especial de XML) combinado con un vínculo
    # hacia el evento anterior, para ejercitar también el nombre del padre
    # en la descripción de vínculos.
    {'id': 'b', 'nombre': 'Riesgo Legal & Cumplimiento <tag_sin_cerrar',
     'vinculos': [{'id_padre': 'a', 'tipo': 'AND', 'probabilidad': 100,
                   'factor_severidad': 1.0, 'umbral_severidad': 0}]},
]
perdidas_por_evento = [perdidas_A, perdidas_B]
frecuencias_por_evento = [np.ones(N, dtype=int), np.ones(N, dtype=int)]

report = RLB.ResultReport(perdidas_totales, frecuencias_totales,
                          perdidas_por_evento, frecuencias_por_evento, eventos)

with tempfile.TemporaryDirectory() as tmpdir:
    ruta_pdf = os.path.join(tmpdir, 'reporte_test.pdf')
    try:
        report.create_pdf(ruta_pdf)
        check(True, "create_pdf() no lanza excepción con nombres de evento que rompen markup XML")
        check(os.path.exists(ruta_pdf) and os.path.getsize(ruta_pdf) > 0,
              f"El archivo PDF se generó y tiene contenido (tamaño: "
              f"{os.path.getsize(ruta_pdf) if os.path.exists(ruta_pdf) else 0} bytes)")
    except Exception as e:
        check(False, f"Bug alto #12: create_pdf() NO debería lanzar una excepción "
                     f"por nombres de evento con markup roto (obtenido: {e!r})")


print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
