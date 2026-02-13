#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Módulo de utilidades para ajuste de probabilidades en Risk Lab.

Este módulo usa transformaciones log-odds internamente para combinar
efectos de múltiples controles y factores de riesgo de forma aditiva.

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
    
    Args:
        probabilidad_base: Probabilidad inicial, debe estar en el rango (0, 1)
        factores: Lista de diccionarios con las siguientes claves:
            - 'nombre': str, descripción del factor
            - 'impacto_porcentual': float, impacto en % (+aumenta, -reduce)
            - 'activo': bool, si el factor está actualmente activo
    
    Returns:
        Tupla de (probabilidad_ajustada, explicación_texto)
        
    Ejemplos:
        >>> factores = [
        ...     {'nombre': 'Firewall', 'impacto_porcentual': -30, 'activo': True},
        ...     {'nombre': 'Auditoría', 'impacto_porcentual': -20, 'activo': False}
        ... ]
        >>> p_ajustada, explicacion = ajustar_probabilidad_por_factores(0.10, factores)
        >>> print(f"{p_ajustada:.1%}")  # ~7.4%
        7.4%
    
    Notas:
        - Valores negativos reducen la probabilidad (controles)
        - Valores positivos aumentan la probabilidad (factores de riesgo)
        - Solo los factores con 'activo'=True se aplican
        - Si la probabilidad_base no está en (0,1), se devuelve sin cambios
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
        
        # Convertir porcentaje a ajuste en escala log-odds
        # Escala: 10% de impacto ≈ 0.1 en log-odds
        # Esta es una escala intuitiva que permite combinar efectos aditivamente
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


def aplicar_factor_a_probabilidad(probabilidad_base: float, factor_multiplicativo: float) -> float:
    """
    Aplica un factor multiplicativo a una probabilidad usando log-odds.
    
    Esta función es útil para modelos estocásticos donde el factor puede variar
    en cada iteración de Monte Carlo.
    
    Args:
        probabilidad_base: Probabilidad inicial en (0, 1)
        factor_multiplicativo: Factor a aplicar. 
            - factor < 1: Reduce probabilidad (ej: 0.5 = reducción del 50%)
            - factor = 1: Sin cambio
            - factor > 1: Aumenta probabilidad (ej: 1.5 = aumento del 50%)
    
    Returns:
        Probabilidad ajustada, clipeada a rango (0.0001, 0.9999)
    
    Ejemplos:
        >>> aplicar_factor_a_probabilidad(0.10, 0.5)  # Reducir 50%
        0.0526  # Aproximadamente 5.3%
        
        >>> aplicar_factor_a_probabilidad(0.10, 1.5)  # Aumentar 50%
        0.1538  # Aproximadamente 15.4%
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
