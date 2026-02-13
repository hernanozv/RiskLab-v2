# Especificación del Formato JSON para Risk Lab

Este documento describe en detalle la estructura del archivo JSON que utiliza Risk Lab para guardar y cargar simulaciones de riesgo. Con esta guía, un asistente de IA puede generar archivos JSON válidos que pueden ser importados directamente en Risk Lab.

---

## Estructura Raíz del JSON

```json
{
    "num_simulaciones": 10000,
    "eventos_riesgo": [...],
    "scenarios": [...],
    "current_scenario_name": null
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `num_simulaciones` | integer | Sí | Número de iteraciones Monte Carlo (típico: 10000) |
| `eventos_riesgo` | array | Sí | Lista de eventos de riesgo de la simulación principal |
| `scenarios` | array | No | Lista de escenarios alternativos |
| `current_scenario_name` | string/null | No | Nombre del escenario actualmente seleccionado |

---

## Checklist Rápido (JSON estricto) - Para evitar errores de importación

- **Comillas dobles**: todas las claves y strings deben usar `"` (comillas dobles). JSON no acepta comillas simples.
- **Escapes en strings**: si un string necesita caracteres especiales, deben estar escapados (ej. `\n`, `\t`, `\"`). Idealmente evitar `\n`/`\t` en `nombre`.
- **Sin comentarios**: no incluir `//` ni `/* */` en el JSON final.
- **Sin comas finales**: no dejar comas finales en objetos/arrays (trailing commas).
- **Tipos numéricos reales**: los campos numéricos deben ser números, no strings.
- **Beta frecuencia (freq_opcion=5)**: siempre incluir `beta_alpha` y `beta_beta` (ambos > 0).

---

## Reglas estructurales obligatorias (Para generación por IA)

Estas reglas evitan errores comunes de importación (por `KeyError`/`TypeError`) durante `cargar_configuracion()`.

### A) Listas: siempre listas (nunca `null`)

- **`eventos_riesgo`**: siempre `[]` si está vacío (nunca `null`).
- **`scenarios`**: siempre `[]` si está vacío (nunca `null`).
- **`vinculos`** (en cada evento): siempre `[]` si no hay vínculos (nunca `null`).
- **`factores_ajuste`** (en cada evento): siempre `[]` si no hay factores (nunca `null`).

### B) Eventos: claves mínimas obligatorias (siempre presentes)

Cada objeto de evento debe incluir **todas** estas claves (aunque muchas sean `null` según la distribución):

- `id`, `nombre`, `activo`
- Severidad:
  - `sev_opcion`, `sev_input_method`, `sev_minimo`, `sev_mas_probable`, `sev_maximo`, `sev_params_direct`
- Frecuencia:
  - `freq_opcion`, `tasa`, `num_eventos`, `prob_exito`
  - `pg_minimo`, `pg_mas_probable`, `pg_maximo`, `pg_confianza`, `pg_alpha`, `pg_beta`
  - `beta_minimo`, `beta_mas_probable`, `beta_maximo`, `beta_confianza`, `beta_alpha`, `beta_beta`
- Dependencias y controles:
  - `vinculos`, `factores_ajuste`

**Nota**:
- Si una clave no aplica: usar `null` (para campos numéricos/strings opcionales) o `[]` (para listas).
- Para `sev_params_direct`: usar `{}` cuando no aplica o cuando `sev_input_method` = `"min_mode_max"`.

### C) IDs y referencias internas

- Usar `id` como string con formato UUID v4.
- **No** agregar prefijos/sufijos al `id` (ej. `"override:"`).
- En la importación, Risk Lab **remapea** los IDs a nuevos UUIDs; por lo tanto, los IDs del archivo **no necesitan coincidir** con IDs previos externos.
- Lo que sí es obligatorio: cada `vinculos[i].id_padre` debe referenciar un `id` existente **dentro del mismo archivo** (en la lista de eventos correspondiente).

### D) Escenarios: no existen “overrides parciales”

- Un escenario contiene `eventos_riesgo` como una lista de eventos **completos** (misma estructura que eventos principales).
- No generar objetos parciales tipo “override” con solo 2-3 campos: si un escenario redefine un evento, debe incluir el evento con **todas las claves mínimas** (ver sección B).

### E) Vínculos: evitar ciclos (DAG)

- El grafo de dependencias debe ser acíclico (DAG): **no crear ciclos**.
- Validar que no haya referencias a eventos inexistentes.

### F) Tipos de dato consistentes (evitar `TypeError`)

- **Montos/monetarios**: siempre números (int/float), nunca strings.
- **Porcentajes**: usar enteros (ej. `30` = 30%).
- **Probabilidades**: usar decimales entre 0 y 1 (ej. `0.1` = 10%).

### G) Rangos válidos (validar antes de exportar)

- Para `sev_input_method = "min_mode_max"`: `sev_minimo < sev_mas_probable < sev_maximo`.
- Frecuencia Poisson (`freq_opcion = 1`): `tasa > 0`.
- Frecuencia Binomial (`freq_opcion = 2`): `num_eventos > 0` y `0 ≤ prob_exito ≤ 1`.
- Frecuencia Bernoulli (`freq_opcion = 3`): `0 ≤ prob_exito ≤ 1`.
- Poisson-Gamma (`freq_opcion = 4`):
  - Si se usa directo: `pg_alpha > 1` y `pg_beta > 0`.
  - Si se usa min/mode/max: `0 < pg_minimo < pg_mas_probable < pg_maximo` y `0 < pg_confianza < 100`.
- Factores estocásticos: `confiabilidad` debe estar en `[0, 100]`.

## Estructura de un Evento de Riesgo

Cada evento de riesgo tiene la siguiente estructura:

```json
{
    "id": "uuid-único-del-evento",
    "nombre": "Nombre del evento",
    "activo": true,
    
    "sev_opcion": 1,
    "sev_input_method": "min_mode_max",
    "sev_minimo": 10000,
    "sev_mas_probable": 50000,
    "sev_maximo": 200000,
    "sev_params_direct": {},
    
    "freq_opcion": 1,
    "tasa": 2.5,
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
```

### Campos Comunes

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `id` | string | Sí | UUID único del evento (formato: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) |
| `nombre` | string | Sí | Nombre descriptivo del evento (máx. 50 caracteres) |
| `activo` | boolean | No | Si el evento está activo en la simulación (default: `true`) |

---

## Distribuciones de Severidad

El campo `sev_opcion` determina la distribución de severidad:

| sev_opcion | Distribución | Descripción |
|------------|--------------|-------------|
| 1 | Normal | Distribución normal/gaussiana |
| 2 | LogNormal | Distribución log-normal |
| 3 | PERT (Beta) | Distribución PERT basada en Beta |
| 4 | Pareto/GPD | Distribución Pareto Generalizada |
| 5 | Uniforme | Distribución uniforme |

### Método de Entrada (`sev_input_method`)

| Valor | Descripción |
|-------|-------------|
| `"min_mode_max"` | Usa mínimo, más probable y máximo (default) |
| `"direct"` | Usa parámetros directos de la distribución |

**POLÍTICA PARA GENERACIÓN POR IA (OBLIGATORIA)**:
- Para evitar errores de parametrización durante importación, cuando:
  - `sev_opcion = 2` (LogNormal)
  - `sev_opcion = 4` (Pareto/GPD)
  el agente **DEBE** usar `sev_input_method: "direct"`.
- En esos casos, `sev_minimo`, `sev_mas_probable`, `sev_maximo` deben ser `null` y `sev_params_direct` debe contener los parámetros requeridos.

---

### 1. Normal (`sev_opcion: 1`)

#### Método Min/Mode/Max:
```json
{
    "sev_opcion": 1,
    "sev_input_method": "min_mode_max",
    "sev_minimo": 10000,
    "sev_mas_probable": 50000,
    "sev_maximo": 100000,
    "sev_params_direct": {}
}
```
- `sev_minimo`: Valor mínimo esperado
- `sev_mas_probable`: Valor más probable (moda)
- `sev_maximo`: Valor máximo esperado
- Restricción: `minimo < mas_probable < maximo`

#### Método Directo:
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

**Parámetros aceptados** (elegir UNA de estas combinaciones):

| Combinación | Campos requeridos | Validación |
|--------------|-------------------|------------|
| **Opción A** | `mean`, `std` | `std` > 0, `mean` puede ser cualquier valor |
| **Opción B** | `mu`, `sigma` | `sigma` > 0, `mu` puede ser cualquier valor |

**REGLAS CRÍTICAS**:
- `sev_minimo`, `sev_mas_probable`, `sev_maximo` deben ser `null`
- `sev_params_direct` NO puede ser `{}`
- `std` o `sigma` DEBE ser estrictamente > 0 (nunca 0 o negativo)
- NO mezclar opciones (ej: no usar `mean` con `sigma`)

---

### 2. LogNormal (`sev_opcion: 2`)

#### Método Min/Mode/Max:
```json
{
    "sev_opcion": 2,
    "sev_input_method": "min_mode_max",
    "sev_minimo": 5000,
    "sev_mas_probable": 25000,
    "sev_maximo": 150000,
    "sev_params_direct": {}
}
```

**NOTA IMPORTANTE PARA EL AGENTE**:
- Para generación automática (IA), **NO usar** `min_mode_max` en LogNormal.
- Usar siempre `sev_input_method: "direct"` con una parametrización canónica (ver abajo).

#### Método Directo (3 opciones):

**PARAMETRIZACIÓN CANÓNICA (RECOMENDADA PARA IA)**: Parámetros nativos SciPy (`s`, `scale`, `loc`)
```json
{
    "sev_opcion": 2,
    "sev_input_method": "direct",
    "sev_minimo": null,
    "sev_mas_probable": null,
    "sev_maximo": null,
    "sev_params_direct": {
        "s": 0.8,
        "scale": 36315,
        "loc": 0
    }
}
```

**Validaciones ESTRICTAS (canónica)**:
- `s` > 0
- `scale` > 0
- `loc` debe ser numérico (típicamente 0)
- No incluir otras claves adicionales (ej: no mezclar con `mean/std` o `mu/sigma`)

**Opción A: Media y desviación estándar en escala original (X)**
```json
{
    "sev_opcion": 2,
    "sev_input_method": "direct",
    "sev_minimo": null,
    "sev_mas_probable": null,
    "sev_maximo": null,
    "sev_params_direct": {
        "mean": 50000,
        "std": 30000,
        "loc": 0
    }
}
```

**Validaciones ESTRICTAS**:
- `mean` > 0 (no puede ser 0 o negativo)
- `std` > 0 (no puede ser 0 o negativo)
- `loc` ≥ 0 (típicamente 0)
- `mean` debe ser significativamente mayor que `std` para evitar valores negativos
- **Recomendación**: `mean` ≥ `std` para distribución realista

**Opción B: Parámetros μ y σ de ln(X)**
```json
{
    "sev_opcion": 2,
    "sev_input_method": "direct",
    "sev_minimo": null,
    "sev_mas_probable": null,
    "sev_maximo": null,
    "sev_params_direct": {
        "mu": 10.5,
        "sigma": 0.8,
        "loc": 0
    }
}
```

**Validaciones ESTRICTAS**:
- `mu` puede ser cualquier número real (positivo, negativo o cero)
- `sigma` > 0 (ESTRICTAMENTE positivo, no puede ser 0)
- `loc` ≥ 0 (típicamente 0)
- `sigma` típicamente está entre 0.1 y 3.0 para distribuciones realistas

**Opción C: Parámetros nativos SciPy (s, scale)**
```json
{
    "sev_opcion": 2,
    "sev_input_method": "direct",
    "sev_minimo": null,
    "sev_mas_probable": null,
    "sev_maximo": null,
    "sev_params_direct": {
        "s": 0.8,
        "scale": 36315,
        "loc": 0
    }
}
```

**Validaciones ESTRICTAS**:
- `s` > 0 (shape parameter, equivale a `sigma`)
- `scale` > 0 (scale parameter, equivale a exp(`mu`))
- `loc` ≥ 0 (location parameter)
- `s` típicamente 0.1 - 3.0
- `scale` debe ser un valor positivo realista

**REGLAS CRÍTICAS para LogNormal**:
- NUNCA dejar `sev_params_direct` vacío `{}` con `sev_input_method: "direct"`
- `sev_minimo`, `sev_mas_probable`, `sev_maximo` DEBEN ser `null`
- Elegir SOLO UNA de las 3 opciones (A, B o C)
- NO mezclar parámetros (ej: no usar `mean` con `sigma`)
- Para generación por IA: preferir siempre la parametrización canónica `s/scale/loc`

---

### 3. PERT/Beta (`sev_opcion: 3`)

Solo admite método Min/Mode/Max:
```json
{
    "sev_opcion": 3,
    "sev_input_method": "min_mode_max",
    "sev_minimo": 10000,
    "sev_mas_probable": 40000,
    "sev_maximo": 120000,
    "sev_params_direct": {}
}
```
- Restricción: `minimo < mas_probable < maximo`
- La distribución PERT es una variante de Beta que da más peso al valor más probable

---

### 4. Pareto/GPD (`sev_opcion: 4`)

#### Método Min/Mode/Max:
```json
{
    "sev_opcion": 4,
    "sev_input_method": "min_mode_max",
    "sev_minimo": 100000,
    "sev_mas_probable": 500000,
    "sev_maximo": 5000000,
    "sev_params_direct": {}
}
```

**NOTA IMPORTANTE PARA EL AGENTE**:
- Para generación automática (IA), **NO usar** `min_mode_max` en Pareto/GPD.
- Usar siempre `sev_input_method: "direct"`.

#### Método Directo:
```json
{
    "sev_opcion": 4,
    "sev_input_method": "direct",
    "sev_minimo": null,
    "sev_mas_probable": null,
    "sev_maximo": null,
    "sev_params_direct": {
        "c": 0.3,
        "scale": 200000,
        "loc": 100000
    }
}
```

**Validaciones ESTRICTAS**:
- `c` (ξ): Shape parameter (puede ser negativo, cero o positivo)
  - `c` < 0: Cola finita (distribución acotada superiormente)
  - `c` = 0: Cola exponencial (distribución exponencial)
  - `c` > 0: Cola pesada (Pareto, eventos extremos)
  - Rango típico: -0.5 a +0.5
- `scale` (β): Scale parameter **DEBE ser > 0**
- `loc` (μ): Location/threshold parameter (≥ 0, marca el umbral mínimo)

**REGLAS CRÍTICAS para Pareto/GPD**:
- Para importación válida: `sev_input_method` debe ser `"direct"`
- `sev_params_direct` debe incluir **exactamente** `c`, `scale`, `loc`
- `scale` > 0
- `loc` debe ser numérico (típicamente ≥ 0)

**REGLAS CRÍTICAS**:
- `scale` NUNCA puede ser 0 o negativo
- `loc` determina el valor mínimo de la distribución
- Para riesgos operacionales, típicamente `c` está entre 0.1 y 0.4
- `sev_minimo`, `sev_mas_probable`, `sev_maximo` DEBEN ser `null`

---

### 5. Uniforme (`sev_opcion: 5`)

Solo requiere mínimo y máximo:
```json
{
    "sev_opcion": 5,
    "sev_input_method": "min_mode_max",
    "sev_minimo": 20000,
    "sev_mas_probable": null,
    "sev_maximo": 80000,
    "sev_params_direct": {}
}
```
- `sev_mas_probable` se ignora para Uniforme
- Restricción: `minimo < maximo`

---

## Distribuciones de Frecuencia

El campo `freq_opcion` determina la distribución de frecuencia:

| freq_opcion | Distribución | Descripción |
|-------------|--------------|-------------|
| 1 | Poisson | Número de eventos por período |
| 2 | Binomial | Número de éxitos en n intentos |
| 3 | Bernoulli | Evento ocurre (1) o no (0) |
| 4 | Poisson-Gamma | Poisson con tasa incierta |
| 5 | Beta | Probabilidad anual incierta |

---

### 1. Poisson (`freq_opcion: 1`)

```json
{
    "freq_opcion": 1,
    "tasa": 2.5,
    "num_eventos": null,
    "prob_exito": null
}
```
- `tasa` (λ): Tasa media de ocurrencia por período (debe ser > 0)

---

### 2. Binomial (`freq_opcion: 2`)

```json
{
    "freq_opcion": 2,
    "tasa": null,
    "num_eventos": 10,
    "prob_exito": 0.15
}
```
- `num_eventos` (n): Número de eventos posibles (entero > 0)
- `prob_exito` (p): Probabilidad de éxito por evento (0 ≤ p ≤ 1)

---

### 3. Bernoulli (`freq_opcion: 3`)

```json
{
    "freq_opcion": 3,
    "tasa": null,
    "num_eventos": null,
    "prob_exito": 0.25
}
```
- `prob_exito` (p): Probabilidad de que el evento ocurra (0 ≤ p ≤ 1)
- Resultado: 0 (no ocurre) o 1 (ocurre)

---

### 4. Poisson-Gamma (`freq_opcion: 4`)

Modela incertidumbre en la tasa de Poisson usando una distribución Gamma:

```json
{
    "freq_opcion": 4,
    "tasa": null,
    "num_eventos": null,
    "prob_exito": null,
    "pg_minimo": 1,
    "pg_mas_probable": 3,
    "pg_maximo": 8,
    "pg_confianza": 90,
    "pg_alpha": null,
    "pg_beta": null
}
```

**Opción A: Usar Min/Mode/Max (recomendado)**
- `pg_minimo`: Tasa mínima esperada (> 0)
- `pg_mas_probable`: Tasa más probable (> pg_minimo)
- `pg_maximo`: Tasa máxima esperada (> pg_mas_probable)
- `pg_confianza`: % de confianza del rango (0-100, típicamente 90)
- Los parámetros alpha/beta se calculan automáticamente

**Validaciones ESTRICTAS Opción A**:
- 0 < `pg_minimo` < `pg_mas_probable` < `pg_maximo`
- `pg_confianza` entre 50 y 99 (típico: 90)
- `pg_alpha` y `pg_beta` deben ser `null`
- `tasa`, `num_eventos`, `prob_exito` deben ser `null`

**Opción B: Parámetros directos**
```json
{
    "freq_opcion": 4,
    "tasa": null,
    "num_eventos": null,
    "prob_exito": null,
    "pg_minimo": null,
    "pg_mas_probable": null,
    "pg_maximo": null,
    "pg_confianza": null,
    "pg_alpha": 5.0,
    "pg_beta": 2.0
}
```

**Validaciones ESTRICTAS Opción B**:
- `pg_alpha` > 1 (shape, típicamente 2-20)
- `pg_beta` > 0 (rate, típicamente 0.5-10)
- `pg_minimo`, `pg_mas_probable`, `pg_maximo`, `pg_confianza` deben ser `null`
- `tasa`, `num_eventos`, `prob_exito` deben ser `null`

**REGLAS CRÍTICAS Poisson-Gamma**:
- Usar SOLO Opción A o SOLO Opción B, NO mezclar
- Si usa min/mode/max: alpha/beta = `null`
- Si usa alpha/beta: min/mode/max/confianza = `null`

---

### 5. Beta Frecuencia (`freq_opcion: 5`)

Modela incertidumbre en la probabilidad anual:

```json
{
    "freq_opcion": 5,
    "tasa": null,
    "num_eventos": null,
    "prob_exito": null,
    "beta_minimo": 5,
    "beta_mas_probable": 15,
    "beta_maximo": 40,
    "beta_confianza": 90,
    "beta_alpha": 2.0,
    "beta_beta": 8.0
}
```

**REGLA CRÍTICA PARA IMPORTACIÓN EN RISK LAB**:
- Risk Lab reconstruye la distribución de frecuencia Beta **a partir de `beta_alpha` y `beta_beta`**.
- Por lo tanto, para que el JSON sea importable, **`beta_alpha` y `beta_beta` deben estar presentes y ser > 0**.
- Los campos `beta_minimo`, `beta_mas_probable`, `beta_maximo`, `beta_confianza` se usan en la UI y en la lógica de simulación (formateo y ajustes), por lo que **NO deben ser `null` cuando `freq_opcion=5`**.

**UNIDADES (IMPORTANTE)**:
- En el JSON: `beta_minimo`, `beta_mas_probable`, `beta_maximo`, `beta_confianza` son **PORCENTAJES** (0-100).
- En el cálculo interno de Risk Lab (`obtener_parametros_beta_frecuencia`): estos valores se convierten a proporciones dividiendo por 100, y se valida:
  - `0 ≤ min < mode < max ≤ 1`
  - `0 < confianza < 1`

**Opción A: Usar Min/Mode/Max (valores en porcentaje) + incluir alpha/beta calculados**
- `beta_minimo`: Probabilidad mínima % (0 ≤ x < beta_mas_probable)
- `beta_mas_probable`: Probabilidad más probable %
- `beta_maximo`: Probabilidad máxima % (< 100)
- `beta_confianza`: % de confianza del rango (típicamente 90)
- Restricción: 0% ≤ minimo < mas_probable < maximo ≤ 100%
- **Además**: incluir `beta_alpha` y `beta_beta` (calculados a partir de esos valores)

**Validaciones ESTRICTAS Opción A**:
- 0 ≤ `beta_minimo` < `beta_mas_probable` < `beta_maximo` ≤ 100
- `beta_confianza` debe ser **estrictamente** entre 0 y 100 (ej: 80, 90, 95). No usar 0 ni 100.
- `beta_alpha` > 0 y `beta_beta` > 0
- `tasa`, `num_eventos`, `prob_exito` deben ser `null`

**Opción B: Parámetros directos (recomendado para evitar ambigüedades)**

**IMPORTANTE**: aunque uses `beta_alpha`/`beta_beta`, igual debes incluir `beta_minimo`/`beta_mas_probable`/`beta_maximo`/`beta_confianza` como números (no `null`) para evitar errores en UI y durante simulación.

```json
{
    "freq_opcion": 5,
    "tasa": null,
    "num_eventos": null,
    "prob_exito": null,
    "beta_minimo": 5,
    "beta_mas_probable": 15,
    "beta_maximo": 40,
    "beta_confianza": 90,
    "beta_alpha": 2.0,
    "beta_beta": 8.0
}
```

**Validaciones ESTRICTAS Opción B**:
- `beta_alpha` > 0 (típicamente 0.5-20)
- `beta_beta` > 0 (típicamente 0.5-20)
- Para moda en el centro: `beta_alpha` ≈ `beta_beta` > 1
- Para moda baja: `beta_alpha` < `beta_beta`
- Para moda alta: `beta_alpha` > `beta_beta`
- `beta_minimo`, `beta_mas_probable`, `beta_maximo`, `beta_confianza` deben ser numéricos y cumplir `0 ≤ min < mode < max ≤ 100`
- `beta_confianza` debe ser **estrictamente** entre 0 y 100
- `tasa`, `num_eventos`, `prob_exito` deben ser `null`

**REGLAS CRÍTICAS Beta Frecuencia**:
- `beta_alpha` y `beta_beta` son **obligatorios** para importación
- Los valores de `beta_minimo`/`beta_mas_probable`/`beta_maximo` son **PORCENTAJES (0-100)**, no decimales (0-1)
- Si se incluyen min/mode/max/confianza, deben ser coherentes y respetar el orden (0 ≤ min < mode < max ≤ 100)
- NUNCA usar `null` en `beta_minimo`/`beta_mas_probable`/`beta_maximo`/`beta_confianza` cuando `freq_opcion=5`

---

## Vínculos (Dependencias entre Eventos)

Los vínculos permiten que la ocurrencia de un evento dependa de otros:

```json
{
    "vinculos": [
        {
            "id_padre": "uuid-del-evento-padre",
            "tipo": "AND"
        },
        {
            "id_padre": "uuid-otro-evento-padre",
            "tipo": "AND"
        }
    ]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_padre` | string | UUID del evento del que depende |
| `tipo` | string | Tipo de dependencia: `"AND"` u `"OR"` |

**Validaciones ESTRICTAS**:
- `tipo` debe ser exactamente `"AND"` o `"OR"` (en mayúsculas)
- No se permiten valores como `"and"`, `"Or"`, `"Y"`, `"O"`

### Lógica de Dependencias:
- **AND**: El evento hijo solo puede ocurrir si TODOS los padres ocurrieron
- **OR**: El evento hijo puede ocurrir si AL MENOS UN padre ocurrió

### Importante:
- No crear dependencias cíclicas (A → B → A)
- Los IDs de padre deben existir en la lista de eventos
- Un evento sin vínculos es independiente

---

## Factores de Ajuste (Controles/Factores de Riesgo)

Los factores modifican la frecuencia y/o severidad de un evento. Hay dos modelos:

### Modelo Estático

Aplica un impacto fijo en cada simulación:

```json
{
    "factores_ajuste": [
        {
            "nombre": "Firewall Perimetral",
            "activo": true,
            "tipo_modelo": "estatico",
            
            "afecta_frecuencia": true,
            "impacto_porcentual": -30,
            
            "afecta_severidad": true,
            "impacto_severidad_pct": -20
        }
    ]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre` | string | Nombre descriptivo del factor |
| `activo` | boolean | Si el factor está activo |
| `tipo_modelo` | string | `"estatico"` |
| `afecta_frecuencia` | boolean | Si afecta la frecuencia |
| `impacto_porcentual` | integer | % de impacto en frecuencia (-99 a +∞). Negativo reduce, positivo aumenta |
| `afecta_severidad` | boolean | Si afecta la severidad |
| `impacto_severidad_pct` | integer | % de impacto en severidad (-99 a +∞) |

**Fórmula estático**: `factor = 1 + (impacto/100)`
- -30% → factor = 0.70 → reduce 30%
- +50% → factor = 1.50 → aumenta 50%

---

### Modelo Estocástico

El control tiene una probabilidad de funcionar en cada iteración:

```json
{
    "factores_ajuste": [
        {
            "nombre": "Sistema Anti-Malware",
            "activo": true,
            "tipo_modelo": "estocastico",
            
            "confiabilidad": 70,
            
            "reduccion_efectiva": 80,
            "reduccion_fallo": 10,
            
            "reduccion_severidad_efectiva": 50,
            "reduccion_severidad_fallo": 0
        }
    ]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre` | string | Nombre descriptivo |
| `activo` | boolean | Si está activo |
| `tipo_modelo` | string | `"estocastico"` |
| `confiabilidad` | integer | % probabilidad de que funcione (0-100) |
| `reduccion_efectiva` | integer | % reducción si funciona (-100 a +99). Positivo reduce |
| `reduccion_fallo` | integer | % reducción si falla (-100 a +99) |
| `reduccion_severidad_efectiva` | integer | % reducción severidad si funciona |
| `reduccion_severidad_fallo` | integer | % reducción severidad si falla |

**Fórmula estocástico**: `factor = 1 - (reduccion/100)`
- reduccion = 80 → factor = 0.20 → reduce 80%
- reduccion = -20 → factor = 1.20 → aumenta 20%

**Comportamiento**: En cada iteración, el sistema genera un número aleatorio. Si es menor que `confiabilidad/100`, aplica `reduccion_efectiva`; si no, aplica `reduccion_fallo`.

---

### Modelo Seguro/Transferencia de Riesgo

Los seguros modelan pólizas de seguro con deducibles, coberturas y límites específicos:

```json
{
    "factores_ajuste": [
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
    ]
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `nombre` | string | Sí | Nombre descriptivo de la póliza |
| `activo` | boolean | Sí | Si el seguro está activo |
| `tipo_modelo` | string | Sí | **DEBE ser "estatico"** |
| `tipo_severidad` | string | Sí | **DEBE ser "seguro"** (identifica como póliza) |
| `seguro_tipo_deducible` | string | Sí | **"agregado"** o **"por_ocurrencia"** |
| `seguro_deducible` | integer | Sí | Monto del deducible (≥ 0, en moneda local) |
| `seguro_cobertura_pct` | integer | Sí | % de cobertura sobre el exceso (1-100) |
| `seguro_limite_ocurrencia` | integer | Sí | Límite por siniestro (0 = sin límite) |
| `seguro_limite` | integer | Sí | Límite agregado anual (0 = sin límite) |
| `afecta_frecuencia` | boolean | Sí | **DEBE ser false** para seguros |
| `impacto_porcentual` | integer | Sí | **DEBE ser 0** para seguros |
| `afecta_severidad` | boolean | Sí | **DEBE ser false** para seguros |
| `impacto_severidad_pct` | integer | Sí | **DEBE ser 0** para seguros |

#### Tipos de Deducible:

**"agregado"**: El deducible se aplica a la suma total de pérdidas del año
- Uso: Pólizas anuales tradicionales (property, liability general)
- Ejemplo: Deducible anual de $100K, luego todo está cubierto

**"por_ocurrencia"**: El deducible se aplica a cada siniestro individual
- Uso: Pólizas por evento (cyber, professional liability)
- Ejemplo: Cada ataque tiene deducible de $25K

#### Rangos Válidos:

| Parámetro | Rango | Notas |
|-----------|-------|-------|
| `seguro_deducible` | 0 - 999,999,999 | 0 = sin deducible (poco común) |
| `seguro_cobertura_pct` | 1 - 100 | Típico: 80-100% |
| `seguro_limite_ocurrencia` | 0 - 999,999,999 | 0 = sin límite por evento |
| `seguro_limite` | 0 - 999,999,999 | 0 = sin límite anual |

#### Ejemplos de Configuración:

**Seguro Cyber Por Ocurrencia:**
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
    "afecta_severidad": false,
    "impacto_severidad_pct": 0
}
```

**Seguro Property Agregado:**
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
    "afecta_severidad": false,
    "impacto_severidad_pct": 0
}
```

#### Orden de Aplicación en Simulación:

1. Generar pérdidas individuales (severidad bruta)
2. Aplicar factores de mitigación (controles estáticos/estocásticos)
3. **Aplicar seguros POR OCURRENCIA** a cada pérdida mitigada
4. Agregar pérdidas por simulación (suma anual)
5. **Aplicar seguros AGREGADOS** al total anual

**IMPORTANTE**: Los seguros cubren la pérdida DESPUÉS de la mitigación de controles.

---

## Escenarios

Los escenarios son configuraciones alternativas con sus propios eventos:

```json
{
    "scenarios": [
        {
            "nombre": "Escenario Pesimista",
            "descripcion": "Análisis con controles reducidos",
            "eventos_riesgo": [
                { ... evento 1 ... },
                { ... evento 2 ... }
            ]
        }
    ]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre` | string | Nombre único del escenario |
| `descripcion` | string | Descripción opcional |
| `eventos_riesgo` | array | Lista de eventos (misma estructura que eventos principales) |

---

## Ejemplo Completo

```json
{
    "num_simulaciones": 10000,
    "eventos_riesgo": [
        {
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "nombre": "Ataque de Ransomware",
            "activo": true,
            
            "sev_opcion": 2,
            "sev_input_method": "direct",
            "sev_minimo": null,
            "sev_mas_probable": null,
            "sev_maximo": null,
            "sev_params_direct": {
                "s": 0.8,
                "scale": 36315,
                "loc": 0
            },
            
            "freq_opcion": 1,
            "tasa": 1.5,
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
            "factores_ajuste": [
                {
                    "nombre": "EDR Avanzado",
                    "activo": true,
                    "tipo_modelo": "estocastico",
                    "confiabilidad": 85,
                    "reduccion_efectiva": 70,
                    "reduccion_fallo": 10,
                    "reduccion_severidad_efectiva": 40,
                    "reduccion_severidad_fallo": 0,
                    "afecta_frecuencia": true,
                    "impacto_porcentual": -50,
                    "afecta_severidad": false,
                    "impacto_severidad_pct": 0
                }
            ]
        },
        {
            "id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
            "nombre": "Brecha de Datos Post-Ransomware",
            "activo": true,
            
            "sev_opcion": 3,
            "sev_input_method": "min_mode_max",
            "sev_minimo": 100000,
            "sev_mas_probable": 500000,
            "sev_maximo": 2000000,
            "sev_params_direct": {},
            
            "freq_opcion": 3,
            "tasa": null,
            "num_eventos": null,
            "prob_exito": 0.4,
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
            
            "vinculos": [
                {
                    "id_padre": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "tipo": "AND"
                }
            ],
            "factores_ajuste": []
        }
    ],
    "scenarios": [],
    "current_scenario_name": null
}
```

---

## ERRORES COMUNES Y CÓMO EVITARLOS

### ❌ ERROR #1: Mezclar métodos de entrada

**INCORRECTO**:
```jsonc
{
    "sev_opcion": 2,
    "sev_input_method": "direct",
    "sev_minimo": 10000,  // ❌ NO debe estar si usa "direct"
    "sev_params_direct": {
        "mu": 10.5,
        "sigma": 0.8
    }
}
```

**CORRECTO**:
```jsonc
{
    "sev_opcion": 2,
    "sev_input_method": "direct",
    "sev_minimo": null,  // ✓ DEBE ser null
    "sev_mas_probable": null,
    "sev_maximo": null,
    "sev_params_direct": {
        "mu": 10.5,
        "sigma": 0.8,
        "loc": 0
    }
}
```

---

### ❌ ERROR #2: Dejar sev_params_direct vacío con método "direct"

**INCORRECTO**:
```jsonc
{
    "sev_opcion": 1,
    "sev_input_method": "direct",
    "sev_params_direct": {}  // ❌ VACIÓ = ERROR
}
```

**CORRECTO**:
```jsonc
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

---

### ❌ ERROR #3: Usar parámetros incorrectos para método min_mode_max

**INCORRECTO**:
```jsonc
{
    "sev_opcion": 1,
    "sev_input_method": "min_mode_max",
    "sev_minimo": 10000,
    "sev_mas_probable": 50000,
    "sev_maximo": 100000,
    "sev_params_direct": {  // ❌ NO debe tener contenido
        "mean": 50000
    }
}
```

**CORRECTO**:
```jsonc
{
    "sev_opcion": 1,
    "sev_input_method": "min_mode_max",
    "sev_minimo": 10000,
    "sev_mas_probable": 50000,
    "sev_maximo": 100000,
    "sev_params_direct": {}  // ✓ VACIÓ para min_mode_max
}
```

---

### ❌ ERROR #4: Orden incorrecto en min < mode < max

**INCORRECTO**:
```jsonc
{
    "sev_minimo": 100000,
    "sev_mas_probable": 50000,  // ❌ mas_probable < minimo
    "sev_maximo": 200000
}
```

**CORRECTO**:
```jsonc
{
    "sev_minimo": 50000,
    "sev_mas_probable": 100000,  // ✓ minimo < mode < maximo
    "sev_maximo": 200000
}
```

---

### ❌ ERROR #5: Parámetros de distribución en cero o negativos

**INCORRECTO LogNormal**:
```jsonc
{
    "sev_params_direct": {
        "mean": 50000,
        "std": 0  // ❌ std NO puede ser 0
    }
}
```

**CORRECTO**:
```jsonc
{
    "sev_params_direct": {
        "mean": 50000,
        "std": 15000  // ✓ std > 0
    }
}
```

---

### ❌ ERROR #6: Mezclar parámetros de LogNormal

**INCORRECTO**:
```jsonc
{
    "sev_params_direct": {
        "mean": 50000,  // ❌ Opción A (mean/std)
        "sigma": 0.8    // ❌ Opción B (mu/sigma)
        // NO MEZCLAR
    }
}
```

**CORRECTO (Opción A)**:
```json
{
    "sev_params_direct": {
        "mean": 50000,
        "std": 30000,
        "loc": 0
    }
}
```

**CORRECTO (Opción B)**:
```json
{
    "sev_params_direct": {
        "mu": 10.5,
        "sigma": 0.8,
        "loc": 0
    }
}
```

---

### ❌ ERROR #7: Poisson-Gamma/Beta con parámetros mixtos

**INCORRECTO**:
```jsonc
{
    "freq_opcion": 4,
    "pg_minimo": 1,
    "pg_mas_probable": 3,
    "pg_maximo": 8,
    "pg_alpha": 5.0  // ❌ NO mezclar min/mode/max con alpha/beta
}
```

**CORRECTO (Min/Mode/Max)**:
```json
{
    "freq_opcion": 4,
    "tasa": null,
    "num_eventos": null,
    "prob_exito": null,
    "pg_minimo": 1,
    "pg_mas_probable": 3,
    "pg_maximo": 8,
    "pg_confianza": 90,
    "pg_alpha": null,  // ✓ null cuando usa min/mode/max
    "pg_beta": null
}
```

**CORRECTO (Alpha/Beta)**:
```json
{
    "freq_opcion": 4,
    "tasa": null,
    "num_eventos": null,
    "prob_exito": null,
    "pg_minimo": null,  // ✓ null cuando usa alpha/beta
    "pg_mas_probable": null,
    "pg_maximo": null,
    "pg_confianza": null,
    "pg_alpha": 5.0,
    "pg_beta": 2.0
}
```

---

### ❌ ERROR #8: Beta Frecuencia con porcentajes como decimales

**INCORRECTO**:
```jsonc
{
    "freq_opcion": 5,
    "beta_minimo": 0.05,  // ❌ Debe ser 5 (no 0.05)
    "beta_mas_probable": 0.15,  // ❌ Debe ser 15
    "beta_maximo": 0.40  // ❌ Debe ser 40
}
```

**CORRECTO**:
```json
{
    "freq_opcion": 5,
    "tasa": null,
    "num_eventos": null,
    "prob_exito": null,
    "beta_minimo": 5,  // ✓ Porcentaje como entero
    "beta_mas_probable": 15,
    "beta_maximo": 40,
    "beta_confianza": 90,
    "beta_alpha": 2.0,
    "beta_beta": 8.0
}
```

---

### ❌ ERROR #9: Probabilidades fuera de rango (Bernoulli/Binomial)

**INCORRECTO**:
```jsonc
{
    "freq_opcion": 3,
    "prob_exito": 25  // ❌ Debe ser 0.25 (no 25)
}
```

**CORRECTO**:
```json
{
    "freq_opcion": 3,
    "tasa": null,
    "num_eventos": null,
    "prob_exito": 0.25,  // ✓ Entre 0 y 1
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
    "beta_beta": null
}
```

---

### ❌ ERROR #10: Seguros sin tipo_severidad o con campos incorrectos

**INCORRECTO**:
```jsonc
{
    "nombre": "Cyber Insurance",
    "activo": true,
    "tipo_modelo": "estatico",
    // ❌ FALTA tipo_severidad: "seguro"
    "seguro_deducible": 25000,
    "afecta_frecuencia": true,  // ❌ DEBE ser false
    "impacto_porcentual": -30  // ❌ DEBE ser 0
}
```

**CORRECTO**:
```json
{
    "nombre": "Cyber Insurance",
    "activo": true,
    "tipo_modelo": "estatico",
    "tipo_severidad": "seguro",  // ✓ REQUERIDO
    "seguro_tipo_deducible": "por_ocurrencia",
    "seguro_deducible": 25000,
    "seguro_cobertura_pct": 80,
    "seguro_limite_ocurrencia": 500000,
    "seguro_limite": 2000000,
    "afecta_frecuencia": false,  // ✓ false para seguros
    "impacto_porcentual": 0,  // ✓ 0 para seguros
    "afecta_severidad": false,
    "impacto_severidad_pct": 0
}
```

---

### ❌ ERROR #11: Omitir campos requeridos aunque sean null

**INCORRECTO**:
```jsonc
{
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "nombre": "Ransomware",
    "sev_opcion": 1,
    "freq_opcion": 1,
    "tasa": 2.5
    // ❌ FALTAN muchos campos
}
```

**CORRECTO**:
```json
{
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "nombre": "Ransomware",
    "activo": true,
    "sev_opcion": 1,
    "sev_input_method": "min_mode_max",
    "sev_minimo": 10000,
    "sev_mas_probable": 50000,
    "sev_maximo": 200000,
    "sev_params_direct": {},
    "freq_opcion": 1,
    "tasa": 2.5,
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
```

---

## REGLAS CRÍTICAS - CHECKLIST OBLIGATORIO

### Antes de generar el JSON, verificar:

#### ☑️ Severidad:
- [ ] `sev_opcion` entre 1 y 5
- [ ] Si `sev_input_method` = "min_mode_max":
  - [ ] `sev_minimo` < `sev_mas_probable` < `sev_maximo`
  - [ ] `sev_params_direct` = `{}`
- [ ] Si `sev_input_method` = "direct":
  - [ ] `sev_minimo` = `null`, `sev_mas_probable` = `null`, `sev_maximo` = `null`
  - [ ] `sev_params_direct` NO está vacío
  - [ ] Parámetros > 0 donde aplica (`std`, `sigma`, `s`, `scale`)
  - [ ] NO mezclar opciones (mean/std vs mu/sigma vs s/scale)

#### ☑️ Frecuencia:
- [ ] `freq_opcion` entre 1 y 5
- [ ] Poisson (1): `tasa` > 0, resto = `null`
- [ ] Binomial (2): `num_eventos` > 0, `0 ≤ prob_exito ≤ 1`, resto = `null`
- [ ] Bernoulli (3): `0 ≤ prob_exito ≤ 1`, resto = `null`
- [ ] Poisson-Gamma (4):
  - [ ] Si min/mode/max: valores válidos, alpha/beta = `null`
  - [ ] Si alpha/beta: `alpha` > 1, `beta` > 0, min/mode/max = `null`
- [ ] Beta (5):
  - [ ] Si min/mode/max: `0 ≤ min < mode < max ≤ 100` y **además** `beta_alpha`/`beta_beta` > 0
  - [ ] Si alpha/beta: ambos > 0, y `beta_minimo`/`beta_mas_probable`/`beta_maximo`/`beta_confianza` deben ser numéricos (no `null`) y coherentes
  - [ ] Valores son PORCENTAJES (0-100), no decimales (0-1)

#### ☑️ Factores Estáticos:
- [ ] `tipo_modelo` = "estatico"
- [ ] `impacto_porcentual` entre -99 y +200
- [ ] `impacto_severidad_pct` entre -99 y +200
- [ ] Si no afecta frecuencia: `afecta_frecuencia` = `false`, `impacto_porcentual` = 0
- [ ] Si no afecta severidad: `afecta_severidad` = `false`, `impacto_severidad_pct` = 0

#### ☑️ Factores Estocásticos:
- [ ] `tipo_modelo` = "estocastico"
- [ ] `confiabilidad` entre 0 y 100
- [ ] `reduccion_efectiva`, `reduccion_fallo` entre -100 y +99
- [ ] `reduccion_severidad_efectiva`, `reduccion_severidad_fallo` entre -100 y +99

#### ☑️ Factores Seguro:
- [ ] `tipo_modelo` = "estatico"
- [ ] `tipo_severidad` = "seguro"
- [ ] `seguro_tipo_deducible` = "agregado" o "por_ocurrencia"
- [ ] `seguro_deducible` ≥ 0
- [ ] `seguro_cobertura_pct` entre 1 y 100
- [ ] `seguro_limite_ocurrencia` ≥ 0 (0 = sin límite)
- [ ] `seguro_limite` ≥ 0 (0 = sin límite)
- [ ] `afecta_frecuencia` = `false`, `impacto_porcentual` = 0
- [ ] `afecta_severidad` = `false`, `impacto_severidad_pct` = 0

#### ☑️ General:
- [ ] Todos los UUIDs son únicos y tienen formato válido
- [ ] Nombres de eventos no vacíos (máx 50 caracteres)
- [ ] Nombres sin saltos de línea, tabs ni caracteres de control
- [ ] Sin ciclos en vínculos
- [ ] Todos los `id_padre` existen
- [ ] Todos los campos requeridos presentes (incluso si son `null`)
- [ ] JSON sintácticamente válido

---

## Validaciones Importantes

### Al crear el JSON:

1. **IDs únicos**: Cada evento debe tener un UUID único
2. **Nombres no vacíos**: Máximo 50 caracteres
3. **Distribuciones válidas**: 
   - Severidad: `sev_opcion` entre 1 y 5
   - Frecuencia: `freq_opcion` entre 1 y 5
4. **Parámetros coherentes**:
   - Para Min/Mode/Max: `minimo < mas_probable < maximo`
   - Para Poisson: `tasa > 0`
   - Para Binomial: `num_eventos > 0`, `0 ≤ prob_exito ≤ 1`
   - Para probabilidades: entre 0 y 1 (o 0% y 100%)
5. **Sin ciclos**: Las dependencias no deben formar ciclos
6. **Vínculos válidos**: Los `id_padre` deben existir

### Campos que se ignoran al cargar:
- `dist_severidad` (objeto no serializable)
- `dist_frecuencia` (objeto no serializable)
- `_usa_estocastico` (flag temporal)
- `_factores_vector` (array temporal)
- `_factores_severidad_vector` (array temporal)
- `_factor_severidad_estatico` (flag temporal)

---

## Generación de UUIDs

Para generar UUIDs válidos en Python:
```python
import uuid
nuevo_id = str(uuid.uuid4())
# Ejemplo: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

---

## Notas para Asistentes de IA

### 🚨 REGLAS FUNDAMENTALES (NUNCA VIOLAR)

1. **SIEMPRE incluir TODOS los campos**, incluso si son `null`. Risk Lab espera la estructura completa.
2. **NUNCA mezclar métodos de entrada**:
   - Si `sev_input_method` = "min_mode_max": usar min/mode/max, `sev_params_direct` = `{}`
   - Si `sev_input_method` = "direct": min/mode/max = `null`, `sev_params_direct` CON contenido
   - Si no se proveen parámetros directos explícitos, **NO inventar** `sev_params_direct`: usar `min_mode_max`
   - Excepción obligatoria para IA: si `sev_opcion` es LogNormal (2) o Pareto/GPD (4), **usar siempre `direct`**
3. **NUNCA dejar `sev_params_direct` vacío `{}` con método "direct"**
4. **NUNCA usar parámetros en 0 o negativos** donde no está permitido:
   - `std`, `sigma`, `s`, `scale` SIEMPRE > 0
   - `tasa` (Poisson) SIEMPRE > 0
   - `num_eventos` (Binomial) SIEMPRE > 0
   - `pg_alpha` > 1 y `pg_beta` > 0 (Poisson-Gamma)
   - `beta_alpha` > 0 y `beta_beta` > 0 (Beta frecuencia)
5. **NUNCA mezclar opciones de parámetros** (ej: `mean` con `sigma` en LogNormal)
6. **SIEMPRE verificar orden**: `minimo` < `mas_probable` < `maximo`

7. **NUNCA inventar parámetros directos**:
   - Si `sev_opcion` es LogNormal (2) o Pareto/GPD (4), el agente debe usar `direct`.
   - Si el usuario no provee `s/scale/loc` (LogNormal) o `c/scale/loc` (GPD) o una combinación directa válida, el agente **debe pedir esos parámetros** en lugar de adivinar.
   - No derivar parámetros con heurísticas (ej: “asumir c=0.3” o “scale = promedio”), porque tiende a producir distribuciones inválidas o irreales.

SI freq_opcion == 1 -> tasa debe ser > 0 (no usar 0.0). Si el evento debe estar inactivo, usar "activo": false.

SI freq_opcion == 3 -> prob_exito requerido y 0 < prob_exito < 1. No usar 1.0 exacto (usar 0.999 si se necesita casi certeza).

SI freq_opcion == 5 -> beta_alpha y beta_beta requeridos (ambos > 0). Si el usuario tiene min/mode/max en %, deben convertirse a (alpha,beta) y guardarse en beta_alpha/beta_beta.

SI freq_opcion == 5 -> beta_minimo/beta_mas_probable/beta_maximo/beta_confianza deben ser numéricos (no `null`). Si el usuario no provee estos valores, el agente debe pedirlos (no inventarlos).

SI sev_input_method == "direct" -> sev_params_direct NO puede ser {} y debe incluir parámetros válidos (std>0, sigma>0, s>0, scale>0 según distribución).

NO mezclar modos de parametrización (min_mode_max <> direct).

NUNCA dejar claves duplicadas; siempre generar objetos sin claves repetidas.

### 📊 Tipos de Datos y Formatos

1. **Números**: Siempre numéricos, NUNCA strings
   - Correcto: `"tasa": 2.5`
   - Incorrecto: `"tasa": "2.5"`
   - Incorrecto: `"prob_exito": "0,25"` (en JSON los decimales usan punto, no coma)
2. **JSON válido (sin comentarios)**:
   - El archivo final debe ser **JSON estricto**: sin comentarios `//`, sin comentarios `/* */`, y sin comas finales.
   - Los fragmentos del documento que incluyen `// ❌` o `// ✓` son solo explicativos y **NO** deben copiarse al JSON final.
3. **Porcentajes**:
   - Factores estáticos/estocásticos: enteros (30 = 30%)
   - Bernoulli/Binomial `prob_exito`: decimal 0-1 (0.30 = 30%)
   - Beta frecuencia min/mode/max: enteros 0-100 (30 = 30%)
   - Beta frecuencia `beta_alpha`/`beta_beta`: positivos (> 0), no porcentajes
4. **UUIDs**: Strings con formato `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
5. **Booleanos**: `true` o `false` (sin comillas)
6. **Null**: `null` (sin comillas)

7. **Números finitos**:
   - No usar `NaN`, `Infinity`, `-Infinity` (no son JSON válido y fallan al cargar).
   - Evitar valores extremos no realistas que causen inestabilidad numérica (ej. LogNormal con CV enorme).

### 🧼 Reglas de Sanitización de Textos (evitar caracteres no permitidos)

Estas reglas evitan errores al exportar/importar y problemas de parseo/visualización.

**Para `nombre` de eventos y `nombre` de factores**:
- Debe ser `string` no vacío después de `strip()`
- Máximo 50 caracteres
- **NO permitido**:
  - Saltos de línea (`\n`, `\r`)
  - Tabs (`\t`)
  - Caracteres de control (ASCII < 32)
- Recomendación fuerte (IA): usar solo caracteres seguros: letras, números, espacios, y `._-()&/`

**Para `descripcion` (escenarios)**:
- Si se incluye, aplicar las mismas reglas de no-control/no-newlines
- Si el agente no tiene una descripción clara, usar `""` (string vacío) en vez de inventar texto con caracteres extraños

### 🔍 Validaciones Obligatorias Antes de Generar

**Severidad con método directo**:
- [ ] `sev_params_direct` NO está vacío
- [ ] `sev_minimo`, `sev_mas_probable`, `sev_maximo` son `null`
- [ ] Todos los parámetros numéricos > 0 (donde aplica)
- [ ] NO hay mezcla de opciones (mean/std vs mu/sigma vs s/scale)

**Frecuencia con Poisson-Gamma/Beta**:
- [ ] Poisson-Gamma: si usa min/mode/max: `pg_alpha`/`pg_beta` = `null`
- [ ] Poisson-Gamma: si usa alpha/beta: min/mode/max/confianza = `null`
- [ ] Beta: `beta_alpha` y `beta_beta` presentes y > 0 (obligatorio para importación)
- [ ] Beta: `beta_minimo`, `beta_mas_probable`, `beta_maximo`, `beta_confianza` presentes y numéricos (no `null`)
- [ ] Beta: valores en porcentajes (0-100), NO decimales

**Seguros**:
- [ ] `tipo_modelo` = "estatico", `tipo_severidad` = "seguro"
- [ ] `seguro_tipo_deducible` = "agregado" o "por_ocurrencia"
- [ ] `afecta_frecuencia` = `false`, `impacto_porcentual` = 0
- [ ] `afecta_severidad` = `false`, `impacto_severidad_pct` = 0

### 📝 Buenas Prácticas

1. **Usar la plantilla mínima** como base y completarla
2. **Generar UUIDs únicos** para cada evento nuevo
3. **Usar nombres descriptivos** (máx 50 caracteres)
4. **Verificar dos veces** antes de enviar:
   - Orden de min < mode < max
   - Campos `null` correctos según método elegido
   - Parámetros > 0 donde se requiere
5. **Para eventos sin dependencias**: usar `"vinculos": []`
6. **Para eventos sin factores**: usar `"factores_ajuste": []`
7. **El campo `activo`** permite desactivar eventos/factores sin eliminarlos

---

## Plantilla Mínima

```json
{
    "num_simulaciones": 10000,
    "eventos_riesgo": [
        {
            "id": "GENERAR-UUID-AQUI",
            "nombre": "Nombre del Evento",
            "activo": true,
            "sev_opcion": 2,
            "sev_input_method": "direct",
            "sev_minimo": null,
            "sev_mas_probable": null,
            "sev_maximo": null,
            "sev_params_direct": {
                "s": 0.8,
                "scale": 36315,
                "loc": 0
            },
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

---

## Plantilla de Factor Seguro

Para agregar un seguro a un evento, incluir en `factores_ajuste`:

```json
{
    "nombre": "Nombre de la Póliza",
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
    "afecta_severidad": false,
    "impacto_severidad_pct": 0
}
```

---

## Resumen de Tipos de Controles

| Tipo | `tipo_modelo` | `tipo_severidad` | Afecta | Uso |
|------|---------------|------------------|--------|-----|
| **Estático** | "estatico" | (omitir) | Frecuencia/Severidad | Controles fijos |
| **Estocástico** | "estocastico" | (omitir) | Frecuencia/Severidad | Controles con incertidumbre |
| **Seguro** | "estatico" | "seguro" | Solo Severidad | Pólizas de seguro |

---

*Documento generado para Risk Lab Beta v2.0.0*
*Última actualización: Enero 2025*
