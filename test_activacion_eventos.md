# Plan de Verificación: Activación/Desactivación de Eventos

## ✅ CORRECCIONES IMPLEMENTADAS

### 1. **Problema de Modificación de Datos Originales** 
**Ubicación**: `ejecutar_simulacion()` líneas 9181-9210
**Problema**: Al filtrar vínculos, se modificaban directamente los objetos originales en `self.eventos_riesgo`
**Solución**: Se agregó `copy.deepcopy()` antes de filtrar vínculos para crear copias independientes

```python
# ANTES (❌ Modificaba datos originales):
eventos_activos = [e for e in eventos if e.get('activo', True)]
# ... luego se modificaba evento['vinculos'] directamente

# DESPUÉS (✅ Preserva datos originales):
eventos_activos_originales = [e for e in eventos if e.get('activo', True)]
eventos_activos = copy.deepcopy(eventos_activos_originales)
# ... ahora las modificaciones son en la copia
```

### 2. **Filtrado de Vínculos a Eventos Inactivos**
**Ubicación**: `ejecutar_simulacion()` líneas 9195-9210
**Implementación**: Opción C "Ignorar Vínculos"
- Se crea un set con IDs de eventos activos
- Se filtran vínculos que apuntan a eventos inactivos
- Se reporta en consola cuando se ignoran vínculos

## 🔍 PUNTOS DE VERIFICACIÓN

### A. Filtrado de Eventos Activos
- ✅ **Línea 9183**: Solo se seleccionan eventos con `activo == True`
- ✅ **Línea 9186**: Se valida que haya al menos 1 evento activo
- ✅ **Línea 9211**: Se muestra contador "X activos / Y totales" en status bar

### B. Protección de Datos Originales
- ✅ **Línea 9190**: `copy.deepcopy()` preserva datos originales
- ✅ Los vínculos filtrados no afectan `self.eventos_riesgo`
- ✅ Reactivar eventos restaura todos sus vínculos

### C. Procesamiento en Simulación
- ✅ **Línea 9231**: Solo `eventos_activos` se procesan
- ✅ **Línea 9291**: `SimulacionThread` recibe solo eventos activos
- ✅ Vínculos a eventos inactivos ya fueron filtrados

### D. Sincronización UI
- ✅ Checkbox en tabla cambia estado activo
- ✅ Toggle en tarjeta cambia estado activo
- ✅ Cambios se sincronizan entre tabla y tarjetas
- ✅ Estado se persiste en guardar/cargar JSON

## 📋 CASOS DE PRUEBA

### Caso 1: Eventos Independientes
```
Configuración:
- Evento A: ACTIVO
- Evento B: INACTIVO
- Evento C: ACTIVO

Resultado Esperado:
✓ Solo A y C se simulan
✓ B no aparece en resultados
✓ Total eventos procesados: 2
```

### Caso 2: Eventos con Vínculos a Activos
```
Configuración:
- Evento A: ACTIVO
- Evento B: ACTIVO (vinculado a A)
- Evento C: ACTIVO (vinculado a B)

Resultado Esperado:
✓ Todos se simulan
✓ Vínculos funcionan normalmente
✓ Total eventos procesados: 3
```

### Caso 3: Eventos con Vínculos a Inactivos
```
Configuración:
- Evento A: INACTIVO
- Evento B: ACTIVO (vinculado a A)
- Evento C: ACTIVO

Resultado Esperado:
✓ Solo B y C se simulan
✓ Vínculo de B a A se ignora (mensaje en consola)
✓ B se simula como independiente
✓ Total eventos procesados: 2
```

### Caso 4: Cadena de Vínculos Mixta
```
Configuración:
- Evento A: ACTIVO
- Evento B: ACTIVO (vinculado a A)
- Evento C: INACTIVO (vinculado a B)
- Evento D: ACTIVO (vinculado a C)

Resultado Esperado:
✓ Solo A, B, D se simulan
✓ C se excluye
✓ Vínculo D→C se ignora
✓ D se simula como independiente
✓ Total eventos procesados: 3
```

### Caso 5: Persistencia de Vínculos
```
Acción:
1. Crear A (activo) y B (activo, vinculado a A)
2. Desactivar A
3. Ejecutar simulación (B simula sin vínculo)
4. Reactivar A
5. Ejecutar simulación nuevamente

Resultado Esperado:
✓ En paso 3: B simula sin vínculo
✓ En paso 5: B vuelve a tener vínculo a A
✓ Los vínculos NO se pierden permanentemente
```

## 🎯 RESUMEN DE LA LÓGICA

### Flujo de Ejecución:
1. **Seleccionar eventos base** (escenario o todos)
2. **Filtrar eventos activos** (`activo == True`)
3. **Validar mínimo 1 activo**
4. **Hacer copia profunda** (preservar originales)
5. **Filtrar vínculos inválidos** (padres inactivos)
6. **Preparar eventos para simulación**
7. **Enviar a SimulacionThread**
8. **Simular solo eventos activos**

### Garantías:
- ✅ Solo eventos activos se simulan
- ✅ Vínculos a eventos inactivos se ignoran
- ✅ Datos originales no se modifican
- ✅ Vínculos se restauran al reactivar eventos
- ✅ UI refleja estado correcto en todo momento

## 🔧 DEBUGGING

### Mensajes de Consola Esperados:
```
[DEBUG EJECUTAR V2] ========================================
[DEBUG EJECUTAR V2] Número de eventos originales: 5
[DEBUG EJECUTAR V2] Número de eventos activos: 3
[DEBUG] Evento 'B': se ignoraron 1 vínculo(s) a eventos inactivos
[DEBUG] Evento 'D': se ignoraron 1 vínculo(s) a eventos inactivos
```

### Verificación Visual en UI:
- Status bar: "Simulando con 3 de 5 eventos activos"
- Panel eventos: "3 activos / 5 totales"
- Tarjetas inactivas: opacidad 50%, sombra reducida
- Filas inactivas en tabla: gris, itálica
