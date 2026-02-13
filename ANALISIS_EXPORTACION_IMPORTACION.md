# 🔍 ANÁLISIS: Exportación/Importación de Factores Estocásticos

**Fecha:** 4 de noviembre de 2025  
**Objetivo:** Verificar que factores estocásticos se guarden y carguen correctamente  

---

## 📊 Estado Actual

### ✅ Lo Que Funciona Bien

#### 1. Guardado de `factores_ajuste` ✅
**Líneas 12964-12976**

```python
for evento in self.eventos_riesgo:
    evento_data = copy.deepcopy(evento)  # ✅ Preserva factores_ajuste
    
    # Remover distribuciones no serializables
    if 'dist_severidad' in evento_data:
        del evento_data['dist_severidad']
    if 'dist_frecuencia' in evento_data:
        del evento_data['dist_frecuencia']
    
    # DEBUG: Verificar guardado
    if 'factores_ajuste' in evento_data and evento_data['factores_ajuste']:
        print(f"[DEBUG] Guardando '{evento_data.get('nombre')}' con {len(evento_data['factores_ajuste'])} factores")
    
    configuracion['eventos_riesgo'].append(evento_data)
```

**Estado:** ✅ **CORRECTO**
- `copy.deepcopy()` preserva toda la estructura de `factores_ajuste`
- Incluye todos los campos: nombre, tipo_modelo, confiabilidad, reduccion_efectiva, etc.

---

#### 2. Carga de `factores_ajuste` ✅
**Líneas 13139-13142**

```python
# DEBUG: Verificar si tiene factores_ajuste
if 'factores_ajuste' in evento_data and evento_data['factores_ajuste']:
    print(f"[DEBUG CARGAR] Evento '{evento_data.get('nombre')}' tiene {len(evento_data['factores_ajuste'])} factores")
else:
    print(f"[DEBUG CARGAR] Evento '{evento_data.get('nombre')}' NO tiene factores_ajuste")
```

**Estado:** ✅ **CORRECTO**
- Los factores se cargan automáticamente del JSON
- No requiere procesamiento especial

---

## ⚠️ Problema Encontrado

### ❌ Flags Temporales No Se Limpian

**Líneas 12964-12976 - Código Actual:**

```python
evento_data = copy.deepcopy(evento)

# Solo se remueven distribuciones
del evento_data['dist_severidad']
del evento_data['dist_frecuencia']

# ❌ NO se remueven flags temporales:
# - '_usa_estocastico'
# - '_factores_vector' (numpy array!)

configuracion['eventos_riesgo'].append(evento_data)
```

**Impacto:**

### Problema 1: `_factores_vector` es un Numpy Array
```python
evento['_factores_vector'] = np.array([0.5, 0.2, 1.0, ...])  # 10,000 elementos

# Al guardar con json.dump():
json.dump(configuracion, f)  # ❌ FALLA si hay numpy arrays
```

**Error Esperado:**
```
TypeError: Object of type ndarray is not JSON serializable
```

### Problema 2: Datos Innecesarios
Los flags `_usa_estocastico` y `_factores_vector` son **temporales** y solo se usan durante la simulación. NO deberían guardarse porque:
- Son regenerados en cada simulación
- `_factores_vector` es diferente en cada ejecución (estocástico)
- Ocupan espacio innecesario en el archivo JSON

---

## 🐛 Escenarios de Fallo

### Escenario 1: Guardar después de Simular

```
1. Usuario configura evento con factor estocástico
2. Usuario ejecuta simulación
   → evento['_usa_estocastico'] = True
   → evento['_factores_vector'] = np.array([...])  # 10,000 valores
3. Usuario guarda simulación
   → json.dump() intenta serializar numpy array
   → ❌ FALLA con TypeError
```

**Probabilidad:** 🔴 **ALTA** (casi seguro si simulas antes de guardar)

---

### Escenario 2: Guardar sin Simular

```
1. Usuario configura evento con factor estocástico
2. Usuario guarda simulación (sin simular)
   → evento NO tiene '_usa_estocastico' ni '_factores_vector'
   → ✅ FUNCIONA (json.dump() exitoso)
```

**Probabilidad:** 🟢 **BAJA** (usuarios normalmente simulan antes de guardar)

---

## 🔧 Solución Requerida

### Agregar Limpieza de Flags Temporales

**Ubicación:** Líneas 12966-12970

**Código Corregido:**
```python
for evento in self.eventos_riesgo:
    evento_data = copy.deepcopy(evento)
    
    # Remover distribuciones no serializables
    if 'dist_severidad' in evento_data:
        del evento_data['dist_severidad']
    if 'dist_frecuencia' in evento_data:
        del evento_data['dist_frecuencia']
    
    # ✅ NUEVO: Remover flags temporales de simulación
    if '_usa_estocastico' in evento_data:
        del evento_data['_usa_estocastico']
    if '_factores_vector' in evento_data:
        del evento_data['_factores_vector']
    
    # DEBUG
    if 'factores_ajuste' in evento_data and evento_data['factores_ajuste']:
        print(f"[DEBUG] Guardando '{evento_data.get('nombre')}' con {len(evento_data['factores_ajuste'])} factores")
    
    configuracion['eventos_riesgo'].append(evento_data)
```

**Misma corrección necesaria en escenarios (líneas 12985-12992)**

---

## 📋 Validación Completa

### Flujo de Guardado:
```
1. Evento en memoria:
   {
     'nombre': 'DDoS',
     'factores_ajuste': [
       {
         'nombre': 'Firewall',
         'tipo_modelo': 'estocastico',
         'confiabilidad': 50,
         'reduccion_efectiva': 100,
         'reduccion_fallo': 0,
         'activo': True
       }
     ],
     '_usa_estocastico': True,  # ❌ Temporal
     '_factores_vector': np.array([...])  # ❌ Temporal
   }

2. Deep copy + limpieza:
   evento_data = copy.deepcopy(evento)
   del evento_data['_usa_estocastico']  # ✅ Remover
   del evento_data['_factores_vector']  # ✅ Remover

3. JSON guardado:
   {
     'nombre': 'DDoS',
     'factores_ajuste': [
       {
         'nombre': 'Firewall',
         'tipo_modelo': 'estocastico',
         'confiabilidad': 50,
         'reduccion_efectiva': 100,
         'reduccion_fallo': 0,
         'activo': True
       }
     ]
   }  ✅ LIMPIO
```

### Flujo de Carga:
```
1. JSON cargado:
   {
     'nombre': 'DDoS',
     'factores_ajuste': [...] ✅
   }

2. Evento en memoria (después de cargar):
   {
     'nombre': 'DDoS',
     'factores_ajuste': [...] ✅
     # NO tiene _usa_estocastico ni _factores_vector (correcto)
   }

3. Al simular (se regeneran automáticamente):
   # Líneas 1206-1247 procesan factores_ajuste
   evento['_usa_estocastico'] = True  ✅ Regenerado
   evento['_factores_vector'] = np.ones(...)  ✅ Regenerado
```

---

## ✅ Estructura Correcta del JSON

### Evento con Factor Estocástico:
```json
{
  "id": "abc-123",
  "nombre": "Ataque DDoS",
  "freq_opcion": 1,
  "tasa": 10,
  "sev_opcion": 2,
  "sev_minimo": 1000,
  "sev_mas_probable": 5000,
  "sev_maximo": 10000,
  "factores_ajuste": [
    {
      "nombre": "Firewall",
      "tipo_modelo": "estocastico",
      "confiabilidad": 50,
      "reduccion_efectiva": 100,
      "reduccion_fallo": 0,
      "activo": true,
      "impacto_porcentual": -100
    },
    {
      "nombre": "Antivirus",
      "tipo_modelo": "estocastico",
      "confiabilidad": 70,
      "reduccion_efectiva": 80,
      "reduccion_fallo": 10,
      "activo": true,
      "impacto_porcentual": -80
    }
  ]
}
```

**Campos que DEBEN guardarse:**
- ✅ `factores_ajuste` (lista completa)
- ✅ `nombre`, `tipo_modelo`, `confiabilidad`, etc.
- ✅ `activo` (para desactivar temporalmente)

**Campos que NO deben guardarse:**
- ❌ `_usa_estocastico` (flag temporal)
- ❌ `_factores_vector` (numpy array, regenerado cada vez)

---

## 🧪 Plan de Testing

### Test 1: Guardar después de Simular
```
1. Crear evento con factor estocástico
2. Ejecutar simulación (10,000 iteraciones)
3. Guardar simulación
   ✅ Debe guardar sin errores
   ✅ JSON no debe contener '_usa_estocastico' ni '_factores_vector'
```

### Test 2: Cargar y Re-Simular
```
1. Cargar simulación guardada
2. Verificar que factores_ajuste estén presentes
   ✅ Debe mostrar factores en UI
   ✅ Debe tener todos los campos (confiabilidad, etc.)
3. Ejecutar nueva simulación
   ✅ Debe regenerar '_usa_estocastico' y '_factores_vector'
   ✅ Debe producir resultados estocásticos correctos
```

### Test 3: Multiple Factores
```
1. Crear evento con 3 factores estocásticos
2. Simular
3. Guardar
4. Cargar
5. Verificar que los 3 factores estén presentes
   ✅ Debe cargar 3 factores con configuraciones correctas
```

---

## 📊 Checklist de Corrección

### En Guardado (eventos principales):
- [ ] Remover `_usa_estocastico` antes de JSON
- [ ] Remover `_factores_vector` antes de JSON
- [ ] Verificar `factores_ajuste` se guarda completo

### En Guardado (escenarios):
- [ ] Remover `_usa_estocastico` antes de JSON
- [ ] Remover `_factores_vector` antes de JSON
- [ ] Verificar `factores_ajuste` se guarda completo

### En Carga:
- [✅] `factores_ajuste` se carga automáticamente (ya funciona)
- [✅] NO necesita regenerar flags (se hace en simulación)

---

## 🎯 Conclusión

### Estado Actual:
- ✅ `factores_ajuste` se guarda correctamente
- ✅ `factores_ajuste` se carga correctamente
- ❌ Flags temporales pueden causar error de serialización
- ❌ JSON contiene datos innecesarios

### Después de Corrección:
- ✅ `factores_ajuste` se guarda correctamente
- ✅ `factores_ajuste` se carga correctamente
- ✅ Flags temporales se limpian antes de guardar
- ✅ JSON limpio y serializable

### Impacto de la Corrección:
- 🔴 **CRÍTICO:** Evita TypeError al guardar después de simular
- 🟢 **MEJORA:** JSON más limpio (sin datos temporales)
- 🟢 **MEJORA:** Archivos JSON más pequeños

---

**Prioridad:** 🔴 **ALTA** (Evita error crítico)  
**Complejidad:** 🟢 **BAJA** (4 líneas de código)  
**Testing:** Necesario después de corrección
