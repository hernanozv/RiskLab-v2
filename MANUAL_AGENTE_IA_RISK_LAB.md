# Manual para Agentes de IA - Risk Lab

<!--
╔══════════════════════════════════════════════════════════════════╗
║  MAPA DEL DOCUMENTO — Manual del Agente IA                      ║
║                                                                  ║
║  ROL: Manual de referencia para agentes de IA. Explica QUÉ      ║
║  configurar y CÓMO interpretar los requerimientos del usuario.  ║
║                                                                  ║
║  SECCIONES (en orden de lectura):                               ║
║  1. Propósito y cross-references                                ║
║  2. Workflow recomendado (resumen)                              ║
║  3. Guía de selección: Distribuciones Frecuencia y Severidad    ║
║  4. ⭐ Plantilla JSON Completa (referencia rápida)              ║
║  5. Modo Avanzado: Parámetros Directos (Fase 2+)               ║
║     ⚠️ Contiene reglas CRÍTICAS de pg_alpha/pg_beta y Beta     ║
║  6. Preguntas Guía para el Agente                               ║
║  7. Modelo de Dependencias (Vínculos)                           ║
║  8. Factores de Ajuste (estático, estocástico, seguro)          ║
║  9. Escalamiento de Severidad por Frecuencia                    ║
║  10. Rangos, Validaciones, Conversión lenguaje natural          ║
║  11. Escenarios, Errores comunes, Checklist final               ║
║                                                                  ║
║  DOCUMENTOS COMPLEMENTARIOS:                                    ║
║  • Asistente GPT Risk Lab — System prompt con metodología       ║
║    conversacional, flujo de trabajo y guía anti-duplicación     ║
║  • ESPECIFICACION_JSON_RISK_LAB — Estructura JSON exacta,      ║
║    campos, tipos, validaciones y plantillas por distribución    ║
║  • MANUAL_INTERPRETACION_RESULTADOS — Cómo leer resultados     ║
╚══════════════════════════════════════════════════════════════════╝
-->

## Propósito de este Manual

Este manual está diseñado para que un agente de IA pueda asistir a usuarios en la preparación de análisis de riesgo cuantitativo utilizando simulación Monte Carlo. El objetivo es generar un archivo JSON válido que pueda importarse directamente en Risk Lab.

> **📌 IMPORTANTE**: Este manual explica **QUÉ configurar** y **CÓMO interpretar** los requerimientos del usuario. Para la **estructura JSON exacta** (campos obligatorios, tipos de datos, reglas de validación y plantillas), consultar siempre **`ESPECIFICACION_JSON_RISK_LAB.md`**. Ambos archivos son complementarios y necesarios para generar un JSON válido.
>
> Para **interpretar los resultados** de la simulación una vez ejecutada en Risk Lab, consultar **`MANUAL_INTERPRETACION_RESULTADOS_RISK_LAB.md`**.

---

## Flujo de Trabajo Recomendado

### Fase 1: Recopilación de Información

El agente debe obtener la siguiente información del usuario:

#### 1.1 Contexto General
- **¿Qué período de análisis?** (típicamente 1 año)
- **¿Cuál es la moneda?** (USD, EUR, etc. - Risk Lab no maneja moneda, solo valores numéricos)
- **¿Cuántas simulaciones desea?** (recomendado: 10,000 para precisión estadística)

#### 1.2 Identificación de Eventos de Riesgo
Preguntar al usuario:
- ¿Cuáles son los principales riesgos que enfrenta?
- Para cada riesgo:
  - Nombre descriptivo
  - ¿Cuántas veces al año podría ocurrir? (frecuencia)
  - ¿Cuál sería el impacto económico? (severidad)
  - ¿Existe relación con otros riesgos?
  - ¿Hay controles o factores que modifiquen este riesgo?

> **Nota sobre `activo`**: Cada evento y cada factor tiene un campo `activo` (boolean). Usar `false` para desactivar un evento o factor sin eliminarlo — útil para comparar escenarios "con control" vs "sin control", o para excluir temporalmente un evento. Los eventos inactivos no se simulan; los vínculos que apuntan a eventos inactivos se ignoran automáticamente.

---

## Guía de Selección de Distribuciones

### Distribuciones de FRECUENCIA

| Situación | Distribución | freq_opcion |
|-----------|--------------|-------------|
| "Ocurre aproximadamente X veces al año" | **Poisson** | 1 |
| "Hay N oportunidades, cada una con probabilidad P" | **Binomial** | 2 |
| "Ocurre o no ocurre (una vez máximo)" | **Bernoulli** | 3 |
| "No estoy seguro de la tasa exacta" | **Poisson-Gamma** | 4 |
| "No estoy seguro de la probabilidad exacta" | **Beta** | 5 |

#### Cuándo usar cada una:

**Poisson (freq_opcion: 1)**
- Usuario dice: "Tenemos unos 3 incidentes de seguridad al año"
- Usuario dice: "Recibimos alrededor de 5 reclamos anuales"
- **Parámetro**: `tasa` = número promedio esperado

**Binomial (freq_opcion: 2)**
- Usuario dice: "Tenemos 50 proveedores, cada uno con 5% de probabilidad de fallar"
- Usuario dice: "Procesamos 1000 transacciones, 0.1% pueden tener errores"
- **Parámetros**: `num_eventos` = N intentos, `prob_exito` = probabilidad por intento

**Bernoulli (freq_opcion: 3)**
- Usuario dice: "Un terremoto severo, ocurre o no"
- Usuario dice: "Un ataque dirigido específico"
- **Parámetro**: `prob_exito` = probabilidad de ocurrencia (0 a 1)

**Poisson-Gamma (freq_opcion: 4)**
- Usuario dice: "Entre 2 y 8 incidentes, probablemente unos 4"
- Usuario expresa incertidumbre sobre la tasa
- **Parámetros obligatorios**: `pg_alpha` (> 1) y `pg_beta` (> 0) — **SIEMPRE requeridos, nunca null**. Calcularlos con la fórmula PERT si el usuario da min/mode/max.
- **Parámetros opcionales** (para documentación): `pg_minimo`, `pg_mas_probable`, `pg_maximo`, `pg_confianza`

**Beta (freq_opcion: 5)**
- Usuario dice: "Probabilidad entre 10% y 40%, probablemente 20%"
- Para eventos tipo Bernoulli con incertidumbre en la probabilidad
- **Parámetros**: `beta_minimo`, `beta_mas_probable`, `beta_maximo` (en %), `beta_confianza`
- **⚠️ OBLIGATORIO**: Además se deben incluir `beta_alpha` y `beta_beta` calculados (> 0). Sin ellos, la importación falla. Ver el snippet de cálculo en `ESPECIFICACION_JSON_RISK_LAB.md` sección Beta Frecuencia.

---

### Distribuciones de SEVERIDAD

| Situación | Distribución | sev_opcion |
|-----------|--------------|------------|
| Pérdidas simétricas alrededor de un valor central | **Normal** | 1 |
| Pérdidas con cola derecha (más extremos altos) | **LogNormal** | 2 |
| Estimación por expertos (min/probable/max) | **PERT** | 3 |
| Eventos catastróficos con cola muy pesada | **Pareto/GPD** | 4 |
| Cualquier valor igualmente probable en un rango | **Uniforme** | 5 |

> **🚨 POLÍTICA OBLIGATORIA PARA IA**: Para `sev_opcion = 2` (LogNormal) y `sev_opcion = 4` (Pareto/GPD), el agente **DEBE** usar `sev_input_method: "direct"` con parámetros directos. No usar `min_mode_max` para estas distribuciones — puede causar errores de parametrización en la importación. Ver detalles en `ESPECIFICACION_JSON_RISK_LAB.md`.

#### Cuándo usar cada una:

**Normal (sev_opcion: 1)**
- Pérdidas relativamente predecibles
- Variación simétrica
- Usuario dice: "Generalmente entre $40K y $60K, típicamente $50K"

**LogNormal (sev_opcion: 2)** ⭐ **MÁS COMÚN PARA RIESGOS**
- La mayoría de pérdidas operacionales
- Pérdidas siempre positivas
- Posibilidad de extremos altos pero improbables
- Usuario dice: "Normalmente $50K-$200K, pero podría llegar a $1M"

**PERT (sev_opcion: 3)**
- Cuando el usuario da tres estimaciones claras
- Ideal para opiniones de expertos
- Usuario dice: "Mínimo $10K, más probable $50K, máximo $200K"

**Pareto/GPD (sev_opcion: 4)**
- Eventos catastróficos
- Ciberseguridad, desastres naturales
- Cola muy pesada (eventos extremos son más probables que en LogNormal)
- Usuario dice: "Típicamente $100K pero podría ser $5M o más"

**Uniforme (sev_opcion: 5)**
- Alta incertidumbre
- Cualquier valor en el rango es igualmente probable
- Usuario dice: "Puede ser cualquier cosa entre $20K y $80K, no tengo idea"

---

## Plantilla JSON Completa (Referencia Rápida)

> ⚠️ **Esta plantilla es la referencia principal** para la estructura de un evento. Copiar y completar con los valores del usuario. Para un modelo básico PERT+Poisson, solo cambiar `id`, `nombre`, `sev_minimo/mas_probable/maximo` y `tasa`. Para distribuciones avanzadas, ver la sección "Modo Avanzado: Parámetros Directos de Distribuciones" más adelante.

```json
{
    "num_simulaciones": 10000,
    "eventos_riesgo": [
        {
            "id": "GENERAR-UUID-UNICO",
            "nombre": "Nombre descriptivo del evento",
            "activo": true,
            
            "sev_opcion": 3,
            "sev_input_method": "min_mode_max",
            "sev_minimo": 10000,
            "sev_mas_probable": 50000,
            "sev_maximo": 200000,
            "sev_params_direct": {},
            "sev_limite_superior": null,
            
            "freq_opcion": 1,
            "freq_limite_superior": null,
            "tasa": 2.0,
            "num_eventos": null,
            "prob_exito": null,
            "pg_minimo": null,
            "pg_mas_probable": null,
            "pg_maximo": null,
            "pg_confianza": null,
            "pg_alpha": null,
            "pg_beta": null,
            "beta_minimo": null,
            "beta_mas_probable": null,
            "beta_maximo": null,
            "beta_confianza": null,
            "beta_alpha": null,
            "beta_beta": null,
            
            "sev_freq_activado": false,
            "sev_freq_modelo": "reincidencia",
            "sev_freq_tipo_escalamiento": "lineal",
            "sev_freq_paso": 0.5,
            "sev_freq_base": 1.5,
            "sev_freq_factor_max": 5.0,
            "sev_freq_tabla": [],
            "sev_freq_alpha": 0.5,
            "sev_freq_solo_aumento": true,
            "sev_freq_sistemico_factor_max": 3.0,
            
            "vinculos": [],
            "factores_ajuste": []
        }
    ],
    "scenarios": [],
    "current_scenario_name": null
}
```

> **Nota:** en este ejemplo PERT+Poisson (`freq_opcion: 1`), los campos `pg_alpha/pg_beta` están en `null` porque Poisson no los usa. **Para `freq_opcion=4` (Poisson-Gamma), `pg_alpha` y `pg_beta` son OBLIGATORIOS y nunca `null`.** Para `freq_opcion=5` (Beta), `beta_alpha`, `beta_beta` y `beta_minimo/mas_probable/maximo/confianza` son todos obligatorios y nunca `null`.

---

## Modo Avanzado: Parámetros Directos de Distribuciones

> 💡 **¿Modelo básico PERT+Poisson?** Esta sección es para Fase 2+ (distribuciones avanzadas). Para un modelo básico, usar la Plantilla JSON de arriba y saltar directamente a "Preguntas Guía para el Agente".
> ⚠️ **Excepción:** si se usa `freq_opcion=4` (Poisson-Gamma) o `freq_opcion=5` (Beta), **leer obligatoriamente** las subsecciones "Poisson-Gamma" y "Beta Frecuencia" de esta sección para las reglas de `pg_alpha`/`pg_beta` y `beta_alpha`/`beta_beta`.

Risk Lab permite ingresar parámetros estadísticos directos en lugar de usar min/mode/max. Esto es útil cuando el usuario tiene datos históricos o conoce los parámetros exactos de la distribución.

### Cuándo usar parámetros directos:
- El usuario tiene un estudio actuarial o estadístico previo
- Hay datos históricos analizados
- Se conocen los parámetros de la distribución por literatura
- Mayor precisión técnica requerida

### Configuración JSON para Parámetros Directos:

Para usar parámetros directos, cambiar:
```json
"sev_input_method": "direct"
```
Y completar el objeto `sev_params_direct` según la distribución.

---

### SEVERIDAD - Parámetros Directos

#### Normal (sev_opcion: 1)

```json
{
    "sev_opcion": 1,
    "sev_input_method": "direct",
    "sev_minimo": null,
    "sev_mas_probable": null,
    "sev_maximo": null,
    "sev_params_direct": {
        "mean": 50000,
        "std": 15000
    }
}
```

| Parámetro | Alias | Descripción | Restricción |
|-----------|-------|-------------|-------------|
| `mean` | `mu` | Media de la distribución | Cualquier valor |
| `std` | `sigma` | Desviación estándar | > 0 |

**Interpretación**: ~68% de valores entre mean±std, ~95% entre mean±2*std

---

#### LogNormal (sev_opcion: 2)

Tres opciones de parametrización:

**Opción A: Media y desviación en escala original (X)**
```json
{
    "sev_opcion": 2,
    "sev_input_method": "direct",
    "sev_params_direct": {
        "mean": 50000,
        "std": 30000,
        "loc": 0
    }
}
```
- `mean`: Media de X (valores observados)
- `std`: Desviación estándar de X
- `loc`: Desplazamiento (típicamente 0)

**Opción B: Parámetros μ y σ de ln(X)**
```json
{
    "sev_opcion": 2,
    "sev_input_method": "direct",
    "sev_params_direct": {
        "mu": 10.5,
        "sigma": 0.8,
        "loc": 0
    }
}
```
- `mu`: Media de ln(X) - parámetro de ubicación del logaritmo
- `sigma`: Desviación estándar de ln(X) (> 0)
- `loc`: Desplazamiento

**Opción C: Parámetros nativos SciPy (s, scale)**
```json
{
    "sev_opcion": 2,
    "sev_input_method": "direct",
    "sev_params_direct": {
        "s": 0.8,
        "scale": 36315,
        "loc": 0
    }
}
```
- `s`: Shape parameter (= σ de ln(X), > 0)
- `scale`: Scale parameter (= exp(μ), > 0)
- `loc`: Location parameter

**Conversiones útiles:**
```
Si conoces mean y std de X:
  σ² = ln(1 + (std/mean)²)
  μ = ln(mean) - σ²/2
  
Si conoces μ y σ:
  mean = exp(μ + σ²/2)
  std = mean × √(exp(σ²) - 1)
```

**⭐ Guía práctica: Convertir min/mode/max del usuario a parámetros directos LogNormal**

Cuando el usuario da estimaciones tipo "entre $50K y $500K, más probable $100K", seguir estos pasos:

```
Paso 1: Estimar media y std con fórmula PERT
  mean_aprox = (min + 4 × mode + max) / 6
  std_aprox  = (max - min) / 6

Paso 2: Convertir a parámetros de ln(X)
  σ² = ln(1 + (std_aprox / mean_aprox)²)
  μ  = ln(mean_aprox) - σ²/2

Paso 3: Usar Opción B (mu/sigma) o convertir a Opción C (s/scale)
  s = √σ²
  scale = exp(μ)
```

**Ejemplo**: Usuario dice "mínimo $20K, más probable $50K, máximo $200K"
```
  mean ≈ (20000 + 4×50000 + 200000) / 6 ≈ 70000
  std  ≈ (200000 - 20000) / 6 ≈ 30000
  σ²   = ln(1 + (30000/70000)²) = ln(1.184) ≈ 0.169
  μ    = ln(70000) - 0.169/2 ≈ 11.07
  → Usar: {"mu": 11.07, "sigma": 0.41, "loc": 0}
  → O equivalente: {"s": 0.41, "scale": 64500, "loc": 0}
```

---

#### Pareto/GPD (sev_opcion: 4)

```json
{
    "sev_opcion": 4,
    "sev_input_method": "direct",
    "sev_params_direct": {
        "c": 0.3,
        "scale": 200000,
        "loc": 100000
    }
}
```

| Parámetro | Símbolo | Descripción | Valores típicos |
|-----------|---------|-------------|-----------------|
| `c` | ξ (xi) | Shape - controla peso de cola | -0.5 a 1.0 |
| `scale` | β (beta) | Scale - dispersión | > 0 |
| `loc` | μ (mu) | Location - umbral mínimo | ≥ 0 |

**Interpretación del parámetro c (shape):**
- `c < 0`: Cola finita (distribución Weibull), máximo = loc + scale/|c|
- `c = 0`: Cola exponencial (decaimiento rápido)
- `c > 0`: Cola pesada tipo Pareto (eventos extremos más probables)
  - c = 0.1-0.3: Cola moderadamente pesada
  - c = 0.3-0.5: Cola pesada (ciberseguridad típico)
  - c > 0.5: Cola muy pesada (catástrofes)

**Ejemplo práctico:**
- `c=0.3, scale=200000, loc=100000` → Pérdidas desde $100K, típicamente $200K-$500K, posibles extremos de varios millones

**⭐ Guía práctica: Estimar parámetros GPD desde descripción del usuario**

| Pregunta al usuario | Parámetro |
|---------------------|-----------|
| "¿Cuál es la pérdida mínima si ocurre?" | `loc` = ese valor |
| "¿Cuál es la pérdida típica sobre el mínimo?" | `scale` ≈ (pérdida típica - loc) |
| "¿Qué tan extremos pueden ser los eventos?" | `c` según tabla abajo |

**Estimación de `c` (shape):**

| Descripción del usuario | `c` sugerido |
|-------------------------|--------------|
| "Pérdidas acotadas, no pueden superar X" | -0.2 a -0.1 |
| "Decaimiento rápido, extremos muy raros" | 0.0 a 0.1 |
| "Posibles extremos significativos" | 0.1 a 0.3 |
| "Cola pesada, ciberseguridad/fraude" | 0.3 a 0.5 |
| "Catastrófico, sin límite práctico" | 0.5 a 1.0 |

**Ejemplo**: Usuario dice "pérdida mínima $100K, típicamente $200K-$400K, pero podría llegar a varios millones"
```
  loc = 100000 (umbral mínimo)
  scale = 200000 (típico sobre el mínimo ≈ $300K - $100K)
  c = 0.3 (cola pesada, posibles extremos altos)
  → Usar: {"c": 0.3, "scale": 200000, "loc": 100000}
```

---

### FRECUENCIA - Parámetros Directos

#### Poisson-Gamma (freq_opcion: 4)

> ⚠️ **REGLA CRÍTICA**: `pg_alpha` y `pg_beta` son **SIEMPRE OBLIGATORIOS** para `freq_opcion=4`. **Nunca dejarlos en `null`** — si están null, la importación falla con CRASH TOTAL. El camino min/mode/max como fallback interno es frágil (usa optimización scipy que puede fallar silenciosamente). Siempre calcular y proveer `pg_alpha` y `pg_beta` explícitamente.

**Con min/mode/max del usuario (calcular alpha/beta con fórmula PERT)**:
```json
{
    "freq_opcion": 4,
    "pg_minimo": 1,
    "pg_mas_probable": 3,
    "pg_maximo": 8,
    "pg_confianza": 90,
    "pg_alpha": 9.01,
    "pg_beta": 2.57
}
```

**Fórmula para calcular `pg_alpha` y `pg_beta`:**
```
mean = (mínimo + 4 × más_probable + máximo) / 6
var  = ((máximo - mínimo) / 6)²
pg_alpha = mean² / var      (si resulta ≤ 1, usar 1.5 como mínimo)
pg_beta  = mean / var
```
Los campos min/mode/max/confianza son opcionales (para documentación/UI). Lo que importa es que `pg_alpha` y `pg_beta` estén siempre presentes con valores numéricos válidos.

**Con parámetros directos α y β (sin min/mode/max)**:
```json
{
    "freq_opcion": 4,
    "pg_minimo": null,
    "pg_mas_probable": null,
    "pg_maximo": null,
    "pg_confianza": null,
    "pg_alpha": 5.0,
    "pg_beta": 2.0
}
```

| Parámetro | Descripción | Restricción |
|-----------|-------------|-------------|
| `pg_alpha` | Shape de la Gamma | > 1 (para moda definida) |
| `pg_beta` | Rate de la Gamma | > 0 |

**Propiedades de Gamma(α, β):**
```
Media = α / β
Moda = (α - 1) / β  (cuando α > 1)
Varianza = α / β²
```

**Ejemplo:** `alpha=5, beta=2` → Media=2.5, Moda=2.0, Varianza=1.25

---

#### Beta Frecuencia (freq_opcion: 5)

> ⚠️ **REGLA CRÍTICA**: `beta_alpha` y `beta_beta` son **SIEMPRE OBLIGATORIOS** (ambos > 0). Además, `beta_minimo`, `beta_mas_probable`, `beta_maximo` y `beta_confianza` **NO pueden ser `null`** cuando `freq_opcion=5` — deben ser numéricos. Sin estos campos la importación falla con CRASH TOTAL.

```json
{
    "freq_opcion": 5,
    "beta_minimo": 5,
    "beta_mas_probable": 15,
    "beta_maximo": 40,
    "beta_confianza": 90,
    "beta_alpha": 2.0,
    "beta_beta": 8.0
}
```
**Nota:** los valores de `beta_minimo/beta_mas_probable/beta_maximo` son **PORCENTAJES (0-100)**, no decimales (0-1).

| Parámetro | Descripción | Restricción |
|-----------|-------------|-------------|
| `beta_alpha` | Parámetro α de Beta | > 0 |
| `beta_beta` | Parámetro β de Beta | > 0 |

**Propiedades de Beta(α, β):**
```
Media = α / (α + β)
Moda = (α - 1) / (α + β - 2)  (cuando α, β > 1)
Varianza = αβ / [(α + β)²(α + β + 1)]
```

**Ejemplo:** `alpha=2, beta=8` → Media=0.20 (20%), Moda=0.125 (12.5%)

**Interpretación Bayesiana:**
- α = "éxitos observados + 1"
- β = "fracasos observados + 1"
- Si hubo 5 eventos en 25 años: α=6, β=21 → Media≈22%

---

### Tabla Resumen de Parámetros Directos

| Distribución | sev_opcion | Parámetros directos | Cuándo usar |
|--------------|------------|---------------------|-------------|
| Normal | 1 | mean, std | Datos simétricos |
| LogNormal | 2 | mean/std, mu/sigma, o s/scale | Datos históricos de pérdidas |
| PERT | 3 | No soporta | Solo min/mode/max |
| Pareto/GPD | 4 | c, scale, loc | Análisis de extremos (EVT) |
| Uniforme | 5 | No soporta | Solo min/max |

| Distribución | freq_opcion | Parámetros directos | Cuándo usar |
|--------------|-------------|---------------------|-------------|
| Poisson | 1 | Solo `tasa` | Frecuencia conocida |
| Binomial | 2 | n, p | Ensayos conocidos |
| Bernoulli | 3 | Solo `prob_exito` | Probabilidad conocida |
| Poisson-Gamma | 4 | pg_alpha, pg_beta | Análisis Bayesiano |
| Beta | 5 | beta_alpha, beta_beta | Análisis Bayesiano |

---

### Ejemplo Completo con Parámetros Directos

```json
{
    "id": "evt-perdida-operacional-001",
    "nombre": "Pérdida Operacional (datos históricos)",
    "activo": true,
    
    "sev_opcion": 2,
    "sev_input_method": "direct",
    "sev_minimo": null,
    "sev_mas_probable": null,
    "sev_maximo": null,
    "sev_params_direct": {
        "mu": 10.82,
        "sigma": 1.2,
        "loc": 0
    },
    "sev_limite_superior": null,
    
    "freq_opcion": 4,
    "freq_limite_superior": null,
    "tasa": null,
    "num_eventos": null,
    "prob_exito": null,
    "pg_minimo": null,
    "pg_mas_probable": null,
    "pg_maximo": null,
    "pg_confianza": null,
    "pg_alpha": 4.5,
    "pg_beta": 1.5,
    "beta_minimo": null,
    "beta_mas_probable": null,
    "beta_maximo": null,
    "beta_confianza": null,
    "beta_alpha": null,
    "beta_beta": null,
    
    "vinculos": [],
    "factores_ajuste": []
}
```

Este evento modela:
- **Severidad**: LogNormal con μ=10.82, σ=1.2 → Media≈$75K, mediana≈$50K, posibles extremos >$500K
- **Frecuencia**: Poisson-Gamma con α=4.5, β=1.5 → Tasa media=3/año, con incertidumbre

---

## Preguntas Guía para el Agente

### Para determinar FRECUENCIA:

```
1. "¿Con qué frecuencia cree que podría ocurrir este evento en un año?"
   
   - Si responde con un número aproximado → Poisson
   - Si responde "solo una vez o ninguna" → Bernoulli
   - Si responde con un rango → Poisson-Gamma o Beta

2. "¿Hay múltiples oportunidades para que ocurra?"
   
   - Si hay N intentos independientes → Binomial
   - Si es un evento único posible → Bernoulli

3. "¿Qué tan seguro está de esa frecuencia?"
   
   - Muy seguro → Poisson o Bernoulli
   - Incierto → Poisson-Gamma (para tasas) o Beta (para probabilidades)
```

### Para determinar SEVERIDAD:

```
1. "¿Cuál sería el impacto económico si ocurriera?"
   
   - Pedir: mínimo, más probable, máximo

2. "¿Es posible un escenario extremo mucho mayor que el máximo típico?"
   
   - Sí, definitivamente → Pareto/GPD
   - Posible pero raro → LogNormal
   - No realmente → Normal o PERT

3. "¿El impacto varía mucho o es relativamente constante?"
   
   - Varía mucho → LogNormal o Pareto
   - Relativamente constante → Normal o PERT
```

---

## Modelo de Dependencias (Vínculos)

### Cuándo crear vínculos:

| Situación | Tipo de Vínculo |
|-----------|------------------|
| "B solo puede ocurrir si A ocurrió" | B depende de A (AND) |
| "B puede ocurrir si A o C ocurrieron" | B depende de A y C (OR) |
| "B no puede ocurrir si A ocurrió" | B excluido por A (EXCLUYE) |
| "Son eventos en cadena" | Crear cadena de dependencias |

### Campos de cada vínculo:

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `id_padre` | string | (requerido) | UUID del evento padre |
| `tipo` | string | (requerido) | `"AND"`, `"OR"` o `"EXCLUYE"` |
| `probabilidad` | integer | 100 | Probabilidad de activación del vínculo (1-100%) |
| `factor_severidad` | float | 1.0 | Multiplicador de severidad condicional (0.10-5.00) |
| `umbral_severidad` | integer | 0 | Pérdida neta mínima del padre para activar ($, ≥0) |

### Cuándo usar cada campo avanzado:

**`probabilidad` (<100)**
- "Si ocurre phishing, hay un 60% de que se comprometan credenciales"
- Modela la probabilidad condicional de que un evento derive en otro

**`factor_severidad` (≠1.0)**
- "Si ocurre un terremoto, los daños por incendio son 2x peores" → factor = 2.0
- "Si hay backup, la pérdida de datos es menor" → factor = 0.5
- **AND**: los factores de todos los vínculos AND activos se **multiplican**
- **OR**: se toma el **máximo** de los factores OR activos
- **EXCLUYE**: no aporta factor de severidad (siempre 1.0)

**`umbral_severidad` (>0)**
- "La brecha de datos solo se activa si el ataque causó más de $50K" → umbral = 50000
- Compara contra la pérdida **neta** del padre (post-controles y seguros)
- $0 = sin umbral, basta con que el padre haya ocurrido

### Ejemplo JSON de vínculos avanzados:

```json
"vinculos": [
    {
        "id_padre": "uuid-evento-phishing",
        "tipo": "AND",
        "probabilidad": 60,
        "factor_severidad": 1.5,
        "umbral_severidad": 10000
    },
    {
        "id_padre": "uuid-evento-vulnerabilidad",
        "tipo": "OR",
        "probabilidad": 80,
        "factor_severidad": 2.0,
        "umbral_severidad": 0
    }
]
```

### Ejemplos de cadenas de riesgo:

**Ciberataque en cadena:**
1. Phishing exitoso (evento raíz)
2. Compromiso de credenciales (depende AND de 1, prob: 60%)
3. Movimiento lateral (depende AND de 2, factor_sev: 1.3)
4. Exfiltración de datos (depende AND de 3, umbral: $50K)
5. Ransomware (depende AND de 2 o 3, factor_sev: 2.0)

**Desastre natural:**
1. Terremoto (evento raíz)
2. Daño a infraestructura (depende AND de 1, factor_sev: 1.5)
3. Interrupción de operaciones (depende AND de 2)
4. Pérdida de datos (depende OR de 1 y otro evento)

### Reglas importantes:
- **NO crear ciclos** (A→B→C→A es inválido)
- Los eventos raíz no tienen vínculos
- Un hijo puede tener múltiples padres
- `factor_severidad` para EXCLUYE siempre debe ser 1.0 (se ignora en simulación)
- Campos `probabilidad`, `factor_severidad` y `umbral_severidad` son opcionales (backward compatible)

---

## Modelo de Factores/Controles

### Cuándo usar Modelo ESTÁTICO vs ESTOCÁSTICO:

| Situación | Modelo |
|-----------|--------|
| "El control siempre reduce X%" | **Estático** |
| "El control funciona el Y% de las veces" | **Estocástico** |
| Control técnico automatizado | **Estático** o **Estocástico** |
| Control humano (puede fallar) | **Estocástico** |
| Seguro o cobertura fija | **Estático** |

> **⚠️ CAMPO CRÍTICO**: El campo `nombre` es **obligatorio** en todos los factores y es el **único campo que Risk Lab NO auto-genera**. Si falta, la UI mostrará celdas vacías. Siempre incluir un nombre descriptivo.

### Modelo Estático:
```
Preguntar: "¿En qué porcentaje reduce este control el riesgo?"
- Si reduce frecuencia: impacto_porcentual negativo (ej: -30)
- Si aumenta riesgo: impacto_porcentual positivo (ej: +20)
```

### Modelo Estocástico:
```
Preguntar:
1. "¿Qué tan confiable es el control? (% de veces que funciona)"
   → confiabilidad (0-100)

2. "Cuando funciona, ¿cuánto reduce el riesgo?"
   → reduccion_efectiva (positivo reduce)

3. "Cuando falla, ¿hay algún efecto residual?"
   → reduccion_fallo (típicamente 0-10)
```

### Ejemplos de controles comunes:

| Control | Tipo | Configuración sugerida |
|---------|------|------------------------|
| Firewall | Estático | freq: -40%, sev: -20% |
| Antivirus/EDR | Estocástico | 80% conf, 70% efectivo, 10% fallo |
| Backup | Estocástico | 95% conf, 80% sev efectivo |
| Capacitación | Estático | freq: -25% |
| MFA | Estático | freq: -50% |
| SIEM | Estocástico | 70% conf, 40% efectivo |
| DLP | Estocástico | 75% conf, 60% efectivo, 5% fallo |
| **Seguro Cyber** | **Seguro** | ded: $25K/ocurr, cob: 80%, lím: $500K/evento, $2M/año |
| **Seguro Property** | **Seguro** | ded: $100K/año, cob: 90%, lím: $5M/año |

---

### Estructura JSON Completa de Factores

#### Factor Estático - JSON Completo:

```json
{
    "nombre": "Firewall Perimetral",
    "activo": true,
    "tipo_modelo": "estatico",
    
    "afecta_frecuencia": true,
    "impacto_porcentual": -40,
    
    "afecta_severidad": true,
    "impacto_severidad_pct": -20
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre` | string | Nombre descriptivo del control |
| `activo` | boolean | Si el factor está habilitado |
| `tipo_modelo` | string | **"estatico"** |
| `afecta_frecuencia` | boolean | Si modifica la frecuencia |
| `impacto_porcentual` | integer | % impacto en frecuencia (mínimo -99, sin límite superior) |
| `afecta_severidad` | boolean | Si modifica la severidad |
| `impacto_severidad_pct` | integer | % impacto en severidad (mínimo -99, sin límite superior) |

**⚠️ CONVENCIÓN DE SIGNOS - ESTÁTICO:**
- **Valor NEGATIVO = REDUCE** (ej: -30 reduce 30%)
- **Valor POSITIVO = AUMENTA** (ej: +20 aumenta 20%)
- Fórmula: `factor = 1 + (impacto/100)`

---

#### Factor Estocástico - JSON Completo:

```json
{
    "nombre": "Sistema EDR",
    "activo": true,
    "tipo_modelo": "estocastico",
    
    "confiabilidad": 85,
    
    "reduccion_efectiva": 70,
    "reduccion_fallo": 10,
    
    "reduccion_severidad_efectiva": 50,
    "reduccion_severidad_fallo": 5
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre` | string | Nombre descriptivo del control |
| `activo` | boolean | Si el factor está habilitado |
| `tipo_modelo` | string | **"estocastico"** |
| `confiabilidad` | integer | % de veces que funciona (0-100) |
| `reduccion_efectiva` | integer | % reducción frecuencia si funciona |
| `reduccion_fallo` | integer | % reducción frecuencia si falla |
| `reduccion_severidad_efectiva` | integer | % reducción severidad si funciona |
| `reduccion_severidad_fallo` | integer | % reducción severidad si falla |

**⚠️ CONVENCIÓN DE SIGNOS - ESTOCÁSTICO (OPUESTA AL ESTÁTICO):**
- **Valor POSITIVO = REDUCE** (ej: 80 reduce 80%)
- **Valor NEGATIVO = AUMENTA** (ej: -20 aumenta 20%)
- Fórmula: `factor = 1 - (reduccion/100)`

**⚠️ COMPORTAMIENTO**: En cada iteración, el sistema genera **un único** número aleatorio por factor. Si "funciona", aplica `reduccion_efectiva` (frecuencia) y `reduccion_severidad_efectiva` (severidad) simultáneamente. Si "falla", aplica `reduccion_fallo` y `reduccion_severidad_fallo`. Es decir, **el mismo sorteo** determina ambos efectos.

---

### Diferencia Crítica de Convenciones

| Modelo | Para REDUCIR | Para AUMENTAR | Ejemplo reduce 30% |
|--------|--------------|---------------|-------------------|
| **Estático** | Valor negativo | Valor positivo | `-30` |
| **Estocástico** | Valor positivo | Valor negativo | `30` |

**Ejemplo comparativo:**
- Control que reduce 50% en estático: `"impacto_porcentual": -50`
- Control que reduce 50% en estocástico: `"reduccion_efectiva": 50`

---

## Controles de Tipo Seguro/Transferencia de Riesgo

> ⚠️ **REGLA CRÍTICA**: Los seguros se modelan **EXCLUSIVAMENTE** como `factores_ajuste` con `tipo_severidad: "seguro"` dentro de los eventos que cubren. **NUNCA crear un evento de riesgo independiente para representar un seguro** — un evento con severidad 0 o `sev_params_direct: {"mean": 0, "std": 0}` es matemáticamente inválido y causa crash.

Risk Lab permite modelar pólizas de seguro como un tipo especial de control que afecta la severidad de las pérdidas. A diferencia de los controles estáticos/estocásticos que reducen porcentualmente, los seguros modelan la mecánica real de una póliza: deducible, cobertura porcentual y límites.

### Cuándo usar Seguro vs Control Estático:

| Situación | Tipo de Control |
|-----------|-----------------|
| "Tenemos un seguro con deducible y límite" | **Seguro** |
| "La póliza cubre el 80% sobre el deducible" | **Seguro** |
| "Un control reduce la pérdida en X%" | **Estático** |
| "Transferimos el riesgo a un tercero con términos específicos" | **Seguro** |

### Tipos de Deducible:

| Tipo | Descripción | Uso típico |
|------|-------------|------------|
| **Agregado Anual** | El deducible se aplica a la suma de todas las pérdidas del año | Pólizas anuales tradicionales |
| **Por Ocurrencia** | El deducible se aplica a cada siniestro individual | Pólizas por evento, cyber |

### Orden de Aplicación en la Simulación:

```
1. Generar pérdidas individuales (severidad bruta)
2. Aplicar escalamiento de severidad por frecuencia (si sev_freq_activado = true)
3. Aplicar factor de severidad de vínculos (si factor_severidad ≠ 1.0)
4. Aplicar factor de severidad de controles (mitigación)
5. Aplicar seguros POR OCURRENCIA a cada pérdida mitigada
6. Agregar pérdidas por simulación (suma anual)
7. Aplicar seguros AGREGADOS al total anual
```

**Importante:**
- El escalamiento de severidad por frecuencia se aplica PRIMERO, antes de vínculos, controles y seguros
- El factor de severidad de vínculos se aplica después del escalamiento, antes de controles y seguros
- Los controles de mitigación (estáticos/estocásticos) reducen la pérdida después del factor de vínculos
- Los seguros cubren la pérdida residual después de la mitigación de controles

---

### Factor Seguro - JSON Completo:

```json
{
    "nombre": "Póliza Cyber Liability",
    "activo": true,
    "tipo_modelo": "estatico",
    "tipo_severidad": "seguro",
    
    "seguro_tipo_deducible": "por_ocurrencia",
    "seguro_deducible": 50000,
    "seguro_cobertura_pct": 80,
    "seguro_limite_ocurrencia": 500000,
    "seguro_limite": 2000000,
    
    "afecta_frecuencia": false,
    "impacto_porcentual": 0,
    "afecta_severidad": true,
    "impacto_severidad_pct": 0
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre` | string | Nombre descriptivo de la póliza |
| `activo` | boolean | Si el seguro está habilitado |
| `tipo_modelo` | string | **"estatico"** (requerido) |
| `tipo_severidad` | string | **"seguro"** (identifica como póliza) |
| `seguro_tipo_deducible` | string | **"agregado"** o **"por_ocurrencia"** |
| `seguro_deducible` | integer | Monto del deducible (≥ 0) |
| `seguro_cobertura_pct` | integer | % de cobertura sobre el exceso (1-100) |
| `seguro_limite_ocurrencia` | integer | Límite por siniestro (0 = sin límite) |
| `seguro_limite` | integer | Límite agregado anual (0 = sin límite) |
| `afecta_frecuencia` | boolean | **DEBE ser `false`** para seguros |
| `impacto_porcentual` | integer | **DEBE ser `0`** para seguros |
| `afecta_severidad` | boolean | **DEBE ser `true`** — si es `false`, el seguro se ignora completamente en simulación |
| `impacto_severidad_pct` | integer | **DEBE ser `0`** para seguros |

> ⚠️ **`afecta_severidad: true` es OBLIGATORIO** para que el seguro tenga efecto en la simulación. Si se omite o se pone `false`, el seguro se ignora silenciosamente y no reduce ninguna pérdida.

---

### Fórmula de Cálculo del Seguro:

**Para cada pérdida individual (seguro por ocurrencia):**
```
exceso = max(pérdida_mitigada - deducible, 0)
pago_seguro = exceso × cobertura_pct
pago_seguro = min(pago_seguro, limite_ocurrencia)  // si limite_ocurrencia > 0
pérdida_neta = pérdida_mitigada - pago_seguro
```

**Para pérdida anual agregada (seguro agregado):**
```
exceso_anual = max(pérdida_total_año - deducible, 0)
pago_seguro = exceso_anual × cobertura_pct
pago_seguro = min(pago_seguro, limite_anual)  // si limite > 0
pérdida_neta = pérdida_total_año - pago_seguro
```

**Límite agregado anual para seguros por ocurrencia:**
```
pago_total_año = suma(pagos_individuales)
pago_efectivo = min(pago_total_año, limite_anual)  // si limite > 0
```

---

### Ejemplos de Configuración de Seguros:

#### Seguro Por Ocurrencia (Cyber típico):

```json
{
    "nombre": "Cyber Insurance",
    "activo": true,
    "tipo_modelo": "estatico",
    "tipo_severidad": "seguro",
    "seguro_tipo_deducible": "por_ocurrencia",
    "seguro_deducible": 25000,
    "seguro_cobertura_pct": 80,
    "seguro_limite_ocurrencia": 500000,
    "seguro_limite": 2000000,
    "afecta_frecuencia": false,
    "impacto_porcentual": 0,
    "afecta_severidad": true,
    "impacto_severidad_pct": 0
}
```

**Interpretación:**
- Cada siniestro: deducible $25K, cubre 80% del exceso, máximo $500K por evento
- Límite anual: $2M (si hay múltiples eventos, el seguro paga máximo $2M en total)

**Ejemplo numérico:**
- Siniestro de $600K:
  - Exceso: $600K - $25K = $575K
  - Pago seguro: $575K × 80% = $460K (< límite $500K)
  - Pérdida neta empresa: $600K - $460K = $140K

---

#### Seguro Agregado Anual (Property típico):

```json
{
    "nombre": "Property Insurance",
    "activo": true,
    "tipo_modelo": "estatico",
    "tipo_severidad": "seguro",
    "seguro_tipo_deducible": "agregado",
    "seguro_deducible": 100000,
    "seguro_cobertura_pct": 90,
    "seguro_limite_ocurrencia": 0,
    "seguro_limite": 5000000,
    "afecta_frecuencia": false,
    "impacto_porcentual": 0,
    "afecta_severidad": true,
    "impacto_severidad_pct": 0
}
```

**Interpretación:**
- Deducible anual de $100K (se paga una sola vez al año)
- Cubre 90% del exceso sobre el deducible
- Sin límite por evento individual
- Límite anual: $5M

**Ejemplo numérico:**
- 3 eventos en el año: $50K + $200K + $300K = $550K total
- Exceso: $550K - $100K = $450K
- Pago seguro: $450K × 90% = $405K
- Pérdida neta empresa: $550K - $405K = $145K

---

#### Seguro Sin Límites (Cobertura amplia):

```json
{
    "nombre": "Umbrella Policy",
    "activo": true,
    "tipo_modelo": "estatico",
    "tipo_severidad": "seguro",
    "seguro_tipo_deducible": "agregado",
    "seguro_deducible": 1000000,
    "seguro_cobertura_pct": 100,
    "seguro_limite_ocurrencia": 0,
    "seguro_limite": 0,
    "afecta_frecuencia": false,
    "impacto_porcentual": 0,
    "afecta_severidad": true,
    "impacto_severidad_pct": 0
}
```

**Interpretación:**
- Deducible alto de $1M (póliza excess/umbrella)
- Cobertura del 100% sobre el exceso
- Sin límites (0 = ilimitado)

---

### Preguntas Guía para Configurar Seguros:

```
1. "¿Cómo funciona el deducible de su póliza?"
   
   - "Pago un deducible por cada evento" → por_ocurrencia
   - "Pago un deducible anual y luego todo está cubierto" → agregado
   - "El deducible se acumula durante el año" → agregado

2. "¿Cuánto es el deducible?"
   
   → seguro_deducible (monto en moneda)

3. "¿Qué porcentaje cubre el seguro sobre el exceso del deducible?"
   
   → seguro_cobertura_pct (típico: 80-100%)

4. "¿Hay un límite máximo por evento?"
   
   - Si hay límite → seguro_limite_ocurrencia
   - Sin límite por evento → 0

5. "¿Hay un límite máximo anual?"
   
   - Si hay límite → seguro_limite
   - Sin límite anual → 0
```

---

### Múltiples Factores por Evento

Un evento puede tener varios factores (estáticos, estocásticos y seguros combinados). Los factores de frecuencia y severidad se combinan **multiplicativamente**:

- **2 controles de -30% cada uno** → factor total = 0.70 × 0.70 = 0.49 (reduce 51%, no 60%)
- **Estocásticos**: cada uno tiene un sorteo **independiente** (pueden funcionar o fallar de forma separada)
- **Recomendación**: usar 2-5 factores por evento. Con muchos factores (5+), el efecto combinado puede tender a 0 rápidamente
- **Evitar reducción 100%** salvo barreras absolutas (preferir 90-95%), ya que un factor con 100% que "funciona" anula todos los demás

### Combinando Seguros con Otros Controles:

Es común tener controles de mitigación Y seguro para el mismo evento:

```json
{
    "factores_ajuste": [
        {
            "nombre": "Firewall + IDS",
            "activo": true,
            "tipo_modelo": "estatico",
            "afecta_frecuencia": true,
            "impacto_porcentual": -40,
            "afecta_severidad": true,
            "impacto_severidad_pct": -30
        },
        {
            "nombre": "Cyber Insurance",
            "activo": true,
            "tipo_modelo": "estatico",
            "tipo_severidad": "seguro",
            "seguro_tipo_deducible": "por_ocurrencia",
            "seguro_deducible": 50000,
            "seguro_cobertura_pct": 80,
            "seguro_limite_ocurrencia": 500000,
            "seguro_limite": 2000000,
            "afecta_frecuencia": false,
            "impacto_porcentual": 0,
            "afecta_severidad": true,
            "impacto_severidad_pct": 0
        }
    ]
}
```

**Orden de aplicación:**
1. Firewall reduce frecuencia en 40%
2. Firewall reduce severidad en 30%: pérdida $100K → $70K
3. Seguro aplica a pérdida mitigada: ($70K - $50K) × 80% = $16K pago
4. Pérdida neta: $70K - $16K = $54K

---

### Rangos y Límites para Seguros:

| Parámetro | Rango válido | Notas |
|-----------|--------------|-------|
| `seguro_deducible` | 0 - 999,999,999 | 0 = sin deducible |
| `seguro_cobertura_pct` | 1 - 100 | Típico: 80% |
| `seguro_limite_ocurrencia` | 0 - 999,999,999 | 0 = sin límite por evento |
| `seguro_limite` | 0 - 999,999,999 | 0 = sin límite anual |

---

### Nota sobre campos estáticos en factores estocásticos

> Si `tipo_modelo` es `"estocastico"`, los campos estáticos (`afecta_frecuencia`, `impacto_porcentual`, `afecta_severidad`, `impacto_severidad_pct`) son **ignorados en simulación**. Risk Lab los agrega automáticamente con valores neutros si no están presentes. **No es necesario incluirlos** al generar un factor estocástico.

---

## Escalamiento de Severidad por Frecuencia

Risk Lab permite modelar la relación entre la frecuencia de ocurrencia de un evento y la severidad de sus pérdidas. Esta funcionalidad es útil cuando eventos repetidos tienden a ser progresivamente más costosos, o cuando años con frecuencia anormalmente alta correlacionan con pérdidas más severas.

### Cuándo usar Escalamiento de Severidad por Frecuencia:

| Situación | Modelo | Configuración sugerida |
|-----------|--------|------------------------|
| "Cada incidente adicional es más costoso que el anterior" | **Reincidencia Lineal** | paso=0.3-0.5, factor_max=3.0-5.0 |
| "Los incidentes se agravan exponencialmente" | **Reincidencia Exponencial** | base=1.3-2.0, factor_max=5.0 |
| "Los primeros 2 son normales, después se triplican" | **Reincidencia Tabla** | tabla con rangos personalizados |
| "Años con muchos incidentes tienen incidentes más graves" | **Sistémico** | alpha=0.3-0.8, solo_aumento=true |
| "La severidad no depende de cuántas veces ocurra" | **No usar** | sev_freq_activado=false |

### Cuándo usar cada modelo:

**Reincidencia** — Impacto progresivo por ocurrencia individual
- El tercer ataque de ransomware en el año es peor que el primero (agotamiento de backups, fatiga del equipo)
- Cada falla de un proveedor acumula más impacto operativo
- Cada reclamo regulatorio adicional genera sanciones crecientes

**Sistémico** — Correlación frecuencia-severidad a nivel anual
- Años con muchos ciberataques tienden a tener ataques más sofisticados (indicador de campaña coordinada)
- Alta frecuencia de fraude indica debilidad sistémica → pérdidas individuales más altas
- Condiciones macroeconómicas que aumentan tanto frecuencia como severidad

### Preguntas Guía para el Agente:

```
1. "¿Cada incidente adicional tiende a ser más costoso que el anterior?"
   
   - Sí, progresivamente → Reincidencia Lineal
   - Sí, se agrava rápido → Reincidencia Exponencial
   - Sí, pero con escalones definidos → Reincidencia Tabla
   - No, son independientes → No usar escalamiento

2. "¿Existe una correlación entre años con muchos incidentes y la gravedad de cada uno?"
   
   - Sí, más frecuencia = peores incidentes → Sistémico (solo_aumento=true)
   - Sí, bidireccional → Sistémico (solo_aumento=false)
   - No → No usar modelo sistémico

3. "¿Hay un tope máximo de amplificación razonable?"
   
   - "Máximo el doble" → factor_max=2.0
   - "Hasta 3-5 veces peor" → factor_max=3.0-5.0
   - "Sin límite práctico" → factor_max=10.0
```

### Configuración JSON:

**Reincidencia Lineal** (caso más común):
```json
{
    "sev_freq_activado": true,
    "sev_freq_modelo": "reincidencia",
    "sev_freq_tipo_escalamiento": "lineal",
    "sev_freq_paso": 0.5,
    "sev_freq_factor_max": 5.0
}
```

**Sistémico** (correlación frecuencia-severidad):
```json
{
    "sev_freq_activado": true,
    "sev_freq_modelo": "sistemico",
    "sev_freq_alpha": 0.5,
    "sev_freq_solo_aumento": true,
    "sev_freq_sistemico_factor_max": 3.0
}
```

**Reincidencia Tabla** (escalones definidos):
```json
{
    "sev_freq_activado": true,
    "sev_freq_modelo": "reincidencia",
    "sev_freq_tipo_escalamiento": "tabla",
    "sev_freq_tabla": [
        {"desde": 1, "hasta": 2, "multiplicador": 1.0},
        {"desde": 3, "hasta": 5, "multiplicador": 1.5},
        {"desde": 6, "hasta": null, "multiplicador": 3.0}
    ]
}
```

### Notas importantes:

- **Distribución Bernoulli** (`freq_opcion=3`): el modelo reincidencia no produce efecto (frecuencia máxima = 1, la primera ocurrencia siempre tiene multiplicador 1.0). Usar modelo sistémico si se necesita correlación frecuencia-severidad
- **Desactivado por defecto**: si no se incluyen campos `sev_freq_*` en el JSON, la funcionalidad queda inactiva (backward compatible)
- Para detalles técnicos completos (fórmulas, validaciones, estructura de tabla), ver sección "Escalamiento de Severidad por Frecuencia" en `ESPECIFICACION_JSON_RISK_LAB.md`

---

## Límites Superiores (Caps de Frecuencia y Severidad)

Risk Lab permite definir un **límite superior** para la frecuencia y/o la severidad de cada evento, truncando la distribución mediante **rejection sampling** (re-muestrea valores que exceden el límite en lugar de recortarlos, preservando la forma natural de la distribución).

### Cuándo usar:

| Situación | Campo | Ejemplo |
|-----------|-------|---------|
| "La multa máxima es $500K por infracción" | `sev_limite_superior` | `500000` |
| "Máximo 12 incidentes al año" | `freq_limite_superior` | `12` |
| "La pérdida no puede superar el valor del activo" | `sev_limite_superior` | valor del activo |
| Sin restricción | ambos | `null` |

### Preguntas Guía:

```
1. "¿Existe un tope físico, contractual o regulatorio para el impacto de este evento?"
   
   - Sí → sev_limite_superior = ese monto
   - No → null

2. "¿Hay un máximo de veces que podría ocurrir por año?"
   
   - Sí (tope físico) → freq_limite_superior = ese número
   - No → null
```

### Reglas:
- `freq_limite_superior` solo tiene efecto con Poisson, Binomial y Poisson-Gamma (Bernoulli/Beta ya generan 0 o 1)
- `sev_limite_superior` aplica a todas las distribuciones de severidad
- **No usar como parche** para distribuciones mal parametrizadas — ajustar parámetros primero
- Ambos campos son opcionales; `null` = sin límite (backward compatible)

### Configuración JSON:

```json
{
    "sev_limite_superior": 500000,
    "freq_limite_superior": 10
}
```

Para detalles técnicos completos (rejection sampling, validaciones), ver sección "Límites Superiores" en `ESPECIFICACION_JSON_RISK_LAB.md`.

---

## Rangos y Límites de Parámetros

### Severidad (valores monetarios):

| Parámetro | Mínimo | Máximo | Notas |
|-----------|--------|--------|-------|
| `sev_minimo` | > 0 | < sev_mas_probable | **Nunca 0 ni null** (causa crash) |
| `sev_mas_probable` | > sev_minimo | < sev_maximo | Valor central |
| `sev_maximo` | > sev_mas_probable | Sin límite | Valor extremo |

### Frecuencia:

| Distribución | Parámetro | Rango válido |
|--------------|-----------|--------------|
| Poisson | `tasa` | > 0 (típico: 0.1 - 50) |
| Binomial | `num_eventos` | ≥ 1 (entero) |
| Binomial | `prob_exito` | 0 - 1 |
| Bernoulli | `prob_exito` | 0 - 1 |
| Poisson-Gamma | `pg_alpha` | **> 1** (SIEMPRE obligatorio, nunca null) |
| Poisson-Gamma | `pg_beta` | **> 0** (SIEMPRE obligatorio, nunca null) |
| Poisson-Gamma | `pg_minimo` | > 0 (opcional, para documentación) |
| Poisson-Gamma | `pg_mas_probable` | > pg_minimo (opcional) |
| Poisson-Gamma | `pg_maximo` | > pg_mas_probable (opcional) |
| Poisson-Gamma | `pg_confianza` | 1 - 99, típico: 90 (opcional) |
| Beta | `beta_minimo` | 0 - 100 (%) |
| Beta | `beta_mas_probable` | > beta_minimo, < beta_maximo |
| Beta | `beta_maximo` | > beta_mas_probable, ≤ 100 |
| Beta | `beta_confianza` | 1 - 99 (típico: 90) |

### Factores/Controles:

| Modelo | Parámetro | Rango válido |
|--------|-----------|--------------|
| Estático | `impacto_porcentual` | -99 a +∞ (sin límite superior) |
| Estático | `impacto_severidad_pct` | -99 a +∞ (sin límite superior) |
| Estocástico | `confiabilidad` | 0 - 100 |
| Estocástico | `reduccion_efectiva` | -100 a +99 |
| Estocástico | `reduccion_fallo` | -100 a +99 |
| Estocástico | `reduccion_severidad_efectiva` | -100 a +99 |
| Estocástico | `reduccion_severidad_fallo` | -100 a +99 |
| Seguro | `seguro_deducible` | 0 - 999,999,999 |
| Seguro | `seguro_cobertura_pct` | 1 - 100 |
| Seguro | `seguro_limite_ocurrencia` | 0 - 999,999,999 |
| Seguro | `seguro_limite` | 0 - 999,999,999 |

### Límites Superiores:

| Parámetro | Rango válido | Notas |
|-----------|--------------|-------|
| `sev_limite_superior` | `null` o > 0 | Monto en moneda. `null` = sin límite |
| `freq_limite_superior` | `null` o entero > 0 | Número máximo de ocurrencias. `null` = sin límite |

### Simulación:

| Parámetro | Rango válido | Recomendado |
|-----------|--------------|-------------|
| `num_simulaciones` | 100 - 1,000,000 | 10,000 |

---

## Validaciones que el Agente DEBE Verificar

### Antes de generar el JSON:

1. **Cada evento tiene un nombre único y descriptivo**
2. **Todos los UUIDs son únicos** (generar con uuid4)
3. **Parámetros de severidad coherentes**: minimo < mas_probable < maximo
4. **Parámetros de frecuencia válidos**:
   - Poisson: tasa > 0 (nunca null ni 0)
   - Binomial: num_eventos > 0, 0 ≤ prob_exito ≤ 1
   - Bernoulli: 0 ≤ prob_exito ≤ 1
   - Poisson-Gamma: `pg_alpha` > 1 y `pg_beta` > 0 **SIEMPRE** (nunca null). Si se incluyen min/mode/max: pg_minimo < pg_mas_probable < pg_maximo
   - Beta: `beta_alpha` > 0 y `beta_beta` > 0 **SIEMPRE** (nunca null). Además: 0 ≤ beta_minimo < beta_mas_probable < beta_maximo ≤ 100 (porcentajes, nunca null)
5. **Sin ciclos en dependencias**
6. **IDs de padres existen**
7. **Al menos un evento definido**
8. **Factores tienen tipo_modelo válido** ("estatico" o "estocastico")
9. **Seguros tienen tipo_severidad = "seguro" y parámetros válidos**
10. **Seguros tienen seguro_tipo_deducible válido** ("agregado" o "por_ocurrencia")
11. **Si usa escalamiento sev_freq: `sev_freq_activado` = `true` y modelo/parámetros válidos**
12. **Si usa reincidencia tabla: `sev_freq_tabla` es array con `{desde, hasta, multiplicador}`**
13. **Si usa límites superiores: `sev_limite_superior` es `null` o > 0; `freq_limite_superior` es `null` o entero > 0**

---

## Conversión de Lenguaje Natural a Parámetros

### Frecuencia:

| Usuario dice | Traducción |
|--------------|------------|
| "Raro, quizás una vez cada 2 años" | Poisson tasa=0.5 o Bernoulli prob=0.5 |
| "Una vez al año" | Poisson tasa=1.0 o Bernoulli prob=0.5-0.7 |
| "Varias veces al año" | Poisson tasa=3-5 |
| "Frecuente, mensualmente" | Poisson tasa=12 |
| "Muy raro, 1 en 10 años" | Bernoulli prob=0.1 |
| "Entre 2 y 5 veces" | Poisson-Gamma (2, 3, 5) |
| "Probabilidad del 20-30%" | Beta (20, 25, 30) |

### Severidad:

| Usuario dice | Traducción sugerida |
|--------------|---------------------|
| "Menor, unos pocos miles" | PERT min/mode/max (1K, 5K, 15K) |
| "Moderado, decenas de miles" | LogNormal **direct** — convertir (20K, 50K, 150K) a mu/sigma con guía PERT→LogNormal |
| "Significativo, cientos de miles" | LogNormal **direct** — convertir (100K, 300K, 1M) a mu/sigma con guía PERT→LogNormal |
| "Catastrófico, millones" | Pareto/GPD **direct** — usar guía de estimación c/scale/loc |
| "No tengo idea, entre X e Y" | Uniforme min/max (X, Y) |

> **Recordatorio**: LogNormal y Pareto/GPD **requieren** `sev_input_method: "direct"`. Ver la sección "Modo Avanzado: Parámetros Directos de Distribuciones" para guías de conversión.

---

## Escenarios Alternativos

Los escenarios permiten comparar diferentes configuraciones (ej: con/sin controles, optimista/pesimista).

### Cuándo crear escenarios:

1. **Análisis de controles**: Comparar situación actual vs. con nuevo control
2. **Análisis de sensibilidad**: Variar parámetros clave
3. **Escenarios optimista/pesimista**: Diferentes supuestos

### Estructura:

```json
{
    "scenarios": [
        {
            "nombre": "Sin Controles",
            "descripcion": "Escenario baseline sin controles implementados",
            "eventos_riesgo": [
                { "id": "...", "nombre": "...", "activo": true, "sev_opcion": 3, "..." : "evento COMPLETO sin factores_ajuste" }
            ]
        },
        {
            "nombre": "Pesimista",
            "descripcion": "Frecuencias y severidades aumentadas 30%",
            "eventos_riesgo": [
                { "id": "...", "nombre": "...", "activo": true, "sev_opcion": 3, "..." : "evento COMPLETO con parametros ajustados" }
            ]
        }
    ]
}
```

> ⚠️ **Cada evento dentro de un escenario debe ser COMPLETO** — con todos los campos obligatorios (id, nombre, activo, sev_*, freq_*, vinculos, factores_ajuste, etc.). No existen "overrides parciales". Ver la estructura completa en `ESPECIFICACION_JSON_RISK_LAB.md`.

---

## Errores Comunes a Evitar

### 1. Parámetros inválidos
❌ `"sev_minimo": 100000, "sev_mas_probable": 50000` (min > mode)
✅ `"sev_minimo": 50000, "sev_mas_probable": 100000`

### 2. Probabilidades fuera de rango
❌ `"prob_exito": 1.5` (mayor que 1)
✅ `"prob_exito": 0.15`

### 3. Ciclos en dependencias
❌ Evento A depende de B, B depende de A
✅ Solo dependencias acíclicas (DAG)

### 4. IDs inexistentes en vínculos
❌ `"id_padre": "evento-que-no-existe"`
✅ Verificar que todos los id_padre existan

### 5. Campos faltantes
❌ Omitir campos requeridos
✅ Incluir todos los campos aunque sean null

### 6. Tipos incorrectos
❌ `"tasa": "2.5"` (string en lugar de número)
✅ `"tasa": 2.5`

---

## Checklist Final para el Agente

Antes de entregar el JSON al usuario, verificar:

**Integridad sintáctica:**
- [ ] El JSON es un documento completo (no truncado) que pasa `json.loads()` sin error
- [ ] Todos los valores numéricos son números válidos (un solo punto decimal máximo, no strings)
- [ ] No hay caracteres de control sin escapar, comentarios ni trailing commas

**Estructura y claves:**
- [ ] Todos los UUIDs son únicos (formato UUID v4)
- [ ] Todos los nombres de eventos son descriptivos y no vacíos
- [ ] `eventos_riesgo`, `scenarios`, `vinculos`, `factores_ajuste` son listas `[]` (nunca `null`)
- [ ] Cada escenario usa `eventos_riesgo` como clave (no `events` ni otra variante)
- [ ] num_simulaciones es al menos 1000 (recomendado 10000)

**Severidad:**
- [ ] Si `sev_input_method: "min_mode_max"` → `sev_minimo < sev_mas_probable < sev_maximo`, todos > 0 (nunca 0, nunca null)
- [ ] Si `sev_input_method: "direct"` → `sev_minimo/mas_probable/maximo` son `null` (claves presentes) y `sev_params_direct` tiene parámetros válidos (nunca `{}` vacío)
- [ ] `std`/`sigma`/`s`/`scale` siempre > 0 en `sev_params_direct`
- [ ] PERT/Uniforme solo con `"min_mode_max"`; LogNormal/Pareto solo con `"direct"`

**Frecuencia:**
- [ ] `freq_opcion=1` → `tasa` > 0 (nunca null ni 0)
- [ ] `freq_opcion=2` → `num_eventos` > 0 (entero) y `0 ≤ prob_exito ≤ 1`
- [ ] `freq_opcion=3` → `0 ≤ prob_exito ≤ 1`
- [ ] `freq_opcion=4` → `pg_alpha` > 1 y `pg_beta` > 0, ambos numéricos (**nunca null**)
- [ ] `freq_opcion=5` → `beta_alpha` > 0 y `beta_beta` > 0 (**nunca null**); `beta_minimo/mas_probable/maximo/confianza` numéricos (**nunca null**)

**Factores y seguros:**
- [ ] Todo factor tiene campo `nombre` (no vacío)
- [ ] Factores tienen `tipo_modelo` definido (`"estatico"` o `"estocastico"`)
- [ ] Todo factor estático que afecte severidad tiene `afecta_severidad: true` explícito
- [ ] **Seguros son `factores_ajuste` (NUNCA eventos independientes)** con `tipo_severidad: "seguro"`
- [ ] Seguros: `afecta_severidad: true` (OBLIGATORIO), `afecta_frecuencia: false`, `impacto_porcentual: 0`, `impacto_severidad_pct: 0`
- [ ] Seguros: `seguro_tipo_deducible` es `"agregado"` o `"por_ocurrencia"`, `seguro_cobertura_pct` entre 1-100

**Vínculos:**
- [ ] Todo `id_padre` referencia un `id` existente dentro del mismo archivo/escenario
- [ ] `tipo` en mayúsculas exactas: `"AND"`, `"OR"`, `"EXCLUYE"`
- [ ] `probabilidad` entre 1-100, `factor_severidad` entre 0.10-5.00, `umbral_severidad` ≥ 0
- [ ] `factor_severidad` = 1.0 para tipo EXCLUYE
- [ ] Sin ciclos en el grafo de dependencias (DAG)

**Límites superiores (si se usan):**
- [ ] `sev_limite_superior` es `null` o número > 0
- [ ] `freq_limite_superior` es `null` o entero > 0

---

## Notas Técnicas para el Agente

### Generación de UUIDs en Python:
```python
import uuid
nuevo_id = str(uuid.uuid4())
```

### Formato de números:
- Todos los valores monetarios son números enteros o decimales (sin formato de moneda)
- Los porcentajes se expresan como enteros (30 = 30%, no 0.30)
- Las probabilidades se expresan como decimales entre 0 y 1

### Valores por defecto recomendados:
- `num_simulaciones`: 10000
- `activo`: true
- `sev_input_method`: "min_mode_max"
- `pg_confianza`: 90
- `beta_confianza`: 90

