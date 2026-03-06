# Manual de Interpretación de Resultados - Risk Lab

## Propósito de este Manual

Este manual está diseñado para que un agente de IA pueda interpretar, analizar y comunicar los resultados de las simulaciones Monte Carlo generadas por Risk Lab. El objetivo es ayudar al usuario a entender el impacto de los riesgos en su organización y tomar decisiones informadas.

> **📌 Documentos complementarios:**
> - **`MANUAL_AGENTE_IA_RISK_LAB.md`** — Guía para configurar la simulación y generar el JSON de entrada
> - **`ESPECIFICACION_JSON_RISK_LAB.md`** — Estructura técnica del JSON de importación
> - **Este manual** — Interpretación de resultados una vez ejecutada la simulación

---

## Estructura del Reporte PDF Exportado

El usuario proporcionará un **PDF exportado desde Risk Lab**. El PDF contiene las siguientes secciones en este orden:

### Sección 1: Resumen Ejecutivo de Resultados
Tabla con las métricas principales:
- Media de Pérdidas Agregadas
- Desviación Estándar
- VaR al 90%
- OpVaR al 99%
- Pérdida Esperada más allá del OpVaR 99% (CVaR)
- Máximo

### Sección 2: Frecuencia de Eventos Materializados
Tabla con:
- Número mínimo de eventos materializados
- Número más probable de eventos materializados (moda)
- Número máximo de eventos materializados

### Sección 3: Percentiles de Pérdida Agregada
Tabla con percentiles: P50, P75, P80, P85, P90, P95, P99

### Sección 4: Estadísticas por Evento de Riesgo
Para cada evento individual:
- Media de Impacto
- Desviación Estándar
- Eventos mínimos/más probables/máximos materializados

### Sección 5: Percentiles de Pérdida por Evento
Tabla matricial: cada evento como fila × percentiles como columnas (P50-P99), más una fila de "Pérdida Total"

### Sección 6: Gráficos de Análisis
Hasta 9 gráficos (ver sección "Gráficos y su Interpretación" más abajo)

### Formato de moneda en el PDF
Los valores monetarios usan formato: **`$X.XXX`** (punto como separador de miles, sin decimales). Ejemplo: `$1.250.000` = un millón doscientos cincuenta mil.

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
| **Mediana (P50)** | Valor central: 50% de simulaciones por debajo | Escenario "típico" — más robusto que la media ante outliers |
| **Desviación Estándar** | Dispersión alrededor de la media | Volatilidad/incertidumbre del riesgo |
| **VaR al 90%** | Percentil 90 de pérdidas | Pérdida que NO se excederá en 90% de los casos |
| **OpVaR al 99%** | Percentil 99 de pérdidas | Pérdida máxima en escenarios extremos (1 en 100) |
| **Pérdida Esperada más allá del OpVaR 99%** | Media de pérdidas > P99 (CVaR/ES) | Severidad promedio en escenarios catastróficos |
| **Máximo** | Mayor pérdida observada en todas las simulaciones | Peor caso absoluto simulado (depende de N) |

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

#### Mediana vs. Media — Insight Clave
```
"La mediana de $[MEDIANA] vs. la media de $[MEDIA] indica que 
[SI MEDIA >> MEDIANA: 'la distribución tiene cola pesada — eventos extremos 
infrecuentes elevan el promedio significativamente. El escenario típico es 
mejor que el promedio sugiere, pero los extremos son severos.']
[SI MEDIA ≈ MEDIANA: 'la distribución es relativamente simétrica — el 
promedio es un buen indicador del escenario típico.']"
```

**Regla práctica:**
- **Media/Mediana > 1.5**: Cola pesada — usar mediana para planificación operativa, media para reservas
- **Media/Mediana ≈ 1.0**: Simétrica — usar media como referencia principal

#### Máximo Simulado
```
"La pérdida máxima observada fue de $[MAX]. Este valor representa el peor 
escenario entre las [N] simulaciones ejecutadas. Importante: con más 
simulaciones, este valor podría ser aún mayor."
```

**Uso:**
- Punto de referencia para planificación de crisis
- NO usar como límite de exposición (es una sola observación)
- Comparar con límites de seguro y capacidad de absorción

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

### Impacto de Vínculos en los Resultados por Evento

Cuando un evento tiene vínculos (dependencias) configurados, sus resultados reflejan el efecto combinado de:

- **Activación condicional**: El evento solo se simula en las iteraciones donde sus condiciones de dependencia se cumplen, lo que reduce su frecuencia efectiva
- **Probabilidad de activación** (`probabilidad`): Si es <100%, solo un porcentaje de las activaciones del padre derivan en el hijo
- **Factor de severidad** (`factor_severidad`): Multiplica las pérdidas del evento hijo cuando el vínculo está activo
- **Umbral de severidad** (`umbral_severidad`): El padre debe superar un monto de pérdida neta para que el vínculo se active

**Patrones típicos en eventos con vínculos:**

| Patrón | Causa Probable | Interpretación |
|--------|----------------|----------------|
| Frecuencia baja + severidad alta | factor_severidad > 1.0 | Evento raro pero amplificado por cascada |
| Muchas simulaciones en $0 | probabilidad < 100% o umbral alto | La dependencia filtra muchas activaciones |
| Distribución bimodal | Vínculos OR con diferentes factores | Dos regímenes según qué padre se activa |
| Media mucho menor que evento aislado | factor_severidad < 1.0 | La cascada atenúa la severidad |

**Cómo comunicar:**
```
"El evento '[NOMBRE]' depende de [PADRE(S)]. En las simulaciones donde 
se activa la cascada, la severidad se multiplica por [FACTOR]x. El umbral 
de $[UMBRAL] en el padre filtra las activaciones menores, enfocando el 
impacto en escenarios donde el padre causa pérdidas significativas."
```

### Impacto del Escalamiento de Severidad por Frecuencia en los Resultados

Cuando un evento tiene activado el escalamiento de severidad por frecuencia (`sev_freq_activado: true`), los resultados muestran patrones característicos que difieren de una simulación LDA estándar donde frecuencia y severidad son independientes.

**Efecto general:** La pérdida media con escalamiento es **mayor** que sin escalamiento, porque las ocurrencias adicionales dentro de una misma simulación reciben multiplicadores crecientes (reincidencia) o porque simulaciones con frecuencia alta amplifican la severidad (sistémico).

**Patrones típicos en eventos con escalamiento:**

| Patrón | Modelo | Interpretación |
|--------|--------|----------------|
| Media significativamente mayor que sin escalamiento | Reincidencia o Sistémico | El escalamiento amplifica pérdidas como se espera |
| Pérdida por ocurrencia mayor en simulaciones de alta frecuencia | Reincidencia | Las ocurrencias tardías son más costosas que las primeras |
| Cola derecha más pesada | Ambos | Simulaciones con muchos eventos generan pérdidas desproporcionadamente altas |
| Correlación no lineal frecuencia-pérdida en gráfico de dispersión | Reincidencia | Más eventos → pérdida crece más que linealmente |
| Dispersión vertical mayor en frecuencias altas | Sistémico | Severidad amplificada por z-score en años de alta frecuencia |
| Poca diferencia vs. sin escalamiento | Reincidencia con Bernoulli | Bernoulli solo produce 0 o 1 ocurrencia → la 1ª siempre tiene multiplicador 1.0 |

**Cómo comunicar (Reincidencia):**
```
"El evento '[NOMBRE]' tiene configurado escalamiento de severidad por reincidencia.
Esto significa que cada ocurrencia adicional dentro del mismo año es progresivamente 
más costosa (multiplicador [TIPO]: [DESCRIPCION]).

- Sin escalamiento, la pérdida media sería ~$[X]
- Con escalamiento, la pérdida media es ~$[Y] (aumento del [%])
- En simulaciones con [N]+ ocurrencias, la pérdida por ocurrencia promedia $[Z], 
  vs $[W] en simulaciones con 1-2 ocurrencias

Esto modela el efecto de [RAZON: fatiga organizacional / agotamiento de recursos / 
sanciones regulatorias crecientes / etc.]."
```

**Cómo comunicar (Sistémico):**
```
"El evento '[NOMBRE]' tiene configurado escalamiento sistémico (alpha=[ALPHA]).
Años con frecuencia anormalmente alta (por encima de la media de [FREQ_MEDIA]) 
amplifican la severidad de cada pérdida individual.

- En años típicos (frecuencia ≈ media), el impacto es similar al base
- En años de alta frecuencia (z-score > 1), la severidad se amplifica hasta [FACTOR_MAX]x
[SI solo_aumento=true: '- En años de baja frecuencia, la severidad NO se reduce (solo_aumento activo)']
[SI solo_aumento=false: '- En años de baja frecuencia, la severidad se reduce proporcionalmente']

Esto modela la correlación sistémica donde [RAZON: debilidad organizacional / 
campaña coordinada / condiciones macroeconómicas adversas]."
```

**Análisis cuantitativo del impacto:**

Para evaluar el efecto del escalamiento, comparar:
```
Ratio de amplificación = Media_con_escalamiento / Media_sin_escalamiento

Valores típicos:
- Ratio 1.0-1.3: Efecto leve (alpha bajo o paso pequeño)
- Ratio 1.3-2.0: Efecto moderado (configuración típica)
- Ratio 2.0-3.0: Efecto fuerte (paso/alpha alto o frecuencia alta)
- Ratio > 3.0: Efecto muy fuerte (verificar si es realista)
```

**Insight clave — Interacción con otros componentes:**
El escalamiento se aplica ANTES de vínculos, controles y seguros. Esto significa que:
- Los controles mitigan la pérdida ya escalada (el beneficio del control es proporcionalmente mayor)
- Los seguros cubren la pérdida post-escalamiento y post-mitigación
- Los factores de severidad de vínculos se multiplican sobre la pérdida ya escalada

---

### Impacto de Controles Estocásticos en los Resultados

Cuando un evento tiene **factores estocásticos** (controles que pueden funcionar o fallar), los resultados muestran patrones característicos:

**Distribuciones bimodales o multimodales:**
Un control estocástico con alta confiabilidad y alta efectividad genera dos "regímenes":
- **Régimen 1 (control funciona)**: Pérdidas reducidas significativamente
- **Régimen 2 (control falla)**: Pérdidas a nivel base (sin mitigación)

```
"El histograma del evento '[NOMBRE]' muestra una distribución bimodal:
- Un pico en $[BAJO] (cuando el control [NOMBRE_CONTROL] funciona, [CONF]% del tiempo)
- Un pico en $[ALTO] (cuando falla, [100-CONF]% del tiempo)

Esto confirma que el control es efectivo cuando opera, pero su tasa de fallo 
del [100-CONF]% genera un riesgo residual significativo."
```

**Patrones por configuración de controles:**

| Configuración | Patrón esperado en resultados |
|---------------|-------------------------------|
| 1 control, alta confiabilidad (>80%) | Bimodal: pico grande bajo + pico pequeño alto |
| 1 control, baja confiabilidad (<50%) | Bimodal: pico grande alto + pico pequeño bajo |
| 2+ controles independientes | Multimodal (2^n regímenes posibles) |
| Control con 100% efectividad | Muchas simulaciones en $0 cuando funciona |
| Solo reducción de frecuencia | Frecuencia bimodal, severidad por evento sin cambio |

**Insight clave — Múltiples factores:**
Los factores se combinan multiplicativamente. Con 2+ controles de alta efectividad, la pérdida puede tender a 0 en muchas simulaciones. Si se observa >50% de simulaciones en $0, verificar si es realista que tantos controles funcionen simultáneamente.

---

### Información de Vínculos en el Reporte PDF

El reporte PDF generado por Risk Lab incluye, para cada evento con vínculos, una línea descriptiva que muestra:
- Tipo de dependencia (AND/OR/EXCLUYE)
- Nombre del evento padre
- Probabilidad de activación
- Factor de severidad (si ≠ 1.0)
- Umbral de severidad (si > $0)

Esta información es clave para que el lector del PDF pueda entender por qué un evento tiene un perfil de pérdida atípico (ej: frecuencia menor a la esperada, o severidad amplificada).

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

### Análisis de Impacto de Seguros

Si la simulación incluye controles de tipo seguro, analizar:

```
"ANÁLISIS DE TRANSFERENCIA DE RIESGO (SEGUROS)

Evento: [NOMBRE]
- Pérdida bruta media (sin seguro): $[X] (de otro escenario o estimación)
- Pérdida neta media (con seguro): $[Y]
- Transferencia efectiva: [((X-Y)/X) × 100]%

Eficiencia del seguro:
- Deducible: $[DED] → pérdidas bajo el deducible no cubiertas
- Cobertura: [COB]% sobre el exceso
- Límite: $[LIM] → pérdidas sobre el límite no cubiertas

Evaluación: Si la prima anual es $[PRIMA], el ratio prima/transferencia 
esperada es [PRIMA/(X-Y)]. Un ratio < 1.0 indica que el seguro es 
económicamente favorable en promedio."
```

**Patrones a identificar en resultados con seguros:**

| Patrón en resultados | Causa probable | Insight |
|----------------------|----------------|---------|
| Pérdida neta truncada arriba | Límite de seguro alcanzado | El seguro no cubre escenarios extremos |
| Distribución "aplanada" en la zona del deducible | Deducible alto | Pérdidas frecuentes menores no se transfieren |
| Poca diferencia bruta vs. neta | Deducible muy alto o baja frecuencia | El seguro aporta poco valor en este escenario |
| Gran diferencia en P99 pero no en media | Seguro efectivo en extremos | Buena protección catastrófica |
| Cola igual con/sin seguro | Límite de seguro insuficiente | Necesita más cobertura o póliza umbrella |

**Preguntas clave sobre seguros:**
1. ¿Qué porcentaje de la pérdida esperada se transfiere al seguro?
2. ¿El límite del seguro cubre el P99? Si no, ¿cuál es la brecha?
3. ¿Cuántas veces al año se activa el seguro (pérdidas > deducible)?
4. ¿Vale la prima? Comparar prima vs. reducción esperada de pérdidas

---

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

## Insights Avanzados para el Analista de Riesgo

### Beneficio de Diversificación

Cuando hay múltiples eventos independientes, el riesgo total es menor que la suma de los riesgos individuales. Calcular:

```
Beneficio de Diversificación:
  Suma P99 individuales = Σ P99(evento_i)
  P99 Total Agregado = P99(pérdida_total)
  Beneficio = 1 - (P99_Total / Suma_P99_individuales)
  
Ejemplo:
  P99 Evento A = $500K, P99 Evento B = $400K, P99 Evento C = $300K
  Suma = $1.2M
  P99 Total = $900K
  Beneficio de diversificación = 1 - (900K/1.2M) = 25%

"La diversificación reduce la exposición extrema en [X]%. Esto significa 
que no todos los eventos se materializan simultáneamente al nivel P99."
```

**Interpretación:**
- **Beneficio alto (>30%)**: Eventos poco correlacionados — buena diversificación natural
- **Beneficio bajo (<10%)**: Eventos altamente dependientes o dominados por uno solo
- **Beneficio ≈ 0%**: Un solo evento domina el riesgo total

---

### Análisis Frecuencia vs. Severidad (Driver Principal)

Para cada evento, identificar si el riesgo es "driver de frecuencia" o "driver de severidad":

```
Para cada evento:
  Frecuencia promedio × Severidad promedio por ocurrencia ≈ Media del evento

  Si Frecuencia > 5 y Severidad individual baja → "Driver de Frecuencia"
  Si Frecuencia < 1 y Severidad individual alta → "Driver de Severidad"
```

| Driver | Característica en resultados | Estrategia de mitigación |
|--------|------------------------------|--------------------------|
| **Frecuencia** | Muchos eventos, cada uno pequeño. Histograma concentrado | Prevención (reducir tasa de ocurrencia) |
| **Severidad** | Pocos eventos, cada uno grande. Cola pesada, outliers | Transferencia (seguros) y reducción de impacto |
| **Mixto** | Frecuencia moderada + severidad variable | Combinación de controles |

```
"El evento '[NOMBRE]' es un driver de [FRECUENCIA/SEVERIDAD]:
- Frecuencia promedio: [X] eventos/año
- Severidad promedio por ocurrencia: $[Y]
- Recomendación: [ESTRATEGIA]"
```

---

### Análisis de Concentración de Riesgo

Utilizar el gráfico de tornado para calcular el índice Herfindahl-Hirschman (HHI) de concentración:

```
HHI = Σ (contribucion_pct_i)²

Ejemplo: 3 eventos con 50%, 30%, 20%
HHI = 50² + 30² + 20² = 2500 + 900 + 400 = 3800
```

| HHI | Concentración | Interpretación |
|-----|--------------|----------------|
| < 1500 | Baja | Riesgo bien diversificado |
| 1500-2500 | Moderada | Algunos eventos dominan |
| > 2500 | Alta | Uno o dos eventos concentran el riesgo |

```
"El índice de concentración de riesgo es [HHI] ([NIVEL]). 
[SI ALTO: 'Los primeros 2 eventos representan el [X]% del riesgo total. 
Se recomienda priorizar la mitigación de estos eventos antes que distribuir 
recursos entre todos.']
[SI BAJO: 'El riesgo está distribuido entre múltiples eventos. Se 
recomienda una estrategia de controles transversales.']"
```

---

### Contribución Marginal al Riesgo

Para entender cuánto riesgo agrega cada evento al portfolio:

```
Contribución Marginal = Media_Total - Media_Total_sin_evento_i

"Si elimináramos completamente el evento '[NOMBRE]' (ej: con un control 
100% efectivo), la pérdida esperada se reduciría de $[TOTAL] a $[TOTAL-MEDIA_i], 
una reducción de $[MEDIA_i] ([%] del total)."
```

**Nota:** La contribución marginal difiere de la contribución proporcional cuando hay dependencias entre eventos. Si Evento B depende AND de Evento A, eliminar A también elimina B.

---

### Análisis de Capital y Reservas

Derivar requerimientos de capital a partir de los resultados:

```
"REQUERIMIENTOS DE CAPITAL SUGERIDOS

Nivel 1 - Reserva Operativa (pérdidas esperadas):
  Capital = Media = $[MEDIA]
  Cubre: escenario promedio, pérdidas recurrentes

Nivel 2 - Capital de Riesgo (escenarios adversos):
  Capital = VaR 90% = $[P90]
  Cubre: 9 de cada 10 años
  Capital adicional sobre Nivel 1: $[P90 - MEDIA]

Nivel 3 - Capital de Estrés (escenarios extremos):
  Capital = OpVaR 99% = $[P99]
  Cubre: 99 de cada 100 años
  Capital adicional sobre Nivel 2: $[P99 - P90]

Nivel 4 - Capital Catastrófico:
  Capital = CVaR 99% = $[CVaR]
  Cubre: promedio de pérdidas en el peor 1%
  Brecha sobre P99: $[CVaR - P99]"
```

**Framework de decisión:**

| Perfil de riesgo | Nivel de capital recomendado | Complemento |
|------------------|-----------------------------|-------------|
| Conservador | Nivel 3 (P99) | + Seguro catastrófico |
| Moderado | Nivel 2 (P90) | + Seguro para P90-P99 |
| Agresivo | Nivel 1 (Media) | + Seguro amplio |

---

### Eficiencia de la Frontera Riesgo-Retorno

Si hay múltiples escenarios con diferentes niveles de control:

```
Para cada escenario calcular:
  Costo_controles = suma de costos de implementación
  Reduccion_media = Media_base - Media_escenario
  Reduccion_P99 = P99_base - P99_escenario
  
  Eficiencia_media = Reduccion_media / Costo_controles
  Eficiencia_P99 = Reduccion_P99 / Costo_controles

"El escenario '[NOMBRE]' ofrece la mejor relación costo-beneficio:
- Inversión: $[COSTO]
- Reducción de pérdida esperada: $[X] (ratio [Eficiencia_media]:1)
- Reducción de P99: $[Y] (ratio [Eficiencia_P99]:1)

Por cada $1 invertido en controles, se reducen $[RATIO] en pérdidas esperadas."
```

---

### Convergencia de la Simulación

La precisión de las estadísticas depende del número de simulaciones:

```
Error estándar de la media ≈ STD / √N

Ejemplo: STD = $500K, N = 10,000
  Error estándar ≈ $500K / √10000 = $5K
  Intervalo de confianza 95% para la media: Media ± $10K
```

| N simulaciones | Precisión relativa de la media | Precisión de P99 |
|----------------|-------------------------------|-------------------|
| 1,000 | ±3.2% del STD | Baja (solo 10 observaciones en cola) |
| 10,000 | ±1.0% del STD | Moderada (100 observaciones en cola) |
| 100,000 | ±0.3% del STD | Buena (1000 observaciones en cola) |

**Señales de convergencia insuficiente:**
- P99 cambia significativamente si se re-ejecuta la simulación
- P99.99 tiene valores "irregulares"
- Pocos eventos en cola (< 50 observaciones sobre P99)

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

# Ratio de cola (mide peso de la cola)
ratio_cola = P99 / P50

# Ratio Media/Mediana (mide asimetría)
ratio_asimetria = media / mediana  # >1.5 = cola pesada

# Contribución porcentual
contribucion_pct = (media_evento / media_total) * 100

# Probabilidad de excedencia aproximada
prob_excedencia = (num_simulaciones_mayor_umbral / num_simulaciones_total) * 100

# Beneficio de diversificación
suma_P99_individuales = sum(P99_evento_i for each event)
beneficio_diversificacion = 1 - (P99_total / suma_P99_individuales)

# Índice de concentración (HHI)
HHI = sum(contribucion_pct_i ** 2 for each event)

# Error estándar de la media (confianza de la simulación)
error_estandar = desviacion_estandar / sqrt(num_simulaciones)

# Brecha de seguro (insurance gap)
brecha_seguro = P99_con_seguro  # Si > 0, hay riesgo residual no cubierto

# Capital económico (sobre media)
capital_economico = P99 - media

# Severidad promedio por ocurrencia (cuando frecuencia_moda > 0)
severidad_por_ocurrencia = media_evento / frecuencia_promedio_evento
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
- Evento con vínculos siempre en $0: Verificar que los padres se activan y que el umbral_severidad no es demasiado alto
- Severidad mucho mayor/menor que la distribución configurada: Revisar factor_severidad en los vínculos del evento
- Frecuencia del hijo > frecuencia del padre: Posible error en configuración de vínculos (verificar tipo AND/OR)
- Pérdida media mucho mayor que severidad × frecuencia esperada: Verificar si tiene escalamiento de severidad por frecuencia activo (`sev_freq_activado: true`) — el escalamiento amplifica pérdidas en simulaciones de alta frecuencia
- Correlación no lineal entre frecuencia y pérdida en gráfico de dispersión: Puede ser efecto del escalamiento por reincidencia (cada ocurrencia adicional tiene multiplicador creciente)
- Escalamiento activo pero sin efecto visible: Verificar si la distribución de frecuencia es Bernoulli (freq_opcion=3) — el modelo reincidencia no tiene efecto con frecuencia máxima 1

