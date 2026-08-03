# Guía de Uso: Ajuste de Probabilidades con Controles y Factores de Riesgo

## 📋 Descripción General

Esta funcionalidad permite ajustar los eventos de riesgo según controles y factores considerando:
- **Controles**: Reducen el riesgo (valores negativos)
- **Factores de riesgo**: Aumentan el riesgo (valores positivos)

Los factores pueden afectar la **frecuencia** (cada cuánto ocurre el evento) y/o la **severidad** (cuánto cuesta cuando ocurre). Además, cada factor puede modelarse de dos formas:
- **Estático**: aplica un efecto determinístico fijo (el mismo en todas las simulaciones).
- **Estocástico**: modela un control cuya efectividad es incierta; en cada simulación se sortea si el control funciona o falla.

Los ajustes se aplican automáticamente durante la simulación Monte Carlo, combinando múltiples factores de forma matemáticamente correcta usando transformaciones log-odds internamente (para distribuciones de probabilidad) o escalado multiplicativo (para distribuciones de tasa/conteo).

---

## 🚀 Cómo Usar

### **1. Crear o Editar un Evento**

1. En la pestaña **Simulación**, haz clic en **"Agregar Evento"** o edita un evento existente
2. Configura la distribución de frecuencia normalmente (ej: Bernoulli con p=0.10)

### **2. Agregar Factores de Ajuste**

3. Desplázate hacia abajo hasta la sección **"▷ Ajustar probabilidad según controles/factores (0)"**
4. Haz clic en la sección para expandirla (cambiará a **"▽ Ajustar..."**)
5. Haz clic en el botón **"Agregar Factor/Control"**

### **3. Configurar un Factor**

En el diálogo que aparece:

- **Nombre**: Descripción del control o factor
  - Ejemplo: "Firewall actualizado", "Capacitación anual", "Sistema legacy sin parches"
  
- **Impacto (%)**: Porcentaje de impacto en la probabilidad
  - **Valores negativos**: Controles que reducen el riesgo
    - Ejemplo: `-30` para un control que reduce el riesgo en 30%
  - **Valores positivos**: Factores que aumentan el riesgo
    - Ejemplo: `+50` para una vulnerabilidad que aumenta el riesgo en 50%

6. Haz clic en **OK**

### **4. Ver Probabilidad Ajustada en Tiempo Real**

- Al expandir la sección de ajustes, verás un banner amarillo que muestra:
  ```
  Prob. base: 10.0% → Ajustada: 7.4% (-26%)
  ```
- Este valor se actualiza automáticamente cuando:
  - Cambias parámetros de frecuencia
  - Activas/desactivas factores
  - Modificas el impacto de un factor

### **5. Gestionar Factores**

Cada factor en la tabla tiene:
- **Checkbox Activo**: Activa/desactiva el factor sin eliminarlo
- **Nombre**: Descripción del factor
- **Impacto (%)**: Valor editable directamente en la tabla
- **Botón Eliminar**: Elimina el factor permanentemente

### **6. Guardar y Simular**

7. Haz clic en **"✔ Guardar"**
8. Los ajustes se aplicarán **automáticamente** en todas las simulaciones futuras

---

## 💡 Ejemplos Prácticos

### Ejemplo 1: Poisson - "Fallas de Servidor"

**Configuración inicial:**
- Distribución de frecuencia: **Poisson**
- Tasa (λ): **5.0** eventos/año

**Factores de ajuste:**
| Activo | Nombre | Impacto | Tipo |
|--------|--------|---------|------|
| ✅ | Monitoreo 24/7 | -40% | Control |
| ✅ | Redundancia | -30% | Control |

**Resultado:**
```
λ base: 5.000 → Ajustada: 2.100 (-58%)
```

**Cálculo:**
- Factor total = (1 - 0.40) × (1 - 0.30) = 0.42
- λ ajustada = 5.0 × 0.42 = 2.1 eventos/año

---

### Ejemplo 2: Bernoulli - "Falla de Ciberseguridad"

**Configuración inicial:**
- Distribución de frecuencia: **Bernoulli**
- Probabilidad (p): **0.10** (10% anual)

**Factores de ajuste:**
| Activo | Nombre | Impacto | Tipo |
|--------|--------|---------|------|
| ✅ | Firewall corporativo | -30% | Control |
| ✅ | Capacitación del equipo | -20% | Control |
| ✅ | Sistema legacy sin parches | +50% | Riesgo |

**Resultado:**
```
p base: 10.0% → Ajustada: 10.7% (+7%)
```

**Durante la simulación:**
- Para **probabilidades** (Bernoulli, Binomial), se usa **log-odds** para combinar factores
- La combinación de controles y riesgo resulta en un aumento neto del 7%
- Este método garantiza que la probabilidad final esté siempre entre 0 y 1

---

## 🎲 Modelo de Factores: Estático vs. Estocástico

Cada factor se configura con un **tipo de modelo** (campo `tipo_modelo`):

### **Estático (`"estatico"`) — efecto determinístico**

Es el modelo por defecto y el que usan los ejemplos anteriores. El factor aplica un impacto porcentual **fijo**, idéntico en todas las simulaciones (ej: "este control reduce la frecuencia 30% siempre").

- **Cuándo usarlo**: cuando conocés (o estimás) el efecto neto del control y querés tratarlo como un valor constante y confiable.

### **Estocástico (`"estocastico"`) — efectividad incierta**

Modela un control que **puede funcionar o fallar**. En cada simulación se sortea, según su confiabilidad, si el control funciona ese año, y se aplica la reducción correspondiente. Esto captura la **incertidumbre sobre la efectividad del control**, no solo su valor esperado.

Campos principales:

| Campo | Rango | Significado |
|-------|-------|-------------|
| **`confiabilidad`** | 0–100 (%) | Probabilidad de que el control funcione en una simulación dada |
| **`reduccion_efectiva`** | -100 a 99 (%) | Reducción de frecuencia aplicada **cuando el control funciona** |
| **`reduccion_fallo`** | -100 a 99 (%) | Reducción de frecuencia aplicada **cuando el control falla** (típicamente 0, o incluso negativa si al fallar empeora) |

**Cómo funciona internamente (por simulación):**
1. Se sortea un número aleatorio; si es menor que `confiabilidad`, el control **funciona** esa simulación; si no, **falla**.
2. Si funciona, se aplica `reduccion_efectiva`; si falla, se aplica `reduccion_fallo`.
3. El resultado es una distribución de efectos (a veces reduce mucho, a veces poco), en lugar de un único número fijo.

**Ejemplo — "Sistema de respaldo automático":**
- `confiabilidad`: 90% → 9 de cada 10 años el respaldo actúa
- `reduccion_efectiva`: 70% → cuando actúa, reduce la frecuencia de pérdidas 70%
- `reduccion_fallo`: 0% → cuando falla, no reduce nada

En promedio el control reduce ~63% (0.90 × 70%), pero el modelo estocástico también refleja los años en que el control no funciona, generando una cola de escenarios peores que el modelo estático no captura.

### **¿Cuál usar?**

- Usá **estático** cuando quieras un efecto simple, conocido y constante.
- Usá **estocástico** cuando la **incertidumbre sobre si el control funcionará** sea relevante para el riesgo (p. ej. controles con fallas ocasionales, dependientes de terceros o de intervención humana). Es especialmente útil para no subestimar los escenarios extremos (colas de la distribución de pérdidas).

> Podés mezclar factores estáticos y estocásticos en un mismo evento; el motor los combina automáticamente.

---

## 💥 Factores que Afectan la Severidad (no solo la frecuencia)

Un factor no solo puede cambiar **cuántas veces** ocurre un evento (frecuencia), sino también **cuánto cuesta cada ocurrencia** (severidad). Cada factor tiene dos interruptores independientes:

- **`afecta_frecuencia`**: si está activo, el factor ajusta la distribución de frecuencia (es el comportamiento visto hasta acá).
- **`afecta_severidad`**: si está activo, el factor escala la severidad de cada pérdida.

Un mismo factor puede afectar **ambas**, solo una, o ninguna. Ejemplos:
- Un **plan de continuidad** podría no cambiar la frecuencia de incidentes, pero sí reducir el costo de cada uno (solo severidad).
- Una **mala configuración** podría aumentar tanto la cantidad como el costo de los incidentes (ambas).

Para factores **estocásticos**, la severidad tiene sus propios parámetros según el estado del control:

| Campo | Significado |
|-------|-------------|
| **`reduccion_severidad_efectiva`** | Reducción de severidad **cuando el control funciona** |
| **`reduccion_severidad_fallo`** | Reducción de severidad **cuando el control falla** |

> Los seguros son un caso particular de factor de severidad (con deducible, cobertura y límites) y se aplican siempre, independientemente del tipo de modelo del factor.

---

## 🎯 Distribuciones Soportadas y Método de Ajuste

| Distribución | Soporte | Parámetro Ajustado | Método de Combinación |
|--------------|---------|-------------------|----------------------|
| **Poisson** | ✅ Completo | λ (tasa/frecuencia) | Multiplicativo directo |
| **Binomial** | ✅ Completo | p (probabilidad) | Log-odds |
| **Bernoulli** | ✅ Completo | p (probabilidad) | Log-odds |
| **Poisson-Gamma** | ✅ Completo | λ (tasa/frecuencia) | Multiplicativo directo |
| **Beta** | ✅ Completo | p (probabilidad) | Log-odds |
| **Zero-Inflated Poisson (ZIP)** | ✅ Completo | λ (intensidad cuando ocurre) | Multiplicativo directo |

> **Todas** estas distribuciones soportan factores. Para la **Zero-Inflated Poisson** el factor escala su λ multiplicativamente (igual que Poisson), mientras que la probabilidad de "cero estructural" π se mantiene fija.

### **Métodos de Ajuste Explicados:**

1. **Multiplicativo Directo** (para distribuciones de **tasa/conteo**: Poisson, Poisson-Gamma y Zero-Inflated Poisson):
   - Control de -30% → Factor 0.70
   - Riesgo de +50% → Factor 1.50
   - Combinación: Factor_total = Factor1 × Factor2 × ...
   - λ_ajustada = λ_original × Factor_total
   - **Ejemplo**: λ=5.0 con controles -30% y -40% → λ_ajustado = 5.0 × 0.70 × 0.60 = 2.1

2. **Log-odds** (para distribuciones de **probabilidad**: Bernoulli, Binomial y Beta):
   - Transforma p a escala log-odds: logit(p) = ln(p / (1-p))
   - Suma ajustes en escala logit
   - Transforma de vuelta a probabilidad
   - **Ventaja**: Garantiza resultado en rango [0,1] y modela independencia de factores

> **Regla práctica**: el ajuste **log-odds** se usa únicamente cuando el parámetro ajustado es una **probabilidad** (Bernoulli, Binomial, Beta). Cuando el parámetro es una **tasa o conteo** (Poisson, Poisson-Gamma, Zero-Inflated Poisson), el ajuste es **multiplicativo sobre λ**.

---

## 🔧 Casos de Uso Comunes

### **1. Evaluación de Controles**

Comparar escenarios con/sin controles:
1. Crea dos escenarios
2. En uno, activa todos los controles
3. En otro, desactívalos
4. Compara los resultados de simulación

### **2. Análisis de Sensibilidad**

Evaluar el impacto de un control específico:
1. Activa/desactiva un control
2. Observa el cambio en la probabilidad ajustada
3. Ejecuta la simulación para ver el impacto en pérdidas

### **3. Documentación de Controles**

Registrar todos los controles implementados:
- Cada control queda documentado en el evento
- Los eventos con todos sus factores (estáticos y estocásticos, de frecuencia y severidad) se pueden exportar e importar mediante la funcionalidad de export/import JSON del modelo

### **4. Priorización de Inversiones**

Simular el efecto de implementar nuevos controles:
1. Agrega un control con impacto estimado
2. Marca como inactivo (representa "sin implementar")
3. Compara escenarios para justificar inversión

---

## ⚙️ Detalles Técnicos (Opcional)

### **¿Cómo Funciona Internamente?**

1. **Transformación Log-Odds**: Las probabilidades se convierten a escala log-odds
2. **Combinación Aditiva**: Los factores se suman en esta escala
3. **Transformación Inversa**: Se convierte de vuelta a probabilidad válida (0-1)

### **Ventajas del Método:**
- ✅ Combina múltiples factores de forma matemáticamente correcta
- ✅ Garantiza probabilidades válidas (siempre entre 0 y 1)
- ✅ Efectos independientes se modelan aditivamente
- ✅ Compatible con métodos de cuantificación de riesgos estándares

### **Ejemplo de Cálculo:**

```
Probabilidad base: p = 0.10
Control -30%:      log-odds = log(0.10/0.90) + (-0.30) = -2.197 - 0.30 = -2.497
Probabilidad ajustada: p' = 1/(1 + e^(2.497)) ≈ 0.074 (7.4%)
```

---

## 🛡️ Seguridad y Retrocompatibilidad

- ✅ **Retrocompatible**: Eventos sin factores funcionan igual que antes
- ✅ **Seguro**: Si hay error, se usa la distribución original
- ✅ **Opcional**: No afecta a eventos que no usan esta funcionalidad
- ✅ **Validado**: Todos los cálculos pasan tests matemáticos automáticos

---

## 📊 Recomendaciones de Uso

### **DO's (Hacer):**
- ✅ Usa valores de impacto basados en evidencia o estimaciones razonables
- ✅ Documenta la fuente del impacto en el nombre del factor
- ✅ Desactiva controles en lugar de eliminarlos (para análisis de sensibilidad)
- ✅ Revisa la probabilidad ajustada antes de guardar

### **DON'Ts (No Hacer):**
- ❌ No uses valores de impacto extremos sin justificación (>±100%)
- ❌ No combines demasiados factores sin validar el resultado
- ❌ No uses esta funcionalidad como sustituto de análisis riguroso
- ❌ No asumas que los efectos son exactamente aditivos en todos los casos

---

## 🆘 Resolución de Problemas

### **Problema: "⚠️ Falta archivo log_odds_utils.py"**

**Solución:** El archivo `log_odds_utils.py` debe estar en el mismo directorio que `Risk_Lab_Beta.py`.

### **Problema: La probabilidad ajustada no se muestra**

**Posibles causas:**
1. No hay factores activos configurados
2. La probabilidad base no se puede calcular (verifica parámetros de frecuencia)
3. La sección está colapsada (haz clic para expandir)

### **Problema: Los resultados de simulación no cambian**

**Verifica:**
1. Que guardaste el evento después de configurar los factores
2. Que los factores están marcados como "activos" (checkbox)
3. Que la distribución de frecuencia es compatible (todas lo son: Bernoulli, Binomial, Poisson, Poisson-Gamma, Beta y Zero-Inflated Poisson)

---

## 📝 Versión

- **Versión de la funcionalidad**: 2.0 (incluye factores estocásticos y de severidad)
- **Compatible con Risk Lab**: 1.10.0+
- **Fecha**: Agosto 2026

---

## 📞 Soporte

Para preguntas o problemas, consulta la documentación principal de Risk Lab o contacta al equipo de desarrollo.
