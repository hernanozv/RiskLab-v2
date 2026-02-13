# 🧪 Guía de Testing: Factores Estocásticos con Vínculos

## 📋 Test 1: AND + Poisson

### Configuración:

#### Evento Padre: "Vulnerabilidad Detectada"
```
Nombre: Vulnerabilidad Detectada
Tipo de vínculo: Independiente
Distribución Frecuencia: Poisson
  └─ Tasa (λ): 5
Distribución Severidad: PERT
  └─ Mín: $1,000, Más Probable: $5,000, Máx: $10,000
```

#### Evento Hijo: "Explotación Exitosa"
```
Nombre: Explotación Exitosa
Tipo de vínculo: AND
  └─ Depende de: Vulnerabilidad Detectada
Distribución Frecuencia: Poisson
  └─ Tasa (λ): 10

*** FACTOR DE AJUSTE ***
Nombre: Firewall
Tipo de Modelo: Estocástico
  ├─ Confiabilidad: 50%
  ├─ Reducción si efectivo: 100%
  └─ Reducción si falla: 0%

Distribución Severidad: PERT
  └─ Mín: $10,000, Más Probable: $50,000, Máx: $100,000
```

### Simulación:
```
Número de iteraciones: 10,000
```

### Resultados Esperados:

#### Padre "Vulnerabilidad Detectada":
```
Media de frecuencia: ~5 eventos/año
Distribución: Poisson centrada en 5
```

#### Hijo "Explotación Exitosa":

**Frecuencia:**
```
┌─────────────────────────────────────────────────────────┐
│ DISTRIBUCIÓN ESPERADA                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ PICO 1: ~50% simulaciones con 0 eventos                │
│   ├─ Razón: Firewall funciona (50% de las veces)       │
│   └─ λ ≈ 0 (reducción 100%)                           │
│                                                         │
│ DISTRIBUCIÓN 2: ~50% con eventos normales              │
│   ├─ Razón: Firewall falla (50% de las veces)          │
│   ├─ λ ≈ 10 (sin reducción)                           │
│   └─ Media de este grupo: ~10 eventos                  │
│                                                         │
│ MEDIA TOTAL: ~5 eventos/año (0.5 × 0 + 0.5 × 10)      │
└─────────────────────────────────────────────────────────┘
```

**IMPORTANTE:** El hijo SOLO puede ocurrir si el padre ocurre. Esto se ve en el histograma como una reducción adicional en el número total de eventos.

---

## 📋 Test 2: AND + Bernoulli

### Configuración:

#### Evento Padre: "Phishing Enviado"
```
Nombre: Phishing Enviado
Tipo de vínculo: Independiente
Distribución Frecuencia: Poisson
  └─ Tasa (λ): 20
Distribución Severidad: PERT
  └─ Mín: $100, Más Probable: $500, Máx: $1,000
```

#### Evento Hijo: "Credenciales Comprometidas"
```
Nombre: Credenciales Comprometidas
Tipo de vínculo: AND
  └─ Depende de: Phishing Enviado
Distribución Frecuencia: Bernoulli
  └─ Probabilidad de éxito (p): 0.30

*** FACTOR DE AJUSTE ***
Nombre: Capacitación
Tipo de Modelo: Estocástico
  ├─ Confiabilidad: 70%
  ├─ Reducción si efectivo: 90%
  └─ Reducción si falla: 0%

Distribución Severidad: PERT
  └─ Mín: $5,000, Más Probable: $10,000, Máx: $20,000
```

### Resultados Esperados:

**Hijo "Credenciales Comprometidas" (Bernoulli):**
```
┌─────────────────────────────────────────────────────────┐
│ DISTRIBUCIÓN BERNOULLI MODIFICADA                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 70% de simulaciones: Capacitación funciona             │
│   ├─ p ajustada ≈ 0.03 (90% reducción con log-odds)   │
│   └─ ~97% sin eventos, ~3% con 1 evento                │
│                                                         │
│ 30% de simulaciones: Capacitación falla                │
│   ├─ p original = 0.30                                 │
│   └─ ~70% sin eventos, ~30% con 1 evento               │
│                                                         │
│ RESULTADO GLOBAL:                                       │
│   ├─ ~89% simulaciones sin eventos                     │
│   └─ ~11% simulaciones con 1 evento                    │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Test 3: OR + Poisson-Gamma

### Configuración:

#### Eventos Padre (dos):

**Padre 1: "Ataque DDoS Externo"**
```
Tipo de vínculo: Independiente
Distribución Frecuencia: Bernoulli, p = 0.40
```

**Padre 2: "Falla de Hardware"**
```
Tipo de vínculo: Independiente
Distribución Frecuencia: Bernoulli, p = 0.20
```

#### Evento Hijo: "Downtime del Servicio"
```
Nombre: Downtime del Servicio
Tipo de vínculo: OR
  ├─ Depende de: Ataque DDoS Externo
  └─ Depende de: Falla de Hardware
Distribución Frecuencia: Poisson-Gamma
  ├─ Valor mínimo: 1
  ├─ Valor más probable: 10
  └─ Valor máximo: 25

*** FACTOR DE AJUSTE ***
Nombre: Redundancia
Tipo de Modelo: Estocástico
  ├─ Confiabilidad: 80%
  ├─ Reducción si efectivo: 95%
  └─ Reducción si falla: 0%
```

### Resultados Esperados:

**Hijo "Downtime" (Poisson-Gamma con OR):**
```
┌─────────────────────────────────────────────────────────┐
│ VÍNCULO OR: Ocurre si AL MENOS UNO de los padres       │
│ ocurre                                                  │
│                                                         │
│ Padre 1: 40% probabilidad                              │
│ Padre 2: 20% probabilidad                              │
│ P(al menos uno) = 1 - P(ninguno) = 1 - 0.6×0.8 = 52%  │
│                                                         │
│ De ese 52% de simulaciones donde puede ocurrir:        │
│   ├─ 80% Redundancia funciona: μ ≈ 0.5 (95% reducción)│
│   └─ 20% Redundancia falla: μ ≈ 10 (sin reducción)    │
│                                                         │
│ DISTRIBUCIÓN TRIMODAL:                                 │
│   ├─ 48% sin eventos (OR no se cumple)                │
│   ├─ ~42% con muy pocos eventos (redundancia funciona) │
│   └─ ~10% con ~10 eventos (redundancia falla)         │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Test 4: EXCLUYE + Beta

### Configuración:

#### Evento Padre: "Auditoría Programada"
```
Nombre: Auditoría Programada
Tipo de vínculo: Independiente
Distribución Frecuencia: Bernoulli, p = 0.30
```

#### Evento Hijo: "Actividad Sospechosa"
```
Nombre: Actividad Sospechosa
Tipo de vínculo: EXCLUYE
  └─ No puede ocurrir si: Auditoría Programada
Distribución Frecuencia: Beta
  ├─ Valor mínimo: 10%
  ├─ Valor más probable: 50%
  └─ Valor máximo: 90%

*** FACTOR DE AJUSTE ***
Nombre: Monitoreo
Tipo de Modelo: Estocástico
  ├─ Confiabilidad: 60%
  ├─ Reducción si efectivo: 80%
  └─ Reducción si falla: 0%
```

### Resultados Esperados:

**Hijo "Actividad Sospechosa" (Beta con EXCLUYE):**
```
┌─────────────────────────────────────────────────────────┐
│ VÍNCULO EXCLUYE: NO ocurre si padre ocurre             │
│                                                         │
│ Auditoría: 30% probabilidad                            │
│ P(hijo puede ocurrir) = 70%                            │
│                                                         │
│ De ese 70% de simulaciones:                            │
│   ├─ 60% Monitoreo funciona: p_mode ≈ 0.10 (reducido) │
│   └─ 40% Monitoreo falla: p_mode = 0.50 (original)    │
│                                                         │
│ RESULTADO:                                             │
│   ├─ 30% sin eventos (auditoría excluyó)              │
│   ├─ ~42% con pocos eventos (monitoreo funciona)      │
│   └─ ~28% con eventos normales (monitoreo falla)      │
└─────────────────────────────────────────────────────────┘
```

---

## 🔍 Cómo Verificar los Resultados

### 1. Pestaña "Frecuenc"
- Debe mostrar distribución **bimodal** o **trimodal**
- Verificar que hay pico en 0 (control funciona)
- Verificar que hay distribución en valores altos (control falla)

### 2. Pestaña "Distrib"
- Comparar con simulación SIN factor estocástico
- Debe haber mayor dispersión con estocástico
- VaR y CVaR deben ser mayores (captura escenarios de falla)

### 3. Consola de Python
Buscar mensajes de debug (si se agregan temporalmente):
```
[DEBUG ESTOCASTICO] Evento 'Explotación Exitosa' tiene factores estocásticos
[DEBUG ESTOCASTICO]   Factor 'Firewall': 48.0% funciona (esperado: 50.0%)
[DEBUG ESTOCASTICO]   Factor vector: min=0.0000, mean=0.5200, max=1.0000
```

### 4. Reporte Excel
- Exportar resultados
- Analizar percentiles (P10, P50, P90, P95, P99)
- Con estocástico: P95 y P99 deben ser significativamente mayores
- Esto refleja los escenarios donde el control falla

---

## ✅ Checklist de Validación

### Antes de Simular:
- [ ] Evento padre creado y configurado
- [ ] Evento hijo creado con vínculo correcto (AND/OR/EXCLUYE)
- [ ] Factor estocástico agregado al hijo
- [ ] Tipo de modelo: **Estocástico** seleccionado
- [ ] Confiabilidad configurada (ej: 50%)
- [ ] Reducción efectiva configurada (ej: 100%)

### Durante la Simulación:
- [ ] Número de iteraciones: 10,000 (recomendado)
- [ ] Sin errores en consola
- [ ] Progreso normal (sin congelamiento)

### Después de Simular:
- [ ] Histograma de frecuencia muestra bimodalidad
- [ ] Pico cerca de 0 eventos visible
- [ ] Distribución de impacto más dispersa que sin factor
- [ ] VaR 95% mayor que simulación sin factor estocástico
- [ ] Media de frecuencia coherente con expectativa matemática

---

## 🎯 Valores de Referencia Rápida

| Confiabilidad | % Control Funciona | % Control Falla |
|---------------|-------------------|-----------------|
| 30%           | 30%               | 70%             |
| 50%           | 50%               | 50%             |
| 70%           | 70%               | 30%             |
| 90%           | 90%               | 10%             |

| Reducción Efectiva | Factor cuando funciona |
|--------------------|------------------------|
| 100%               | 0.00 (elimina eventos) |
| 90%                | 0.10                   |
| 80%                | 0.20                   |
| 50%                | 0.50                   |

**Fórmula de Media Esperada (Poisson):**
```
Media = Confiabilidad × (λ × Factor_funciona) + (1 - Confiabilidad) × λ

Ejemplo: 50% confiabilidad, 100% reducción, λ = 10
Media = 0.5 × (10 × 0) + 0.5 × 10 = 5
```

---

## 🚨 Problemas Comunes

### Problema 1: No se ve bimodalidad
**Causa:** Iteraciones insuficientes  
**Solución:** Aumentar a 10,000+ iteraciones

### Problema 2: Error en consola "beta_dist no definido"
**Causa:** Bug en versión anterior  
**Solución:** Ya corregido en última versión (usa `beta.rvs()`)

### Problema 3: Evento hijo siempre en 0
**Causa:** Vínculo no configurado correctamente  
**Solución:** Verificar que padre ocurre y vínculo está activo

### Problema 4: Factor no reduce eventos
**Causa:** Modelo estático seleccionado en lugar de estocástico  
**Solución:** Verificar radio button "Estocástico" en UI de factores

---

**Fecha de creación:** 4 de noviembre de 2025  
**Autor:** Cascade AI  
**Versión:** 1.0
