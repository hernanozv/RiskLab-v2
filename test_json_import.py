"""
Test de validación exhaustiva: genera un JSON completo usando SOLO las reglas de los docs,
luego valida contra la lógica real de cargar_configuracion en Risk_Lab_Beta.py.

Cubre:
- 5 distribuciones de severidad: Normal(direct), LogNormal(direct 3 opciones), PERT, Pareto/GPD(direct), Uniforme
- 5 distribuciones de frecuencia: Poisson, Binomial, Bernoulli, Poisson-Gamma, Beta
- 3 tipos de factores: estático, estocástico, seguro
- Vínculos: AND, OR, EXCLUYE con parámetros avanzados
- Escalamiento de severidad por frecuencia (reincidencia + sistémico)
- Escenario completo
"""

import json
import sys
import os
import uuid
import traceback
import numpy as np

# Add the workspace to path so we can import Risk Lab functions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================================
# STEP 1: Build JSON purely from documentation rules (acting as AI agent)
# ============================================================================

# Generate deterministic UUIDs for reproducibility
def make_id(n):
    return f"00000000-0000-0000-0000-{n:012d}"

EVT1_ID = make_id(1)  # PERT + Poisson (basic, root event)
EVT2_ID = make_id(2)  # LogNormal direct (mean/std) + Binomial + static factor
EVT3_ID = make_id(3)  # Pareto/GPD direct + Bernoulli + stochastic factor
EVT4_ID = make_id(4)  # Normal direct (mu/sigma) + Poisson-Gamma + insurance factor
EVT5_ID = make_id(5)  # Uniforme + Beta freq + escalamiento reincidencia
EVT6_ID = make_id(6)  # PERT + Poisson, child AND of EVT1
EVT7_ID = make_id(7)  # LogNormal direct (s/scale/loc) + Poisson, child OR of EVT2+EVT3
EVT8_ID = make_id(8)  # PERT + Poisson, EXCLUYE EVT1
EVT9_ID = make_id(9)  # Normal min_mode_max + Poisson + escalamiento sistémico

test_json = {
    "num_simulaciones": 10000,
    "eventos_riesgo": [
        # ================================================================
        # EVENT 1: PERT (sev_opcion=3) + Poisson (freq_opcion=1)
        # Basic event, root, no factors, no vinculos
        # ================================================================
        {
            "id": EVT1_ID,
            "nombre": "E1: Fraude en pagos (PERT+Poisson)",
            "activo": True,
            
            "sev_opcion": 3,
            "sev_input_method": "min_mode_max",
            "sev_minimo": 10000,
            "sev_mas_probable": 50000,
            "sev_maximo": 200000,
            "sev_params_direct": {},
            
            "freq_opcion": 1,
            "tasa": 3.0,
            "num_eventos": None,
            "prob_exito": None,
            "pg_minimo": None,
            "pg_mas_probable": None,
            "pg_maximo": None,
            "pg_confianza": None,
            "pg_alpha": None,
            "pg_beta": None,
            "beta_minimo": None,
            "beta_mas_probable": None,
            "beta_maximo": None,
            "beta_confianza": None,
            "beta_alpha": None,
            "beta_beta": None,
            
            "sev_freq_activado": False,
            "sev_freq_modelo": "reincidencia",
            "sev_freq_tipo_escalamiento": "lineal",
            "sev_freq_paso": 0.5,
            "sev_freq_base": 1.5,
            "sev_freq_factor_max": 5.0,
            "sev_freq_tabla": [],
            "sev_freq_alpha": 0.5,
            "sev_freq_solo_aumento": True,
            "sev_freq_sistemico_factor_max": 3.0,
            
            "vinculos": [],
            "factores_ajuste": []
        },
        
        # ================================================================
        # EVENT 2: LogNormal direct (mean/std) + Binomial + static factor
        # ================================================================
        {
            "id": EVT2_ID,
            "nombre": "E2: Ciberataque (LogNormal mean/std + Binomial)",
            "activo": True,
            
            "sev_opcion": 2,
            "sev_input_method": "direct",
            "sev_minimo": None,
            "sev_mas_probable": None,
            "sev_maximo": None,
            "sev_params_direct": {"mean": 150000, "std": 75000},
            
            "freq_opcion": 2,
            "tasa": None,
            "num_eventos": 12,
            "prob_exito": 0.08,
            "pg_minimo": None,
            "pg_mas_probable": None,
            "pg_maximo": None,
            "pg_confianza": None,
            "pg_alpha": None,
            "pg_beta": None,
            "beta_minimo": None,
            "beta_mas_probable": None,
            "beta_maximo": None,
            "beta_confianza": None,
            "beta_alpha": None,
            "beta_beta": None,
            
            "sev_freq_activado": False,
            "sev_freq_modelo": "reincidencia",
            "sev_freq_tipo_escalamiento": "lineal",
            "sev_freq_paso": 0.5,
            "sev_freq_base": 1.5,
            "sev_freq_factor_max": 5.0,
            "sev_freq_tabla": [],
            "sev_freq_alpha": 0.5,
            "sev_freq_solo_aumento": True,
            "sev_freq_sistemico_factor_max": 3.0,
            
            "vinculos": [],
            "factores_ajuste": [
                {
                    "nombre": "Firewall WAF",
                    "tipo_modelo": "estatico",
                    "activo": True,
                    "afecta_frecuencia": True,
                    "impacto_porcentual": -30,
                    "afecta_severidad": False,
                    "impacto_severidad_pct": 0,
                    "tipo_severidad": "porcentual"
                }
            ]
        },
        
        # ================================================================
        # EVENT 3: Pareto/GPD direct + Bernoulli + stochastic factor
        # ================================================================
        {
            "id": EVT3_ID,
            "nombre": "E3: Evento catastrófico (Pareto/GPD + Bernoulli)",
            "activo": True,
            
            "sev_opcion": 4,
            "sev_input_method": "direct",
            "sev_minimo": None,
            "sev_mas_probable": None,
            "sev_maximo": None,
            "sev_params_direct": {"c": 0.3, "scale": 500000, "loc": 100000},
            
            "freq_opcion": 3,
            "tasa": None,
            "num_eventos": None,
            "prob_exito": 0.15,
            "pg_minimo": None,
            "pg_mas_probable": None,
            "pg_maximo": None,
            "pg_confianza": None,
            "pg_alpha": None,
            "pg_beta": None,
            "beta_minimo": None,
            "beta_mas_probable": None,
            "beta_maximo": None,
            "beta_confianza": None,
            "beta_alpha": None,
            "beta_beta": None,
            
            "sev_freq_activado": False,
            "sev_freq_modelo": "reincidencia",
            "sev_freq_tipo_escalamiento": "lineal",
            "sev_freq_paso": 0.5,
            "sev_freq_base": 1.5,
            "sev_freq_factor_max": 5.0,
            "sev_freq_tabla": [],
            "sev_freq_alpha": 0.5,
            "sev_freq_solo_aumento": True,
            "sev_freq_sistemico_factor_max": 3.0,
            
            "vinculos": [],
            "factores_ajuste": [
                {
                    "nombre": "Plan de contingencia",
                    "tipo_modelo": "estocastico",
                    "activo": True,
                    "afecta_frecuencia": True,
                    "impacto_porcentual": 0,
                    "afecta_severidad": True,
                    "impacto_severidad_pct": 0,
                    "confiabilidad": 70,
                    "reduccion_efectiva": 80,
                    "reduccion_fallo": 10,
                    "reduccion_severidad_efectiva": 50,
                    "reduccion_severidad_fallo": 5,
                    "tipo_severidad": "porcentual"
                }
            ]
        },
        
        # ================================================================
        # EVENT 4: Normal direct (mu/sigma) + Poisson-Gamma + insurance
        # pg_alpha and pg_beta MUST be provided (never null)
        # ================================================================
        {
            "id": EVT4_ID,
            "nombre": "E4: Falla operativa (Normal direct + PG)",
            "activo": True,
            
            "sev_opcion": 1,
            "sev_input_method": "direct",
            "sev_minimo": None,
            "sev_mas_probable": None,
            "sev_maximo": None,
            "sev_params_direct": {"mu": 80000, "sigma": 20000},
            
            "freq_opcion": 4,
            "tasa": None,
            "num_eventos": None,
            "prob_exito": None,
            "pg_minimo": 1,
            "pg_mas_probable": 3,
            "pg_maximo": 8,
            "pg_confianza": 90,
            "pg_alpha": 4.5,
            "pg_beta": 1.5,
            "beta_minimo": None,
            "beta_mas_probable": None,
            "beta_maximo": None,
            "beta_confianza": None,
            "beta_alpha": None,
            "beta_beta": None,
            
            "sev_freq_activado": False,
            "sev_freq_modelo": "reincidencia",
            "sev_freq_tipo_escalamiento": "lineal",
            "sev_freq_paso": 0.5,
            "sev_freq_base": 1.5,
            "sev_freq_factor_max": 5.0,
            "sev_freq_tabla": [],
            "sev_freq_alpha": 0.5,
            "sev_freq_solo_aumento": True,
            "sev_freq_sistemico_factor_max": 3.0,
            
            "vinculos": [],
            "factores_ajuste": [
                {
                    "nombre": "Póliza de seguro cyber",
                    "tipo_modelo": "estatico",
                    "activo": True,
                    "afecta_frecuencia": False,
                    "impacto_porcentual": 0,
                    "afecta_severidad": True,
                    "impacto_severidad_pct": 0,
                    "tipo_severidad": "seguro",
                    "seguro_deducible": 25000,
                    "seguro_cobertura_pct": 80,
                    "seguro_limite": 500000,
                    "seguro_tipo_deducible": "por_ocurrencia",
                    "seguro_limite_ocurrencia": 200000
                }
            ]
        },
        
        # ================================================================
        # EVENT 5: Uniforme + Beta freq + escalamiento reincidencia
        # beta_alpha/beta_beta MUST be provided (never null)
        # beta_minimo/mas_probable/maximo/confianza are percentages 0-100
        # ================================================================
        {
            "id": EVT5_ID,
            "nombre": "E5: Incidente regulatorio (Uniforme + Beta)",
            "activo": True,
            
            "sev_opcion": 5,
            "sev_input_method": "min_mode_max",
            "sev_minimo": 20000,
            "sev_mas_probable": 50000,
            "sev_maximo": 80000,
            "sev_params_direct": {},
            
            "freq_opcion": 5,
            "tasa": None,
            "num_eventos": None,
            "prob_exito": None,
            "pg_minimo": None,
            "pg_mas_probable": None,
            "pg_maximo": None,
            "pg_confianza": None,
            "pg_alpha": None,
            "pg_beta": None,
            "beta_minimo": 10,
            "beta_mas_probable": 25,
            "beta_maximo": 50,
            "beta_confianza": 90,
            "beta_alpha": 2.5,
            "beta_beta": 7.5,
            
            "sev_freq_activado": True,
            "sev_freq_modelo": "reincidencia",
            "sev_freq_tipo_escalamiento": "lineal",
            "sev_freq_paso": 0.3,
            "sev_freq_base": 1.5,
            "sev_freq_factor_max": 3.0,
            "sev_freq_tabla": [
                {"desde": 1, "hasta": 2, "multiplicador": 1.0},
                {"desde": 3, "hasta": None, "multiplicador": 2.0}
            ],
            "sev_freq_alpha": 0.5,
            "sev_freq_solo_aumento": True,
            "sev_freq_sistemico_factor_max": 3.0,
            
            "vinculos": [],
            "factores_ajuste": []
        },
        
        # ================================================================
        # EVENT 6: PERT + Poisson, child AND of EVT1
        # ================================================================
        {
            "id": EVT6_ID,
            "nombre": "E6: Consecuencia de fraude (AND child)",
            "activo": True,
            
            "sev_opcion": 3,
            "sev_input_method": "min_mode_max",
            "sev_minimo": 5000,
            "sev_mas_probable": 15000,
            "sev_maximo": 50000,
            "sev_params_direct": {},
            
            "freq_opcion": 1,
            "tasa": 1.0,
            "num_eventos": None,
            "prob_exito": None,
            "pg_minimo": None,
            "pg_mas_probable": None,
            "pg_maximo": None,
            "pg_confianza": None,
            "pg_alpha": None,
            "pg_beta": None,
            "beta_minimo": None,
            "beta_mas_probable": None,
            "beta_maximo": None,
            "beta_confianza": None,
            "beta_alpha": None,
            "beta_beta": None,
            
            "sev_freq_activado": False,
            "sev_freq_modelo": "reincidencia",
            "sev_freq_tipo_escalamiento": "lineal",
            "sev_freq_paso": 0.5,
            "sev_freq_base": 1.5,
            "sev_freq_factor_max": 5.0,
            "sev_freq_tabla": [],
            "sev_freq_alpha": 0.5,
            "sev_freq_solo_aumento": True,
            "sev_freq_sistemico_factor_max": 3.0,
            
            "vinculos": [
                {
                    "id_padre": EVT1_ID,
                    "tipo": "AND",
                    "probabilidad": 80,
                    "factor_severidad": 1.5,
                    "umbral_severidad": 30000
                }
            ],
            "factores_ajuste": []
        },
        
        # ================================================================
        # EVENT 7: LogNormal direct (s/scale/loc) + Poisson, child OR of EVT2+EVT3
        # ================================================================
        {
            "id": EVT7_ID,
            "nombre": "E7: Pérdida reputacional (OR child, LogNormal s/scale)",
            "activo": True,
            
            "sev_opcion": 2,
            "sev_input_method": "direct",
            "sev_minimo": None,
            "sev_mas_probable": None,
            "sev_maximo": None,
            "sev_params_direct": {"s": 1.2, "scale": 50000, "loc": 0},
            
            "freq_opcion": 1,
            "tasa": 0.5,
            "num_eventos": None,
            "prob_exito": None,
            "pg_minimo": None,
            "pg_mas_probable": None,
            "pg_maximo": None,
            "pg_confianza": None,
            "pg_alpha": None,
            "pg_beta": None,
            "beta_minimo": None,
            "beta_mas_probable": None,
            "beta_maximo": None,
            "beta_confianza": None,
            "beta_alpha": None,
            "beta_beta": None,
            
            "sev_freq_activado": False,
            "sev_freq_modelo": "reincidencia",
            "sev_freq_tipo_escalamiento": "lineal",
            "sev_freq_paso": 0.5,
            "sev_freq_base": 1.5,
            "sev_freq_factor_max": 5.0,
            "sev_freq_tabla": [],
            "sev_freq_alpha": 0.5,
            "sev_freq_solo_aumento": True,
            "sev_freq_sistemico_factor_max": 3.0,
            
            "vinculos": [
                {
                    "id_padre": EVT2_ID,
                    "tipo": "OR",
                    "probabilidad": 60,
                    "factor_severidad": 2.0,
                    "umbral_severidad": 100000
                },
                {
                    "id_padre": EVT3_ID,
                    "tipo": "OR",
                    "probabilidad": 40,
                    "factor_severidad": 1.0,
                    "umbral_severidad": 0
                }
            ],
            "factores_ajuste": []
        },
        
        # ================================================================
        # EVENT 8: PERT + Poisson, EXCLUYE EVT1
        # factor_severidad MUST be 1.0 for EXCLUYE
        # ================================================================
        {
            "id": EVT8_ID,
            "nombre": "E8: Alternativa a fraude (EXCLUYE)",
            "activo": True,
            
            "sev_opcion": 3,
            "sev_input_method": "min_mode_max",
            "sev_minimo": 8000,
            "sev_mas_probable": 25000,
            "sev_maximo": 60000,
            "sev_params_direct": {},
            
            "freq_opcion": 1,
            "tasa": 2.0,
            "num_eventos": None,
            "prob_exito": None,
            "pg_minimo": None,
            "pg_mas_probable": None,
            "pg_maximo": None,
            "pg_confianza": None,
            "pg_alpha": None,
            "pg_beta": None,
            "beta_minimo": None,
            "beta_mas_probable": None,
            "beta_maximo": None,
            "beta_confianza": None,
            "beta_alpha": None,
            "beta_beta": None,
            
            "sev_freq_activado": False,
            "sev_freq_modelo": "reincidencia",
            "sev_freq_tipo_escalamiento": "lineal",
            "sev_freq_paso": 0.5,
            "sev_freq_base": 1.5,
            "sev_freq_factor_max": 5.0,
            "sev_freq_tabla": [],
            "sev_freq_alpha": 0.5,
            "sev_freq_solo_aumento": True,
            "sev_freq_sistemico_factor_max": 3.0,
            
            "vinculos": [
                {
                    "id_padre": EVT1_ID,
                    "tipo": "EXCLUYE",
                    "probabilidad": 100,
                    "factor_severidad": 1.0,
                    "umbral_severidad": 0
                }
            ],
            "factores_ajuste": []
        },
        
        # ================================================================
        # EVENT 9: Normal min_mode_max + Poisson + escalamiento sistémico
        # ================================================================
        {
            "id": EVT9_ID,
            "nombre": "E9: Riesgo sistémico (Normal mmm + escalamiento sistémico)",
            "activo": True,
            
            "sev_opcion": 1,
            "sev_input_method": "min_mode_max",
            "sev_minimo": 30000,
            "sev_mas_probable": 60000,
            "sev_maximo": 120000,
            "sev_params_direct": {},
            
            "freq_opcion": 1,
            "tasa": 5.0,
            "num_eventos": None,
            "prob_exito": None,
            "pg_minimo": None,
            "pg_mas_probable": None,
            "pg_maximo": None,
            "pg_confianza": None,
            "pg_alpha": None,
            "pg_beta": None,
            "beta_minimo": None,
            "beta_mas_probable": None,
            "beta_maximo": None,
            "beta_confianza": None,
            "beta_alpha": None,
            "beta_beta": None,
            
            "sev_freq_activado": True,
            "sev_freq_modelo": "sistemico",
            "sev_freq_tipo_escalamiento": "lineal",
            "sev_freq_paso": 0.5,
            "sev_freq_base": 1.5,
            "sev_freq_factor_max": 5.0,
            "sev_freq_tabla": [],
            "sev_freq_alpha": 0.5,
            "sev_freq_solo_aumento": True,
            "sev_freq_sistemico_factor_max": 3.0,
            
            "vinculos": [],
            "factores_ajuste": [
                {
                    "nombre": "Control de compliance",
                    "tipo_modelo": "estatico",
                    "activo": True,
                    "afecta_frecuencia": True,
                    "impacto_porcentual": -25,
                    "afecta_severidad": True,
                    "impacto_severidad_pct": -15,
                    "tipo_severidad": "porcentual"
                },
                {
                    "nombre": "Monitoreo automático",
                    "tipo_modelo": "estocastico",
                    "activo": True,
                    "afecta_frecuencia": True,
                    "impacto_porcentual": 0,
                    "afecta_severidad": False,
                    "impacto_severidad_pct": 0,
                    "confiabilidad": 90,
                    "reduccion_efectiva": 60,
                    "reduccion_fallo": 5,
                    "reduccion_severidad_efectiva": 0,
                    "reduccion_severidad_fallo": 0,
                    "tipo_severidad": "porcentual"
                }
            ]
        }
    ],
    
    # ================================================================
    # SCENARIO: Pessimistic variant
    # ================================================================
    "scenarios": [
        {
            "nombre": "Escenario Pesimista",
            "descripcion": "Aumenta frecuencias y severidades",
            "eventos_riesgo": [
                # Copy of EVT1 with higher severity
                {
                    "id": make_id(101),
                    "nombre": "E1: Fraude en pagos (PERT+Poisson)",
                    "activo": True,
                    "sev_opcion": 3,
                    "sev_input_method": "min_mode_max",
                    "sev_minimo": 20000,
                    "sev_mas_probable": 100000,
                    "sev_maximo": 400000,
                    "sev_params_direct": {},
                    "freq_opcion": 1,
                    "tasa": 5.0,
                    "num_eventos": None,
                    "prob_exito": None,
                    "pg_minimo": None,
                    "pg_mas_probable": None,
                    "pg_maximo": None,
                    "pg_confianza": None,
                    "pg_alpha": None,
                    "pg_beta": None,
                    "beta_minimo": None,
                    "beta_mas_probable": None,
                    "beta_maximo": None,
                    "beta_confianza": None,
                    "beta_alpha": None,
                    "beta_beta": None,
                    "sev_freq_activado": False,
                    "sev_freq_modelo": "reincidencia",
                    "sev_freq_tipo_escalamiento": "lineal",
                    "sev_freq_paso": 0.5,
                    "sev_freq_base": 1.5,
                    "sev_freq_factor_max": 5.0,
                    "sev_freq_tabla": [],
                    "sev_freq_alpha": 0.5,
                    "sev_freq_solo_aumento": True,
                    "sev_freq_sistemico_factor_max": 3.0,
                    "vinculos": [],
                    "factores_ajuste": []
                },
                # Copy of EVT4 (PG) in scenario
                {
                    "id": make_id(104),
                    "nombre": "E4: Falla operativa (Normal direct + PG)",
                    "activo": True,
                    "sev_opcion": 1,
                    "sev_input_method": "direct",
                    "sev_minimo": None,
                    "sev_mas_probable": None,
                    "sev_maximo": None,
                    "sev_params_direct": {"mu": 120000, "sigma": 30000},
                    "freq_opcion": 4,
                    "tasa": None,
                    "num_eventos": None,
                    "prob_exito": None,
                    "pg_minimo": 2,
                    "pg_mas_probable": 5,
                    "pg_maximo": 12,
                    "pg_confianza": 90,
                    "pg_alpha": 6.0,
                    "pg_beta": 1.2,
                    "beta_minimo": None,
                    "beta_mas_probable": None,
                    "beta_maximo": None,
                    "beta_confianza": None,
                    "beta_alpha": None,
                    "beta_beta": None,
                    "sev_freq_activado": False,
                    "sev_freq_modelo": "reincidencia",
                    "sev_freq_tipo_escalamiento": "lineal",
                    "sev_freq_paso": 0.5,
                    "sev_freq_base": 1.5,
                    "sev_freq_factor_max": 5.0,
                    "sev_freq_tabla": [],
                    "sev_freq_alpha": 0.5,
                    "sev_freq_solo_aumento": True,
                    "sev_freq_sistemico_factor_max": 3.0,
                    "vinculos": [],
                    "factores_ajuste": [
                        {
                            "nombre": "Póliza de seguro cyber (pesimista)",
                            "tipo_modelo": "estatico",
                            "activo": True,
                            "afecta_frecuencia": False,
                            "impacto_porcentual": 0,
                            "afecta_severidad": True,
                            "impacto_severidad_pct": 0,
                            "tipo_severidad": "seguro",
                            "seguro_deducible": 50000,
                            "seguro_cobertura_pct": 70,
                            "seguro_limite": 300000,
                            "seguro_tipo_deducible": "agregado",
                            "seguro_limite_ocurrencia": 0
                        }
                    ]
                }
            ]
        }
    ],
    "current_scenario_name": None
}


# ============================================================================
# STEP 2: Validate JSON against the actual import code
# ============================================================================

def validate_json():
    """Simulate the exact logic of cargar_configuracion to validate the JSON."""
    
    # Import Risk Lab functions
    from Risk_Lab_Beta import (
        generar_distribucion_severidad,
        generar_distribucion_frecuencia,
        normalizar_factor_global
    )
    
    # Try to import PG/Beta distribution helpers
    try:
        from Risk_Lab_Beta import obtener_parametros_gamma_para_poisson
    except ImportError:
        obtener_parametros_gamma_para_poisson = None
    
    configuracion = test_json
    errors = []
    warnings = []
    success_count = 0
    total_events = 0
    
    print("=" * 70)
    print("VALIDACIÓN DE IMPORT JSON - Simulando cargar_configuracion()")
    print("=" * 70)
    
    # --- Validate root structure ---
    print("\n--- Validando estructura raíz ---")
    assert isinstance(configuracion.get('num_simulaciones'), int), "num_simulaciones debe ser int"
    assert isinstance(configuracion.get('eventos_riesgo'), list), "eventos_riesgo debe ser lista"
    assert isinstance(configuracion.get('scenarios'), list), "scenarios debe ser lista"
    print("✅ Estructura raíz válida")
    
    # --- Validate main events ---
    print("\n--- Validando eventos principales ---")
    id_mapeo = {}
    
    for i, evento_data in enumerate(configuracion.get('eventos_riesgo', [])):
        total_events += 1
        evt_name = evento_data.get('nombre', f'Event #{i}')
        print(f"\n  Evento {i+1}: {evt_name}")
        
        try:
            # 1. Test mandatory field access (same as cargar_configuracion lines 16410-16415)
            sev_opcion = evento_data['sev_opcion']
            sev_input_method = evento_data.get('sev_input_method', 'min_mode_max')
            sev_params_direct = evento_data.get('sev_params_direct', {})
            sev_minimo = evento_data['sev_minimo']
            sev_mas_probable = evento_data['sev_mas_probable']
            sev_maximo = evento_data['sev_maximo']
            
            # 2. Test severity distribution creation
            dist_sev = generar_distribucion_severidad(
                sev_opcion, sev_minimo, sev_mas_probable, sev_maximo,
                input_method=sev_input_method, params_direct=sev_params_direct
            )
            
            # 3. Test frequency distribution
            freq_opcion = evento_data['freq_opcion']
            tasa = evento_data.get('tasa', None)
            num_eventos = evento_data.get('num_eventos', None)
            prob_exito = evento_data.get('prob_exito', None)
            if tasa is not None: tasa = float(tasa)
            if num_eventos is not None: num_eventos = int(num_eventos)
            if prob_exito is not None: prob_exito = float(prob_exito)
            
            pg_params = None
            beta_params = None
            if freq_opcion == 4:
                alpha = evento_data.get('pg_alpha')
                beta_val = evento_data.get('pg_beta')
                if alpha is None or beta_val is None:
                    # Try fallback
                    pg_min = evento_data.get('pg_minimo')
                    pg_mode = evento_data.get('pg_mas_probable')
                    pg_max = evento_data.get('pg_maximo')
                    pg_conf = evento_data.get('pg_confianza')
                    if None not in (pg_min, pg_mode, pg_max, pg_conf) and obtener_parametros_gamma_para_poisson:
                        alpha, beta_val = obtener_parametros_gamma_para_poisson(
                            float(pg_min), float(pg_mode), float(pg_max), float(pg_conf)/100.0
                        )
                if alpha is not None and beta_val is not None:
                    pg_params = (float(alpha), float(beta_val))
            elif freq_opcion == 5:
                alpha = evento_data.get('beta_alpha')
                beta_val = evento_data.get('beta_beta')
                if alpha is not None and beta_val is not None:
                    beta_params = (float(alpha), float(beta_val))
            
            dist_freq = generar_distribucion_frecuencia(
                freq_opcion, tasa=tasa, num_eventos_posibles=num_eventos,
                probabilidad_exito=prob_exito, poisson_gamma_params=pg_params,
                beta_params=beta_params
            )
            
            # 4. Test factor normalization
            if 'factores_ajuste' in evento_data and evento_data['factores_ajuste']:
                for j, f in enumerate(evento_data['factores_ajuste']):
                    f_norm = normalizar_factor_global(f)
                    # Verify insurance fields
                    if f.get('tipo_severidad') == 'seguro':
                        assert f_norm.get('afecta_severidad') == True, \
                            f"Factor seguro '{f.get('nombre')}' MUST have afecta_severidad=True"
                    print(f"    ✅ Factor {j+1}: {f.get('nombre')} - normalizado OK")
            
            # 5. Test vinculo fields
            if evento_data.get('vinculos'):
                for v in evento_data['vinculos']:
                    _ = v['id_padre']  # Must exist
                    _ = v['tipo']  # Must exist
                    prob = max(1, min(100, int(v.get('probabilidad', 100))))
                    fsev = max(0.10, min(5.0, float(v.get('factor_severidad', 1.0))))
                    umbral = max(0, int(v.get('umbral_severidad', 0)))
                    print(f"    ✅ Vínculo: {v['tipo']} padre={v['id_padre'][:8]}... prob={prob} fsev={fsev} umbral={umbral}")
            
            # 6. Test id and nombre
            _ = evento_data['id']
            _ = evento_data['nombre']
            
            # 7. Verify escalamiento fields (if active)
            if evento_data.get('sev_freq_activado', False):
                modelo = evento_data.get('sev_freq_modelo', 'reincidencia')
                print(f"    ✅ Escalamiento: {modelo} activo")
            
            # 8. Sample from distributions to verify they work
            sev_sample = dist_sev.rvs(size=100)
            print(f"    ✅ Severidad: {type(dist_sev).__name__} - media muestral={np.mean(sev_sample):.0f}")
            
            if hasattr(dist_freq, 'rvs'):
                freq_sample = dist_freq.rvs(size=100)
                print(f"    ✅ Frecuencia: media muestral={np.mean(freq_sample):.2f}")
            elif hasattr(dist_freq, 'sample'):
                freq_sample = dist_freq.sample(100)
                print(f"    ✅ Frecuencia: media muestral={np.mean(freq_sample):.2f}")
            
            id_mapeo[evento_data['id']] = str(uuid.uuid4())
            success_count += 1
            print(f"    ✅ IMPORT OK")
            
        except Exception as e:
            errors.append(f"  ❌ {evt_name}: {e}")
            print(f"    ❌ ERROR: {e}")
            traceback.print_exc()
    
    # --- Validate vinculos reference existing events ---
    print("\n--- Validando referencias de vínculos ---")
    event_ids = {e['id'] for e in configuracion['eventos_riesgo']}
    for e in configuracion['eventos_riesgo']:
        for v in e.get('vinculos', []):
            if v['id_padre'] not in event_ids:
                errors.append(f"  ❌ Vínculo roto: {e['nombre']} refiere a padre {v['id_padre']} que no existe")
                print(f"  ❌ Vínculo roto: {e['nombre']} → {v['id_padre']}")
            else:
                print(f"  ✅ {e['nombre']} → padre {v['id_padre'][:8]}... existe")
    
    # --- Check for cycles (DAG) ---
    print("\n--- Verificando ausencia de ciclos (DAG) ---")
    from collections import defaultdict
    graph = defaultdict(list)
    for e in configuracion['eventos_riesgo']:
        for v in e.get('vinculos', []):
            graph[v['id_padre']].append(e['id'])
    
    visited = set()
    rec_stack = set()
    has_cycle = False
    def dfs(node):
        nonlocal has_cycle
        visited.add(node)
        rec_stack.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                has_cycle = True
        rec_stack.remove(node)
    
    for eid in event_ids:
        if eid not in visited:
            dfs(eid)
    
    if has_cycle:
        errors.append("  ❌ Ciclo detectado en el grafo de dependencias")
        print("  ❌ CICLO DETECTADO")
    else:
        print("  ✅ Sin ciclos (DAG válido)")
    
    # --- Validate scenarios ---
    print("\n--- Validando escenarios ---")
    for sc in configuracion.get('scenarios', []):
        sc_name = sc.get('nombre', 'N/A')
        print(f"\n  Escenario: {sc_name}")
        
        _ = sc['nombre']  # mandatory
        
        for i, evento_data in enumerate(sc.get('eventos_riesgo', [])):
            total_events += 1
            evt_name = evento_data.get('nombre', f'Sc Event #{i}')
            print(f"    Evento {i+1}: {evt_name}")
            
            try:
                # Same validation as main events
                sev_opcion = evento_data['sev_opcion']
                sev_minimo = evento_data['sev_minimo']
                sev_mas_probable = evento_data['sev_mas_probable']
                sev_maximo = evento_data['sev_maximo']
                
                dist_sev = generar_distribucion_severidad(
                    evento_data['sev_opcion'],
                    evento_data.get('sev_minimo'),
                    evento_data.get('sev_mas_probable'),
                    evento_data.get('sev_maximo'),
                    input_method=evento_data.get('sev_input_method', 'min_mode_max'),
                    params_direct=evento_data.get('sev_params_direct', {})
                )
                
                freq_opcion = evento_data['freq_opcion']
                tasa = evento_data.get('tasa', None)
                num_eventos = evento_data.get('num_eventos', None)
                prob_exito = evento_data.get('prob_exito', None)
                if tasa is not None: tasa = float(tasa)
                if num_eventos is not None: num_eventos = int(num_eventos)
                if prob_exito is not None: prob_exito = float(prob_exito)
                
                pg_params = None
                beta_params = None
                if freq_opcion == 4:
                    alpha = evento_data.get('pg_alpha')
                    beta_val = evento_data.get('pg_beta')
                    if alpha is None or beta_val is None:
                        pg_min = evento_data.get('pg_minimo')
                        pg_mode = evento_data.get('pg_mas_probable')
                        pg_max = evento_data.get('pg_maximo')
                        pg_conf = evento_data.get('pg_confianza')
                        if None not in (pg_min, pg_mode, pg_max, pg_conf) and obtener_parametros_gamma_para_poisson:
                            alpha, beta_val = obtener_parametros_gamma_para_poisson(
                                float(pg_min), float(pg_mode), float(pg_max), float(pg_conf)/100.0
                            )
                    if alpha is not None and beta_val is not None:
                        pg_params = (float(alpha), float(beta_val))
                elif freq_opcion == 5:
                    alpha = evento_data.get('beta_alpha')
                    beta_val = evento_data.get('beta_beta')
                    if alpha is not None and beta_val is not None:
                        beta_params = (float(alpha), float(beta_val))
                
                dist_freq = generar_distribucion_frecuencia(
                    freq_opcion, tasa=tasa, num_eventos_posibles=num_eventos,
                    probabilidad_exito=prob_exito, poisson_gamma_params=pg_params,
                    beta_params=beta_params
                )
                
                if 'factores_ajuste' in evento_data and evento_data['factores_ajuste']:
                    for f in evento_data['factores_ajuste']:
                        f_norm = normalizar_factor_global(f)
                        if f.get('tipo_severidad') == 'seguro':
                            assert f_norm.get('afecta_severidad') == True
                
                _ = evento_data['id']
                _ = evento_data['nombre']
                
                success_count += 1
                print(f"      ✅ IMPORT OK")
                
            except Exception as e:
                errors.append(f"  ❌ Scenario '{sc_name}' - {evt_name}: {e}")
                print(f"      ❌ ERROR: {e}")
                traceback.print_exc()
    
    # --- Validate JSON serialization roundtrip ---
    print("\n--- Validando serialización JSON ---")
    try:
        json_str = json.dumps(test_json, ensure_ascii=False, indent=2)
        parsed = json.loads(json_str)
        assert len(parsed['eventos_riesgo']) == len(test_json['eventos_riesgo'])
        assert len(parsed['scenarios']) == len(test_json['scenarios'])
        print(f"  ✅ JSON serializable ({len(json_str)} chars)")
    except Exception as e:
        errors.append(f"  ❌ JSON serialization: {e}")
    
    # --- Summary ---
    print("\n" + "=" * 70)
    print("RESUMEN DE VALIDACIÓN")
    print("=" * 70)
    print(f"Total eventos testeados: {total_events}")
    print(f"Exitosos: {success_count}")
    print(f"Errores: {len(errors)}")
    
    if errors:
        print("\n❌ ERRORES ENCONTRADOS:")
        for e in errors:
            print(e)
    else:
        print("\n✅ TODOS LOS EVENTOS IMPORTAN CORRECTAMENTE")
    
    if warnings:
        print("\n⚠️ ADVERTENCIAS:")
        for w in warnings:
            print(w)
    
    # --- Coverage summary ---
    print("\n--- COBERTURA DE TEST ---")
    print("Distribuciones de Severidad:")
    print("  ✅ Normal min_mode_max (E9)")
    print("  ✅ Normal direct mu/sigma (E4)")
    print("  ✅ LogNormal direct mean/std (E2)")
    print("  ✅ LogNormal direct s/scale/loc (E7)")
    print("  ✅ PERT min_mode_max (E1, E6, E8)")
    print("  ✅ Pareto/GPD direct c/scale/loc (E3)")
    print("  ✅ Uniforme min_mode_max (E5)")
    print("Distribuciones de Frecuencia:")
    print("  ✅ Poisson (E1, E6, E7, E8, E9)")
    print("  ✅ Binomial (E2)")
    print("  ✅ Bernoulli (E3)")
    print("  ✅ Poisson-Gamma con pg_alpha/pg_beta (E4, Escenario)")
    print("  ✅ Beta con beta_alpha/beta_beta (E5)")
    print("Factores:")
    print("  ✅ Estático frecuencia (E2, E9)")
    print("  ✅ Estático severidad (E9)")
    print("  ✅ Estocástico frecuencia+severidad (E3)")
    print("  ✅ Estocástico solo frecuencia (E9)")
    print("  ✅ Seguro por_ocurrencia (E4)")
    print("  ✅ Seguro agregado (Escenario)")
    print("Vínculos:")
    print("  ✅ AND con prob+factor_sev+umbral (E6)")
    print("  ✅ OR múltiples padres (E7)")
    print("  ✅ EXCLUYE con factor_sev=1.0 (E8)")
    print("Escalamiento:")
    print("  ✅ Reincidencia lineal (E5)")
    print("  ✅ Sistémico (E9)")
    print("Escenarios:")
    print("  ✅ Escenario con PERT+Poisson y Normal+PG+Seguro")
    print("Otros:")
    print("  ✅ Eventos inactivos: N/A (all active, but field present)")
    print("  ✅ JSON roundtrip serialización")
    print("  ✅ DAG validation (sin ciclos)")
    print("  ✅ Vinculo reference integrity")
    
    return len(errors) == 0


if __name__ == '__main__':
    # Save JSON to file for manual import testing
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_model_exhaustivo.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(test_json, f, ensure_ascii=False, indent=2)
    print(f"JSON guardado en: {json_path}\n")
    
    success = validate_json()
    sys.exit(0 if success else 1)
