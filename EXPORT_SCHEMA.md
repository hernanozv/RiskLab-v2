# Especificación del Formato `Exportar para Análisis (IA)` — Risk Lab

**Versión del schema:** `1.0`
**Extensión:** `.risklab.json` (o `.risklab.json.gz` si está comprimido)
**Idioma de descripciones:** Español (siempre)

Este documento describe el formato y contenido del archivo generado por
`Archivo → Exportar para Análisis (IA)`. El archivo está diseñado para que
un agente IA externo (Claude, GPT, etc.) pueda interpretar los resultados
de una simulación Monte Carlo de Risk Lab sin necesitar contexto adicional.

A diferencia del export PDF, este formato:
- Es **machine-readable** (JSON nativo).
- Incluye **TODA** la configuración de entrada y resultados de salida.
- Tiene **glosario embebido** y descripciones auto-explicativas.
- Pre-computa métricas, percentiles, contribuciones y resúmenes.

---

## Estructura raíz

```
{
  "$schema_version": "1.0",
  "$schema_url": "...",
  "$generated_at": "2026-05-01T...Z",
  "$generator": { ... },
  "metadata": { ... },
  "ai_agent_briefing": { ... },
  "configuration": { ... },
  "execution_metadata": { ... },
  "input_events": [ ... ],
  "input_scenarios": [ ... ],
  "results": { ... },
  "executive_summary": { ... },
  "text_snapshot": { ... },
  "schema_documentation": { ... },
  "input_events_omitidos": [ ... ],
  "input_scenarios_omitidos": [ ... ]
}
```

`input_events_omitidos`/`input_scenarios_omitidos` son campos
**condicionales**: solo aparecen en la raíz si al menos un evento o
escenario del archivo original falló al decodificarse para el export
(cada entrada indica el nombre/id afectado y el motivo). Si todos los
eventos/escenarios se exportaron correctamente, estas claves están
ausentes.

---

## Secciones principales

### 1. Metadatos de versión (`$schema_version`, `$generated_at`, `$generator`)

Identifican la versión del schema y la herramienta. Útil para que el agente
sepa qué espera del formato.

```json
{
  "$schema_version": "1.0",
  "$generated_at": "2026-05-01T22:00:00Z",
  "$generator": {
    "tool": "Risk Lab",
    "version": "1.10.0",
    "metodologia": "Monte Carlo - Loss Distribution Approach (LDA)"
  }
}
```

### 2. `metadata`

```json
{
  "moneda": "USD",
  "unidad_temporal": "año",
  "idioma_descripciones": "es"
}
```

### 3. `ai_agent_briefing`

**Sección clave**: explicación auto-contenida para que el agente entienda
qué es el archivo, cómo se generaron los datos y cómo interpretarlos.

Subcampos:
- `que_es_este_archivo`: descripción general del export.
- `como_se_generaron_los_datos`: metodología Monte Carlo paso a paso.
- `como_interpretar_resultados`: lista de reglas de interpretación.
- `glosario_metricas_clave`: VaR, OpVaR, Modo, Asimetría, Curtosis, etc.
- `preguntas_que_un_agente_puede_responder`: ejemplos de queries soportadas.

### 4. `configuration`

Configuración usada en la corrida.

```json
{
  "num_simulaciones": 10000,
  "moneda": "USD",
  "current_scenario_name": null,
  "execution_source": "main"
}
```

`execution_source` puede ser `"main"` o `"scenario"`.

### 5. `execution_metadata`

Información del entorno de ejecución y orden de procesamiento.

```json
{
  "executed_at": "2026-05-01T22:00:00Z",
  "engine": {
    "rng": "PCG64 (numpy.random.default_rng)",
    "scipy_version": "1.17.1",
    "numpy_version": "2.4.4"
  },
  "engine_limits": {
    "max_eventos_por_evento_por_chunk": 500000000,
    "descripcion": "Limite absoluto del motor: cantidad maxima de ocurrencias individuales generadas por evento dentro de un chunk de simulacion. Si la suma de frecuencias generadas excede este limite, el motor reescala las frecuencias multiplicativamente, lo que preserva el CV pero SUBESTIMA la media de perdidas. Si 'eventos_con_cap_aplicado' no esta vacio, los resultados estan distorsionados.",
    "eventos_con_cap_aplicado": []
  },
  "active_events_count": 5,
  "total_events_count": 7,
  "topological_order": [
    {"position": 1, "event_id": "...", "event_name": "..."}
  ]
}
```

`engine_limits.eventos_con_cap_aplicado` está vacío en la corrida normal;
si algún evento excedió el límite interno del motor, cada entrada trae
`event_id`, `event_name`, `factor_reescalado`,
`suma_frecuencias_original`/`_capeada` y
`media_por_simulacion_original`/`_capeada`.

### 6. `input_events`

Lista de eventos con todas sus configuraciones decodificadas a formato legible.

Cada evento contiene:
- `id`, `nombre`, `activo`
- `frecuencia`: distribución (string + freq_opcion + parámetros + descripción)
- `severidad`: distribución (string + sev_opcion + parámetros + descripción)
- `escalamiento_severidad_por_frecuencia`: configuración con explicación
- `factores_ajuste`: lista de factores con explicación de cada uno
- `vinculos`: lista de vínculos con AND/OR/EXCLUYE + nombre del padre

Ver sección "Eventos en detalle" más abajo.

### 7. `input_scenarios`

Lista de escenarios alternativos. Mismo formato que `input_events` pero anidado por escenario.

### 8. `results`

Sección principal con todos los resultados. Ver "Bloque results" abajo.

### 9. `executive_summary`

Resumen ejecutivo pre-procesado.

```json
{
  "headline": "Pérdida agregada media de $X con VaR 99% de $Y...",
  "key_findings": [
    "Pérdida media esperada: $X anuales",
    "Con 99% de confianza, las pérdidas no superarán $Y...",
    ...
  ],
  "concentracion_riesgo": {
    "top_3_pct": 78.0,
    "concentracion": "Alta",
    "evento_principal": "Fraude interno"
  }
}
```

### 10. `text_snapshot`

Reporte completo en lenguaje natural (mismo texto que muestra la app en el
panel de resultados). Útil para que el agente "lea" el reporte.

```json
{
  "_descripcion": "Reporte completo en lenguaje natural...",
  "content": "Resumen Ejecutivo de Resultados...\n..."
}
```

### 11. `schema_documentation`

Mini-schema embebido con descripciones de los campos clave para que el
agente entienda los tipos y valores válidos.

---

## Eventos en detalle (`input_events[]`)

Cada evento se exporta con descripciones humanas (en español) además de
los códigos internos.

### Frecuencia

```json
"frecuencia": {
  "distribucion": "Poisson",
  "freq_opcion": 1,
  "freq_limite_superior": null,
  "descripcion": "Distribución Poisson: cantidad de eventos por año donde la tasa media λ es fija...",
  "parametros": { "tasa": 5.0 }
}
```

| `freq_opcion` | Distribución (`distribucion`) | Parámetros relevantes |
|---|---|---|
| 1 | Poisson | `tasa` (λ) |
| 2 | Binomial | `num_eventos` (n), `prob_exito` (p) |
| 3 | Bernoulli | `prob_exito` (p) |
| 4 | Poisson-Gamma (Binomial Negativa) | `pg_alpha`, `pg_beta`, `pg_minimo`, `pg_mas_probable`, `pg_maximo` |
| 5 | Beta | `beta_alpha`, `beta_beta`, `beta_minimo`, `beta_mas_probable`, `beta_maximo` |

### Severidad

```json
"severidad": {
  "distribucion": "LogNormal",
  "sev_opcion": 2,
  "sev_input_method": "direct",
  "sev_minimo": null,
  "sev_mas_probable": null,
  "sev_maximo": null,
  "sev_params_direct": { "s": 1.23, "scale": 50000, "loc": 0 },
  "sev_limite_superior": null,
  "descripcion": "Distribución Log-Normal: ln(severidad) ~ Normal..."
}
```

| `sev_opcion` | Distribución |
|---|---|
| 1 | Normal (truncada en 0) |
| 2 | LogNormal |
| 3 | PERT (Beta) |
| 4 | Pareto/GPD (truncada en P99.9) |
| 5 | Uniforme |

`sev_input_method` puede ser `"min_mode_max"` (usa minimo/mas_probable/maximo)
o `"direct"` (usa parámetros nativos en `sev_params_direct`).

### Escalamiento severidad-frecuencia

```json
"escalamiento_severidad_por_frecuencia": {
  "activado": true,
  "modelo": "reincidencia",
  "tipo_escalamiento": "lineal",
  "paso": 0.5,
  "base": null,
  "factor_max": 5.0,
  "tabla": [],
  "alpha": 0.5,
  "solo_aumento": true,
  "sistemico_factor_max": 3.0,
  "explicacion": "Reincidencia lineal con paso 0.5..."
}
```

Modelos: `"reincidencia"` (factor crece por ocurrencia ordinal) o `"sistemico"`
(factor depende del z-score de la frecuencia agregada). Este bloque
siempre incluye TODOS los campos de ambos modelos (`paso`/`base`/`tabla`
para `"reincidencia"`; `alpha`/`solo_aumento`/`sistemico_factor_max` para
`"sistemico"`), no solo los relevantes al `modelo`/`tipo_escalamiento`
activo — los campos del modelo no usado quedan con su valor guardado
(o `null`) pero no afectan el cálculo.

### Factores de ajuste

Cada factor puede ser uno de tres tipos:

Todo factor (de cualquiera de los tres tipos) siempre incluye además un
campo `"activo"` (booleano, `true` por defecto): factores inactivos se
exportan igual, pero no se aplicaron en la simulación.

**Estático** — aplica siempre con un impacto fijo:
```json
{
  "nombre": "Política Anti-Fraude",
  "activo": true,
  "tipo_modelo": "estatico",
  "afecta_frecuencia": true,
  "afecta_severidad": false,
  "impacto_porcentual": -25,
  "impacto_severidad_pct": 0,
  "explicacion": "Factor estático: aplica -25% de impacto en frecuencia SIEMPRE..."
}
```

**Estocástico** — control con probabilidad de funcionar:
```json
{
  "nombre": "Auditoría",
  "activo": true,
  "tipo_modelo": "estocastico",
  "confiabilidad_pct": 80,
  "reduccion_efectiva_pct": 60,
  "reduccion_fallo_pct": 0,
  "reduccion_severidad_efectiva_pct": 30,
  "reduccion_severidad_fallo_pct": 0,
  "explicacion": "Control estocástico con 80% de confiabilidad..."
}
```

**Seguro** — póliza con deducible/cobertura/límites:
```json
{
  "nombre": "Cyber Insurance",
  "activo": true,
  "tipo_modelo": "estatico",
  "tipo_severidad": "seguro",
  "seguro": {
    "tipo_deducible": "por_ocurrencia",
    "deducible": 50000,
    "cobertura_pct": 80,
    "limite_ocurrencia": 500000,
    "limite_agregado_anual": 2000000
  },
  "explicacion": "Póliza de seguro (por_ocurrencia)..."
}
```

`tipo_deducible` puede ser `"por_ocurrencia"` o `"agregado"`.

### Vínculos

```json
{
  "id_padre": "evt-002",
  "nombre_padre": "Falla de servicios",
  "tipo": "AND",
  "probabilidad_pct": 80,
  "factor_severidad": 1.5,
  "umbral_severidad": 100000,
  "explicacion": "Vínculo AND con padre 'Falla de servicios'..."
}
```

`tipo`: `"AND"` (todos los padres deben ocurrir), `"OR"` (al menos uno),
`"EXCLUYE"` (los padres NO deben ocurrir).

---

## Bloque `results` en detalle

Sub-secciones de `results`:

### `aggregate`

Estadísticas agregadas (toda la cartera).

```json
{
  "perdidas_totales": {
    "_descripcion": "Pérdida total agregada por año Monte Carlo...",
    "n": 10000,
    "estadisticas": {
      "media": 1234567,
      "mediana": 980000,
      "desviacion_estandar": 567890,
      "varianza": 322570076,
      "minimo": 0,
      "maximo": 12500000,
      "rango": 12500000,
      "coeficiente_variacion": 0.46,
      "asimetria": 2.34,
      "curtosis": 5.67,
      "porcentaje_ceros": 12.3
    },
    "percentiles": {
      "p1": ..., "p5": ..., "p10": ..., "p25": ..., "p50": ...,
      "p75": ..., "p90": ..., "p95": ..., "p99": ..., "p99_9": ...
    },
    "var_y_opvar": {
      "VaR_90": 2400000,
      "VaR_95": 3100000,
      "VaR_99": 4800000,
      "expected_shortfall_99": 6500000,
      "explicacion": "..."
    },
    "histograma": {
      "bins_edges": [...],
      "counts": [...],
      "n_bins": 100
    },
    "raw_values": [...]   // Solo si opcion 'incluir_raw_arrays' activa
  },
  "frecuencias_totales": { ...similar... }
}
```

### `per_event`

Lista por evento con estadísticas, boxplot, contribución y comportamiento observado.

```json
[
  {
    "event_id": "...",
    "event_name": "Fraude interno",
    "perdidas_estadisticas": { ... },
    "perdidas_percentiles": { ... },
    "frecuencias_estadisticas": { ... },
    "boxplot_stats": {
      "min_excl_outliers": 0,
      "Q1": 280000,
      "mediana": 320000,
      "Q3": 510000,
      "max_excl_outliers": 850000,
      "outliers_count": 1234
    },
    "contribucion_al_total": {
      "porcentaje_de_perdida_media": 35.2,
      "ranking_por_relevancia": 1
    },
    "comportamiento_observado": { ... }
  }
]
```

`contribucion_al_total` y `comportamiento_observado` son campos
**condicionales**, no siempre presentes en cada entrada de `per_event`:
- `contribucion_al_total` solo aparece si la pérdida media agregada de
  la cartera es mayor a 0 y el evento tiene datos de pérdida.
- `comportamiento_observado` solo aparece si el evento tuvo un factor de
  severidad estático distinto de 1.0 aplicado, o un vector de factores
  estocásticos de severidad activo; contiene únicamente las claves
  (`factor_severidad_estatico_aplicado`, `factor_severidad_estocastico_promedio`)
  que efectivamente aplicaron.

### `correlation`

```json
{
  "frecuencia_total_vs_perdida_total": 0.78,
  "_explicacion": "Correlación de Pearson..."
}
```

Nota: el campo es singular (`correlation`, no `correlations`) porque
reporta un único valor de correlación (frecuencia vs. pérdida total).

### `exceedance_curve`

```json
{
  "_descripcion": "Para cada threshold T, P(L > T)...",
  "puntos": [
    {"threshold": 250000, "percentil": 10, "exceedance_probability": 0.90},
    ...
  ],
  "tolerancia_configurada_por_usuario": {
    "valor_T": 2000000,
    "probabilidad_excedencia_pct": 18.0,
    "_explicacion": "El usuario configuró $2M..."
  }
}
```

### `tail_analysis`

```json
{
  "tail_threshold_p80": 1700000,
  "tail_mean": 3200000,
  "tail_max": 12500000,
  "tail_size": 2000,
  "tail_top10_extreme_losses": [12500000, 11800000, ...],
  "interpretacion": "El 20% de años más severos..."
}
```

### `risk_map`

Posicionamiento de eventos en el plano Impacto × Frecuencia.

```json
{
  "_descripcion": "Posicionamiento de cada evento...",
  "umbrales_cuadrantes": {
    "impacto_x": 800000,
    "frecuencia_y": 3,
    "criterio": "mediana × 1.2 (calculado dinámicamente)"
  },
  "events": [
    {
      "event_id": "...",
      "event_name": "Fraude interno",
      "impacto_medio": 850000,
      "impacto_p90": 2400000,
      "frecuencia_modo": 5,
      "frecuencia_media": 4.98,
      "importancia_score": 850000,
      "importancia_formula": "ImpactoMedio (pérdida esperada anual, consistente con el resumen ejecutivo)",
      "cuadrante": "Alto Impacto / Alta Frecuencia"
    }
  ]
}
```

Nota: `importancia_score` es la pérdida media anual esperada del evento
(`impacto_medio`), no un producto de impacto y frecuencia -- usar
siempre el campo `importancia_formula` (incluido en cada evento) como
fuente de verdad de qué fórmula se aplicó, en vez de asumirla.

### `risk_classification`

Clasificación de criticidad (Termómetro/Semáforo).

```json
{
  "umbrales_fijos": {
    "bajo": 3000000,
    "moderado": 32000000,
    "alto": 110000000,
    "_unit": "USD/año"
  },
  "metricas_clave": { "perdida_media": ..., "perdida_p99": ... },
  "zona_actual_segun_media": "BAJO",
  "zona_actual_segun_p99": "MODERADO",
  "probabilidades_por_zona": {
    "bajo_pct": 68.0,
    "moderado_pct": 31.0,
    "alto_pct": 0.99,
    "critico_pct": 0.01
  }
}
```

### `calendar_periods_of_return`

Período de retorno (cada cuántos años se espera cada nivel).

```json
{
  "frecuencia_eventos_por_año_esperada": 13.2,
  "niveles": [
    {
      "nivel": "BAJO",
      "umbral": 3000000,
      "prob_anual_pct": 32.0,
      "periodo_retorno_años": 3.13,
      "etiqueta": "Cada 3.1 años"
    },
    {
      "nivel": "CRITICO",
      "umbral": 110000000,
      "prob_anual_pct": 0.0,
      "periodo_retorno_años": null,
      "etiqueta": ">100 años"
    },
    ...
  ]
}
```

`periodo_retorno_años` es siempre `number` o `null` (nunca un string) --
es `null` cuando ninguna simulación superó el umbral (probabilidad de
excedencia anual = 0, período de retorno no acotado por los datos
observados); en ese caso `etiqueta` indica `">100 años"`.

### `marginal_contribution_per_percentile`

Contribución de cada evento en simulaciones cercanas a cada percentil
(no el promedio simple). Permite ver qué evento DOMINA en cola vs en
escenarios típicos.

```json
{
  "percentiles": ["Media", "P75", "P80", "P90", "P95", "P99"],
  "contribuciones_por_percentil": {
    "Media": [{"evento": "...", "contribucion": ..., "porcentaje": ...}, ...],
    "P99":   [{"evento": "...", "contribucion": ..., "porcentaje": ...}, ...]
  }
}
```

### `scenario_impacts`

```json
{
  "escenarios": [
    {"nombre": "Típico (Media)",      "valor": ..., "probabilidad_etiqueta": "promedio", "_meaning": "Pérdida esperada en un año típico"},
    {"nombre": "Adverso (P90)",       "valor": ..., "probabilidad_etiqueta": "10% de probabilidad anual", "_meaning": "Pérdida que se supera con 10% de probabilidad"},
    {"nombre": "Muy Adverso (P95)",   "valor": ..., "probabilidad_etiqueta": "5% de probabilidad anual", "_meaning": "Pérdida que se supera con 5% de probabilidad"},
    {"nombre": "Extremo (P99)",       "valor": ..., "probabilidad_etiqueta": "1% de probabilidad anual", "_meaning": "Una vez cada 100 años en promedio"}
  ]
}
```

Cada entrada de `escenarios[]` siempre incluye un campo `_meaning` con una
explicación en lenguaje natural del significado del escenario, pensada
para que un agente IA no necesite inferirla del nombre/etiqueta.

### `insurance_effectiveness`

Pólizas de seguro activas con sus parámetros.

```json
{
  "polizas_activas": [
    {
      "nombre": "Cyber",
      "evento_cubierto": "Fraude",
      "tipo_deducible": "por_ocurrencia",
      "deducible": 50000,
      "cobertura_pct": 80,
      "limite_ocurrencia": 500000,
      "limite_agregado": 2000000
    }
  ]
}
```

### `chart_summaries`

Resumen textual de cada gráfico que muestra la app.

```json
{
  "distribucion_perdidas_agregadas": {
    "tipo": "Histograma + KDE",
    "descripcion": "...",
    "datos_clave": { "media": ..., "mediana": ..., "p99": ... }
  },
  "tornado_contribucion": {
    "tipo": "Tornado chart horizontal",
    "ranking_por_media": [...],
    "concentracion_top3_pct": 78.0
  },
  "dispersion_freq_vs_perdida": { "correlacion": 0.78, ... },
  ...
}
```

---

## Opciones del exportador

Al elegir "Exportar para Análisis (IA)" el usuario ve un diálogo con las
siguientes opciones (todas defaultean a `true` excepto las marcadas):

| Opción | Default | Efecto |
|---|---|---|
| Resumen ejecutivo y key findings | ✅ | Incluye `executive_summary` |
| Estadísticas detalladas | ✅ | Incluye `estadisticas`, `percentiles`, `var_y_opvar` |
| Histogramas y curva de excedencia | ✅ | Incluye `histograma`, `exceedance_curve`, `tail_analysis`, `chart_summaries` |
| Resultados desglosados por evento | ✅ | Incluye `per_event` |
| Contribución marginal por percentil | ✅ | Incluye `marginal_contribution_per_percentile` |
| Snapshot textual | ✅ | Incluye `text_snapshot` |
| Arrays raw (todas las simulaciones) | ❌ | Incluye `raw_values` (puede ser grande, ~5-50 MB) |
| Comprimir con gzip | ❌ | Genera `.json.gz` (~7× menor) |

---

## Ejemplos de queries que un agente IA puede responder

Una vez compartido este archivo con un agente IA, el agente puede:

1. **Resumir el riesgo**: "Dame un resumen ejecutivo de la cartera"
   → Lee `executive_summary.headline` y `key_findings`.

2. **Analizar concentración**: "¿Qué evento contribuye más al riesgo?"
   → Lee `executive_summary.concentracion_riesgo` y
   `results.chart_summaries.tornado_contribucion`.

3. **Cola de pérdidas**: "¿Hay riesgo de cola? ¿Qué tan extremo?"
   → Lee `results.tail_analysis` y `estadisticas.curtosis/asimetria`.

4. **Efectividad de seguros**: "¿Vale la pena la póliza Cyber?"
   → Lee `results.insurance_effectiveness` y compara
   `results.aggregate.perdidas_totales.estadisticas` vs los parámetros del seguro.

5. **Excedencia de tolerancia**: "¿Cuál es la probabilidad de exceder $2M?"
   → Lee `results.exceedance_curve.puntos` o usa
   `tolerancia_configurada_por_usuario` si el usuario la fijó.

6. **Cuadrantes de riesgo**: "¿Qué eventos son alta frec + alto impacto?"
   → Filtra `results.risk_map.events` por `cuadrante == "Alto Impacto / Alta Frecuencia"`.

7. **Período de retorno**: "¿Cada cuántos años una pérdida ALTA?"
   → Lee `results.calendar_periods_of_return.niveles`.

8. **Efectos por percentil**: "¿Qué evento domina en escenarios extremos?"
   → Lee `results.marginal_contribution_per_percentile.contribuciones_por_percentil.P99`.

---

## FAQ para integradores

**¿Cómo cambia el archivo si no incluyo arrays raw?**
Quedan las estadísticas (media, percentiles, etc.) y los histogramas que
son suficientes para 99% de los análisis IA. El archivo es ~7× más chico.

**¿Puedo reproducir la simulación con este archivo?**
Sí, si activás `incluir_raw_arrays`. Con eso quedan los N valores exactos
generados. Sin ese flag se preserva la metodología y parámetros pero no
los muestreos individuales.

**¿Qué pasa si un campo no aplica?**
El export omite secciones que no tienen sentido (ej: `marginal_contribution`
si el usuario lo desactivó). El agente debe verificar `if "..." in payload`.

**¿Es estable el schema entre versiones?**
Sí, dentro de la versión `1.x`. Si cambia mayormente, sube a `2.0`.
El campo `$schema_version` permite negociar compatibilidad.

**¿Cómo manejar arrays que pueden tener `inf` o `NaN`?**
El export los serializa como `"inf"`, `"-inf"` o `null` respectivamente.

