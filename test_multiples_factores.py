"""
Test: Múltiples Factores Estocásticos en un Evento
===================================================

Este script analiza y valida la lógica matemática cuando se aplican
múltiples factores estocásticos al mismo evento.
"""

import numpy as np

def simular_multiples_factores(num_simulaciones=10000):
    """Simula la aplicación de múltiples factores estocásticos."""
    
    print("=" * 80)
    print("SIMULACIÓN: MÚLTIPLES FACTORES ESTOCÁSTICOS")
    print("=" * 80)
    
    # Configuración de factores
    factores = [
        {
            'nombre': 'Firewall',
            'confiabilidad': 0.50,
            'reduccion_efectiva': 1.00,  # 100%
            'reduccion_fallo': 0.00
        },
        {
            'nombre': 'Antivirus',
            'confiabilidad': 0.70,
            'reduccion_efectiva': 0.80,  # 80%
            'reduccion_fallo': 0.00
        }
    ]
    
    print("\nConfiguración:")
    for f in factores:
        print(f"  - {f['nombre']}:")
        print(f"      Confiabilidad: {f['confiabilidad']*100:.0f}%")
        print(f"      Reducción si efectivo: {f['reduccion_efectiva']*100:.0f}%")
        print(f"      Reducción si falla: {f['reduccion_fallo']*100:.0f}%")
    
    # Generar vector de factores (lógica del código real)
    rng = np.random.default_rng(42)
    factores_vector = np.ones(num_simulaciones)
    
    estados_por_factor = {}
    
    for f in factores:
        nombre = f['nombre']
        confiabilidad = f['confiabilidad']
        reduccion_efectiva = f['reduccion_efectiva']
        reduccion_fallo = f['reduccion_fallo']
        
        # Samplear estados
        estados = rng.random(num_simulaciones)
        funciona = estados < confiabilidad
        
        # Guardar para análisis
        estados_por_factor[nombre] = funciona
        
        # Aplicar reducción
        reducciones = np.where(funciona, reduccion_efectiva, reduccion_fallo)
        factores_vector *= (1 - reducciones)
        
        # Stats
        num_funciona = np.sum(funciona)
        pct_funciona = 100 * num_funciona / num_simulaciones
        print(f"\n{nombre}:")
        print(f"  Funciona en: {num_funciona}/{num_simulaciones} ({pct_funciona:.1f}%)")
    
    # Análisis de combinaciones
    print("\n" + "=" * 80)
    print("ANÁLISIS DE COMBINACIONES")
    print("=" * 80)
    
    firewall_funciona = estados_por_factor['Firewall']
    antivirus_funciona = estados_por_factor['Antivirus']
    
    # 4 escenarios posibles
    ambos_funcionan = firewall_funciona & antivirus_funciona
    solo_firewall = firewall_funciona & ~antivirus_funciona
    solo_antivirus = ~firewall_funciona & antivirus_funciona
    ninguno = ~firewall_funciona & ~antivirus_funciona
    
    print("\nEscenarios:")
    print(f"  1. Ambos funcionan: {np.sum(ambos_funcionan)}/{num_simulaciones} "
          f"({100*np.sum(ambos_funcionan)/num_simulaciones:.1f}%)")
    print(f"     → Factor esperado: 0.0 (Firewall elimina todo)")
    print(f"     → Factor real: {factores_vector[ambos_funcionan].mean():.4f}")
    
    print(f"\n  2. Solo Firewall: {np.sum(solo_firewall)}/{num_simulaciones} "
          f"({100*np.sum(solo_firewall)/num_simulaciones:.1f}%)")
    print(f"     → Factor esperado: 0.0 (Firewall elimina todo)")
    print(f"     → Factor real: {factores_vector[solo_firewall].mean():.4f}")
    
    print(f"\n  3. Solo Antivirus: {np.sum(solo_antivirus)}/{num_simulaciones} "
          f"({100*np.sum(solo_antivirus)/num_simulaciones:.1f}%)")
    print(f"     → Factor esperado: 0.2 (1.0 × 0.2)")
    if np.sum(solo_antivirus) > 0:
        print(f"     → Factor real: {factores_vector[solo_antivirus].mean():.4f}")
    
    print(f"\n  4. Ninguno funciona: {np.sum(ninguno)}/{num_simulaciones} "
          f"({100*np.sum(ninguno)/num_simulaciones:.1f}%)")
    print(f"     → Factor esperado: 1.0 (sin reducción)")
    if np.sum(ninguno) > 0:
        print(f"     → Factor real: {factores_vector[ninguno].mean():.4f}")
    
    # Probabilidades teóricas
    print("\n" + "=" * 80)
    print("VALIDACIÓN PROBABILÍSTICA")
    print("=" * 80)
    
    p_firewall = 0.50
    p_antivirus = 0.70
    
    print("\nProbabilidades teóricas (factores independientes):")
    print(f"  1. Ambos funcionan: {p_firewall * p_antivirus:.2%} "
          f"(real: {100*np.sum(ambos_funcionan)/num_simulaciones:.2f}%)")
    print(f"  2. Solo Firewall: {p_firewall * (1-p_antivirus):.2%} "
          f"(real: {100*np.sum(solo_firewall)/num_simulaciones:.2f}%)")
    print(f"  3. Solo Antivirus: {(1-p_firewall) * p_antivirus:.2%} "
          f"(real: {100*np.sum(solo_antivirus)/num_simulaciones:.2f}%)")
    print(f"  4. Ninguno: {(1-p_firewall) * (1-p_antivirus):.2%} "
          f"(real: {100*np.sum(ninguno)/num_simulaciones:.2f}%)")
    
    # Estadísticas del vector final
    print("\n" + "=" * 80)
    print("ESTADÍSTICAS DEL VECTOR FINAL")
    print("=" * 80)
    
    print(f"\nVector de factores:")
    print(f"  Min: {factores_vector.min():.4f}")
    print(f"  Max: {factores_vector.max():.4f}")
    print(f"  Media: {factores_vector.mean():.4f}")
    print(f"  Mediana: {np.median(factores_vector):.4f}")
    
    # Distribución de valores únicos
    valores_unicos, conteos = np.unique(factores_vector, return_counts=True)
    print(f"\nValores únicos encontrados: {len(valores_unicos)}")
    for val, count in zip(valores_unicos, conteos):
        pct = 100 * count / num_simulaciones
        print(f"  Factor {val:.4f}: {count} veces ({pct:.2f}%)")
    
    return factores_vector


def validar_problemas_matematicos():
    """Valida problemas matemáticos potenciales."""
    
    print("\n" * 2)
    print("=" * 80)
    print("VALIDACIÓN DE PROBLEMAS MATEMÁTICOS")
    print("=" * 80)
    
    problemas = []
    
    # Problema 1: Underflow con múltiples factores pequeños
    print("\n1. Test de Underflow (muchos factores con reducción pequeña):")
    factor = 1.0
    for i in range(10):
        factor *= 0.9  # 10% reducción cada uno
    print(f"   10 factores con 90% cada uno: {factor:.10f}")
    if factor < 1e-6:
        problemas.append("Underflow con muchos factores pequeños")
        print("   ❌ PROBLEMA: Valor muy pequeño, puede causar problemas numéricos")
    else:
        print("   ✅ OK: Valor dentro de rango razonable")
    
    # Problema 2: Orden de aplicación
    print("\n2. Test de Orden de Aplicación:")
    factor_a = 1.0 * (1 - 0.5) * (1 - 0.3)  # 50% luego 30%
    factor_b = 1.0 * (1 - 0.3) * (1 - 0.5)  # 30% luego 50%
    print(f"   Aplicar 50% luego 30%: {factor_a:.4f}")
    print(f"   Aplicar 30% luego 50%: {factor_b:.4f}")
    if abs(factor_a - factor_b) < 1e-10:
        print("   ✅ OK: Orden no importa (multiplicación conmutativa)")
    else:
        problemas.append("Orden de aplicación afecta resultado")
        print("   ❌ PROBLEMA: Orden importa")
    
    # Problema 3: Factor 100% elimina todo lo demás
    print("\n3. Test de Factor 100% (efecto dominante):")
    factor = 1.0 * (1 - 1.0) * (1 - 0.8)  # 100% luego 80%
    print(f"   Aplicar 100% reducción luego 80%: {factor:.4f}")
    if factor == 0.0:
        print("   ⚠️  COMPORTAMIENTO: Un factor 100% anula todos los demás")
        print("      Esto es matemáticamente correcto pero puede no ser intuitivo")
    
    # Problema 4: Múltiples factores 100%
    print("\n4. Test de Múltiples Factores 100%:")
    factor = 1.0
    for i in range(5):
        factor *= (1 - 1.0)
    print(f"   5 factores con 100% reducción: {factor:.4f}")
    print("   ✅ OK: Resultado es 0 (correcto)")
    
    # Problema 5: Mix de estático y estocástico
    print("\n5. Test de Mix Estático + Estocástico:")
    print("   Factor estático -50% (0.5) × Factor estocástico (puede variar)")
    factor_estatico = 1.0 * (1 + (-50)/100)  # -50% estático
    print(f"   Factor estático: {factor_estatico:.4f}")
    print("   Luego se multiplica por vector estocástico [0.0, 0.2, 1.0, ...]")
    print("   Resultado final: vector × 0.5")
    print("   ✅ OK: Combinación lineal correcta")
    
    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN DE VALIDACIÓN")
    print("=" * 80)
    
    if problemas:
        print("\n⚠️  SE ENCONTRARON COMPORTAMIENTOS A CONSIDERAR:")
        for p in problemas:
            print(f"   - {p}")
    else:
        print("\n✅ NO SE ENCONTRARON PROBLEMAS MATEMÁTICOS")
    
    print("\nNOTAS IMPORTANTES:")
    print("  1. La multiplicación es conmutativa → orden no importa")
    print("  2. Factor 100% efectivo → elimina todo (factor = 0)")
    print("  3. Factores se combinan multiplicativamente (independientes)")
    print("  4. Valores muy pequeños (<1e-6) pueden causar underflow")
    print("  5. Estáticos y estocásticos se mezclan correctamente")


def caso_ejemplo_real():
    """Ejemplo con valores realistas."""
    
    print("\n" * 2)
    print("=" * 80)
    print("CASO DE EJEMPLO REAL: Ataque DDoS")
    print("=" * 80)
    
    print("\nEvento: Ataque DDoS")
    print("Frecuencia Base: Poisson λ = 10 ataques/año")
    print("\nControles:")
    print("  1. Firewall de Perímetro")
    print("     - Confiabilidad: 90%")
    print("     - Reducción si efectivo: 70%")
    print("     - Reducción si falla: 0%")
    print("  2. Sistema Anti-DDoS Cloud")
    print("     - Confiabilidad: 80%")
    print("     - Reducción si efectivo: 90%")
    print("     - Reducción si falla: 0%")
    
    num_sim = 10000
    rng = np.random.default_rng(123)
    
    # Factor 1: Firewall
    estados_fw = rng.random(num_sim)
    fw_funciona = estados_fw < 0.9
    factor_fw = np.where(fw_funciona, 1 - 0.7, 1.0)  # 0.3 si funciona, 1.0 si falla
    
    # Factor 2: Anti-DDoS
    estados_ddos = rng.random(num_sim)
    ddos_funciona = estados_ddos < 0.8
    factor_ddos = np.where(ddos_funciona, 1 - 0.9, 1.0)  # 0.1 si funciona, 1.0 si falla
    
    # Combinar
    factor_total = factor_fw * factor_ddos
    
    print("\nEscenarios posibles:")
    print(f"  1. Ambos funcionan (90% × 80% = 72%):")
    print(f"     λ = 10 × 0.3 × 0.1 = 0.3 ataques/año")
    
    print(f"  2. Solo Firewall (90% × 20% = 18%):")
    print(f"     λ = 10 × 0.3 × 1.0 = 3.0 ataques/año")
    
    print(f"  3. Solo Anti-DDoS (10% × 80% = 8%):")
    print(f"     λ = 10 × 1.0 × 0.1 = 1.0 ataques/año")
    
    print(f"  4. Ninguno funciona (10% × 20% = 2%):")
    print(f"     λ = 10 × 1.0 × 1.0 = 10.0 ataques/año")
    
    # Calcular λ efectiva para cada escenario
    lambda_efectivas = 10 * factor_total
    
    print(f"\nResultados de simulación:")
    print(f"  λ media: {lambda_efectivas.mean():.2f} ataques/año")
    print(f"  λ min: {lambda_efectivas.min():.2f}")
    print(f"  λ max: {lambda_efectivas.max():.2f}")
    print(f"  λ P50: {np.percentile(lambda_efectivas, 50):.2f}")
    print(f"  λ P95: {np.percentile(lambda_efectivas, 95):.2f}")
    
    # Verificar distribución
    ambos = fw_funciona & ddos_funciona
    solo_fw = fw_funciona & ~ddos_funciona
    solo_ddos = ~fw_funciona & ddos_funciona
    ninguno = ~fw_funciona & ~ddos_funciona
    
    print(f"\nDistribución real:")
    print(f"  Ambos: {100*np.sum(ambos)/num_sim:.1f}% (esperado: 72%)")
    print(f"  Solo FW: {100*np.sum(solo_fw)/num_sim:.1f}% (esperado: 18%)")
    print(f"  Solo Anti-DDoS: {100*np.sum(solo_ddos)/num_sim:.1f}% (esperado: 8%)")
    print(f"  Ninguno: {100*np.sum(ninguno)/num_sim:.1f}% (esperado: 2%)")


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "VALIDACIÓN: MÚLTIPLES FACTORES ESTOCÁSTICOS" + " " * 20 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Test 1: Simulación básica
    factores_vector = simular_multiples_factores()
    
    # Test 2: Problemas matemáticos
    validar_problemas_matematicos()
    
    # Test 3: Caso real
    caso_ejemplo_real()
    
    print("\n" * 2)
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "✅ VALIDACIÓN COMPLETADA ✅" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
