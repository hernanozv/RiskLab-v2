# Manual para Agentes de IA - Risk Lab

## Propósito de este Manual

Este manual está diseñado para que un agente de IA pueda asistir a usuarios en la preparación de análisis de riesgo cuantitativo utilizando simulación Monte Carlo. El objetivo es generar un archivo JSON válido que pueda importarse directamente en Risk Lab.

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
- **Parámetros**: `pg_minimo`, `pg_mas_probable`, `pg_maximo`, `pg_confianza`

**Beta (freq_opcion: 5)**
- Usuario dice: "Probabilidad entre 10% y 40%, probablemente 20%"
- Para eventos tipo Bernoulli con incertidumbre en la probabilidad
- **Parámetros**: `beta_minimo`, `beta_mas_probable`, `beta_maximo` (en %)

---

### Distribuciones de SEVERIDAD

| Situación | Distribución | sev_opcion |
|-----------|--------------|------------|
| Pérdidas simétricas alrededor de un valor central | **Normal** | 1 |
| Pérdidas con cola derecha (más extremos altos) | **LogNormal** | 2 |
| Estimación por expertos (min/probable/max) | **PERT** | 3 |
| Eventos catastróficos con cola muy pesada | **Pareto/GPD** | 4 |
| Cualquier valor igualmente probable en un rango | **Uniforme** | 5 |

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

## Modo Avanzado: Parámetros Directos de Distribuciones

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

---

### FRECUENCIA - Parámetros Directos

#### Poisson-Gamma (freq_opcion: 4)

En lugar de usar min/mode/max, se pueden especificar α y β directamente:

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

```json
{
    "freq_opcion": 5,
    "beta_minimo": null,
    "beta_mas_probable": null,
    "beta_maximo": null,
    "beta_confianza": null,
    "beta_alpha": 2.0,
    "beta_beta": 8.0
}
```

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
    
    "freq_opcion": 4,
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
|-----------|-----------------|
| "B solo puede ocurrir si A ocurrió" | B depende de A (AND) |
| "B puede ocurrir si A o C ocurrieron" | B depende de A y C (OR) |
| "Son eventos en cadena" | Crear cadena de dependencias |

### Ejemplos de cadenas de riesgo:

**Ciberataque en cadena:**
1. Phishing exitoso (evento raíz)
2. Compromiso de credenciales (depende AND de 1)
3. Movimiento lateral (depende AND de 2)
4. Exfiltración de datos (depende AND de 3)
5. Ransomware (depende AND de 2 o 3)

**Desastre natural:**
1. Terremoto (evento raíz)
2. Daño a infraestructura (depende AND de 1)
3. Interrupción de operaciones (depende AND de 2)
4. Pérdida de datos (depende OR de 1 y otro evento)

### Reglas importantes:
- **NO crear ciclos** (A→B→C→A es inválido)
- Los eventos raíz no tienen vínculos
- Un hijo puede tener múltiples padres

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
| `impacto_porcentual` | integer | % impacto en frecuencia (-99 a +200) |
| `afecta_severidad` | boolean | Si modifica la severidad |
| `impacto_severidad_pct` | integer | % impacto en severidad (-99 a +200) |

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

---

## Controles de Tipo Seguro/Transferencia de Riesgo

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
2. Aplicar factor de severidad de controles (mitigación)
3. Aplicar seguros POR OCURRENCIA a cada pérdida mitigada
4. Agregar pérdidas por simulación (suma anual)
5. Aplicar seguros AGREGADOS al total anual
```

**Importante:** Los controles de mitigación (estáticos/estocásticos) reducen la pérdida ANTES de que se aplique el seguro. Esto significa que el seguro cubre la pérdida residual después de la mitigación.

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
    "afecta_severidad": false,
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
    "seguro_limite": 2000000
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
    "seguro_limite": 5000000
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
    "seguro_limite": 0
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
            "seguro_limite": 2000000
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

### Campos Opcionales de Compatibilidad

Los factores estocásticos también pueden incluir campos del modelo estático para compatibilidad:

```json
{
    "nombre": "Control Híbrido",
    "activo": true,
    "tipo_modelo": "estocastico",
    "confiabilidad": 80,
    "reduccion_efectiva": 60,
    "reduccion_fallo": 10,
    "reduccion_severidad_efectiva": 40,
    "reduccion_severidad_fallo": 0,
    
    "afecta_frecuencia": true,
    "impacto_porcentual": 0,
    "afecta_severidad": true,
    "impacto_severidad_pct": 0
}
```

> **Nota:** Si `tipo_modelo` es "estocastico", los campos estocásticos tienen prioridad. Los campos estáticos se ignoran pero pueden incluirse para compatibilidad.

---

## Rangos y Límites de Parámetros

### Severidad (valores monetarios):

| Parámetro | Mínimo | Máximo | Notas |
|-----------|--------|--------|-------|
| `sev_minimo` | 0 | < sev_mas_probable | Puede ser 0 |
| `sev_mas_probable` | > sev_minimo | < sev_maximo | Valor central |
| `sev_maximo` | > sev_mas_probable | Sin límite | Valor extremo |

### Frecuencia:

| Distribución | Parámetro | Rango válido |
|--------------|-----------|--------------|
| Poisson | `tasa` | > 0 (típico: 0.1 - 50) |
| Binomial | `num_eventos` | ≥ 1 (entero) |
| Binomial | `prob_exito` | 0 - 1 |
| Bernoulli | `prob_exito` | 0 - 1 |
| Poisson-Gamma | `pg_minimo` | > 0 |
| Poisson-Gamma | `pg_mas_probable` | > pg_minimo |
| Poisson-Gamma | `pg_maximo` | > pg_mas_probable |
| Poisson-Gamma | `pg_confianza` | 1 - 99 (típico: 90) |
| Beta | `beta_minimo` | 0 - 100 (%) |
| Beta | `beta_mas_probable` | > beta_minimo, < beta_maximo |
| Beta | `beta_maximo` | > beta_mas_probable, ≤ 100 |
| Beta | `beta_confianza` | 1 - 99 (típico: 90) |

### Factores/Controles:

| Modelo | Parámetro | Rango válido |
|--------|-----------|--------------|
| Estático | `impacto_porcentual` | -99 a +200 |
| Estático | `impacto_severidad_pct` | -99 a +200 |
| Estocástico | `confiabilidad` | 0 - 100 |
| Estocástico | `reduccion_efectiva` | -100 a +99 |
| Estocástico | `reduccion_fallo` | -100 a +99 |
| Estocástico | `reduccion_severidad_efectiva` | -100 a +99 |
| Estocástico | `reduccion_severidad_fallo` | -100 a +99 |
| Seguro | `seguro_deducible` | 0 - 999,999,999 |
| Seguro | `seguro_cobertura_pct` | 1 - 100 |
| Seguro | `seguro_limite_ocurrencia` | 0 - 999,999,999 |
| Seguro | `seguro_limite` | 0 - 999,999,999 |

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
   - Poisson: tasa > 0
   - Binomial: num_eventos > 0, 0 ≤ prob_exito ≤ 1
   - Bernoulli: 0 ≤ prob_exito ≤ 1
   - Poisson-Gamma: pg_minimo < pg_mas_probable < pg_maximo
   - Beta: 0 ≤ beta_minimo < beta_mas_probable < beta_maximo ≤ 100
5. **Sin ciclos en dependencias**
6. **IDs de padres existen**
7. **Al menos un evento definido**
8. **Factores tienen tipo_modelo válido** ("estatico" o "estocastico")
9. **Seguros tienen tipo_severidad = "seguro"** y parámetros válidos
10. **Seguros tienen seguro_tipo_deducible válido** ("agregado" o "por_ocurrencia")

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
| "Menor, unos pocos miles" | PERT (1K, 5K, 15K) |
| "Moderado, decenas de miles" | LogNormal (20K, 50K, 150K) |
| "Significativo, cientos de miles" | LogNormal (100K, 300K, 1M) |
| "Catastrófico, millones" | Pareto (500K, 2M, 10M) |
| "No tengo idea, entre X e Y" | Uniforme (X, Y) |

---

## Plantilla JSON Completa

```json
{
    "num_simulaciones": 10000,
    "eventos_riesgo": [
        {
            "id": "GENERAR-UUID-UNICO",
            "nombre": "Nombre descriptivo del evento",
            "activo": true,
            
            "sev_opcion": 2,
            "sev_input_method": "min_mode_max",
            "sev_minimo": 10000,
            "sev_mas_probable": 50000,
            "sev_maximo": 200000,
            "sev_params_direct": {},
            
            "freq_opcion": 1,
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
            
            "vinculos": [],
            "factores_ajuste": []
        }
    ],
    "scenarios": [],
    "current_scenario_name": null
}
```

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
                // Mismos eventos pero sin factores_ajuste o con factores inactivos
            ]
        },
        {
            "nombre": "Pesimista",
            "descripcion": "Frecuencias y severidades aumentadas 30%",
            "eventos_riesgo": [
                // Eventos con parámetros ajustados
            ]
        }
    ]
}
```

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

- [ ] Todos los UUIDs son únicos
- [ ] Todos los nombres de eventos son descriptivos y únicos
- [ ] sev_minimo < sev_mas_probable < sev_maximo (cuando aplica)
- [ ] Parámetros de frecuencia válidos según distribución elegida
- [ ] No hay ciclos en los vínculos
- [ ] Todos los id_padre referencian eventos existentes
- [ ] Factores tienen tipo_modelo definido ("estatico" o "estocastico")
- [ ] Seguros tienen tipo_severidad = "seguro" y seguro_tipo_deducible válido
- [ ] Seguros tienen seguro_cobertura_pct entre 1-100
- [ ] JSON es válido sintácticamente
- [ ] num_simulaciones es al menos 1000 (recomendado 10000)

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

