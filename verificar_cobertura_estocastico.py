"""
Script de Verificación: Cobertura de Factores Estocásticos
============================================================

Este script verifica que todos los caminos de código donde se generan
muestras de frecuencia incluyen soporte para factores estocásticos.
"""

import re

def verificar_cobertura():
    """Verifica la cobertura de factores estocásticos en el código."""
    
    print("=" * 80)
    print("VERIFICACIÓN DE COBERTURA: FACTORES ESTOCÁSTICOS")
    print("=" * 80)
    
    # Leer archivo
    with open('Risk_Lab_Beta.py', 'r', encoding='utf-8') as f:
        codigo = f.read()
    
    # Buscar todos los bloques donde se usa usa_estocastico
    patron_usa_estocastico = r"usa_estocastico = evento\.get\('_usa_estocastico', False\)"
    usos = list(re.finditer(patron_usa_estocastico, codigo))
    
    print(f"\n✅ Encontrados {len(usos)} bloques que verifican '_usa_estocastico'")
    
    for i, match in enumerate(usos, 1):
        linea = codigo[:match.start()].count('\n') + 1
        print(f"   {i}. Línea {linea}")
    
    # Verificar que cada bloque tiene soporte para las 5 distribuciones
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE DISTRIBUCIONES POR BLOQUE")
    print("=" * 80)
    
    distribuciones = [
        ("Poisson", r"freq_opcion == 1"),
        ("Binomial", r"freq_opcion == 2"),
        ("Bernoulli", r"freq_opcion == 3"),
        ("Poisson-Gamma", r"freq_opcion == 4"),
        ("Beta", r"freq_opcion == 5")
    ]
    
    # Para cada uso de usa_estocastico, verificar contexto
    for i, match in enumerate(usos, 1):
        linea_inicio = codigo[:match.start()].count('\n') + 1
        
        # Extraer las siguientes 500 líneas de código después del match
        contexto = codigo[match.start():match.start() + 20000]
        
        print(f"\nBloque {i} (línea {linea_inicio}):")
        
        for nombre, patron in distribuciones:
            if re.search(patron, contexto[:5000]):  # Buscar en las siguientes líneas
                print(f"   ✅ {nombre}")
            else:
                print(f"   ❌ {nombre} - NO ENCONTRADO")
    
    # Verificar uso correcto de factores_vector[indices]
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE SLICING CORRECTO")
    print("=" * 80)
    
    patron_slicing = r"factores_vector\[indices_a_simular\]"
    slicings = list(re.finditer(patron_slicing, codigo))
    
    print(f"\n✅ Encontrados {len(slicings)} usos de 'factores_vector[indices_a_simular]'")
    
    # Verificar que hay al menos 3 (vínculos nuevos, vínculos antiguos con padres, vínculos antiguos sin padres)
    if len(slicings) >= 15:  # 5 distribuciones × 3 bloques
        print("✅ Cobertura adecuada (esperado: 15+, encontrado: {})".format(len(slicings)))
    else:
        print("⚠️  Cobertura puede ser insuficiente (esperado: 15+, encontrado: {})".format(len(slicings)))
    
    # Verificar imports correctos
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE IMPORTS")
    print("=" * 80)
    
    # Verificar que NO existe beta_dist.rvs (excepto self.beta_dist que es válido)
    patron_beta_dist_error = r"(?<!self\.)beta_dist\.rvs"
    if re.search(patron_beta_dist_error, codigo):
        print("❌ ERROR: Encontrado 'beta_dist.rvs' sin 'self.' (debería ser 'beta.rvs')")
    else:
        print("✅ No se encontró 'beta_dist.rvs' incorrecto (correcto)")
    
    # Verificar que existe beta.rvs
    if "beta.rvs" in codigo:
        print("✅ Encontrado 'beta.rvs' (correcto)")
    else:
        print("⚠️  No se encontró 'beta.rvs'")
    
    # Verificar flags guardados
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE FLAGS")
    print("=" * 80)
    
    if "evento['_usa_estocastico'] = True" in codigo:
        print("✅ Flag '_usa_estocastico' se guarda correctamente")
    else:
        print("❌ Flag '_usa_estocastico' NO se guarda")
    
    if "evento['_factores_vector'] = factores_vector" in codigo:
        print("✅ Flag '_factores_vector' se guarda correctamente")
    else:
        print("❌ Flag '_factores_vector' NO se guarda")
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    
    issues = []
    
    if len(usos) < 4:
        issues.append(f"Solo {len(usos)} bloques verifican '_usa_estocastico' (esperado: 4)")
    
    patron_beta_dist_error = r"(?<!self\.)beta_dist\.rvs"
    if re.search(patron_beta_dist_error, codigo):
        issues.append("Bug: 'beta_dist.rvs' encontrado (debería ser 'beta.rvs')")
    
    if "evento['_usa_estocastico'] = True" not in codigo:
        issues.append("Flag '_usa_estocastico' no se guarda")
    
    if "evento['_factores_vector'] = factores_vector" not in codigo:
        issues.append("Flag '_factores_vector' no se guarda")
    
    if issues:
        print("\n❌ SE ENCONTRARON PROBLEMAS:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("\n✅ NO SE ENCONTRARON PROBLEMAS")
        print("   Sistema de factores estocásticos completamente implementado")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        verificar_cobertura()
    except FileNotFoundError:
        print("ERROR: No se encontró el archivo Risk_Lab_Beta.py")
        print("Asegúrate de ejecutar este script desde el directorio correcto")
    except Exception as e:
        print(f"ERROR: {str(e)}")
