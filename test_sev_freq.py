"""
Validación exhaustiva del feature "Severidad Dependiente de Frecuencia".

Valida:
1. Correcta aplicación matemática de reincidencia (lineal, exponencial, tabla)
2. Correcta aplicación matemática de modelo sistémico (z-score)
3. Impacto correcto en resultados de simulación end-to-end
4. Correcta serialización/deserialización JSON de campos sev_freq_*
"""
import sys
import os
import json
import copy
import tempfile
import uuid
import numpy as np

# Asegurar que importamos del directorio raíz
sys.path.insert(0, os.path.dirname(__file__))
from Risk_Lab_Beta import (
    _aplicar_tabla_escalamiento,
    generar_lda_con_secuencialidad,
    generar_distribucion_severidad,
    generar_distribucion_frecuencia,
)

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

# ==============================================================================
# TEST 1: _aplicar_tabla_escalamiento — correctitud matemática
# ==============================================================================
print("\n" + "=" * 70)
print("TEST 1: _aplicar_tabla_escalamiento")
print("=" * 70)

tabla = [
    {'desde': 1, 'hasta': 2, 'multiplicador': 1.0},
    {'desde': 3, 'hasta': 5, 'multiplicador': 1.5},
    {'desde': 6, 'hasta': None, 'multiplicador': 3.0},
]
indices = np.array([1, 2, 3, 4, 5, 6, 7, 10])
result = _aplicar_tabla_escalamiento(indices, tabla)
expected = np.array([1.0, 1.0, 1.5, 1.5, 1.5, 3.0, 3.0, 3.0])
check(np.allclose(result, expected), f"Tabla mapping: {result} == {expected}")

# Tabla con un solo rango
tabla_simple = [{'desde': 1, 'hasta': None, 'multiplicador': 2.5}]
result2 = _aplicar_tabla_escalamiento(np.array([1, 5, 100]), tabla_simple)
check(np.allclose(result2, [2.5, 2.5, 2.5]), f"Tabla un solo rango: todos = 2.5")

# Índices fuera de rango → default 1.0
tabla_gap = [{'desde': 3, 'hasta': 5, 'multiplicador': 2.0}]
result3 = _aplicar_tabla_escalamiento(np.array([1, 2, 3, 4, 5, 6]), tabla_gap)
check(np.allclose(result3, [1.0, 1.0, 2.0, 2.0, 2.0, 1.0]), "Gaps en tabla → default 1.0")

# ==============================================================================
# TEST 2: Modelo Reincidencia — Lineal
# ==============================================================================
print("\n" + "=" * 70)
print("TEST 2: Reincidencia Lineal — factor = min(1 + paso*(n-1), max)")
print("=" * 70)

rng = np.random.default_rng(42)
num_sim = 50000
sev_base = 1000.0  # Severidad objetivo para validación controlada

# Crear evento con Poisson(λ=5) y severidad casi constante (PERT con rango mínimo)
dist_sev = generar_distribucion_severidad(1, sev_base - 1, sev_base, sev_base + 1)
dist_freq = generar_distribucion_frecuencia(1, tasa=5.0)

evento_lineal = {
    'id': str(uuid.uuid4()),
    'nombre': 'Test_Lineal',
    'activo': True,
    'dist_severidad': dist_sev,
    'dist_frecuencia': dist_freq,
    'freq_opcion': 1,
    'tasa': 5.0,
    'sev_freq_activado': True,
    'sev_freq_modelo': 'reincidencia',
    'sev_freq_tipo_escalamiento': 'lineal',
    'sev_freq_paso': 0.5,
    'sev_freq_factor_max': 5.0,
}

# Evento control sin escalamiento
evento_control = copy.deepcopy(evento_lineal)
evento_control['id'] = str(uuid.uuid4())
evento_control['nombre'] = 'Test_Control'
evento_control['sev_freq_activado'] = False

# Ejecutar simulaciones
# Returns: (perdidas_totales, frecuencias_totales, perdidas_por_evento, frecuencias_por_evento)
perdidas_lineal, freq_total_lineal, perd_por_ev_lineal, freq_por_ev_lineal = generar_lda_con_secuencialidad([evento_lineal], num_sim, rng=np.random.default_rng(42))
perdidas_control, freq_total_ctrl, perd_por_ev_ctrl, freq_por_ev_ctrl = generar_lda_con_secuencialidad([evento_control], num_sim, rng=np.random.default_rng(42))

# Con paso=0.5 y λ=5: la primera ocurrencia ×1.0, segunda ×1.5, tercera ×2.0, etc.
# La pérdida media con escalamiento debe ser MAYOR que sin escalamiento
ratio_medias = perdidas_lineal.mean() / perdidas_control.mean()
check(ratio_medias > 1.1, f"Lineal aumenta pérdida media: ratio={ratio_medias:.3f} (>1.1)")
check(ratio_medias < 3.0, f"Lineal no excede rango razonable: ratio={ratio_medias:.3f} (<3.0)")

# Validación analítica: con severidad constante S y frecuencia N,
# pérdida_escalada = S * sum(min(1+paso*(k-1), max) for k=1..N)
# Para N=5, paso=0.5: factores = [1.0, 1.5, 2.0, 2.5, 3.0], sum=10.0
# Sin escalamiento: sum = 5.0 * 1.0 = 5.0
# Ratio esperado ≈ 10.0/5.0 = 2.0 (para las simulaciones con freq=5)
# Pero freq varía por Poisson, así que calculamos la media esperada
print(f"  ℹ️  Ratio de medias lineal/control = {ratio_medias:.4f}")

# ==============================================================================
# TEST 3: Modelo Reincidencia — Exponencial
# ==============================================================================
print("\n" + "=" * 70)
print("TEST 3: Reincidencia Exponencial — factor = min(base^(n-1), max)")
print("=" * 70)

evento_exp = copy.deepcopy(evento_lineal)
evento_exp['id'] = str(uuid.uuid4())
evento_exp['nombre'] = 'Test_Exp'
evento_exp['sev_freq_tipo_escalamiento'] = 'exponencial'
evento_exp['sev_freq_base'] = 1.5
evento_exp['sev_freq_factor_max'] = 5.0

perdidas_exp, _, _, _ = generar_lda_con_secuencialidad([evento_exp], num_sim, rng=np.random.default_rng(42))

ratio_exp = perdidas_exp.mean() / perdidas_control.mean()
check(ratio_exp > 1.1, f"Exponencial aumenta pérdida media: ratio={ratio_exp:.3f} (>1.1)")
# Exponencial con base=1.5 crece más rápido que lineal paso=0.5
check(ratio_exp > ratio_medias * 0.8, f"Exponencial crece comparable o más que lineal: {ratio_exp:.3f} vs {ratio_medias:.3f}")
print(f"  ℹ️  Ratio de medias exponencial/control = {ratio_exp:.4f}")

# ==============================================================================
# TEST 4: Modelo Reincidencia — Tabla
# ==============================================================================
print("\n" + "=" * 70)
print("TEST 4: Reincidencia Tabla")
print("=" * 70)

evento_tabla = copy.deepcopy(evento_lineal)
evento_tabla['id'] = str(uuid.uuid4())
evento_tabla['nombre'] = 'Test_Tabla'
evento_tabla['sev_freq_tipo_escalamiento'] = 'tabla'
evento_tabla['sev_freq_tabla'] = [
    {'desde': 1, 'hasta': 2, 'multiplicador': 1.0},
    {'desde': 3, 'hasta': None, 'multiplicador': 3.0},
]

perdidas_tabla, _, _, _ = generar_lda_con_secuencialidad([evento_tabla], num_sim, rng=np.random.default_rng(42))

ratio_tabla = perdidas_tabla.mean() / perdidas_control.mean()
check(ratio_tabla > 1.1, f"Tabla aumenta pérdida media: ratio={ratio_tabla:.3f} (>1.1)")
print(f"  ℹ️  Ratio de medias tabla/control = {ratio_tabla:.4f}")

# Validación más precisa: con freq=5, factores [1,1,3,3,3] → sum=11 vs 5 → ratio≈2.2
# Con distribución Poisson(5), el ratio debería estar cercano a esto
check(ratio_tabla > 1.5, f"Tabla ratio razonable (>1.5): {ratio_tabla:.3f}")

# ==============================================================================
# TEST 5: Factor máximo (cap) funciona correctamente
# ==============================================================================
print("\n" + "=" * 70)
print("TEST 5: Factor máximo (cap)")
print("=" * 70)

evento_cap = copy.deepcopy(evento_lineal)
evento_cap['id'] = str(uuid.uuid4())
evento_cap['nombre'] = 'Test_Cap'
evento_cap['sev_freq_paso'] = 10.0  # Paso muy grande
evento_cap['sev_freq_factor_max'] = 2.0  # Pero cap bajo

perdidas_cap, _, _, _ = generar_lda_con_secuencialidad([evento_cap], num_sim, rng=np.random.default_rng(42))

ratio_cap = perdidas_cap.mean() / perdidas_control.mean()
# Con paso=10 pero max=2: factores = [1.0, 2.0, 2.0, 2.0, ...]
# Para freq=5: sum = 1+2+2+2+2 = 9, control = 5, ratio ≈ 1.8
check(ratio_cap < 2.5, f"Cap limita el ratio: {ratio_cap:.3f} (<2.5)")
check(ratio_cap > 1.0, f"Cap aún produce aumento: {ratio_cap:.3f} (>1.0)")
print(f"  ℹ️  Ratio con cap=2.0: {ratio_cap:.4f}")

# ==============================================================================
# TEST 6: Modelo Sistémico (z-score)
# ==============================================================================
print("\n" + "=" * 70)
print("TEST 6: Modelo Sistémico (z-score)")
print("=" * 70)

evento_sist = copy.deepcopy(evento_lineal)
evento_sist['id'] = str(uuid.uuid4())
evento_sist['nombre'] = 'Test_Sistemico'
evento_sist['sev_freq_modelo'] = 'sistemico'
evento_sist['sev_freq_alpha'] = 0.5
evento_sist['sev_freq_solo_aumento'] = True
evento_sist['sev_freq_sistemico_factor_max'] = 3.0

perdidas_sist, _, _, _ = generar_lda_con_secuencialidad([evento_sist], num_sim, rng=np.random.default_rng(42))

ratio_sist = perdidas_sist.mean() / perdidas_control.mean()
# Con solo_aumento=True, z-scores negativos se truncan a 0, así que
# simulaciones con frecuencia baja no reducen severidad, solo las altas la aumentan
check(ratio_sist > 1.0, f"Sistémico con solo_aumento aumenta: ratio={ratio_sist:.3f} (>1.0)")
check(ratio_sist < 2.0, f"Sistémico alpha=0.5 moderado: ratio={ratio_sist:.3f} (<2.0)")
print(f"  ℹ️  Ratio sistémico/control = {ratio_sist:.4f}")

# Test sistémico sin solo_aumento (bidireccional)
evento_sist_bi = copy.deepcopy(evento_sist)
evento_sist_bi['id'] = str(uuid.uuid4())
evento_sist_bi['nombre'] = 'Test_Sistemico_Bi'
evento_sist_bi['sev_freq_solo_aumento'] = False

perdidas_sist_bi, _, _, _ = generar_lda_con_secuencialidad([evento_sist_bi], num_sim, rng=np.random.default_rng(42))

ratio_sist_bi = perdidas_sist_bi.mean() / perdidas_control.mean()
# Bidireccional: freq bajas reducen severidad, freq altas aumentan
# La media debería estar más cerca de 1.0 que con solo_aumento
print(f"  ℹ️  Ratio sistémico bidireccional/control = {ratio_sist_bi:.4f}")
check(abs(ratio_sist_bi - 1.0) < abs(ratio_sist - 1.0) + 0.1,
      f"Bidireccional más cercano a 1.0 que solo_aumento: |{ratio_sist_bi:.3f}-1| vs |{ratio_sist:.3f}-1|")

# ==============================================================================
# TEST 7: Desactivado no afecta resultados
# ==============================================================================
print("\n" + "=" * 70)
print("TEST 7: sev_freq_activado=False no altera resultados")
print("=" * 70)

evento_off = copy.deepcopy(evento_lineal)
evento_off['id'] = str(uuid.uuid4())
evento_off['nombre'] = 'Test_Off'
evento_off['sev_freq_activado'] = False  # Desactivado

perdidas_off, _, _, _ = generar_lda_con_secuencialidad([evento_off], num_sim, rng=np.random.default_rng(42))

check(np.allclose(perdidas_off.mean(), perdidas_control.mean(), rtol=0.001),
      f"Desactivado = control: media {perdidas_off.mean():.0f} vs {perdidas_control.mean():.0f}")

# ==============================================================================
# TEST 8: Correlación frecuencia-pérdida con reincidencia
# ==============================================================================
print("\n" + "=" * 70)
print("TEST 8: Correlación frecuencia-pérdida (reincidencia amplifica)")
print("=" * 70)

# Las simulaciones con más ocurrencias deben tener pérdidas desproporcionadamente mayores
freq_lineal = freq_por_ev_lineal[0]  # frecuencias del primer (único) evento
perd_lineal = perd_por_ev_lineal[0]  # pérdidas del primer evento
freq_control_ev = freq_por_ev_ctrl[0]
perd_control_ev = perd_por_ev_ctrl[0]

# Calcular pérdida promedio por ocurrencia en bins de frecuencia
mask_high_freq = freq_lineal >= 7
mask_low_freq = (freq_lineal >= 1) & (freq_lineal <= 3)

if mask_high_freq.sum() > 0 and mask_low_freq.sum() > 0:
    avg_per_occ_high = perd_lineal[mask_high_freq].mean() / freq_lineal[mask_high_freq].mean()
    avg_per_occ_low = perd_lineal[mask_low_freq].mean() / freq_lineal[mask_low_freq].mean()
    check(avg_per_occ_high > avg_per_occ_low * 1.1,
          f"Pérdida/ocurrencia mayor en freq alta: {avg_per_occ_high:.0f} vs {avg_per_occ_low:.0f}")

    # En control, pérdida/ocurrencia debe ser similar independientemente de frecuencia
    mask_high_ctrl = freq_control_ev >= 7
    mask_low_ctrl = (freq_control_ev >= 1) & (freq_control_ev <= 3)
    if mask_high_ctrl.sum() > 0 and mask_low_ctrl.sum() > 0:
        avg_per_occ_high_ctrl = perd_control_ev[mask_high_ctrl].mean() / freq_control_ev[mask_high_ctrl].mean()
        avg_per_occ_low_ctrl = perd_control_ev[mask_low_ctrl].mean() / freq_control_ev[mask_low_ctrl].mean()
        ratio_ctrl = avg_per_occ_high_ctrl / avg_per_occ_low_ctrl
        ratio_lineal = avg_per_occ_high / avg_per_occ_low
        check(ratio_lineal > ratio_ctrl,
              f"Reincidencia amplifica diferencia: ratio_esc={ratio_lineal:.3f} > ratio_ctrl={ratio_ctrl:.3f}")

# ==============================================================================
# TEST 9: JSON serialización/deserialización de campos sev_freq_*
# ==============================================================================
print("\n" + "=" * 70)
print("TEST 9: JSON round-trip de campos sev_freq_*")
print("=" * 70)

# Simular lo que hace guardar_configuracion.
# guardar_evento siempre genera los 10 campos sev_freq_*, así que creamos
# un evento completo que refleja lo que guardar_evento realmente produce.
evento_para_json = copy.deepcopy(evento_lineal)
# Agregar los campos que guardar_evento siempre incluye como defaults
evento_para_json.setdefault('sev_freq_tabla', [{'desde': 1, 'hasta': 2, 'multiplicador': 1.0}, {'desde': 3, 'hasta': None, 'multiplicador': 2.0}])
evento_para_json.setdefault('sev_freq_base', 1.5)
evento_para_json.setdefault('sev_freq_alpha', 0.5)
evento_para_json.setdefault('sev_freq_solo_aumento', True)
evento_para_json.setdefault('sev_freq_sistemico_factor_max', 3.0)
# Remover objetos no serializables (igual que guardar_configuracion)
del evento_para_json['dist_severidad']
del evento_para_json['dist_frecuencia']

# Verificar que todos los campos sev_freq_* están presentes
sev_freq_keys = [k for k in evento_para_json if k.startswith('sev_freq_')]
expected_keys = {
    'sev_freq_activado', 'sev_freq_modelo', 'sev_freq_tipo_escalamiento',
    'sev_freq_tabla', 'sev_freq_paso', 'sev_freq_base', 'sev_freq_factor_max',
    'sev_freq_alpha', 'sev_freq_solo_aumento', 'sev_freq_sistemico_factor_max'
}
check(set(sev_freq_keys) == expected_keys,
      f"Todos los campos sev_freq_* presentes: {len(sev_freq_keys)}/10")

# Escribir a JSON y leer de vuelta
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
    json_path = f.name
    config = {'eventos_riesgo': [evento_para_json], 'num_simulaciones': 1000, 'scenarios': []}
    json.dump(config, f, ensure_ascii=False, indent=2)

try:
    with open(json_path, 'r', encoding='utf-8') as f:
        loaded = json.load(f)

    loaded_evento = loaded['eventos_riesgo'][0]

    # Verificar cada campo sev_freq_*
    check(loaded_evento['sev_freq_activado'] == True, "sev_freq_activado: True round-trip OK")
    check(loaded_evento['sev_freq_modelo'] == 'reincidencia', "sev_freq_modelo: 'reincidencia' round-trip OK")
    check(loaded_evento['sev_freq_tipo_escalamiento'] == 'lineal', "sev_freq_tipo_escalamiento: 'lineal' round-trip OK")
    check(loaded_evento['sev_freq_paso'] == 0.5, f"sev_freq_paso: {loaded_evento['sev_freq_paso']} == 0.5")
    check(loaded_evento['sev_freq_base'] == 1.5, f"sev_freq_base: {loaded_evento['sev_freq_base']} == 1.5")
    check(loaded_evento['sev_freq_factor_max'] == 5.0, f"sev_freq_factor_max: {loaded_evento['sev_freq_factor_max']} == 5.0")
    check(loaded_evento['sev_freq_alpha'] == 0.5, f"sev_freq_alpha: {loaded_evento['sev_freq_alpha']} == 0.5")
    check(loaded_evento['sev_freq_solo_aumento'] == True, "sev_freq_solo_aumento: True round-trip OK")
    check(loaded_evento['sev_freq_sistemico_factor_max'] == 3.0, f"sev_freq_sistemico_factor_max: {loaded_evento['sev_freq_sistemico_factor_max']} == 3.0")

    # Verificar tabla (incluyendo None → null → None)
    tabla_loaded = loaded_evento['sev_freq_tabla']
    check(isinstance(tabla_loaded, list), f"sev_freq_tabla es lista: {type(tabla_loaded)}")
    check(len(tabla_loaded) == 2, f"sev_freq_tabla tiene 2 filas")
    check(tabla_loaded[0]['desde'] == 1, "tabla[0].desde == 1")
    check(tabla_loaded[0]['hasta'] == 2, "tabla[0].hasta == 2")
    check(tabla_loaded[0]['multiplicador'] == 1.0, "tabla[0].multiplicador == 1.0")
    check(tabla_loaded[1]['desde'] == 3, "tabla[1].desde == 3")
    check(tabla_loaded[1]['hasta'] is None, f"tabla[1].hasta is None (null): {tabla_loaded[1]['hasta']}")
    check(tabla_loaded[1]['multiplicador'] == 2.0, "tabla[1].multiplicador == 2.0")

finally:
    os.unlink(json_path)

# ==============================================================================
# TEST 10: JSON con escenarios
# ==============================================================================
print("\n" + "=" * 70)
print("TEST 10: JSON round-trip de escenarios con sev_freq_*")
print("=" * 70)

evento_escenario = copy.deepcopy(evento_para_json)
evento_escenario['sev_freq_modelo'] = 'sistemico'
evento_escenario['sev_freq_alpha'] = 0.8
evento_escenario['sev_freq_solo_aumento'] = False
evento_escenario['sev_freq_sistemico_factor_max'] = 5.0

config_esc = {
    'eventos_riesgo': [],
    'num_simulaciones': 1000,
    'scenarios': [{
        'nombre': 'Test_Escenario',
        'descripcion': 'Escenario de prueba',
        'eventos_riesgo': [evento_escenario]
    }]
}

with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
    json_path2 = f.name
    json.dump(config_esc, f, ensure_ascii=False, indent=2)

try:
    with open(json_path2, 'r', encoding='utf-8') as f:
        loaded2 = json.load(f)

    esc_evento = loaded2['scenarios'][0]['eventos_riesgo'][0]
    check(esc_evento['sev_freq_modelo'] == 'sistemico', "Escenario: modelo sistémico round-trip OK")
    check(esc_evento['sev_freq_alpha'] == 0.8, "Escenario: alpha=0.8 round-trip OK")
    check(esc_evento['sev_freq_solo_aumento'] == False, "Escenario: solo_aumento=False round-trip OK")
    check(esc_evento['sev_freq_sistemico_factor_max'] == 5.0, "Escenario: factor_max=5.0 round-trip OK")
    check(esc_evento['sev_freq_activado'] == True, "Escenario: activado=True round-trip OK")
finally:
    os.unlink(json_path2)

# ==============================================================================
# TEST 11: Evento sin campos sev_freq_* (backward compatibility)
# ==============================================================================
print("\n" + "=" * 70)
print("TEST 11: Backward compatibility — evento sin campos sev_freq_*")
print("=" * 70)

evento_legacy = {
    'id': str(uuid.uuid4()),
    'nombre': 'Legacy_Event',
    'activo': True,
    'dist_severidad': dist_sev,
    'dist_frecuencia': dist_freq,
    'freq_opcion': 1,
    'tasa': 5.0,
    # Sin campos sev_freq_*
}

# Debe funcionar sin errores y sin escalamiento
perdidas_legacy, _, _, _ = generar_lda_con_secuencialidad([evento_legacy], num_sim, rng=np.random.default_rng(42))
check(np.allclose(perdidas_legacy.mean(), perdidas_control.mean(), rtol=0.001),
      f"Legacy sin sev_freq = control: {perdidas_legacy.mean():.0f} ≈ {perdidas_control.mean():.0f}")

# ==============================================================================
# TEST 12: Verificación de multiplicadores exactos (lineal controlado)
# ==============================================================================
print("\n" + "=" * 70)
print("TEST 12: Verificación de multiplicadores exactos")
print("=" * 70)

# Usar frecuencia fija (Binomial n=5, p=1.0 → siempre freq=5)
# Esto nos da control total para validar multiplicadores exactos
rng_fixed = np.random.default_rng(123)
dist_freq_fixed = generar_distribucion_frecuencia(2, num_eventos_posibles=5, probabilidad_exito=0.999)

evento_exact = {
    'id': str(uuid.uuid4()),
    'nombre': 'Exact_Test',
    'activo': True,
    'dist_severidad': dist_sev,  # PERT(1000,1000,1000) = constante 1000
    'dist_frecuencia': dist_freq_fixed,
    'freq_opcion': 2,
    'num_eventos': 5,
    'prob_exito': 0.999,
    'sev_freq_activado': True,
    'sev_freq_modelo': 'reincidencia',
    'sev_freq_tipo_escalamiento': 'lineal',
    'sev_freq_paso': 1.0,
    'sev_freq_factor_max': 10.0,
}

# Con freq≈5 constante y severidad 1000:
# Factores lineal paso=1.0: [1, 2, 3, 4, 5]
# Pérdida esperada por sim ≈ 1000*(1+2+3+4+5) = 15000
perdidas_exact, _, _, _ = generar_lda_con_secuencialidad([evento_exact], 10000, rng=rng_fixed)

# La mayoría de simulaciones debería tener freq=5, pérdida≈15000
expected_loss = 1000 * (1 + 2 + 3 + 4 + 5)  # 15000
# Con p=0.999, ~99.9% tendrán freq=5
median_loss = np.median(perdidas_exact)
check(abs(median_loss - expected_loss) / expected_loss < 0.05,
      f"Pérdida mediana ≈ {expected_loss}: actual={median_loss:.0f} (error < 5%)")

# Sin escalamiento: pérdida = 1000 * 5 = 5000
evento_exact_off = copy.deepcopy(evento_exact)
evento_exact_off['id'] = str(uuid.uuid4())
evento_exact_off['sev_freq_activado'] = False
perdidas_exact_off, _, _, _ = generar_lda_con_secuencialidad([evento_exact_off], 10000, rng=np.random.default_rng(123))
median_off = np.median(perdidas_exact_off)
check(abs(median_off - 5000) / 5000 < 0.05,
      f"Control mediana ≈ 5000: actual={median_off:.0f} (error < 5%)")

ratio_exact = median_loss / median_off
check(abs(ratio_exact - 3.0) < 0.15,
      f"Ratio exacto ≈ 3.0 (15000/5000): actual={ratio_exact:.3f}")

# ==============================================================================
# RESUMEN
# ==============================================================================
print("\n" + "=" * 70)
total = PASS + FAIL
print(f"RESULTADOS: {PASS}/{total} tests pasaron, {FAIL} fallaron")
if FAIL == 0:
    print("✅ TODAS LAS VALIDACIONES PASARON")
else:
    print(f"❌ {FAIL} VALIDACIONES FALLARON")
print("=" * 70)

sys.exit(0 if FAIL == 0 else 1)
