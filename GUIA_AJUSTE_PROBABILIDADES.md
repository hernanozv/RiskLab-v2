# Guía de Uso: Ajuste de Probabilidades con Controles y Factores de Riesgo

## 📋 Descripción General

Esta funcionalidad permite ajustar la probabilidad de frecuencia de los eventos de riesgo considerando:
- **Controles**: Reducen la probabilidad de ocurrencia (valores negativos)
- **Factores de riesgo**: Aumentan la probabilidad de ocurrencia (valores positivos)

Los ajustes se aplican automáticamente durante la simulación Monte Carlo, combinando múltiples factores de forma matemáticamente correcta usando transformaciones log-odds internamente.

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

## 🎯 Distribuciones Soportadas y Método de Ajuste

| Distribución | Soporte | Parámetro Ajustado | Método de Combinación |
|--------------|---------|-------------------|----------------------|
| **Poisson** | ✅ Completo | λ (frecuencia) | Multiplicativo directo |
| **Binomial** | ✅ Completo | p (probabilidad) | Log-odds |
| **Bernoulli** | ✅ Completo | p (probabilidad) | Log-odds |
| **Poisson-Gamma** | ✅ Completo | Valor más probable | Multiplicativo directo |
| **Beta** | ✅ Completo | p más probable | Log-odds |

### **Métodos de Ajuste Explicados:**

1. **Multiplicativo Directo** (para frecuencias esperadas):
   - Control de -30% → Factor 0.70
   - Riesgo de +50% → Factor 1.50
   - Combinación: Factor_total = Factor1 × Factor2 × ...
   - Parámetro_ajustado = Parámetro_original × Factor_total
   - **Ejemplo**: λ=5.0 con controles -30% y -40% → λ_ajustado = 5.0 × 0.70 × 0.60 = 2.1

2. **Log-odds** (para probabilidades):
   - Transforma p a escala log-odds: logit(p) = ln(p / (1-p))
   - Suma ajustes en escala logit
   - Transforma de vuelta a probabilidad
   - **Ventaja**: Garantiza resultado en rango [0,1] y modela independencia de factores

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
- Se puede exportar con la funcionalidad de batch import/export (próximamente)

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
3. Que la distribución de frecuencia es compatible (Bernoulli, Binomial, Poisson)

---

## 📝 Versión

- **Versión de la funcionalidad**: 1.0
- **Compatible con Risk Lab**: 1.10.0+
- **Fecha**: Noviembre 2024

---

## 📞 Soporte

Para preguntas o problemas, consulta la documentación principal de Risk Lab o contacta al equipo de desarrollo.
