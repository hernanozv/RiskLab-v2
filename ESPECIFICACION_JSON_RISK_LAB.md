# Especificación del Formato JSON para Risk Lab

<!--
╔══════════════════════════════════════════════════════════════════╗
║  MAPA DEL DOCUMENTO — Especificación JSON Risk Lab              ║
║                                                                  ║
║  ROL: Especificación técnica del formato JSON. Define la        ║
║  estructura exacta, campos, tipos de datos y validaciones.      ║
║  Es la FUENTE DE VERDAD para nombres de campos y valores.       ║
║                                                                  ║
║  SECCIONES (en orden de lectura):                               ║
║  1. Estructura Raíz del JSON                                    ║
║  2. ⭐ Checklist Rápido (resumen de reglas críticas)            ║
║  3. Reglas Estructurales (A-I) — claves, tipos, comportamiento  ║
║  4. Estructura de un Evento de Riesgo (template + campos)       ║
║  5. Distribuciones de Severidad (Normal, LogNormal, PERT,       ║
║     Pareto/GPD, Uniforme) con templates por distribución        ║
║  6. Distribuciones de Frecuencia (Poisson, Binomial,            ║
║     Bernoulli, Poisson-Gamma, Beta) con templates               ║
║  7. Vinculaciones (AND/OR/EXCLUYE)                              ║
║  8. Factores de Ajuste (estático, estocástico, seguro)          ║
║  9. Orden de aplicación en simulación                           ║
║  10. Escalamiento de Severidad por Frecuencia                   ║
║  11. Escenarios                                                  ║
║  12. Errores comunes con ejemplos ❌/✅                          ║
║  13. Checklists detallados de validación                        ║
║                                                                  ║
║  DOCUMENTOS COMPLEMENTARIOS:                                    ║
║  • Asistente GPT Risk Lab — Metodología conversacional,         ║
║    flujo de trabajo (Fases 1-3) y guía anti-duplicación        ║
║  • MANUAL_AGENTE_IA_RISK_LAB — QUÉ configurar y CÓMO          ║
║    interpretar requerimientos del usuario                       ║
╚══════════════════════════════════════════════════════════════════╝
-->

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
| `num_simulaciones` | integer | Sí | Número de iteraciones Monte Carlo (mínimo: 1, típico: 10000, máximo recomendado: 100000) |
| `eventos_riesgo` | array | Sí | Lista de eventos de riesgo de la simulación principal |
| `scenarios` | array | No | Lista de escenarios alternativos |
| `current_scenario_name` | string/null | No | Nombre del escenario actualmente seleccionado |

---

## Checklist Rápido (JSON estricto) - Para evitar errores de importación

### Integridad sintáctica (el JSON debe ser parseable)
- **Comillas dobles**: todas las claves y strings deben usar `"` (comillas dobles). JSON no acepta comillas simples.
- **Escapes en strings**: si un string necesita caracteres especiales, deben estar escapados (ej. `\n`, `\t`, `\"`). Idealmente evitar `\n`/`\t` en `nombre`.
- **Sin comentarios**: no incluir `//` ni `/* */` en el JSON final.
- **Sin comas finales**: no dejar comas finales en objetos/arrays (trailing commas).
- **Tipos numéricos reales**: los campos numéricos deben ser números válidos, no strings. **Nunca generar tokens numéricos malformados** como `0.01.6` — cada número debe tener como máximo un punto decimal.
- **Sin caracteres de control**: no incluir caracteres con código < 0x20 (tabuladores, retornos de carro binarios, bytes nulos) sin escapar en strings. Usar `json.dumps()` para garantizar escape correcto.
- **Documento completo**: el JSON debe ser un documento completo y válido. Si el output se trunca, es preferible generar menos eventos que un JSON incompleto.

### Integridad de parámetros (el importador no crashea)
- **Beta frecuencia (freq_opcion=5)**: siempre incluir `beta_alpha` y `beta_beta` (ambos > 0). Además `beta_minimo/beta_mas_probable/beta_maximo/beta_confianza` numéricos (nunca null).
- **Poisson-Gamma (freq_opcion=4)**: siempre incluir `pg_alpha` (> 1) y `pg_beta` (> 0). **NUNCA dejarlos en null** — calcularlos con la fórmula PERT si el usuario da min/mode/max.
- **Poisson (freq_opcion=1)**: `tasa` debe ser > 0, **nunca null ni 0**.
- **Severidad directa**: si `sev_input_method: "direct"`, `sev_params_direct` NUNCA puede ser `{}` vacío. Debe tener parámetros válidos (`std`/`sigma`/`s`/`scale` > 0).
- **PERT/Uniforme**: `sev_minimo < sev_mas_probable < sev_maximo`, todos > 0, nunca null ni 0.

### Integridad semántica (el modelo tiene sentido)
- **Seguros = factores, NO eventos**: las pólizas de seguro se modelan como `factores_ajuste` con `tipo_severidad: "seguro"`. **NUNCA crear un evento de riesgo para representar un seguro** (un evento con severidad 0 o negativa no tiene sentido y causa errores).
- **Vínculos resolubles**: todo `vinculos[].id_padre` debe referenciar un `id` existente dentro del mismo archivo/escenario.
- **Sin ciclos**: el grafo de dependencias debe ser un DAG (acíclico).

---

## Reglas estructurales obligatorias (Para generación por IA)

Estas reglas evitan errores comunes de importación (`KeyError`/`TypeError`) que causan fallo total.

### A) Listas: siempre listas (nunca `null`)

- **`eventos_riesgo`**: siempre `[]` si está vacío (nunca `null`).
- **`scenarios`**: siempre `[]` si está vacío (nunca `null`).
- **`vinculos`** (en cada evento): siempre `[]` si no hay vínculos (nunca `null`).
- **`factores_ajuste`** (en cada evento): siempre `[]` si no hay factores (nunca `null`).

### B) Eventos: claves mínimas obligatorias (siempre presentes)

Cada objeto de evento debe incluir **todas** estas claves (aunque muchas sean `null` según la distribución):

- `id`, `nombre`, `activo`
- Severidad:
  - `sev_opcion`, `sev_input_method`, `sev_minimo`, `sev_mas_probable`, `sev_maximo`, `sev_params_direct`, `sev_limite_superior`
- Frecuencia:
  - `freq_opcion`, `freq_limite_superior`, `tasa`, `num_eventos`, `prob_exito`
  - `pg_minimo`, `pg_mas_probable`, `pg_maximo`, `pg_confianza`, `pg_alpha`, `pg_beta`
  - `beta_minimo`, `beta_mas_probable`, `beta_maximo`, `beta_confianza`, `beta_alpha`, `beta_beta`
- Escalamiento de severidad por frecuencia:
  - `sev_freq_activado`, `sev_freq_modelo`, `sev_freq_tipo_escalamiento`
  - `sev_freq_paso`, `sev_freq_base`, `sev_freq_factor_max`
  - `sev_freq_tabla`, `sev_freq_alpha`, `sev_freq_solo_aumento`, `sev_freq_sistemico_factor_max`
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
- Frecuencia Bernoulli (`freq_opcion = 3`): `0 ≤ prob_exito ≤ 1`. (El código acepta 0 y 1, pero se recomienda evitar extremos si el evento tiene factores estocásticos; usar 0.001 o 0.999 en su lugar.)
- Poisson-Gamma (`freq_opcion = 4`): `pg_alpha > 1` y `pg_beta > 0` son **SIEMPRE obligatorios** (nunca `null`). Si también se incluyen min/mode/max para documentación: `0 < pg_minimo < pg_mas_probable < pg_maximo` y `0 < pg_confianza < 100`.
- Beta frecuencia (`freq_opcion = 5`): `beta_alpha > 0` y `beta_beta > 0`. Además, `0 ≤ beta_minimo < beta_mas_probable < beta_maximo ≤ 100` (porcentajes).
- Factores estocásticos: `confiabilidad` debe estar en `[0, 100]`.

### H) Comportamiento de la importación ante errores

Risk Lab maneja errores de forma **asimétrica** durante la importación:

| Tipo de error | Comportamiento | Consecuencia |
|---------------|----------------|--------------|
| **Severidad inválida** (parámetros incorrectos) | En eventos principales: el evento se **omite** y se muestra advertencia. En escenarios: el evento se agrega con severidad nula (puede fallar en simulación) | Los demás eventos se importan correctamente |
| **Frecuencia inválida** (parámetros faltantes o fuera de rango) | **CRASH TOTAL** de la importación | No se importa ningún evento |
| **Campo obligatorio faltante** (`id`, `nombre`, `sev_opcion`, `freq_opcion`) | **CRASH TOTAL** (`KeyError`) | No se importa ningún evento |
| **`sev_minimo`/`sev_mas_probable`/`sev_maximo` faltantes** | **CRASH TOTAL** (`KeyError`) | No se importa ningún evento |
| **JSON sintácticamente inválido** | **CRASH TOTAL** | Error de parseo |

**CONSECUENCIA PARA EL AGENTE**: Es más seguro equivocarse en la severidad (el evento se omite pero el resto carga) que en la frecuencia o campos estructurales (nada se importa). Sin embargo, en eventos dentro de **escenarios**, un error de severidad NO omite el evento sino que lo agrega con severidad nula, lo cual puede causar errores al simular. Por lo tanto, asegurar parámetros de severidad válidos siempre.

### I) Tabla de referencia rápida: campos por evento

Esta tabla muestra **exactamente** qué sucede si cada campo falta o es inválido:

| Campo | Si falta | Default implícito |
|-------|----------|--------------------|
| `id` | **CRASH** | — |
| `nombre` | **CRASH** | — |
| `activo` | OK | `true` |
| `sev_opcion` | **CRASH** | — |
| `sev_input_method` | OK | `"min_mode_max"` |
| `sev_minimo` | **CRASH** | — |
| `sev_mas_probable` | **CRASH** | — |
| `sev_maximo` | **CRASH** | — |
| `sev_params_direct` | OK | `{}` |
| `sev_limite_superior` | OK | `null` (sin límite) |
| `freq_opcion` | **CRASH** | — |
| `freq_limite_superior` | OK | `null` (sin límite) |
| `tasa` | OK (pero **CRASH** si `freq_opcion=1` y es `null` o ≤ 0) | `null` |
| `num_eventos` | OK | `null` |
| `prob_exito` | OK (pero **CRASH** si `freq_opcion=2`/`3` y es `null`) | `null` |
| `pg_minimo/mas_probable/maximo/confianza` | OK | `null` (opcionales, solo documentación) |
| `pg_alpha` | OK (pero **CRASH** si `freq_opcion=4` y es `null`) | `null` |
| `pg_beta` | OK (pero **CRASH** si `freq_opcion=4` y es `null`) | `null` |
| `beta_minimo/mas_probable/maximo/confianza` | OK (pero **CRASH** si `freq_opcion=5` y son `null`) | `null` |
| `beta_alpha` | OK (pero **CRASH** si `freq_opcion=5` y es `null` o ≤ 0) | `null` |
| `beta_beta` | OK (pero **CRASH** si `freq_opcion=5` y es `null` o ≤ 0) | `null` |
| `sev_freq_activado` | OK | `false` |
| `sev_freq_modelo` | OK | `"reincidencia"` |
| `sev_freq_tipo_escalamiento` | OK | `"lineal"` |
| `sev_freq_paso` | OK | `0.5` |
| `sev_freq_base` | OK | `1.5` |
| `sev_freq_factor_max` | OK | `5.0` |
| `sev_freq_tabla` | OK | `[]` |
| `sev_freq_alpha` | OK | `0.5` |
| `sev_freq_solo_aumento` | OK | `true` |
| `sev_freq_sistemico_factor_max` | OK | `3.0` |
| `vinculos` | OK | `[]` |
| `factores_ajuste` | OK | `[]` |

**REGLA DE ORO**: Incluir SIEMPRE las **claves** `id`, `nombre`, `sev_opcion`, `sev_minimo`, `sev_mas_probable`, `sev_maximo`, y `freq_opcion` en cada evento. Si alguna clave falta, **toda la importación falla**. Los valores de `sev_minimo/sev_mas_probable/sev_maximo` dependen del método:
- Con `sev_input_method: "min_mode_max"` (PERT/Uniforme/Normal): **DEBEN ser los valores monetarios reales > 0** (nunca 0, nunca null).
- Con `sev_input_method: "direct"` (LogNormal/Pareto/Normal): deben ser `null` (los parámetros van en `sev_params_direct`).

**Nota Poisson-Gamma**: Cuando `freq_opcion=4`, `pg_alpha` (> 1) y `pg_beta` (> 0) deben ser numéricos — **NUNCA `null`**. Calcularlos con la fórmula PERT si el usuario da min/mode/max. Ver sección Poisson-Gamma.

**Nota Beta**: Cuando `freq_opcion=5`, `beta_alpha` y `beta_beta` deben ser numéricos (> 0) o la frecuencia fallará (CRASH TOTAL). Ver sección Beta Frecuencia.

**Nota Poisson**: Cuando `freq_opcion=1`, `tasa` debe ser numérico y > 0 — **NUNCA `null` ni 0**. Si no se tiene dato, usar un fallback documentado (ej: 0.01) y marcar como estimado.

---

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
    "sev_limite_superior": null,
    
    "freq_opcion": 1,
    "freq_limite_superior": null,
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
- `sev_opcion = 1` (Normal) también soporta `"direct"` con parámetros `mean/std` o `mu/sigma`.
- **RESTRICCIÓN**: `sev_opcion = 3` (PERT) y `sev_opcion = 5` (Uniforme) **SOLO soportan `min_mode_max`**. Usar `"direct"` con estas distribuciones causará **CRASH TOTAL**.

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

#### Método Directo (2 opciones + parametrización canónica):

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

**REGLAS CRÍTICAS para LogNormal**:
- NUNCA dejar `sev_params_direct` vacío `{}` con `sev_input_method: "direct"`
- `sev_minimo`, `sev_mas_probable`, `sev_maximo` DEBEN ser `null`
- Elegir SOLO UNA de las opciones (Canónica, A o B)
- NO mezclar parámetros (ej: no usar `mean` con `sigma`)
- Para generación por IA: preferir siempre la parametrización canónica `s/scale/loc`

---

### 3. PERT/Beta (`sev_opcion: 3`)

> ⚠️ **SOLO admite método `min_mode_max`**. Si se usa `sev_input_method: "direct"` con `sev_minimo`/`sev_mas_probable`/`sev_maximo` en `null`, la importación fallará con **CRASH TOTAL** (`ValueError: Min/Mode/Max requeridos para PERT`).
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
- Para importación válida por IA: `sev_input_method` debe ser `"direct"`
- `sev_params_direct` debe incluir **exactamente** `c`, `scale`, `loc`
- `scale` NUNCA puede ser 0 o negativo (> 0 obligatorio)
- `loc` debe ser numérico (típicamente ≥ 0); determina el valor mínimo de la distribución
- `sev_minimo`, `sev_mas_probable`, `sev_maximo` DEBEN ser `null`
- Para riesgos operacionales, típicamente `c` está entre 0.1 y 0.4

---

### 5. Uniforme (`sev_opcion: 5`)

> ⚠️ **SOLO admite método `min_mode_max`**. Si se usa `sev_input_method: "direct"` con `sev_minimo`/`sev_maximo` en `null`, la importación fallará con **CRASH TOTAL** (`ValueError: Min/Max requeridos para Uniforme`).

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

> ⚠️ Si `freq_opcion=1` y `tasa` es `null` o ≤ 0, la importación falla completamente (CRASH TOTAL).

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

> ⚠️ Si `freq_opcion=2` o `freq_opcion=3` y `prob_exito` es `null` o está fuera de [0, 1], la importación falla completamente (CRASH TOTAL).

---

### 4. Poisson-Gamma (`freq_opcion: 4`)

Modela incertidumbre en la tasa de Poisson usando una distribución Gamma.

> ⚠️ **REGLA CRÍTICA**: `pg_alpha` y `pg_beta` son **SIEMPRE OBLIGATORIOS** para `freq_opcion=4`. **Nunca dejarlos en `null`** — si están null, la importación falla con CRASH TOTAL. El camino min/mode/max como fallback interno es frágil (usa optimización scipy que puede fallar silenciosamente). Siempre calcular y proveer `pg_alpha` y `pg_beta` explícitamente.

**Ejemplo con valores calculados desde min/mode/max del usuario:**
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
    "pg_alpha": 5.76,
    "pg_beta": 1.92
}
```

**Fórmula para calcular `pg_alpha` y `pg_beta` a partir de estimaciones del usuario:**
```
Dado: mínimo, más_probable, máximo (todos > 0, min < mode < max)

mean = (mínimo + 4 × más_probable + máximo) / 6
var  = ((máximo - mínimo) / 6)²

pg_alpha = mean² / var      (si resulta ≤ 1, usar 1.5 como mínimo)
pg_beta  = mean / var

Ejemplo: min=1, mode=3, max=8
  mean = (1 + 12 + 8) / 6 = 3.50
  var  = ((8 - 1) / 6)² = 1.36
  pg_alpha = 3.50² / 1.36 = 9.01
  pg_beta  = 3.50 / 1.36 = 2.57
```

**Ejemplo con parámetros directos (sin min/mode/max):**
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

**Validaciones ESTRICTAS**:
- `pg_alpha` **> 1** (shape, típicamente 2-20). NUNCA `null`.
- `pg_beta` **> 0** (rate, típicamente 0.5-10). NUNCA `null`.
- `tasa`, `num_eventos`, `prob_exito` deben ser `null`
- `pg_minimo/pg_mas_probable/pg_maximo/pg_confianza` son opcionales (para documentación/UI). Si se incluyen: `0 < min < mode < max` y `0 < confianza < 100`.

> ⚠️ **CRASH TOTAL**: Si `freq_opcion=4` y `pg_alpha` o `pg_beta` son `null` o inválidos, la importación falla completamente y no se carga ningún evento.

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
- Internamente Risk Lab los convierte a proporciones dividiendo por 100.

**Opción A: Calcular alpha/beta a partir de Min/Mode/Max**

El agente debe calcular `beta_alpha` y `beta_beta` antes de generar el JSON. Método simplificado:

```python
# Inputs: porcentajes del JSON
beta_minimo = 10      # 10%
beta_mas_probable = 20 # 20%
beta_maximo = 40      # 40%
beta_confianza = 90   # 90%

# Paso 1: Convertir a proporciones (0-1)
p_min = beta_minimo / 100       # 0.10
p_mode = beta_mas_probable / 100 # 0.20
p_max = beta_maximo / 100       # 0.40

# Paso 2: Estimar media (fórmula PERT)
media = (p_min + 4 * p_mode + p_max) / 6

# Paso 3: Estimar varianza
rango = p_max - p_min
confianza_prop = beta_confianza / 100  # 0.90
varianza = (rango / 6.0) ** 2 * (1.0 / confianza_prop)

# Paso 4: Calcular alpha y beta por método de momentos
temp = media * (1 - media) / varianza - 1
alpha = max(media * temp, 1.1)   # Asegurar > 1
beta = max((1 - media) * temp, 1.1)

# Resultado: usar alpha y beta en el JSON
# beta_alpha = round(alpha, 4)
# beta_beta = round(beta, 4)
```

- `beta_minimo`: Probabilidad mínima % (0 ≤ x < beta_mas_probable)
- `beta_mas_probable`: Probabilidad más probable %
- `beta_maximo`: Probabilidad máxima % (< 100)
- `beta_confianza`: % de confianza del rango (típicamente 90)
- Restricción: 0% ≤ minimo < mas_probable < maximo ≤ 100%
- **Además**: incluir `beta_alpha` y `beta_beta` calculados con el método anterior

**Validaciones ESTRICTAS Opción A**:
- 0 ≤ `beta_minimo` < `beta_mas_probable` < `beta_maximo` ≤ 100
- `beta_confianza` debe ser **estrictamente** entre 0 y 100 (ej: 80, 90, 95). No usar 0 ni 100.
- `beta_alpha` > 0 y `beta_beta` > 0 (el método de momentos anterior garantiza > 1)
- `tasa`, `num_eventos`, `prob_exito` deben ser `null`

**Opción B: Usar alpha/beta directamente (recomendado si no se tiene min/mode/max)**

Si el agente conoce directamente los parámetros alpha/beta, o prefiere evitar el cálculo, puede asignarlos directamente y derivar min/mode/max coherentes:

- `beta_alpha` y `beta_beta` > 0 (ambos > 1 recomendado para que exista moda)
- Moda de la distribución = `(alpha - 1) / (alpha + beta - 2)` (cuando alpha, beta > 1)
- Derivar: `beta_mas_probable` = moda × 100, y estimar min/max razonables alrededor

**IMPORTANTE**: aunque uses alpha/beta directos, igual debes incluir `beta_minimo`/`beta_mas_probable`/`beta_maximo`/`beta_confianza` como números (no `null`) para evitar errores en UI y durante simulación.

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

> ⚠️ **CRASH TOTAL**: Si `freq_opcion=5` y `beta_alpha` o `beta_beta` son `null` o ≤ 0, la importación falla completamente. Siempre incluir ambos con valores positivos.

---

## Límites Superiores (Caps de Frecuencia y Severidad)

Risk Lab permite definir un **límite superior** tanto para la frecuencia como para la severidad de cada evento. Estos límites actúan como caps que impiden que la simulación genere valores por encima del tope especificado.

### Campos JSON

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `sev_limite_superior` | float/null | `null` | Límite máximo de severidad por ocurrencia (en moneda). `null` = sin límite |
| `freq_limite_superior` | integer/null | `null` | Máximo de ocurrencias por año. `null` = sin límite |

### Comportamiento en Simulación (Rejection Sampling)

Cuando se define un límite superior, Risk Lab **no** recorta los valores al tope (lo cual generaría un pico artificial en el límite). En su lugar, utiliza **rejection sampling**: los valores que superan el límite se re-muestrean de la distribución original hasta obtener un valor dentro del rango permitido. Esto preserva la forma natural de la distribución truncada.

- Se realizan hasta 100 intentos de re-muestreo por valor
- Si después de 100 intentos aún hay valores por encima del límite, esos valores se fijan al límite como fallback
- El resultado es una distribución que mantiene su forma natural hasta el punto de corte, sin picos artificiales

### Frecuencia: `freq_limite_superior`

- **Solo aplica** a distribuciones que pueden generar más de 1 ocurrencia: **Poisson** (`freq_opcion=1`), **Binomial** (`freq_opcion=2`) y **Poisson-Gamma** (`freq_opcion=4`)
- **No aplica** a Bernoulli (`freq_opcion=3`) ni Beta (`freq_opcion=5`) porque estas distribuciones solo generan 0 o 1 ocurrencias
- El valor debe ser un **entero positivo** o `null` (sin límite)
- Ejemplo: `"freq_limite_superior": 10` → máximo 10 ocurrencias por año

### Severidad: `sev_limite_superior`

- Aplica a **todas** las distribuciones de severidad (Normal, LogNormal, PERT, GPD, Uniforme)
- El valor debe ser un **número positivo** (en moneda) o `null` (sin límite)
- Se aplica a cada ocurrencia individual (no al total anual)
- Ejemplo: `"sev_limite_superior": 500000` → cada ocurrencia tiene un impacto máximo de $500K

### Cuándo usar límites superiores

- **Frecuencia**: cuando existe un tope físico o contractual de ocurrencias (ej: "máximo 12 incidentes al año porque hay 12 ventanas de mantenimiento")
- **Severidad**: cuando existe un tope contractual, regulatorio o físico al impacto por evento (ej: "la multa máxima es $500K por infracción")
- **No usar** como sustituto de elegir la distribución correcta — si la distribución genera valores irrealistas, es mejor ajustar sus parámetros
- **Precaución**: si el límite es muy restrictivo respecto a la distribución (ej: cap=2 con Poisson λ=8), la mayoría de las muestras serán re-muestreadas y el fallback al cap puede activarse, generando un pequeño pico residual

### Ejemplo JSON

```json
{
    "sev_limite_superior": 500000,
    "freq_limite_superior": 10
}
```

### Validaciones

| Campo | Restricción |
|-------|-------------|
| `sev_limite_superior` | `null` (sin límite) o número > 0 |
| `freq_limite_superior` | `null` (sin límite) o entero > 0 |

### Cuándo NO incluir estos campos

- Si el evento no necesita caps, usar `null` o no incluir los campos (el default es `null` = sin límite)
- Archivos JSON creados antes de esta funcionalidad son **100% backward compatible**: la ausencia de estos campos equivale a sin límite

---

## Vínculos (Dependencias entre Eventos)

Los vínculos permiten que la ocurrencia de un evento dependa de otros, con probabilidad de activación, factor de severidad condicional y umbral de severidad del padre configurables:

```json
{
    "vinculos": [
        {
            "id_padre": "uuid-del-evento-padre",
            "tipo": "AND",
            "probabilidad": 100,
            "factor_severidad": 1.5,
            "umbral_severidad": 50000
        },
        {
            "id_padre": "uuid-otro-evento-padre",
            "tipo": "OR",
            "probabilidad": 75,
            "factor_severidad": 1.0,
            "umbral_severidad": 0
        }
    ]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_padre` | string | UUID del evento del que depende |
| `tipo` | string | Tipo de dependencia: `"AND"`, `"OR"` o `"EXCLUYE"` |
| `probabilidad` | integer | Probabilidad de activación del vínculo (1-100). Opcional, default: 100 |
| `factor_severidad` | float | Multiplicador de severidad condicional (0.10-5.00). Opcional, default: 1.0 |
| `umbral_severidad` | integer | Pérdida mínima del padre para considerar que "ocurrió" ($, ≥0). Opcional, default: 0 |

**Validaciones ESTRICTAS**:
- `tipo` debe ser exactamente `"AND"`, `"OR"` o `"EXCLUYE"` (en mayúsculas)
- No se permiten valores como `"and"`, `"Or"`, `"Y"`, `"O"`, `"excluye"`
- `probabilidad` debe ser un entero entre 1 y 100. Si se omite, se asume 100 (backward compatible)
- Valores fuera de rango se normalizan a `max(1, min(100, valor))`
- `factor_severidad` debe ser un float entre 0.10 y 5.00. Si se omite, se asume 1.0 (neutral, backward compatible)
- Valores fuera de rango se normalizan a `max(0.10, min(5.0, valor))`
- `umbral_severidad` debe ser un entero ≥ 0. Si se omite, se asume 0 (sin umbral, backward compatible)

### Lógica de Dependencias:
- **AND**: El evento hijo solo puede ocurrir si TODOS los padres AND ocurrieron Y sus vínculos se activaron (según su probabilidad)
- **OR**: El evento hijo puede ocurrir si AL MENOS UN padre OR ocurrió Y su vínculo se activó
- **EXCLUYE**: El evento hijo solo puede ocurrir si los padres EXCLUYE NO ocurrieron, o si ocurrieron pero sus vínculos no se activaron

### Probabilidad de Activación:
- 100% = comportamiento determinístico (el vínculo siempre se activa cuando la condición del padre se cumple)
- <100% = el vínculo se activa probabilísticamente en cada simulación
- La probabilidad NO modifica la distribución de frecuencia del hijo; actúa como compuerta sobre si se samplea o no

### Factor de Severidad Condicional:
- 1.0 = neutral, no modifica la severidad del evento hijo (default)
- >1.0 = amplifica la severidad del evento hijo cuando el vínculo está activo (ej: 1.5 = +50%)
- <1.0 = atenúa la severidad del evento hijo (ej: 0.5 = -50%)
- **AND**: los factores de todos los vínculos AND activos se **multiplican** entre sí
- **OR**: se toma el **máximo** de los factores de los vínculos OR activos
- **EXCLUYE**: no aporta factor de severidad
- El factor combinado se aplica a las pérdidas individuales ANTES de los factores de control y seguros
- Solo se aplica en las simulaciones donde `condicion_final` es `True`

### Umbral de Severidad del Padre:
- 0 = sin umbral, basta con que el padre tenga frecuencia > 0 (default, backward compatible)
- >0 = el padre se considera "ocurrido" solo si su pérdida total en esa simulación ≥ umbral
- Solo aplica a vínculos de tipo AND y OR (EXCLUYE no usa umbral en la UI)
- Permite modelar dependencias condicionadas a la magnitud del impacto del padre

### Importante:
- No crear dependencias cíclicas (A → B → A)
- Los IDs de padre deben existir en la lista de eventos
- Un evento sin vínculos es independiente
- Archivos JSON sin campos `probabilidad`, `factor_severidad` o `umbral_severidad` son backward compatible (se asumen defaults)

---

## Factores de Ajuste (Controles/Factores de Riesgo)

Los factores modifican la frecuencia y/o severidad de un evento. Hay dos modelos:

> ⚠️ **CAMPO OBLIGATORIO EN TODOS LOS FACTORES**: `nombre` debe estar presente y ser un string no vacío. Risk Lab agrega defaults para casi todos los campos de un factor, pero **NO agrega `nombre`**. Si falta, la UI puede mostrar celdas vacías o generar errores al visualizar.

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
| `nombre` | string | **OBLIGATORIO.** Nombre descriptivo del factor (no se auto-genera) |
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
| `reduccion_efectiva` | integer | % reducción de **frecuencia** si funciona (-100 a +99). Positivo reduce |
| `reduccion_fallo` | integer | % reducción de **frecuencia** si falla (-100 a +99) |
| `reduccion_severidad_efectiva` | integer | % reducción de **severidad** si funciona (-100 a +99) |
| `reduccion_severidad_fallo` | integer | % reducción de **severidad** si falla (-100 a +99) |

**Fórmula estocástico**: `factor = 1 - (reduccion/100)`
- reduccion = 80 → factor = 0.20 → reduce 80%
- reduccion = -20 → factor = 1.20 → aumenta 20%

**Comportamiento**: En cada iteración, el sistema genera **un único** número aleatorio por factor. Si es menor que `confiabilidad/100`, el control "funciona" y aplica `reduccion_efectiva` (frecuencia) y `reduccion_severidad_efectiva` (severidad). Si no, el control "falla" y aplica `reduccion_fallo` (frecuencia) y `reduccion_severidad_fallo` (severidad). Es decir, **el mismo sorteo** determina ambos efectos simultáneamente.

**Nota sobre campos estáticos en factores estocásticos**: Cuando `tipo_modelo` es `"estocastico"`, los campos estáticos (`afecta_frecuencia`, `impacto_porcentual`, `afecta_severidad`, `impacto_severidad_pct`) son **ignorados en simulación**. Risk Lab los agrega automáticamente con valores neutros si no están presentes. Por lo tanto, **NO es necesario incluirlos** al generar un factor estocástico.

---

### Modelo Seguro/Transferencia de Riesgo

> ⚠️ **REGLA CRÍTICA**: Los seguros se modelan **EXCLUSIVAMENTE** como `factores_ajuste` con `tipo_severidad: "seguro"` dentro de los eventos que cubren. **NUNCA crear un evento de riesgo independiente para representar un seguro**. Un evento con severidad 0 o `sev_params_direct: {"mean": 0, "std": 0}` es matemáticamente inválido (Normal con std=0 crashea) y conceptualmente incorrecto. Si el usuario menciona un seguro, agregarlo como factor dentro del evento correspondiente.

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
            "afecta_severidad": true,
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
| `afecta_severidad` | boolean | Sí | **DEBE ser true** para seguros (si es false, el seguro se ignora en simulación) |
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
    "afecta_severidad": true,
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
    "afecta_severidad": true,
    "impacto_severidad_pct": 0
}
```

#### Orden de Aplicación en Simulación:

1. Generar pérdidas individuales (severidad bruta)
2. **Aplicar escalamiento de severidad por frecuencia** (si `sev_freq_activado` = `true`)
3. **Aplicar factor de severidad de vínculos** (si el evento tiene vínculos con `factor_severidad` ≠ 1.0)
4. Aplicar factores de mitigación (controles estáticos/estocásticos)
5. **Aplicar seguros POR OCURRENCIA** a cada pérdida mitigada
6. Agregar pérdidas por simulación (suma anual)
7. **Aplicar seguros AGREGADOS** al total anual

**IMPORTANTE**: El escalamiento de severidad por frecuencia se aplica ANTES de los vínculos, controles y seguros. El factor de severidad de vínculos se aplica ANTES de los controles y seguros. Los seguros cubren la pérdida DESPUÉS de la mitigación de controles.

---

## Escalamiento de Severidad por Frecuencia

Esta funcionalidad permite que la severidad de las pérdidas se escale automáticamente en función de cuántas veces ocurre el evento en cada simulación. Modela el concepto de que eventos repetidos tienden a ser progresivamente peores (reincidencia) o que años con frecuencia anómala correlacionan con severidad anómala (impacto sistémico).

El escalamiento se aplica **después** de generar las pérdidas individuales y **antes** de aplicar factores de control, seguros y vínculos.

### Campos JSON

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `sev_freq_activado` | boolean | `false` | Activa o desactiva el escalamiento. Si `false`, los demás campos se ignoran |
| `sev_freq_modelo` | string | `"reincidencia"` | Modelo de escalamiento: `"reincidencia"` o `"sistemico"` |
| `sev_freq_tipo_escalamiento` | string | `"lineal"` | Solo para modelo reincidencia: `"lineal"`, `"exponencial"` o `"tabla"` |
| `sev_freq_paso` | float | `0.5` | Solo para tipo `"lineal"`: incremento del multiplicador por cada ocurrencia adicional |
| `sev_freq_base` | float | `1.5` | Solo para tipo `"exponencial"`: base de la exponenciación |
| `sev_freq_factor_max` | float | `5.0` | Multiplicador máximo (cap) para modelo reincidencia |
| `sev_freq_tabla` | array | `[]` | Solo para tipo `"tabla"`: lista de rangos con multiplicadores (ver estructura abajo) |
| `sev_freq_alpha` | float | `0.5` | Solo para modelo `"sistemico"`: sensibilidad del factor al z-score de frecuencia |
| `sev_freq_solo_aumento` | boolean | `true` | Solo para modelo `"sistemico"`: si `true`, z-scores negativos se truncan a 0 (solo aumenta, nunca reduce) |
| `sev_freq_sistemico_factor_max` | float | `3.0` | Solo para modelo `"sistemico"`: multiplicador máximo |

### Restricción de distribución de frecuencia

El escalamiento **solo tiene efecto** cuando la distribución de frecuencia permite más de una ocurrencia por simulación. Con **Bernoulli** (`freq_opcion=3`), la frecuencia es siempre 0 o 1, por lo que el modelo reincidencia no produce ningún efecto (la primera ocurrencia siempre tiene multiplicador 1.0). El modelo sistémico sí puede tener efecto con Bernoulli (escala por z-score de la frecuencia en el conjunto de simulaciones).

### Modelo Reincidencia (`sev_freq_modelo: "reincidencia"`)

Cada ocurrencia dentro de una misma simulación recibe un multiplicador creciente según su índice ordinal (1ª, 2ª, 3ª...).

#### Tipo Lineal (`sev_freq_tipo_escalamiento: "lineal"`)

**Fórmula**: `multiplicador(n) = min(1 + paso × (n - 1), factor_max)`

Donde `n` = índice ordinal de la ocurrencia (1, 2, 3...).

**Ejemplo** con `paso=0.5`, `factor_max=5.0` y frecuencia=5:
- Ocurrencia 1: ×1.0
- Ocurrencia 2: ×1.5
- Ocurrencia 3: ×2.0
- Ocurrencia 4: ×2.5
- Ocurrencia 5: ×3.0

```json
{
    "sev_freq_activado": true,
    "sev_freq_modelo": "reincidencia",
    "sev_freq_tipo_escalamiento": "lineal",
    "sev_freq_paso": 0.5,
    "sev_freq_factor_max": 5.0
}
```

#### Tipo Exponencial (`sev_freq_tipo_escalamiento: "exponencial"`)

**Fórmula**: `multiplicador(n) = min(base^(n-1), factor_max)`

**Ejemplo** con `base=1.5`, `factor_max=5.0` y frecuencia=5:
- Ocurrencia 1: ×1.0 (1.5⁰)
- Ocurrencia 2: ×1.5 (1.5¹)
- Ocurrencia 3: ×2.25 (1.5²)
- Ocurrencia 4: ×3.375 (1.5³)
- Ocurrencia 5: ×5.0 (cap)

```json
{
    "sev_freq_activado": true,
    "sev_freq_modelo": "reincidencia",
    "sev_freq_tipo_escalamiento": "exponencial",
    "sev_freq_base": 1.5,
    "sev_freq_factor_max": 5.0
}
```

#### Tipo Tabla (`sev_freq_tipo_escalamiento: "tabla"`)

Permite definir multiplicadores arbitrarios por rango de ocurrencia.

**Estructura de cada fila de `sev_freq_tabla`**:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `desde` | integer | Índice de ocurrencia inicial del rango (≥ 1) |
| `hasta` | integer/null | Índice de ocurrencia final del rango (`null` = sin límite superior) |
| `multiplicador` | float | Multiplicador a aplicar en este rango (> 0) |

**Ejemplo**: las primeras 2 ocurrencias normales, a partir de la 3ª se triplican:
```json
{
    "sev_freq_activado": true,
    "sev_freq_modelo": "reincidencia",
    "sev_freq_tipo_escalamiento": "tabla",
    "sev_freq_tabla": [
        {"desde": 1, "hasta": 2, "multiplicador": 1.0},
        {"desde": 3, "hasta": null, "multiplicador": 3.0}
    ]
}
```

**Reglas de la tabla**:
- Los rangos se evalúan en orden; ocurrencias que no caen en ningún rango reciben multiplicador 1.0
- `hasta: null` significa "desde ese índice en adelante"
- En JSON, `null` se serializa como `null` (no como string `"null"`)
- Evitar solapamiento de rangos (el último rango que aplica gana)

### Modelo Sistémico (`sev_freq_modelo: "sistemico"`)

En vez de escalar por ocurrencia individual, el modelo sistémico escala **todas** las pérdidas de una simulación por un factor basado en qué tan anómala es la frecuencia total de esa simulación respecto a su distribución.

**Fórmula**:
```
z = (freq_simulacion - freq_media) / freq_std
si solo_aumento: z = max(z, 0)
factor = clip(1 + alpha × z, 1/factor_max, factor_max)
```

- `alpha`: sensibilidad. Con alpha=0.5 y z=2 (frecuencia 2 desviaciones por encima de la media), el factor es 2.0
- `solo_aumento=true`: solo simulaciones con frecuencia por encima de la media amplifican la severidad; las de baja frecuencia quedan intactas
- `solo_aumento=false`: bidireccional — frecuencia baja reduce severidad, frecuencia alta la aumenta

```json
{
    "sev_freq_activado": true,
    "sev_freq_modelo": "sistemico",
    "sev_freq_alpha": 0.5,
    "sev_freq_solo_aumento": true,
    "sev_freq_sistemico_factor_max": 3.0
}
```

### Validaciones

| Campo | Restricción |
|-------|-------------|
| `sev_freq_modelo` | `"reincidencia"` o `"sistemico"` |
| `sev_freq_tipo_escalamiento` | `"lineal"`, `"exponencial"` o `"tabla"` |
| `sev_freq_paso` | > 0 (típico: 0.1 - 2.0) |
| `sev_freq_base` | > 1.0 (típico: 1.2 - 3.0) |
| `sev_freq_factor_max` | > 1.0 (típico: 2.0 - 10.0) |
| `sev_freq_alpha` | > 0 (típico: 0.1 - 1.0) |
| `sev_freq_sistemico_factor_max` | > 1.0 (típico: 2.0 - 5.0) |
| `sev_freq_tabla` | Array de objetos con `desde` (int ≥ 1), `hasta` (int/null), `multiplicador` (float > 0) |

### Cuándo NO incluir estos campos

- Si el evento no necesita escalamiento, basta con `"sev_freq_activado": false` (o no incluir ningún campo `sev_freq_*` — los defaults desactivan la funcionalidad)
- Archivos JSON creados antes de esta funcionalidad son **100% backward compatible**: la ausencia de campos `sev_freq_*` equivale a `sev_freq_activado: false`

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
| `eventos_riesgo` | array | Lista de eventos **completos** (misma estructura que eventos principales, con TODOS los campos de sección B) |

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
            "sev_limite_superior": null,
            
            "freq_opcion": 1,
            "freq_limite_superior": null,
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
            
            "sev_freq_activado": true,
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
            "factores_ajuste": [
                {
                    "nombre": "EDR Avanzado",
                    "activo": true,
                    "tipo_modelo": "estocastico",
                    "confiabilidad": 85,
                    "reduccion_efectiva": 70,
                    "reduccion_fallo": 10,
                    "reduccion_severidad_efectiva": 40,
                    "reduccion_severidad_fallo": 0
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
            "sev_limite_superior": null,
            
            "freq_opcion": 3,
            "freq_limite_superior": null,
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
            
            "vinculos": [
                {
                    "id_padre": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "tipo": "AND",
                    "probabilidad": 100,
                    "factor_severidad": 1.5,
                    "umbral_severidad": 50000
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

### ❌ ERROR #7: Poisson-Gamma con pg_alpha/pg_beta null

**INCORRECTO** (pg_alpha y pg_beta en null — causa CRASH TOTAL):
```jsonc
{
    "freq_opcion": 4,
    "pg_minimo": 1,
    "pg_mas_probable": 3,
    "pg_maximo": 8,
    "pg_confianza": 90,
    "pg_alpha": null,  // ❌ NUNCA null para freq_opcion=4
    "pg_beta": null     // ❌ NUNCA null para freq_opcion=4
}
```

**CORRECTO (min/mode/max + alpha/beta CALCULADOS con fórmula PERT)**:
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
    "pg_alpha": 9.01,
    "pg_beta": 2.57
}
```
Los campos min/mode/max/confianza son opcionales (para documentación/UI). Lo que importa es que `pg_alpha` y `pg_beta` estén siempre presentes con valores numéricos válidos.

**CORRECTO (solo alpha/beta, sin min/mode/max)**:
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
    "afecta_severidad": true,  // ✓ DEBE ser true para seguros
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
- [ ] Si `sev_opcion` = 3 (PERT) o 5 (Uniforme): `sev_input_method` **DEBE** ser `"min_mode_max"` (no soportan `"direct"`)
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
- [ ] Bernoulli (3): `0 ≤ prob_exito ≤ 1`, resto = `null`. Recomendación: evitar 0.0 y 1.0 exactos si hay factores estocásticos
- [ ] Poisson-Gamma (4):
  - [ ] `pg_alpha` > 1 y `pg_beta` > 0 **SIEMPRE** (nunca `null`). Calcularlos con fórmula PERT si se parte de min/mode/max.
  - [ ] Si se incluyen min/mode/max: `0 < min < mode < max`, `0 < confianza < 100` (opcionales, para documentación)
- [ ] Beta (5):
  - [ ] Si min/mode/max: `0 ≤ min < mode < max ≤ 100` y **además** `beta_alpha`/`beta_beta` > 0
  - [ ] Si alpha/beta: ambos > 0, y `beta_minimo`/`beta_mas_probable`/`beta_maximo`/`beta_confianza` deben ser numéricos (no `null`) y coherentes
  - [ ] Valores son PORCENTAJES (0-100), no decimales (0-1)

#### ☑️ Factores Estáticos:
- [ ] `tipo_modelo` = "estatico"
- [ ] `impacto_porcentual` ≥ -99 (mínimo -99, sin límite superior; la normalización solo clipea el mínimo)
- [ ] `impacto_severidad_pct` ≥ -99 (misma regla)
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
- [ ] `afecta_severidad` = **`true`** (OBLIGATORIO para que el seguro funcione), `impacto_severidad_pct` = 0

#### ☑️ Escalamiento de Severidad por Frecuencia (si se usa):
- [ ] `sev_freq_activado` es `true` o `false`
- [ ] `sev_freq_modelo` es `"reincidencia"` o `"sistemico"`
- [ ] Si reincidencia lineal: `sev_freq_paso` > 0
- [ ] Si reincidencia exponencial: `sev_freq_base` > 1.0
- [ ] Si reincidencia tabla: `sev_freq_tabla` es array con objetos `{desde, hasta, multiplicador}`
- [ ] `sev_freq_factor_max` > 1.0 (para reincidencia)
- [ ] Si sistémico: `sev_freq_alpha` > 0, `sev_freq_sistemico_factor_max` > 1.0
- [ ] `sev_freq_tabla[i].hasta` puede ser `null` (sin límite) o entero
- [ ] Si `sev_freq_activado` = `false`, los demás campos se ignoran (no necesitan validación)

#### ☑️ Límites Superiores (si se usan):
- [ ] `sev_limite_superior` es `null` (sin límite) o número > 0
- [ ] `freq_limite_superior` es `null` (sin límite) o entero > 0
- [ ] Si `freq_limite_superior` se usa con Bernoulli o Beta (`freq_opcion` 3 o 5), no tiene efecto (estas distribuciones ya generan 0 o 1)
- [ ] Si ambos son `null`, los campos pueden omitirse (backward compatible)

#### ☑️ Vínculos:
- [ ] Todos los `id_padre` existen en la lista de eventos
- [ ] `tipo` es exactamente `"AND"`, `"OR"` o `"EXCLUYE"` (mayúsculas). **Nota**: la importación NO valida este valor; un valor incorrecto (ej. `"and"`) pasaría la importación pero fallaría en simulación
- [ ] `probabilidad` entre 1 y 100 (si se incluye). Valores fuera de rango se normalizan automáticamente
- [ ] `factor_severidad` entre 0.10 y 5.00 (si se incluye). Valores fuera de rango se normalizan automáticamente. Para `EXCLUYE`, debe ser 1.0
- [ ] `umbral_severidad` ≥ 0 (si se incluye)
- [ ] No hay ciclos en el grafo de dependencias (DAG)

#### ☑️ Factores de Ajuste:
- [ ] Cada factor tiene `nombre` (string no vacío) — no se auto-genera
- [ ] `tipo_modelo` es `"estatico"` o `"estocastico"` (los demás campos se normalizan automáticamente)
- [ ] Si es seguro: `tipo_severidad` = `"seguro"`, `seguro_tipo_deducible` válido

#### ☑️ General:
- [ ] Todos los UUIDs son únicos y tienen formato válido
- [ ] Nombres de eventos no vacíos (máx 50 caracteres)
- [ ] Nombres sin saltos de línea, tabs ni caracteres de control
- [ ] Todos los campos de CRASH (ver sección I) presentes — incluso si son `null`
- [ ] Parámetros de frecuencia completos y válidos (errores = CRASH TOTAL, ver sección H)
- [ ] JSON sintácticamente válido (sin comentarios, sin comas finales, comillas dobles)

---

## Notas sobre campos que NO debe generar el agente

- **`simulation_results`**: Campo opcional que Risk Lab usa internamente para guardar resultados. **NO incluir** al generar JSON.
- **Campos con prefijo `_`** (ej. `_usa_estocastico`, `_factores_vector`): Son flags temporales internos. **NO incluir** al generar JSON.
- **`dist_severidad`, `dist_frecuencia`**: Objetos internos no serializables. **NO incluir**.
- **`eventos_padres`**: Formato legacy de vínculos. **NUNCA usar**. Siempre usar `vinculos`.

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
5. **NUNCA mezclar opciones de parámetros** (ej: `mean` con `sigma` en LogNormal). LogNormal tiene 3 opciones: Canónica (`s/scale/loc`), A (`mean/std/loc`), B (`mu/sigma/loc`)
6. **SIEMPRE verificar orden**: `minimo` < `mas_probable` < `maximo`
7. **NUNCA usar `sev_input_method: "direct"` con PERT (`sev_opcion=3`) o Uniforme (`sev_opcion=5`)**:
   - Estas distribuciones SOLO soportan `"min_mode_max"`. Usar `"direct"` causa **CRASH TOTAL**.
8. **Reglas por distribución de frecuencia** (errores = CRASH TOTAL):
   - Poisson (`freq_opcion=1`): `tasa` > 0. Si el evento debe estar inactivo, usar `"activo": false` en vez de `tasa: 0`.
   - Binomial (`freq_opcion=2`): `num_eventos` > 0 (entero), `0 ≤ prob_exito ≤ 1`.
   - Bernoulli (`freq_opcion=3`): `0 ≤ prob_exito ≤ 1`. Evitar 0.0 y 1.0 exactos si el evento tiene factores estocásticos (los ajustes por log-odds fallan en extremos; usar 0.001 o 0.999).
   - Beta (`freq_opcion=5`): `beta_alpha` y `beta_beta` obligatorios (> 0). Además, `beta_minimo`/`beta_mas_probable`/`beta_maximo`/`beta_confianza` deben ser numéricos (no `null`), en porcentajes (0-100). Si el usuario no provee estos valores, pedirlos en vez de inventarlos.
9. **NUNCA dejar claves duplicadas** en el JSON; siempre generar objetos sin claves repetidas.

### 📊 Tipos de Datos y Formatos

1. **Números**: Siempre numéricos, NUNCA strings
   - Correcto: `"tasa": 2.5`
   - Incorrecto: `"tasa": "2.5"`
   - Incorrecto: `"prob_exito": "0,25"` (en JSON los decimales usan punto, no coma)
   - Un string numérico como `"2.5"` podría no fallar en algunos casos, pero **no es confiable**. Usar siempre tipos nativos JSON.
   - **Truncamiento silencioso**: `num_eventos: 10.5` se trunca a `10` sin advertencia. Usar siempre enteros para campos enteros.
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

## Plantillas Mínimas

### Plantilla A: PERT + Poisson (la más simple, para min/mode/max)

```json
{
    "num_simulaciones": 10000,
    "eventos_riesgo": [
        {
            "id": "GENERAR-UUID-AQUI",
            "nombre": "Nombre del Evento",
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

### Plantilla B: LogNormal + Poisson (para parámetros directos)

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
    "afecta_severidad": true,
    "impacto_severidad_pct": 0
}
```

---

## Resumen de Tipos de Controles

| Tipo | `tipo_modelo` | `tipo_severidad` | Afecta | Uso |
|------|---------------|------------------|--------|-----|
| **Estático** | "estatico" | no incluir | Frecuencia/Severidad | Controles fijos |
| **Estocástico** | "estocastico" | no incluir | Frecuencia/Severidad | Controles con incertidumbre |
| **Seguro** | "estatico" | "seguro" | Solo Severidad | Pólizas de seguro |

---

