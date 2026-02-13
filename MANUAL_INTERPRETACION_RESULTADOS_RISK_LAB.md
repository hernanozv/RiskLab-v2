# Manual de Interpretación de Resultados - Risk Lab

## Propósito de este Manual

Este manual está diseñado para que un agente de IA pueda interpretar, analizar y comunicar los resultados de las simulaciones Monte Carlo generadas por Risk Lab. El objetivo es ayudar al usuario a entender el impacto de los riesgos en su organización y tomar decisiones informadas.

---

## Estructura de Resultados de Risk Lab

Risk Lab genera dos tipos principales de resultados:

1. **Resultados Agregados**: Estadísticas y gráficos de la pérdida total combinada
2. **Resultados por Evento**: Estadísticas y análisis de cada evento de riesgo individual

---

## Resumen Ejecutivo de Pérdidas Agregadas

### Métricas Principales

| Métrica | Descripción | Interpretación |
|---------|-------------|----------------|
| **Media de Pérdidas Agregadas** | Promedio de todas las simulaciones | Pérdida esperada anual (Expected Loss) |
| **Desviación Estándar** | Dispersión alrededor de la media | Volatilidad/incertidumbre del riesgo |
| **VaR al 90%** | Percentil 90 de pérdidas | Pérdida que NO se excederá en 90% de los casos |
| **OpVaR al 99%** | Percentil 99 de pérdidas | Pérdida máxima en escenarios extremos (1 en 100) |
| **Pérdida Esperada más allá del OpVaR 99%** | Media de pérdidas > P99 (CVaR/ES) | Severidad promedio en escenarios catastróficos |

### Cómo Interpretar para el Usuario

#### Media de Pérdidas Agregadas
```
"Basado en la simulación, su organización puede esperar pérdidas anuales 
promedio de $[MEDIA]. Este es el valor que debería presupuestar como 
reserva base para cubrir riesgos operacionales."
```

**Aplicación práctica:**
- Presupuesto de contingencia
- Cálculo de primas de seguro
- Provisiones contables

#### Desviación Estándar
```
"La desviación estándar de $[STD] indica que las pérdidas reales pueden 
variar significativamente. En aproximadamente 68% de los años, las pérdidas 
estarán entre $[MEDIA-STD] y $[MEDIA+STD]."
```

**Interpretación del Coeficiente de Variación (CV = STD/Media):**
- CV < 0.5: Riesgo relativamente predecible
- CV 0.5-1.0: Variabilidad moderada
- CV > 1.0: Alta incertidumbre, posibles eventos extremos

#### VaR al 90% (Value at Risk)
```
"Con 90% de confianza, las pérdidas anuales no superarán $[VaR90]. 
Solo en 1 de cada 10 años esperaríamos pérdidas mayores a este valor."
```

**Uso típico:**
- Definición de apetito de riesgo
- Límites de tolerancia operacional
- Requisitos de capital regulatorio

#### OpVaR al 99% (Operational VaR)
```
"En escenarios extremos (1 en 100 años), las pérdidas podrían alcanzar 
hasta $[OpVaR99]. Este valor representa el 'peor caso razonable' para 
planificación de crisis."
```

**Uso típico:**
- Pruebas de estrés
- Planificación de continuidad de negocio
- Cobertura de seguros catastróficos

#### CVaR / Expected Shortfall (Pérdida más allá del OpVaR)
```
"Si ocurriera un evento catastrófico (peor que el 99% de los escenarios), 
la pérdida promedio sería de $[CVaR]. Este es el valor que la organización 
debería estar preparada para absorber en el peor escenario."
```

**Importancia:**
- Más informativo que VaR para colas pesadas
- Captura la severidad de eventos extremos
- Requerido por regulaciones como Basilea III/IV

---

## Estadísticas de Frecuencia Agregada

| Métrica | Descripción | Interpretación |
|---------|-------------|----------------|
| **Mínimo de eventos** | Menor cantidad de eventos en una simulación | Mejor escenario posible |
| **Moda de eventos** | Cantidad más frecuente de eventos | Escenario más probable |
| **Máximo de eventos** | Mayor cantidad de eventos en una simulación | Peor escenario de frecuencia |

### Cómo Interpretar

```
"En el escenario más probable, su organización experimentará [MODA] eventos 
de riesgo al año. Sin embargo, en casos extremos podrían ocurrir hasta 
[MAXIMO] eventos."
```

**Análisis adicional:**
- Si Mínimo = 0: Existe probabilidad de años sin pérdidas
- Si Moda << Media: Distribución sesgada (muchos años buenos, pocos muy malos)
- Si Máximo >> Moda: Posibilidad de "tormentas perfectas" de múltiples eventos

---

## Tabla de Percentiles de Pérdida Agregada

Risk Lab genera una tabla con los siguientes percentiles:

| Percentil | Significado | Uso Típico |
|-----------|-------------|------------|
| **P10** | Solo 10% de escenarios tienen pérdidas menores | Escenario optimista |
| **P20-P40** | Escenarios favorables | Planificación optimista |
| **P50 (Mediana)** | 50% de escenarios arriba/abajo | Escenario "típico" |
| **P60-P80** | Escenarios moderadamente adversos | Planificación conservadora |
| **P90** | VaR 90% - Solo 10% peor | Apetito de riesgo típico |
| **P95** | Solo 5% de escenarios peor | Tolerancia de riesgo |
| **P99** | Solo 1% de escenarios peor | Escenarios extremos |
| **P99.99** | 1 en 10,000 escenarios | Eventos catastróficos |

### Cómo Comunicar la Tabla

```
"La tabla de percentiles muestra la distribución completa de pérdidas posibles:

- En un año típico (P50), esperamos pérdidas de aproximadamente $[P50]
- En 9 de cada 10 años, las pérdidas serán menores a $[P90]
- En el peor 1% de los casos, las pérdidas podrían superar $[P99]

Esto nos permite establecer diferentes niveles de reservas según el 
nivel de confianza deseado."
```

---

## Estadísticas por Evento Individual

Para cada evento de riesgo, Risk Lab calcula:

| Métrica | Descripción |
|---------|-------------|
| **Media de Impacto** | Pérdida promedio anual por este evento |
| **Desviación Estándar** | Variabilidad del impacto |
| **Frecuencia Mínima** | Menor número de ocurrencias simuladas |
| **Frecuencia Moda** | Número más probable de ocurrencias |
| **Frecuencia Máxima** | Mayor número de ocurrencias simuladas |
| **Tabla de Percentiles** | Distribución completa de pérdidas |

### Análisis de Contribución al Riesgo

Para identificar los eventos más críticos, calcular:

```
Contribución % = (Media Evento / Media Total) × 100
```

**Clasificación de eventos:**
- **Críticos** (>25% contribución): Requieren atención prioritaria
- **Significativos** (10-25%): Monitoreo cercano
- **Moderados** (5-10%): Gestión estándar
- **Menores** (<5%): Monitoreo básico

### Cómo Comunicar

```
"El evento '[NOMBRE]' contribuye con $[MEDIA] (X% del total) a las pérdidas 
esperadas anuales. Con una frecuencia más probable de [MODA] ocurrencias 
por año, este evento representa [CLASIFICACION] en su perfil de riesgo."
```

---

## Gráficos y su Interpretación

Risk Lab genera 9 tipos de gráficos principales:

### 1. Distribución de Pérdidas Agregadas (Histograma)

**Qué muestra:** Histograma de todas las pérdidas simuladas con líneas de Media y P90.

**Cómo interpretar:**
- **Forma simétrica (campana)**: Riesgos predecibles, pocos extremos
- **Sesgo a la derecha (cola larga)**: Posibilidad de eventos extremos
- **Bimodal (dos picos)**: Dos "regímenes" de riesgo (ej: con/sin evento catastrófico)

**Comunicar al usuario:**
```
"El histograma muestra que la mayoría de escenarios resultan en pérdidas 
entre $[RANGO_PRINCIPAL]. Sin embargo, la cola derecha indica que eventos 
extremos de hasta $[MAXIMO_VISIBLE] son posibles, aunque poco probables."
```

### 2. Distribución sin Ceros

**Qué muestra:** Mismo histograma pero excluyendo simulaciones sin pérdidas.

**Cuándo es relevante:**
- Eventos con baja probabilidad de ocurrencia
- Controles muy efectivos que previenen muchos eventos

**Comunicar:**
```
"Cuando ocurren pérdidas, la distribución muestra [DESCRIPCION]. 
La diferencia con el histograma completo indica que en [X]% de los 
escenarios no hubo pérdidas gracias a los controles implementados."
```

### 3. Curva de Excedencia

**Qué muestra:** Probabilidad de que las pérdidas excedan cualquier valor dado.

**Lectura del gráfico:**
- Eje X: Valor de pérdida
- Eje Y: Probabilidad de exceder ese valor
- La curva siempre decrece de izquierda a derecha

**Uso práctico:**
```
"La curva de excedencia permite responder preguntas como:
- ¿Cuál es la probabilidad de perder más de $1M? → [X]%
- ¿Qué pérdida tiene solo 5% de probabilidad de ser excedida? → $[Y]

Esto es útil para definir umbrales de tolerancia y coberturas de seguro."
```

### 4. Histograma de Frecuencia de Eventos

**Qué muestra:** Distribución del número total de eventos por simulación.

**Interpretación:**
- **Concentrado en pocos valores**: Frecuencia predecible
- **Disperso**: Alta variabilidad en número de eventos
- **Cola derecha**: Posibilidad de "avalanchas" de eventos

**Comunicar:**
```
"El histograma de frecuencia muestra que típicamente ocurren entre 
[RANGO] eventos al año. La probabilidad de experimentar más de [N] 
eventos es aproximadamente [X]%."
```

### 5. Dispersión Frecuencia vs. Pérdidas

**Qué muestra:** Relación entre número de eventos y pérdida total.

**Patrones a identificar:**
- **Correlación lineal fuerte**: Más eventos = proporcionalmente más pérdidas
- **Dispersión vertical alta**: Severidad variable (algunos eventos mucho peores)
- **Puntos aislados arriba**: Eventos de alta severidad individual

**Comunicar:**
```
"El gráfico de dispersión muestra [DESCRIPCION DE PATRON]. Esto indica 
que [INTERPRETACION - ej: 'la severidad es más importante que la frecuencia' 
o 'la frecuencia es el driver principal de pérdidas']."
```

### 6. Comparación de Densidad entre Eventos (KDE)

**Qué muestra:** Curvas de densidad superpuestas para cada evento.

**Análisis:**
- Eventos con curvas más a la derecha = mayor severidad típica
- Eventos con colas más largas = mayor potencial de extremos
- Superposición indica eventos de impacto similar

**Comunicar:**
```
"La comparación de densidades revela que:
- [EVENTO_A] tiene la mayor severidad típica
- [EVENTO_B] tiene la cola más pesada (mayor riesgo extremo)
- [EVENTO_C] y [EVENTO_D] tienen perfiles similares"
```

### 7. Gráfico de Tornado (Contribución por Evento)

**Qué muestra:** Contribución promedio de cada evento a la pérdida total, ordenado de mayor a menor.

**Es el gráfico más importante para priorización.**

**Comunicar:**
```
"El gráfico de tornado identifica los eventos que más contribuyen al riesgo:

1. [EVENTO_TOP1]: $[VALOR] ([X]% del total) - PRIORIDAD ALTA
2. [EVENTO_TOP2]: $[VALOR] ([X]% del total) - PRIORIDAD ALTA
3. [EVENTO_TOP3]: $[VALOR] ([X]% del total) - PRIORIDAD MEDIA
...

Los primeros [N] eventos representan el [X]% del riesgo total. 
Enfocar recursos en estos eventos tendrá el mayor impacto."
```

### 8. Box Plots por Evento

**Qué muestra:** Distribución de pérdidas para cada evento (mediana, cuartiles, outliers).

**Elementos del box plot:**
- **Caja**: 50% central de los datos (Q1 a Q3)
- **Línea en caja**: Mediana (P50)
- **Bigotes**: Rango típico
- **Puntos**: Outliers (eventos extremos)

**Comunicar:**
```
"Los box plots revelan la variabilidad de cada evento:
- [EVENTO] tiene la mayor dispersión, indicando alta incertidumbre
- [EVENTO] tiene muchos outliers, sugiriendo potencial de extremos
- [EVENTO] es más predecible (caja estrecha)"
```

### 9. Cola de Pérdidas (Tail Risk)

**Qué muestra:** Solo el 20% superior de pérdidas (P80-P100), con líneas en P90, P95, P99.

**Es crítico para análisis de riesgo extremo.**

**Comunicar:**
```
"El análisis de cola muestra el comportamiento en escenarios adversos:
- El P90 ($[VALOR]) representa el umbral de 'año malo'
- El P95 ($[VALOR]) indica escenarios severos
- El P99 ($[VALOR]) marca eventos potencialmente catastróficos

La forma de la cola [DESCRIPCION] sugiere [INTERPRETACION]."
```

---

## Guía de Análisis de Riesgos

### Preguntas Clave que el Agente Debe Responder

#### 1. ¿Cuál es la exposición total al riesgo?
```
Respuesta: "La exposición anual esperada es de $[MEDIA], con un rango 
de $[P10] a $[P90] en el 80% de los escenarios. En casos extremos 
(1 en 100), las pérdidas podrían alcanzar $[P99]."
```

#### 2. ¿Cuáles son los riesgos más críticos?
```
Usar el gráfico de tornado para identificar los top 3-5 eventos.
Calcular el % de contribución de cada uno.
```

#### 3. ¿Es el riesgo manejable?
```
Comparar:
- Media vs. Presupuesto de contingencia
- P90 vs. Capacidad de absorción
- P99 vs. Límites de seguro
```

#### 4. ¿Qué tan efectivos son los controles?
```
Comparar escenarios con/sin controles.
Calcular reducción porcentual en Media y P90.
```

#### 5. ¿Dónde enfocar recursos de mitigación?
```
Priorizar eventos por:
1. Contribución a la pérdida total
2. Relación costo-beneficio de controles
3. Manejabilidad del riesgo
```

---

## Comunicación de Resultados por Audiencia

### Para Ejecutivos (C-Level)

**Enfoque:** Resumen ejecutivo, impacto en negocio, decisiones requeridas.

```
"RESUMEN EJECUTIVO DE RIESGOS

Exposición Anual:
- Pérdida esperada: $[MEDIA]
- Peor caso razonable (P99): $[P99]

Top 3 Riesgos Críticos:
1. [Evento]: $[Contribución] anuales
2. [Evento]: $[Contribución] anuales
3. [Evento]: $[Contribución] anuales

Recomendaciones:
- [Acción prioritaria 1]
- [Acción prioritaria 2]

Inversión requerida vs. Reducción esperada: [ROI]"
```

### Para Gestores de Riesgo

**Enfoque:** Detalle técnico, distribuciones, análisis de sensibilidad.

```
"ANÁLISIS TÉCNICO DE RIESGOS

Estadísticas de Pérdida Agregada:
- Media: $[MEDIA] ± $[STD]
- Coeficiente de Variación: [CV]
- VaR 90%: $[VaR90]
- CVaR 99%: $[CVaR]

Análisis por Evento:
[Tabla detallada con todas las métricas]

Análisis de Cola:
- Índice de cola: [Estimación]
- Eventos que dominan la cola: [Lista]

Efectividad de Controles:
[Comparación antes/después]"
```

### Para Auditores/Reguladores

**Enfoque:** Metodología, supuestos, cumplimiento.

```
"DOCUMENTACIÓN DE MODELO DE RIESGO

Metodología: Simulación Monte Carlo con [N] iteraciones
Distribuciones utilizadas: [Lista por evento]
Supuestos clave: [Lista]

Resultados de Capital:
- Capital requerido (VaR 99%): $[VALOR]
- Capital requerido (CVaR 99%): $[VALOR]

Validación:
- Pruebas de backtesting: [Resultados]
- Análisis de sensibilidad: [Resultados]"
```

---

## Recomendaciones Basadas en Resultados

### Según el Perfil de Riesgo

| Perfil | Característica | Recomendación |
|--------|----------------|---------------|
| **Concentrado** | Top 2 eventos > 60% | Mitigar eventos dominantes |
| **Disperso** | Ningún evento > 20% | Controles transversales |
| **Cola Pesada** | P99/P50 > 5 | Transferencia (seguros) |
| **Alta Frecuencia** | Moda > 10 eventos/año | Automatizar controles |
| **Alta Variabilidad** | CV > 1.5 | Reservas dinámicas |

### Según Comparación con Tolerancia

| Situación | Análisis | Acción |
|-----------|----------|--------|
| Media > Presupuesto | Riesgo excede capacidad | Reducir exposición urgente |
| P90 > Tolerancia | Riesgo alto en escenarios probables | Transferir o mitigar |
| P99 > Capacidad total | Riesgo existencial | Plan de crisis + seguro catastrófico |
| Media < 50% Presupuesto | Posible sobre-provisión | Optimizar reservas |

---

## Análisis de Escenarios

### Comparación de Escenarios

Cuando hay múltiples escenarios simulados:

```
"COMPARACIÓN DE ESCENARIOS

| Escenario | Media | P90 | P99 | Reducción vs. Base |
|-----------|-------|-----|-----|-------------------|
| Base (actual) | $[X] | $[Y] | $[Z] | - |
| Con controles | $[X'] | $[Y'] | $[Z'] | [%] |
| Pesimista | $[X''] | $[Y''] | $[Z''] | +[%] |

El escenario con controles reduce la pérdida esperada en [%], 
con una inversión de $[COSTO]. El ROI es de [X]:1."
```

### Análisis de Sensibilidad

Identificar qué parámetros tienen mayor impacto:

```
"SENSIBILIDAD DE RESULTADOS

Los resultados son más sensibles a:
1. Frecuencia de [Evento X] - ±10% frecuencia = ±$[Y] en Media
2. Severidad de [Evento Y] - ±20% severidad = ±$[Z] en P99
3. Efectividad de [Control W] - ±15% efectividad = ±$[V] en Media

Recomendación: Enfocarse en mejorar la precisión de estos parámetros."
```

---

## Indicadores de Alerta

### Señales de Riesgo Elevado

| Indicador | Umbral de Alerta | Significado |
|-----------|------------------|-------------|
| P99/Media | > 5 | Cola muy pesada |
| STD/Media (CV) | > 1.5 | Alta volatilidad |
| Max Eventos/Moda | > 3 | Posibles avalanchas |
| Top 1 Evento % | > 40% | Concentración peligrosa |
| P99 / Capacidad | > 0.8 | Cerca del límite |

### Señales de Modelo Inadecuado

| Señal | Posible Problema |
|-------|------------------|
| Muchas simulaciones en $0 | Frecuencias muy bajas, aumentar N |
| P99.99 = P99 | Cola truncada, revisar distribución |
| CV muy bajo (<0.1) | Modelo demasiado determinístico |
| Eventos siempre en mínimo | Frecuencia mal especificada |

---

## Plantilla de Reporte de Interpretación

```markdown
# Reporte de Análisis de Riesgos - [Organización]

## Resumen Ejecutivo

**Exposición Total Anual:**
- Pérdida Esperada: $[MEDIA]
- Rango Probable (P10-P90): $[P10] - $[P90]
- Peor Caso Razonable (P99): $[P99]

**Eventos Críticos:**
1. [Nombre]: [%] del riesgo total
2. [Nombre]: [%] del riesgo total
3. [Nombre]: [%] del riesgo total

**Nivel de Riesgo:** [BAJO/MODERADO/ALTO/CRÍTICO]

## Análisis Detallado

### Distribución de Pérdidas
[Descripción del histograma y forma de la distribución]

### Análisis de Cola
[Descripción de riesgos extremos]

### Efectividad de Controles
[Análisis de impacto de controles actuales]

## Recomendaciones

### Prioridad Alta
1. [Acción] - Impacto esperado: $[X] reducción

### Prioridad Media
1. [Acción] - Impacto esperado: $[X] reducción

### Monitoreo Continuo
- [Indicador a monitorear]

## Próximos Pasos
1. [Paso 1]
2. [Paso 2]
3. [Paso 3]
```

---

## Glosario de Términos

| Término | Definición |
|---------|------------|
| **VaR** | Value at Risk - Pérdida máxima con cierto nivel de confianza |
| **CVaR/ES** | Conditional VaR / Expected Shortfall - Media de pérdidas en la cola |
| **OpVaR** | Operational VaR - VaR aplicado a riesgos operacionales |
| **Percentil** | Valor bajo el cual cae cierto porcentaje de observaciones |
| **Media** | Valor esperado o promedio |
| **Moda** | Valor más frecuente |
| **Desviación Estándar** | Medida de dispersión alrededor de la media |
| **Cola** | Extremo de la distribución (típicamente el derecho/pérdidas altas) |
| **Monte Carlo** | Método de simulación basado en muestreo aleatorio |
| **KDE** | Kernel Density Estimation - Estimación suavizada de densidad |

---

## Notas Técnicas para el Agente

### Cálculos Útiles

```python
# Coeficiente de Variación
CV = desviacion_estandar / media

# Ratio de cola
ratio_cola = P99 / P50

# Contribución porcentual
contribucion_pct = (media_evento / media_total) * 100

# Probabilidad de excedencia aproximada
prob_excedencia = (num_simulaciones_mayor_umbral / num_simulaciones_total) * 100
```

### Interpretación de Formas de Distribución

| Forma | Características | Implicación |
|-------|-----------------|-------------|
| Simétrica | Media ≈ Mediana ≈ Moda | Riesgo balanceado |
| Sesgo derecho | Media > Mediana > Moda | Riesgo de cola |
| Bimodal | Dos picos | Dos regímenes de riesgo |
| Exponencial | Decaimiento rápido | Muchos pequeños, pocos grandes |
| Cola pesada | P99 >> P90 | Eventos extremos significativos |

### Banderas Rojas en Resultados

- Media = 0: Verificar si los eventos están activos
- STD = 0: Distribución degenerada, revisar parámetros
- P99 = P50: Cola truncada artificialmente
- Frecuencia siempre 0: Probabilidad muy baja o error en frecuencia

