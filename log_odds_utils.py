#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Módulo de utilidades para ajuste de probabilidades en Risk Lab.

Este módulo usa transformaciones log-odds internamente para combinar
efectos de múltiples controles y factores de riesgo de forma aditiva.

IMPORTANTE — semántica de 'impacto_porcentual' / 'factor_multiplicativo':
El número que el usuario ingresa (p.ej. -30 para "reduce 30%") NO se aplica
como un porcentaje literal sobre la probabilidad. Se convierte en un shift
ADITIVO en la escala log-odds (impacto_pct * 0.01), y luego se vuelve a
transformar a probabilidad con la función logística. Esto permite combinar
varios factores sumando sus shifts, pero como consecuencia la reducción/
aumento REAL de la probabilidad depende del valor de la probabilidad base:
    - Para p_base=10%, un "-30%" produce una reducción real de ~24% (p final ≈7.6%)
    - Para p_base=50%, un "-30%" produce una reducción real de ~15% (p final ≈42.6%)
El "-30%" nominal y la reducción real coinciden solo aproximadamente para
probabilidades base pequeñas. Esta es una decisión de diseño deliberada
(la escala log-odds es lo que permite sumar varios controles de forma
consistente), pero cualquier UI o reporte que muestre este valor debe
aclarar que es un "impacto nominal en escala log-odds", no un porcentaje
de reducción exacto de la probabilidad.

Autor: Risk Lab Team
Versión: 1.0
"""

import numpy as np
from typing import List, Dict, Tuple, Optional


def ajustar_probabilidad_por_factores(
    probabilidad_base: float, 
    factores: List[Dict]
) -> Tuple[float, str]:
    """
    Ajusta una probabilidad base aplicando múltiples factores de control/riesgo.

    Los factores se combinan usando la escala log-odds, lo que permite:
    - Combinar efectos independientes de forma aditiva
    - Mantener probabilidades en el rango válido (0, 1)
    - Modelar tanto controles (reducen riesgo) como factores (aumentan riesgo)

    ATENCIÓN — 'impacto_porcentual' NO es un porcentaje literal de reducción/
    aumento de la probabilidad: es un shift aditivo en escala log-odds
    (impacto_pct * 0.01). El efecto real sobre la probabilidad depende de
    probabilidad_base y normalmente será DISTINTO al número nominal (ver
    ejemplo abajo: -30% nominal produce ~24% de reducción real para p=10%).
    Esto es intencional (permite sumar varios factores de forma consistente
    en escala log-odds), pero cualquier texto/UI que muestre
    'impacto_porcentual' debe aclarar que es un impacto nominal, no un
    porcentaje exacto.

    Args:
        probabilidad_base: Probabilidad inicial, debe estar en el rango (0, 1)
        factores: Lista de diccionarios con las siguientes claves:
            - 'nombre': str, descripción del factor
            - 'impacto_porcentual': float, shift nominal en escala log-odds,
              expresado como si fuera un % (+aumenta, -reduce). NO es el %
              de cambio real de la probabilidad (ver nota ATENCIÓN arriba).
            - 'activo': bool, si el factor está actualmente activo

    Returns:
        Tupla de (probabilidad_ajustada, explicación_texto)

    Ejemplos:
        >>> factores = [
        ...     {'nombre': 'Firewall', 'impacto_porcentual': -30, 'activo': True},
        ...     {'nombre': 'Auditoría', 'impacto_porcentual': -20, 'activo': False}
        ... ]
        >>> p_ajustada, explicacion = ajustar_probabilidad_por_factores(0.10, factores)
        >>> print(f"{p_ajustada:.1%}")  # 7.6% (reducción REAL ~24%, no 30%)
        7.6%

    Notas:
        - Valores negativos reducen la probabilidad (controles)
        - Valores positivos aumentan la probabilidad (factores de riesgo)
        - Solo los factores con 'activo'=True se aplican
        - Si la probabilidad_base no está en (0,1), se devuelve sin cambios
        - El % de cambio REAL de la probabilidad no es igual al
          'impacto_porcentual' nominal; varía según probabilidad_base
          (ver docstring del módulo)
    """
    # Validar probabilidad base
    if not isinstance(probabilidad_base, (int, float)):
        return probabilidad_base, "Error: probabilidad_base debe ser numérica"
    
    if not (0 < probabilidad_base < 1):
        return probabilidad_base, f"Probabilidad base ({probabilidad_base:.3f}) fuera de rango válido (0, 1)"
    
    # Validar factores
    if not factores or not isinstance(factores, list):
        return probabilidad_base, "Sin factores de ajuste"
    
    # Convertir probabilidad a log-odds (logit)
    try:
        log_odds = np.log(probabilidad_base / (1 - probabilidad_base))
    except (ValueError, ZeroDivisionError, RuntimeWarning) as e:
        return probabilidad_base, f"Error en conversión a log-odds: {str(e)}"
    
    # Aplicar cada factor activo
    ajustes_aplicados = []
    total_ajuste_log_odds = 0.0
    
    for factor in factores:
        # Validar estructura del factor
        if not isinstance(factor, dict):
            continue
            
        # Verificar si está activo
        if not factor.get('activo', True):
            continue
        
        # Verificar si afecta frecuencia (True por defecto para backward compat)
        if not factor.get('afecta_frecuencia', True):
            continue
        
        # Obtener impacto
        impacto_pct = factor.get('impacto_porcentual', 0)
        if not isinstance(impacto_pct, (int, float)) or impacto_pct == 0:
            continue
        
        # Convertir el "impacto nominal" a un shift en escala log-odds.
        # NOTA: esto NO es un porcentaje literal de la probabilidad — es un
        # shift aditivo (impacto_pct/100) en log-odds que permite combinar
        # varios factores sumando. El % de cambio REAL sobre la probabilidad
        # depende de probabilidad_base (ver docstring del módulo y de esta
        # función para el detalle numérico).
        ajuste_log_odds = impacto_pct * 0.01
        
        log_odds += ajuste_log_odds
        total_ajuste_log_odds += ajuste_log_odds
        
        nombre = factor.get('nombre', 'Factor sin nombre')
        ajustes_aplicados.append(f"{nombre}: {impacto_pct:+.0f}%")
    
    # Convertir log-odds ajustado de vuelta a probabilidad (función logística)
    try:
        # Usar implementación numéricamente estable
        if log_odds >= 0:
            exp_neg = np.exp(-log_odds)
            probabilidad_ajustada = 1.0 / (1.0 + exp_neg)
        else:
            exp_pos = np.exp(log_odds)
            probabilidad_ajustada = exp_pos / (1.0 + exp_pos)
    except (OverflowError, RuntimeWarning):
        # En caso de overflow, saturar en los límites
        probabilidad_ajustada = 0.9999 if log_odds > 0 else 0.0001
    
    # Asegurar que está en rango válido para scipy
    probabilidad_ajustada = float(np.clip(probabilidad_ajustada, 0.0001, 0.9999))
    
    # Generar explicación
    if ajustes_aplicados:
        cambio_pct = ((probabilidad_ajustada / probabilidad_base) - 1) * 100
        explicacion = f"Probabilidad base: {probabilidad_base:.1%}\n"
        explicacion += "Factores aplicados:\n"
        explicacion += "\n".join(f"  • {ajuste}" for ajuste in ajustes_aplicados)
        explicacion += f"\n\nProbabilidad ajustada: {probabilidad_ajustada:.1%}"
        explicacion += f"\nCambio neto: {cambio_pct:+.1f}%"
    else:
        explicacion = "No hay factores activos. Probabilidad sin cambios."
        probabilidad_ajustada = probabilidad_base
    
    return probabilidad_ajustada, explicacion


def aplicar_factor_a_probabilidad_vec(probabilidad_base: float, factores_vector) -> np.ndarray:
    """
    Versión vectorizada de aplicar_factor_a_probabilidad. Aplica un vector de
    factores multiplicativos a una misma probabilidad base, retornando un vector
    de probabilidades ajustadas.

    Algoritmo equivalente al escalar (verificado matemáticamente):
      log_odds = log(p_base / (1 - p_base))
      log_odds_ajustado = log_odds + (factor - 1)
      prob_ajustada = sigmoid(log_odds_ajustado)
      → clipeada a [0.0001, 0.9999]
      → factor == 1 retorna probabilidad_base exacta
      → factor <= 0 retorna 0.0001

    Args:
        probabilidad_base: Probabilidad inicial en (0, 1).
        factores_vector: array-like de factores multiplicativos.

    Returns:
        np.ndarray de probabilidades ajustadas, mismo tamaño que factores_vector,
        clipeadas a (0.0001, 0.9999).
    """
    f = np.asarray(factores_vector, dtype=np.float64)
    if not (0 < probabilidad_base < 1):
        return np.full_like(f, float(np.clip(probabilidad_base, 0.0001, 0.9999)))

    log_odds_base = np.log(probabilidad_base / (1 - probabilidad_base))
    log_odds = log_odds_base + (f - 1.0)
    # Logística numéricamente estable
    probs = np.where(
        log_odds >= 0,
        1.0 / (1.0 + np.exp(-log_odds)),
        np.exp(log_odds) / (1.0 + np.exp(log_odds))
    )
    # Paridad exacta con la versión escalar para los casos especiales
    probs = np.where(f == 1.0, probabilidad_base, probs)
    probs = np.where(f <= 0, 0.0001, probs)
    return np.clip(probs, 0.0001, 0.9999)


def aplicar_factor_a_probabilidad(probabilidad_base: float, factor_multiplicativo: float) -> float:
    """
    Aplica un factor multiplicativo "nominal" a una probabilidad usando log-odds.

    Esta función es útil para modelos estocásticos donde el factor puede variar
    en cada iteración de Monte Carlo.

    ATENCIÓN: `factor_multiplicativo` NO se aplica como un multiplicador
    literal sobre probabilidad_base (no es `p_ajustada = p_base * factor`).
    Internamente se convierte a un shift log-odds equivalente a
    `(factor_multiplicativo - 1) * 100` puntos de "impacto nominal" (ver
    `ajustar_probabilidad_por_factores`), por lo que el cambio REAL de la
    probabilidad depende de probabilidad_base y normalmente NO coincide con
    el "factor - 1" nominal (ver ejemplos abajo).

    Args:
        probabilidad_base: Probabilidad inicial en (0, 1)
        factor_multiplicativo: Factor nominal a aplicar (en escala log-odds).
            - factor < 1: Reduce probabilidad (ej nominal: 0.5 ⇒ "-50%" nominal,
              pero la reducción REAL de la probabilidad es distinta, ver ejemplo)
            - factor = 1: Sin cambio
            - factor > 1: Aumenta probabilidad (ej nominal: 1.5 ⇒ "+50%" nominal,
              reducción/aumento REAL distinto al nominal, ver ejemplo)

    Returns:
        Probabilidad ajustada, clipeada a rango (0.0001, 0.9999)

    Ejemplos (valores verificados numéricamente):
        >>> aplicar_factor_a_probabilidad(0.10, 0.5)  # "-50%" nominal
        0.063137  # Reducción REAL: ~36.9% (no 50%)

        >>> aplicar_factor_a_probabilidad(0.10, 1.5)  # "+50%" nominal
        0.154828  # Aumento REAL: ~54.8% (no 50%)
    """
    # Validar entrada
    if not (0 < probabilidad_base < 1):
        return np.clip(probabilidad_base, 0.0001, 0.9999)
    
    if factor_multiplicativo <= 0:
        return 0.0001
    
    if factor_multiplicativo == 1.0:
        return probabilidad_base
    
    try:
        # Convertir a log-odds
        log_odds = np.log(probabilidad_base / (1 - probabilidad_base))
        
        # Aplicar factor (en escala log-odds, multiplicar es sumar el log)
        # Pero queremos que factor_multiplicativo actúe sobre la probabilidad directamente
        # Por lo tanto, usamos una aproximación: ajuste_pct = (factor - 1) * 100
        ajuste_pct = (factor_multiplicativo - 1) * 100
        ajuste_log_odds = ajuste_pct * 0.01
        
        log_odds_ajustado = log_odds + ajuste_log_odds
        
        # Convertir de vuelta a probabilidad (función logística estable)
        if log_odds_ajustado >= 0:
            exp_neg = np.exp(-log_odds_ajustado)
            probabilidad_ajustada = 1.0 / (1.0 + exp_neg)
        else:
            exp_pos = np.exp(log_odds_ajustado)
            probabilidad_ajustada = exp_pos / (1.0 + exp_pos)
        
        # Clipear a rango válido
        return float(np.clip(probabilidad_ajustada, 0.0001, 0.9999))
    
    except (OverflowError, RuntimeWarning, ValueError):
        # En caso de error, retornar valor seguro
        if factor_multiplicativo < 1:
            return 0.0001
        else:
            return 0.9999


def validar_implementacion() -> bool:
    """
    Ejecuta tests de validación para verificar la correctitud matemática.
    
    Returns:
        True si todos los tests pasan, False en caso contrario
    """
    print("=" * 70)
    print("VALIDACIÓN DE IMPLEMENTACIÓN - log_odds_utils.py")
    print("=" * 70)
    
    tests_exitosos = 0
    tests_totales = 0
    
    # Test 1: Sin factores
    tests_totales += 1
    p_base = 0.10
    factores = []
    p_ajustada, _ = ajustar_probabilidad_por_factores(p_base, factores)
    if abs(p_ajustada - p_base) < 0.0001:
        print(f"✓ Test 1: Sin factores - Probabilidad sin cambios")
        tests_exitosos += 1
    else:
        print(f"✗ Test 1 FALLÓ: Esperado {p_base}, obtenido {p_ajustada}")
    
    # Test 2: Factor inactivo
    tests_totales += 1
    factores = [{'nombre': 'Control', 'impacto_porcentual': -50, 'activo': False}]
    p_ajustada, _ = ajustar_probabilidad_por_factores(p_base, factores)
    if abs(p_ajustada - p_base) < 0.0001:
        print(f"✓ Test 2: Factor inactivo - Sin cambios")
        tests_exitosos += 1
    else:
        print(f"✗ Test 2 FALLÓ: Esperado {p_base}, obtenido {p_ajustada}")
    
    # Test 3: Control reduce probabilidad
    tests_totales += 1
    factores = [{'nombre': 'Firewall', 'impacto_porcentual': -30, 'activo': True}]
    p_ajustada, _ = ajustar_probabilidad_por_factores(p_base, factores)
    if p_ajustada < p_base and p_ajustada > 0:
        print(f"✓ Test 3: Control -30% reduce probabilidad: {p_base:.1%} → {p_ajustada:.1%}")
        tests_exitosos += 1
    else:
        print(f"✗ Test 3 FALLÓ: Control no redujo probabilidad correctamente")
    
    # Test 4: Factor de riesgo aumenta probabilidad
    tests_totales += 1
    factores = [{'nombre': 'Vulnerabilidad', 'impacto_porcentual': 50, 'activo': True}]
    p_ajustada, _ = ajustar_probabilidad_por_factores(p_base, factores)
    if p_ajustada > p_base and p_ajustada < 1:
        print(f"✓ Test 4: Factor +50% aumenta probabilidad: {p_base:.1%} → {p_ajustada:.1%}")
        tests_exitosos += 1
    else:
        print(f"✗ Test 4 FALLÓ: Factor no aumentó probabilidad correctamente")
    
    # Test 5: Múltiples factores (combinación)
    tests_totales += 1
    factores = [
        {'nombre': 'Control A', 'impacto_porcentual': -30, 'activo': True},
        {'nombre': 'Control B', 'impacto_porcentual': -20, 'activo': True},
        {'nombre': 'Riesgo C', 'impacto_porcentual': 40, 'activo': True}
    ]
    p_ajustada, _ = ajustar_probabilidad_por_factores(p_base, factores)
    # Net: -30-20+40 = -10%, debería reducir ligeramente
    if 0 < p_ajustada < 1:
        print(f"✓ Test 5: Múltiples factores combinados: {p_base:.1%} → {p_ajustada:.1%}")
        tests_exitosos += 1
    else:
        print(f"✗ Test 5 FALLÓ: Combinación incorrecta")
    
    # Test 6: Probabilidades extremas se mantienen en rango
    tests_totales += 1
    factores = [{'nombre': 'Control extremo', 'impacto_porcentual': -99, 'activo': True}]
    p_ajustada, _ = ajustar_probabilidad_por_factores(0.50, factores)
    if 0 < p_ajustada < 1:
        print(f"✓ Test 6: Probabilidad se mantiene en rango válido (0, 1): {p_ajustada:.4f}")
        tests_exitosos += 1
    else:
        print(f"✗ Test 6 FALLÓ: Probabilidad fuera de rango")
    
    # Test 7: Manejo de entrada inválida
    tests_totales += 1
    p_ajustada, msg = ajustar_probabilidad_por_factores(1.5, [])
    if p_ajustada == 1.5 and "fuera de rango" in msg:
        print(f"✓ Test 7: Manejo correcto de probabilidad inválida")
        tests_exitosos += 1
    else:
        print(f"✗ Test 7 FALLÓ: No manejó entrada inválida correctamente")
    
    # Resumen
    print("=" * 70)
    print(f"RESULTADO: {tests_exitosos}/{tests_totales} tests exitosos")
    
    if tests_exitosos == tests_totales:
        print("✅ VALIDACIÓN COMPLETA - Todos los tests pasaron")
        print("=" * 70)
        return True
    else:
        print(f"⚠️ ADVERTENCIA - {tests_totales - tests_exitosos} tests fallaron")
        print("=" * 70)
        return False


# Ejecutar validación al importar el módulo (solo en desarrollo)
if __name__ == "__main__":
    validar_implementacion()
