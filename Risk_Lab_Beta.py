#!/usr/bin/env python
# coding: utf-8

# In[6]:


import sys
import os
import numpy as np
from scipy import stats
from scipy.stats import gaussian_kde
from scipy.optimize import least_squares, minimize
from scipy.stats import poisson, binom, bernoulli, lognorm, beta, genpareto, norm, uniform, nbinom, truncnorm
from scipy.special import gamma as gamma_func, factorial
import matplotlib
matplotlib.use('Qt5Agg')
from InteractiveFigureCanvas import InteractiveFigureCanvas
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import pandas as pd
from matplotlib.ticker import FuncFormatter
import warnings
from tabulate import tabulate
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
import json
import io
import traceback
import uuid
import copy


# Clases personalizadas de SpinBox que ignoran el scroll del mouse
class NoScrollSpinBox(QtWidgets.QSpinBox):
    """QSpinBox que ignora eventos de rueda del mouse para evitar cambios accidentales"""
    def wheelEvent(self, event):
        event.ignore()

class NoScrollDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    """QDoubleSpinBox que ignora eventos de rueda del mouse para evitar cambios accidentales"""
    def wheelEvent(self, event):
        event.ignore()


# Helper function to get correct path for bundled resources
def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError: # sys._MEIPASS might not exist if not bundled
        # Si no se ejecuta en un paquete PyInstaller, usa la ruta del script actual
        base_path = os.path.abspath(os.path.dirname(__file__))
    
    full_path = os.path.join(base_path, relative_path)
    
    # Advertir solo si el recurso no existe (útil para debugging)
    if not os.path.exists(full_path):
        print(f"[ADVERTENCIA] Recurso no encontrado: {full_path}")
    
    return full_path


def ajustar_distribuciones(losses):
    ajustes, pruebas = {}, []

    s, _, scale = stats.lognorm.fit(losses, floc=0)
    D, p = stats.kstest(losses, 'lognorm', args=(s, 0, scale))
    ajustes['LogNormal'] = {'s': round(s,4), 'scale': round(scale,2),
                            'loc': 0, 'KS_D': round(D,4), 'KS_p': round(p,4)}
    pruebas.append(('LogNormal', D))

    mu, sigma = stats.norm.fit(losses)
    D, p = stats.kstest(losses, 'norm', args=(mu, sigma))
    ajustes['Normal'] = {'mu': round(mu,2), 'sigma': round(sigma,2),
                         'KS_D': round(D,4), 'KS_p': round(p,4)}
    pruebas.append(('Normal', D))

    a, loc_g, scale_g = stats.gamma.fit(losses, floc=0)
    D, p = stats.kstest(losses, 'gamma', args=(a, 0, scale_g))
    ajustes['Gamma'] = {'a': round(a,4), 'scale': round(scale_g,2),
                        'loc': 0, 'KS_D': round(D,4), 'KS_p': round(p,4)}
    pruebas.append(('Gamma', D))

    best = min(pruebas, key=lambda x: x[1])[0]
    return ajustes, best

# Configuramos Seaborn y Matplotlib
sns.set(style="whitegrid")

# Ignoramos advertencias de runtime
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Función para formatear números en formato contable personalizado
def currency_format(value):
    """Formatea un número en formato monetario con separador de miles y decimales personalizados."""
    return '${:,.0f}'.format(value).replace(',', 'X').replace('.', ',').replace('X', '.')

# Función para formatear porcentajes sin decimales
def percentage_format(value):
    """Formatea un número entre 0 y 1 como porcentaje sin decimales."""
    return '{:,.0f}%'.format(value * 100).replace('.', ',')

# Funciones para formatear los ejes en los gráficos
def currency_formatter(x, pos):
    """Función de formateo para los ejes que muestra valores monetarios."""
    return currency_format(x)

def percentage_formatter(x, pos):
    """Función de formateo para los ejes que muestra porcentajes."""
    return percentage_format(x)

# Paleta de colores inspirada en MercadoLibre
MELI_AMARILLO = '#FFE600'           # Color principal/identitario
MELI_AMARILLO_OSCURO = '#FFD000'    # Amarillo más oscuro para gradientes
MELI_AZUL = '#3483FA'               # Azul para acciones y elementos interactivos
MELI_AZUL_HOVER = '#2968C8'         # Azul hover state
MELI_AZUL_PRESSED = '#1F50A0'       # Azul pressed state
MELI_AZUL_CORP = '#2D3277'          # Azul corporativo oscuro
MELI_VERDE = '#00A650'              # Verde para éxito y confirmaciones
MELI_VERDE_HOVER = '#008C40'        # Verde hover
MELI_VERDE_PRESSED = '#007535'      # Verde pressed
MELI_ROJO = '#F23D4F'               # Rojo para alertas y errores
MELI_ROJO_HOVER = '#D9313E'         # Rojo hover
MELI_GRIS_TEXTO = '#333333'         # Texto principal
MELI_GRIS_SECUNDARIO = '#666666'    # Texto secundario
MELI_GRIS_FONDO = '#F5F5F5'         # Fondos secundarios
MELI_GRIS_BORDE = '#EDEDED'         # Bordes y separadores
MELI_GRIS_CLARO = '#FAFAFA'         # Fondos muy claros
MELI_AZUL_CLARO = '#E5F0FF'         # Fondo de selección
MELI_MORADO = '#9C27B0'             # Morado para elementos especiales

# ==================== CONSTANTES DE FUENTES Y ESCALADO ====================
# Familia de fuentes con fallbacks para cross-platform
FONT_FAMILY = "Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"

def _get_windows_scale_factor():
    """
    Detecta el factor de escala de Windows ANTES de crear QApplication.
    Permite override manual vía variable de entorno RISK_LAB_SCALE.
    """
    # Verificar override manual primero
    manual_scale = os.environ.get('RISK_LAB_SCALE', '')
    if manual_scale:
        try:
            scale = float(manual_scale)
            if 0.5 <= scale <= 3.0:
                print(f"Usando escala manual: {scale * 100:.0f}%")
                return scale
        except ValueError:
            pass
    
    try:
        import ctypes
        
        # Método 1: GetDpiForSystem (Windows 10+)
        try:
            shcore = ctypes.windll.shcore
            shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
            dpi = ctypes.windll.user32.GetDpiForSystem()
            if dpi and dpi > 96:
                return dpi / 96.0
        except Exception:
            pass
        
        # Método 2: Leer LogPixels del registro (más confiable)
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Control Panel\Desktop")
            log_pixels, _ = winreg.QueryValueEx(key, "LogPixels")
            winreg.CloseKey(key)
            if log_pixels and log_pixels > 96:
                return log_pixels / 96.0
        except Exception:
            pass
            
    except Exception:
        pass
    
    # Si no se detecta escala alta, retornar 1.0
    return 1.0

# Factor de escala del sistema (detectado al inicio)
_SYSTEM_SCALE = _get_windows_scale_factor()
if _SYSTEM_SCALE > 1.0:
    print(f"Escala de Windows detectada: {_SYSTEM_SCALE * 100:.0f}%")
else:
    print("Escala de Windows: 100% (o no detectada)")
    print("  TIP: Si la UI es muy grande, ejecute con: set RISK_LAB_SCALE=1.5 && python Risk_Lab_Beta.py")

def _adjust_font_size(base_size):
    """
    Ajusta el tamaño de fuente para compensar la escala de Windows.
    Con escala > 125%, reduce proporcionalmente para evitar UI gigante.
    """
    if _SYSTEM_SCALE <= 1.25:
        # Escalas 100% y 125% - sin ajuste
        return base_size
    elif _SYSTEM_SCALE <= 1.5:
        # Escala 150% - reducir un 20%
        return round(base_size * 0.80, 1)
    elif _SYSTEM_SCALE <= 1.75:
        # Escala 175% - reducir un 30%
        return round(base_size * 0.70, 1)
    else:
        # Escala 200%+ - reducir un 40%
        return round(base_size * 0.60, 1)

# Tamaños de fuente para UI en puntos (pt) - escalan automáticamente con DPI
# Escala tipográfica coherente con 8 niveles principales
UI_FONT_XSMALL = 8      # Chips, badges pequeños, texto mínimo
UI_FONT_SMALL = 9       # Texto secundario, tooltips, etiquetas
UI_FONT_BODY = 10       # Texto de cuerpo alternativo
UI_FONT_NORMAL = 10.5   # Texto base principal
UI_FONT_BASE = 11       # Labels estándar
UI_FONT_MEDIUM = 12     # Texto destacado, botones primarios
UI_FONT_SUBHEAD = 13    # Encabezados secundarios
UI_FONT_SUBTITLE = 13.5 # Subtítulos de sección, encabezados de cards
UI_FONT_LARGE = 15      # Títulos de diálogos y paneles
UI_FONT_DISPLAY = 16.5  # Texto de énfasis especial
UI_FONT_XLARGE = 18     # Títulos principales de sección
UI_FONT_HEADING = 21    # Encabezados principales
UI_FONT_HERO = 24       # Valores numéricos grandes, KPIs
UI_FONT_ICON = 48       # Iconos emoji grandes

# Tamaños de fuente para matplotlib (en puntos)
PLT_FONT_TITLE = 14     # Títulos de gráficos
PLT_FONT_SUBTITLE = 12  # Subtítulos
PLT_FONT_LABEL = 11     # Etiquetas de ejes
PLT_FONT_TICK = 9.5     # Valores de ejes
PLT_FONT_LEGEND = 8     # Leyendas
PLT_FONT_ANNOTATION = 9 # Anotaciones en gráficos
PLT_FONT_SMALL = 7      # Texto muy pequeño en gráficos

def get_dpi_scale():
    """
    Obtiene el factor de escala DPI actual del sistema.
    Retorna 1.0 si no se puede determinar (fallback seguro).
    """
    try:
        app = QtWidgets.QApplication.instance()
        if app:
            screen = app.primaryScreen()
            if screen:
                # 96 DPI es el valor base estándar de Windows
                return screen.logicalDotsPerInch() / 96.0
    except Exception:
        pass
    return 1.0

def scaled(value):
    """
    Escala un valor en píxeles según el DPI del sistema.
    Usar para tamaños de widgets que necesitan adaptarse a diferentes densidades de pantalla.
    
    Args:
        value: Valor base en píxeles (diseñado para 96 DPI)
    
    Returns:
        Valor escalado como entero
    """
    return int(value * get_dpi_scale())

def scaled_size(width, height):
    """
    Escala un par de dimensiones (ancho, alto) según el DPI del sistema.
    
    Args:
        width: Ancho base en píxeles
        height: Alto base en píxeles
    
    Returns:
        QtCore.QSize escalado
    """
    scale = get_dpi_scale()
    return QtCore.QSize(int(width * scale), int(height * scale))

def aplicar_estilo_meli(ax, tipo='hist'):
    """Aplica un estilo MercadoLibre a los ejes matplotlib."""
    ax.grid(True, linestyle='--', alpha=0.3, color='#CCCCCC')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='both', labelsize=9, colors=MELI_GRIS_SECUNDARIO)
    ax.set_title(ax.get_title(), fontsize=11, color=MELI_GRIS_TEXTO, fontweight='bold')
    ax.set_xlabel(ax.get_xlabel(), fontsize=9.5, color=MELI_GRIS_SECUNDARIO)
    ax.set_ylabel(ax.get_ylabel(), fontsize=9.5, color=MELI_GRIS_SECUNDARIO)

def blend_colors(color1, color2, ratio):
    """Mezcla dos colores hexadecimales según un ratio (0-1)."""
    # Convertir colores hex a RGB
    r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
    r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
    
    # Interpolar
    r = int(r1 * (1-ratio) + r2 * ratio)
    g = int(g1 * (1-ratio) + g2 * ratio)
    b = int(b1 * (1-ratio) + b2 * ratio)
    
    # Convertir de vuelta a hex
    return f'{r:02x}{g:02x}{b:02x}'

# Funciones para obtener parámetros de distribuciones

def obtener_parametros_normal(minimo, mas_probable, maximo):
    """Calcula los parámetros mu y sigma para la distribución Normal utilizando mínimos y máximos."""
    if minimo >= maximo:
        raise ValueError("El valor mínimo debe ser menor que el máximo.")
    mu = mas_probable
    sigma = (maximo - minimo) / (2 * 3)
    return mu, sigma

def obtener_parametros_lognormal(minimo, mas_probable, maximo):
    """
    Calcula los parámetros mu y sigma para la distribución Lognormal.
    
    Utiliza un método robusto que:
    - Intenta primero ajustar usando 'mas_probable' como moda teórica
    - Si sigma > 1.0, reintenta usando 'mas_probable' como mediana (percentil 50%)
    - Valida que los parámetros resultantes sean razonables
    
    Args:
        minimo: Valor mínimo (percentil 10)
        mas_probable: Valor más probable (moda si sigma<=1, mediana si sigma>1)
        maximo: Valor máximo (percentil 90)
    
    Returns:
        (mu, sigma): Parámetros de la distribución LogNormal
    """
    if minimo <= 0 or mas_probable <= 0 or maximo <= 0 or not (minimo < mas_probable < maximo):
        raise ValueError("Los valores deben ser positivos y cumplir mínimo < más probable < máximo.")

    P1 = 0.10
    P2 = 0.90

    # MÉTODO 1: Intentar con ecuación de moda
    def equations_mode(p):
        mu, sigma = p
        if sigma <= 0:
            return [np.inf, np.inf, np.inf]
        eq1 = np.exp(mu - sigma**2) - mas_probable  # Moda = exp(mu - sigma^2)
        eq2 = stats.lognorm.cdf(minimo, s=sigma, scale=np.exp(mu)) - P1
        eq3 = stats.lognorm.cdf(maximo, s=sigma, scale=np.exp(mu)) - P2
        return [eq1, eq2, eq3]

    mu_initial = np.log(mas_probable)
    sigma_initial = 1.0

    result = least_squares(equations_mode, x0=[mu_initial, sigma_initial],
                           bounds=([-np.inf, 1e-6], [np.inf, np.inf]))
    mu, sigma = result.x

    # Si sigma > 1.0, la moda pierde significado; usar método basado en MEDIANA
    if result.success and sigma > 1.0:
        def equations_median(p):
            mu, sigma = p
            if sigma <= 0:
                return [np.inf, np.inf, np.inf]
            # Usar 'mas_probable' como MEDIANA (percentil 50%)
            eq1 = stats.lognorm.cdf(mas_probable, s=sigma, scale=np.exp(mu)) - 0.50
            eq2 = stats.lognorm.cdf(minimo, s=sigma, scale=np.exp(mu)) - P1
            eq3 = stats.lognorm.cdf(maximo, s=sigma, scale=np.exp(mu)) - P2
            return [eq1, eq2, eq3]
        
        # Reintentar con 'mas_probable' como mediana
        result_alt = least_squares(equations_median, x0=[mu_initial, sigma_initial],
                                   bounds=([-np.inf, 1e-6], [np.inf, np.inf]))
        
        if result_alt.success:
            mu_alt, sigma_alt = result_alt.x
            # Usar resultado alternativo y emitir warning
            import warnings
            warnings.warn(
                f"Distribución LogNormal ajustada usando 'más probable' como MEDIANA (no moda) "
                f"debido a alta dispersión (σ={sigma_alt:.2f} > 1.0). "
                f"Esto es normal para distribuciones muy asimétricas.",
                UserWarning
            )
            mu, sigma = mu_alt, sigma_alt
            result = result_alt
    
    # Validación de resultados
    if not result.success or sigma <= 0:
        raise ValueError("No se pudieron estimar los parámetros de la distribución Lognormal.")
    
    # Validación de dispersión extrema
    if sigma > 2.5:
        raise ValueError(
            f"No se pudo ajustar una distribución LogNormal razonable. "
            f"Dispersión muy alta (σ={sigma:.2f} > 2.5). "
            f"Verifique que mínimo={minimo:.2f}, más probable={mas_probable:.2f}, "
            f"máximo={maximo:.2f} sean consistentes. "
            f"Considere usar otra distribución (ej. GPD para colas pesadas)."
        )

    return mu, sigma

def obtener_parametros_pert(minimo, mas_probable, maximo):
    """Calcula los parámetros alpha y beta para la distribución PERT."""
    if maximo == minimo:
        raise ValueError("El valor máximo y mínimo no pueden ser iguales para la distribución PERT.")
    if not (minimo <= mas_probable <= maximo):
        raise ValueError("Los valores deben cumplir que mínimo <= más probable <= máximo.")
    alpha = 1 + 4 * ((mas_probable - minimo) / (maximo - minimo))
    beta_param = 1 + 4 * ((maximo - mas_probable) / (maximo - minimo))
    return alpha, beta_param

def obtener_parametros_gpd(minimo, mas_probable, maximo):
    """Calcula los parámetros xi y beta para la distribución Generalizada de Pareto."""
    if minimo <= 0 or mas_probable <= minimo or mas_probable >= maximo:
        raise ValueError("Los valores deben cumplir mínimo > 0 y mínimo < más probable < máximo.")

    mu = minimo

    p1 = 0.5
    p2 = 0.95

    x1 = mas_probable
    x2 = maximo

    def objective(p):
        xi, beta = p
        if beta <= 0:
            return [np.inf, np.inf]
        
        # VALIDACIÓN CRÍTICA: Para xi < 0, el soporte es finito [mu, mu - beta/xi]
        if xi < 0:
            max_support = mu - beta / xi
            if x1 > max_support or x2 > max_support:
                # Los valores exceden el soporte teórico
                return [np.inf, np.inf]
        
        try:
            # Validar que el argumento de la potencia sea positivo
            arg1 = 1 + xi * (x1 - mu) / beta
            arg2 = 1 + xi * (x2 - mu) / beta
            
            if arg1 <= 0 or arg2 <= 0:
                return [np.inf, np.inf]
            
            if abs(xi) < 1e-10:  # xi ≈ 0, usar forma exponencial
                cdf1 = 1 - np.exp(-(x1 - mu) / beta)
                cdf2 = 1 - np.exp(-(x2 - mu) / beta)
            else:
                cdf1 = 1 - arg1 ** (-1 / xi)
                cdf2 = 1 - arg2 ** (-1 / xi)
        except (ZeroDivisionError, OverflowError, ValueError):
            return [np.inf, np.inf]
        return [cdf1 - p1, cdf2 - p2]

    xi_initial = 0.1
    beta_initial = x1 - mu

    result = least_squares(objective, x0=[xi_initial, beta_initial],
                           bounds=([-np.inf, 1e-6], [np.inf, np.inf]))
    xi, beta = result.x

    if not result.success or beta <= 0:
        raise ValueError("No se pudieron estimar los parámetros de la GPD.")
    
    # VALIDACIÓN POST-OPTIMIZACIÓN
    if xi < 0:
        max_support = mu - beta / xi
        if maximo > max_support * 0.95:  # Margen de seguridad del 5%
            import warnings
            warnings.warn(
                f"GPD con cola finita (ξ={xi:.3f}). Soporte teórico máximo: {max_support:.2f}. "
                f"El máximo ingresado ({maximo:.2f}) está cerca o excede este límite.",
                UserWarning
            )

    return xi, beta, mu

def obtener_parametros_uniforme(minimo, maximo):
    """Configura los parámetros para la distribución Uniforme."""
    if minimo >= maximo:
        raise ValueError("El valor mínimo debe ser menor que el máximo.")
    return minimo, maximo - minimo

def traducir_error(mensaje_error):
    """
    Traduce mensajes de error técnicos comunes de bibliotecas al español.
    
    Args:
        mensaje_error: Mensaje de error original (puede ser str o Exception)
        
    Returns:
        str: Mensaje traducido y más amigable
    """
    msg = str(mensaje_error).lower()
    
    # Diccionario de traducciones comunes
    traducciones = {
        'invalid value': 'valor inválido',
        'not a number': 'no es un número',
        'division by zero': 'división por cero',
        'out of bounds': 'fuera de límites',
        'shape mismatch': 'incompatibilidad de dimensiones',
        'memory error': 'error de memoria',
        'overflow': 'desbordamiento numérico',
        'underflow': 'subdesbordamiento numérico',
        'nan': 'valor no numérico (NaN)',
        'inf': 'infinito',
        'singular matrix': 'matriz singular',
        'not positive definite': 'no es definida positiva',
        'convergence': 'convergencia',
        'failed': 'falló',
        'cannot': 'no se puede',
        'must be': 'debe ser',
        'expected': 'esperado',
        'got': 'obtenido',
        'type error': 'error de tipo',
        'value error': 'error de valor',
        'key error': 'clave no encontrada',
        'index error': 'índice fuera de rango',
        'attribute error': 'atributo no encontrado'
    }
    
    # Aplicar traducciones
    msg_traducido = msg
    for ingles, espanol in traducciones.items():
        msg_traducido = msg_traducido.replace(ingles, espanol)
    
    # Si el mensaje es muy largo, resumir
    if len(msg_traducido) > 200:
        msg_traducido = msg_traducido[:197] + "..."
    
    return msg_traducido

def validar_num_simulaciones(texto):
    """
    Valida el número de simulaciones ingresado por el usuario.
    
    Args:
        texto: String con el número de simulaciones
        
    Returns:
        int: Número de simulaciones validado
        
    Raises:
        ValueError: Si el número no es válido o está fuera de rango
    """
    if not texto or not texto.strip():
        raise ValueError("El número de simulaciones no puede estar vacío.")
    
    try:
        num = int(texto.strip())
    except ValueError:
        raise ValueError("El número de simulaciones debe ser un número entero válido.")
    
    if num < 1000:
        raise ValueError("El número de simulaciones debe ser al menos 1,000 para obtener resultados estadísticamente confiables.")
    
    if num > 10_000_000:
        raise ValueError("El número de simulaciones no debe exceder 10,000,000 debido a limitaciones de memoria.")
    
    return num

def obtener_parametros_gamma_para_poisson(minimo, mas_probable, maximo, confianza=0.8):
    """
    Calcula los parámetros alpha y beta para la distribución Gamma 
    que modelará el parámetro lambda de la distribución Poisson.
    
    Args:
        minimo: Valor mínimo razonable para lambda
        mas_probable: Valor más probable (moda) para lambda
        maximo: Valor máximo razonable para lambda
        confianza: Nivel de confianza asociado al rango [minimo, maximo] (default: 0.8)
    
    Returns:
        alpha: Parámetro de forma (shape)
        beta: Parámetro de tasa (rate)
    """
    if minimo <= 0 or mas_probable <= 0 or maximo <= 0:
        raise ValueError("Todos los valores deben ser positivos.")
    if not (minimo < mas_probable < maximo):
        raise ValueError("Debe cumplirse: mínimo < más probable < máximo.")
    if not (0 < confianza < 1):
        raise ValueError("La confianza debe estar entre 0 y 1.")
    
    # Convertir la confianza a percentiles para los extremos
    tail_prob = (1 - confianza) / 2
    
    # Función objetivo para optimización
    def objective(params):
        alpha, beta = params
        if alpha <= 1 or beta <= 0:  # Restricciones para asegurar que la moda exista y sea positiva
            return 1e10
        
        # La moda de Gamma es (alpha-1)/beta cuando alpha > 1
        estimated_mode = (alpha - 1) / beta
        mode_error = (estimated_mode - mas_probable)**2
        
        # Calcular los cuantiles teóricos para los extremos
        q_min = stats.gamma.ppf(tail_prob, a=alpha, scale=1/beta)
        q_max = stats.gamma.ppf(1-tail_prob, a=alpha, scale=1/beta)
        
        # Error en los cuantiles
        min_error = (q_min - minimo)**2
        max_error = (q_max - maximo)**2
        
        return mode_error + min_error + max_error
    
    # Estimación inicial: usar método de momentos
    mean_est = (minimo + 4*mas_probable + maximo) / 6  # Estimación de la media usando regla de PERT
    var_est = ((maximo - minimo) / 6)**2  # Estimación de la varianza
    
    # Para Gamma: alpha = mean²/var, beta = mean/var
    alpha_init = mean_est**2 / var_est if var_est > 0 else 2.0
    beta_init = mean_est / var_est if var_est > 0 else 1.0
    
    # Asegurar que alpha > 1 para que la moda exista
    alpha_init = max(alpha_init, 1.1)
    
    # Optimización para encontrar mejores parámetros
    result = minimize(objective, [alpha_init, beta_init], method='Nelder-Mead', 
                     bounds=[(1.001, None), (1e-6, None)])
    
    alpha, beta = result.x
    return alpha, beta

def obtener_parametros_beta_frecuencia(minimo, mas_probable, maximo, confianza=0.8):
    """
    Calcula los parámetros alpha y beta para la distribución Beta
    que modelará la probabilidad de ocurrencia anual de un evento.
    
    Args:
        minimo: Probabilidad mínima razonable (como proporción entre 0 y 1)
        mas_probable: Probabilidad más probable (modo, como proporción entre 0 y 1)
        maximo: Probabilidad máxima razonable (como proporción entre 0 y 1)
        confianza: Nivel de confianza asociado al rango [minimo, maximo] (default: 0.8)
    
    Returns:
        alpha: Parámetro de forma alpha
        beta: Parámetro de forma beta
    """
    if not (0 <= minimo < mas_probable < maximo <= 1):
        raise ValueError("Debe cumplirse: 0 ≤ mínimo < más probable < máximo ≤ 1")
    if not (0 < confianza < 1):
        raise ValueError("La confianza debe estar entre 0 y 1.")
    
    # Convertir la confianza a percentiles para los extremos
    tail_prob = (1 - confianza) / 2
    
    # Adaptación de la fórmula PERT
    media = (minimo + 4 * mas_probable + maximo) / 6
    
    # Calcular varianza en función de la confianza
    # Usamos el rango para estimar la desviación estándar
    rango = maximo - minimo
    # Ajustar la varianza según la confianza
    factor_confianza = 1.0 / confianza if confianza > 0 else 1.25
    varianza = (rango / 6.0)**2 * factor_confianza
    
    # Función objetivo para optimización
    def objective(params):
        alpha, beta = params
        if alpha <= 1 or beta <= 1:  # Restricciones para asegurar que la moda exista y esté entre 0 y 1
            return 1e10
        
        # La moda de Beta es (alpha-1)/(alpha+beta-2) cuando alpha, beta > 1
        estimated_mode = (alpha - 1) / (alpha + beta - 2)
        mode_error = (estimated_mode - mas_probable)**2
        
        # Calcular los cuantiles teóricos para los extremos
        q_min = stats.beta.ppf(tail_prob, alpha, beta)
        q_max = stats.beta.ppf(1-tail_prob, alpha, beta)
        
        # Error en los cuantiles
        min_error = (q_min - minimo)**2
        max_error = (q_max - maximo)**2
        
        # Penalizar si los parámetros llevan a una media muy diferente de la esperada
        mean_est = alpha / (alpha + beta)
        mean_error = (mean_est - media)**2
        
        return mode_error + min_error + max_error + mean_error
    
    # Estimación inicial basada en momentos
    if varianza <= 0 or not (0 < media < 1):
        # Valores por defecto razonables si los cálculos iniciales no son válidos
        alpha_init = 2.0
        beta_init = 2.0 * (1 - mas_probable) / mas_probable if mas_probable > 0 else 2.0
    else:
        # Fórmulas de momentos para Beta: 
        # alpha = media * [(media*(1-media)/varianza) - 1]
        # beta = (1-media) * [(media*(1-media)/varianza) - 1]
        temp = media * (1 - media) / varianza - 1
        alpha_init = media * temp
        beta_init = (1 - media) * temp
    
    # Asegurar que alpha, beta > 1 para que la moda exista
    alpha_init = max(alpha_init, 1.1)
    beta_init = max(beta_init, 1.1)
    
    # Optimización para encontrar mejores parámetros
    result = minimize(objective, [alpha_init, beta_init], method='Nelder-Mead', 
                     bounds=[(1.001, None), (1.001, None)])
    
    alpha, beta = result.x
    return alpha, beta

class TruncatedGPD:
    """
    Wrapper sobre genpareto que trunca las muestras al percentil 99.9% teórico.
    Solo aplica truncamiento cuando xi > 0 (cola infinita).
    Cuando xi <= 0 la cola ya es finita y se delega directamente.
    """
    
    def __init__(self, c, scale, loc):
        self._dist = genpareto(c=c, scale=scale, loc=loc)
        self.c = c
        self.scale_param = scale
        self.loc_param = loc
        # Calcular cap solo si cola infinita (xi > 0)
        if c > 0:
            self._cap = self._dist.ppf(0.999)
        else:
            self._cap = None
    
    def rvs(self, size=1, random_state=None):
        samples = self._dist.rvs(size=size, random_state=random_state)
        if self._cap is not None:
            samples = np.minimum(samples, self._cap)
        return samples
    
    def mean(self):
        return self._dist.mean()
    
    def var(self):
        return self._dist.var()
    
    def ppf(self, q):
        return self._dist.ppf(q)
    
    def cdf(self, x):
        return self._dist.cdf(x)
    
    def pdf(self, x):
        return self._dist.pdf(x)

class PoissonGammaDistribution:
    """
    Distribución compuesta Poisson-Gamma (también conocida como Binomial Negativa).
    Modela un proceso donde lambda (tasa de Poisson) es una variable aleatoria con distribución Gamma.
    """
    
    def __init__(self, alpha, beta):
        """
        Inicializa la distribución con los parámetros de la Gamma.
        
        Args:
            alpha: Parámetro de forma (shape) de la distribución Gamma
            beta: Parámetro de tasa (rate) de la distribución Gamma
        """
        self.alpha = alpha
        self.beta = beta
        self.gamma_dist = stats.gamma(a=alpha, scale=1/beta)
        
        # Equivalencia con Binomial Negativa para cálculos rápidos
        # En nbinom: p = probabilidad de éxito, n = número de éxitos
        # Relación con Gamma: p = beta/(1+beta), n = alpha
        self.p = beta / (1 + beta)
        self.n = alpha
        self.nb_dist = nbinom(n=self.n, p=self.p)
        
    def rvs(self, size=1, random_state=None):
        """
        Genera muestras aleatorias de la distribución Poisson-Gamma.
        
        Args:
            size: Número de muestras a generar
            random_state: Semilla para reproducibilidad
            
        Returns:
            Muestras aleatorias de la distribución Poisson-Gamma
        """
        # Método 1: Usando la equivalencia con Binomial Negativa (más eficiente)
        return self.nb_dist.rvs(size=size, random_state=random_state)
        
        # Método 2: Generación directa mediante simulación jerárquica
        # (Comentado por eficiencia, pero útil para entender el proceso)
        #
        # # Generar valores de lambda desde la distribución Gamma
        # lambdas = self.gamma_dist.rvs(size=size, random_state=random_state)
        # 
        # # Para cada lambda, generar un valor desde la distribución Poisson
        # results = np.zeros(size, dtype=int)
        # for i, lambda_val in enumerate(lambdas):
        #     results[i] = stats.poisson.rvs(mu=lambda_val, size=1, random_state=random_state)
        # 
        # return results
    
    def mean(self):
        """
        Calcula la media de la distribución Poisson-Gamma.
        La media es alpha/beta.
        """
        return self.alpha / self.beta
    
    def var(self):
        """
        Calcula la varianza de la distribución Poisson-Gamma.
        La varianza es alpha/beta * (1 + 1/beta).
        """
        return (self.alpha / self.beta) * (1 + 1/self.beta)
    
    def pmf(self, k):
        """
        Calcula la función de masa de probabilidad en el punto k.
        Utiliza la equivalencia con la distribución Binomial Negativa.
        """
        return self.nb_dist.pmf(k)
    
    def cdf(self, k):
        """
        Calcula la función de distribución acumulada en el punto k.
        """
        return self.nb_dist.cdf(k)
    
    def ppf(self, q):
        """
        Calcula el cuantil (percentil) para la probabilidad q.
        """
        return self.nb_dist.ppf(q)

class BetaFrequencyDistribution:
    """
    Distribución Beta para modelar la probabilidad de ocurrencia anual.
    Genera valores binarios (0 o 1) basados en una probabilidad que sigue una distribución Beta.
    """
    
    def __init__(self, alpha, beta):
        """
        Inicializa la distribución con los parámetros alpha y beta.
        
        Args:
            alpha: Parámetro de forma alpha (>0)
            beta: Parámetro de forma beta (>0)
        """
        self.alpha = alpha
        self.beta = beta
        self.beta_dist = stats.beta(alpha, beta)
        
    def rvs(self, size=1, random_state=None):
        """
        Genera muestras aleatorias de la distribución Beta
        y las convierte en ocurrencias binarias (0 o 1).
        
        En cada simulación:
        1. Se genera una probabilidad p desde la distribución Beta
        2. Se genera un valor binario con probabilidad p
        
        Args:
            size: Número de muestras a generar
            random_state: Semilla para reproducibilidad
            
        Returns:
            Muestras aleatorias binarias (0 o 1) basadas en la distribución Beta
        """
        try:
            # Asegurar que size es un valor entero y positivo
            if isinstance(size, (list, tuple, np.ndarray)):
                # Si size es una secuencia, calcular el producto total
                n_samples = 1
                for dim in size:
                    n_samples *= int(dim)
            else:
                # Si size es un escalar
                n_samples = int(size)
                
            if n_samples <= 0:
                return np.array([])
                
            # Generar probabilidades desde la distribución Beta
            probs = self.beta_dist.rvs(size=n_samples, random_state=random_state)
            
            # Configurar generador aleatorio compatible con Generator y RandomState
            if isinstance(random_state, np.random.Generator):
                rng = random_state
            elif isinstance(random_state, np.random.RandomState):
                rng = random_state
            elif isinstance(random_state, (int, np.integer)):
                rng = np.random.RandomState(int(random_state))
            else:
                # Fallback: usar el generador global (menos reproducible)
                rng = np.random
            
            # Generar todos los valores binarios de una vez (más eficiente que un bucle)
            results = rng.binomial(1, np.clip(probs, 0, 1))
            
            # Asegurar que el tipo es entero
            results = results.astype(int)
            
            # Restaurar la forma original si size era una secuencia
            if isinstance(size, (list, tuple, np.ndarray)):
                results = results.reshape(size)
                
            return results
            
        except Exception as e:
            # En caso de error crítico, emitir advertencia visible
            import warnings
            warnings.warn(
                f"Error al generar muestras de frecuencia Beta-Bernoulli: {str(e)}. "
                f"Retornando ceros como fallback, pero esto puede afectar los resultados de la simulación.",
                RuntimeWarning,
                stacklevel=2
            )
            # Devolver un array de ceros del tamaño correcto como fallback
            if isinstance(size, (list, tuple, np.ndarray)):
                return np.zeros(size, dtype=int)
            else:
                return np.zeros(int(size), dtype=int)
    
    def mean(self):
        """
        Calcula la media de ocurrencia binaria.
        Para una variable Bernoulli con p ~ Beta(alpha, beta),
        la media es alpha/(alpha + beta).
        """
        return self.alpha / (self.alpha + self.beta)
    
    def var(self):
        """
        Calcula la varianza de ocurrencia binaria.
        Para una variable Bernoulli X con p ~ Beta(alpha, beta),
        la varianza exacta es Var[X] = αβ/[(α+β)²(α+β+1)]
        usando la ley de varianza total: Var[X] = E[Var[X|p]] + Var[E[X|p]]
        """
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b)**2 * (a + b + 1))
    
    def pmf(self, k):
        """
        Calcula la función de masa de probabilidad.
        Para la distribución binaria basada en Beta, sólo k=0 y k=1 tienen probabilidad no-cero.
        """
        try:
            if np.isscalar(k):
                # Para valores escalares
                if k == 0:
                    return 1 - self.mean()
                elif k == 1:
                    return self.mean()
                else:
                    return 0.0
            else:
                # Para arrays, vectorizar para mayor eficiencia
                k_array = np.asarray(k)
                result = np.zeros_like(k_array, dtype=float)
                mean_val = self.mean()
                
                result[k_array == 0] = 1 - mean_val
                result[k_array == 1] = mean_val
                
                return result
        except Exception as e:
            import warnings
            warnings.warn(
                f"Error al calcular PMF de Beta-Bernoulli: {str(e)}. Retornando ceros.",
                RuntimeWarning,
                stacklevel=2
            )
            # Valor por defecto en caso de error
            if np.isscalar(k):
                return 0.0
            else:
                return np.zeros_like(np.asarray(k), dtype=float)
    
    def cdf(self, k):
        """
        Calcula la función de distribución acumulada.
        Para la distribución binaria basada en Beta, la CDF es escalonada:
        0 para k < 0, (1-p) para 0 <= k < 1, y 1 para k >= 1, donde p = media.
        """
        try:
            if np.isscalar(k):
                if k < 0:
                    return 0.0
                elif k < 1:
                    return 1 - self.mean()
                else:
                    return 1.0
            else:
                # Para arrays, usar vectorización para evitar bucles
                k_array = np.asarray(k)
                result = np.ones_like(k_array, dtype=float)
                mean_val = self.mean()
                
                result[k_array < 0] = 0.0
                result[(k_array >= 0) & (k_array < 1)] = 1 - mean_val
                
                return result
        except Exception as e:
            import warnings
            warnings.warn(
                f"Error al calcular CDF de Beta-Bernoulli: {str(e)}. Retornando fallback.",
                RuntimeWarning,
                stacklevel=2
            )
            # Valor por defecto en caso de error
            if np.isscalar(k):
                return 0.0 if k < 0 else 1.0
            else:
                return np.ones_like(np.asarray(k), dtype=float)
            
    def ppf(self, q):
        """
        Calcula el cuantil (percentil) para la probabilidad q.
        Para distribución binaria, solo tenemos valores 0 y 1.
        """
        # Protección contra valores extremos que podrían causar problemas
        if q <= 0:
            return 0
        if q >= 1:
            return 1
            
        # Lógica normal para percentiles intermedios
        if q < 1 - self.mean():
            return 0
        else:
            return 1
    
    def get_beta_parameters(self):
        """
        Devuelve los parámetros alpha y beta de la distribución Beta subyacente.
        """
        return self.alpha, self.beta
    
    def get_beta_distribution(self):
        """
        Devuelve la distribución Beta subyacente.
        Útil para calcular percentiles o visualizar la distribución de probabilidad.
        """
        return self.beta_dist

# ============================================================================
# Función para normalizar factores de ajuste (backward compatibility)
# ============================================================================
def normalizar_factor_global(factor):
    """
    Asegura que el factor tenga todos los campos necesarios.
    Útil para migrar factores de versiones anteriores del archivo JSON.
    """
    factor_norm = factor.copy()
    
    # Si no tiene tipo_modelo, es formato legacy → migrar a estático
    if 'tipo_modelo' not in factor_norm:
        factor_norm['tipo_modelo'] = 'estatico'
    
    # Asegurar campos para modelo estático
    if 'impacto_porcentual' not in factor_norm:
        factor_norm['impacto_porcentual'] = 0
    
    # Asegurar campos para modelo estocástico (valores por defecto)
    if 'confiabilidad' not in factor_norm:
        factor_norm['confiabilidad'] = 100
    
    if 'reduccion_efectiva' not in factor_norm:
        factor_norm['reduccion_efectiva'] = abs(factor_norm.get('impacto_porcentual', 0))
    
    if 'reduccion_fallo' not in factor_norm:
        factor_norm['reduccion_fallo'] = 0
    
    # Asegurar campo activo
    if 'activo' not in factor_norm:
        factor_norm['activo'] = True
    
    # afecta_frecuencia: True por defecto si impacto_porcentual != 0 (backward compat)
    if 'afecta_frecuencia' not in factor_norm:
        factor_norm['afecta_frecuencia'] = factor_norm.get('impacto_porcentual', 0) != 0
    
    # afecta_severidad: False por defecto para mantener comportamiento existente
    if 'afecta_severidad' not in factor_norm:
        factor_norm['afecta_severidad'] = False
    
    # Para modelo ESTÁTICO: impacto porcentual en severidad
    if 'impacto_severidad_pct' not in factor_norm:
        factor_norm['impacto_severidad_pct'] = 0
    
    # Para modelo ESTOCÁSTICO: reducción de severidad cuando funciona/falla
    if 'reduccion_severidad_efectiva' not in factor_norm:
        factor_norm['reduccion_severidad_efectiva'] = 0
    
    if 'reduccion_severidad_fallo' not in factor_norm:
        factor_norm['reduccion_severidad_fallo'] = 0
    
    # =========================================================================
    # MODELO DE SEGURO/TRANSFERENCIA (para severidad)
    # =========================================================================
    # tipo_severidad: 'porcentual' (default) o 'seguro'
    if 'tipo_severidad' not in factor_norm:
        factor_norm['tipo_severidad'] = 'porcentual'
    
    # Campos de seguro (solo usados si tipo_severidad == 'seguro')
    if 'seguro_deducible' not in factor_norm:
        factor_norm['seguro_deducible'] = 0  # Monto que NO cubre el seguro
    
    if 'seguro_cobertura_pct' not in factor_norm:
        factor_norm['seguro_cobertura_pct'] = 100  # % del exceso sobre deducible que cubre
    
    if 'seguro_limite' not in factor_norm:
        factor_norm['seguro_limite'] = 0  # 0 = sin límite agregado (ilimitado)
    
    # NUEVO: Tipo de deducible - 'agregado' (default, backward compat) o 'por_ocurrencia'
    if 'seguro_tipo_deducible' not in factor_norm:
        factor_norm['seguro_tipo_deducible'] = 'agregado'
    
    # NUEVO: Límite por ocurrencia (0 = sin límite por ocurrencia)
    if 'seguro_limite_ocurrencia' not in factor_norm:
        factor_norm['seguro_limite_ocurrencia'] = 0
    
    # =========================================================================
    # VALIDACIÓN: Clipear valores para evitar errores matemáticos
    # =========================================================================
    # Modelo estático: impacto mínimo -99% (factor mínimo 0.01)
    factor_norm['impacto_porcentual'] = max(factor_norm['impacto_porcentual'], -99)
    factor_norm['impacto_severidad_pct'] = max(factor_norm['impacto_severidad_pct'], -99)
    
    # Modelo estocástico: reducción máxima 99% (factor mínimo 0.01, evita negativos)
    factor_norm['reduccion_efectiva'] = min(max(factor_norm['reduccion_efectiva'], -100), 99)
    factor_norm['reduccion_fallo'] = min(max(factor_norm['reduccion_fallo'], -100), 99)
    factor_norm['reduccion_severidad_efectiva'] = min(max(factor_norm['reduccion_severidad_efectiva'], -100), 99)
    factor_norm['reduccion_severidad_fallo'] = min(max(factor_norm['reduccion_severidad_fallo'], -100), 99)
    
    # Confiabilidad: 0-100%
    factor_norm['confiabilidad'] = min(max(factor_norm['confiabilidad'], 0), 100)
    
    return factor_norm


# Funciones para generar y validar distribuciones de severidad y frecuencia
def generar_distribucion_severidad(opcion, minimo, mas_probable, maximo,
                                 input_method='min_mode_max', params_direct=None):
    """
    Genera un objeto de distribución de severidad de scipy.stats.

    Args:
        opcion (int): El índice de la distribución (1:Normal, 2:LogNormal, etc.).
        minimo (float): Valor mínimo (usado si input_method es 'min_mode_max').
        mas_probable (float): Valor más probable (usado si input_method es 'min_mode_max').
        maximo (float): Valor máximo (usado si input_method es 'min_mode_max').
        input_method (str, optional): 'min_mode_max' o 'direct'. Default 'min_mode_max'.
        params_direct (dict, optional): Diccionario con parámetros directos si input_method es 'direct'.
                                         Ej. Lognormal:
                                             {'s': _, 'scale': _, 'loc': _}  # parámetros nativos SciPy
                                             o {'mean': _, 'std': _, 'loc': _}  # media y desviación estándar en X
                                             o {'mu': _, 'sigma': _, 'loc': _}  # parámetros de ln(X)
                                         Ej. Normal: {'mean': _, 'std': _}
                                         Ej. GPD: {'c': _, 'scale': _, 'loc': _}
                                         Default None.
    Returns:
        scipy.stats.rv_frozen: Objeto de distribución congelado.
    Raises:
        ValueError: Si los parámetros son inválidos o el método es incorrecto.
    """
    try:
        distribucion_severidad = None
        dist_nombre = "" # Para mensajes de error

        # --- Lógica para Lognormal (opcion == 2) ---
        if opcion == 2:
            dist_nombre = "Lognormal"
            if input_method == 'direct':
                if not params_direct:
                    raise ValueError("Parámetros directos requeridos para Lognormal.")
                # loc opcional
                try:
                    loc = float(params_direct.get('loc', 0))
                except (TypeError, ValueError, AttributeError) as e:
                    raise ValueError(f"'loc' debe ser numérico para Lognormal. Error: {e}")

                # Prioridad 1: mean/std en escala original
                if 'mean' in params_direct and 'std' in params_direct:
                    try:
                        mean = float(params_direct['mean'])
                        std = float(params_direct['std'])
                    except (TypeError, ValueError, KeyError) as e:
                        raise ValueError(f"'mean' y 'std' deben ser numéricos para Lognormal. Error: {e}")
                    if mean <= 0:
                        raise ValueError("mean debe ser > 0 para Lognormal.")
                    if std <= 0:
                        raise ValueError("std debe ser > 0 para Lognormal.")
                    # Validación de coeficiente de variación extremo
                    cv = std / mean  # Coeficiente de variación
                    if cv > 10:  # Si CV es extremo
                        raise ValueError(
                            f"Coeficiente de variación muy alto (CV={cv:.2f}). "
                            f"La distribución LogNormal puede ser inestable. "
                            f"Considere usar otra distribución o revisar los valores."
                        )
                    # Validación adicional para evitar problemas numéricos
                    ratio_squared = (std**2) / (mean**2)
                    if ratio_squared < 1e-10:
                        raise ValueError(
                            "La relación (std/mean)² es demasiado pequeña y puede causar problemas numéricos. "
                            "Considere ajustar los valores de std o mean."
                        )
                    sigma2 = np.log(1.0 + ratio_squared)
                    sigma = np.sqrt(sigma2)
                    mu = np.log(mean) - 0.5 * sigma2
                    s = sigma
                    scale = np.exp(mu)
                    distribucion_severidad = lognorm(s=s, scale=scale, loc=loc)

                # Prioridad 2: mu/sigma de ln(X)
                elif 'mu' in params_direct and 'sigma' in params_direct:
                    try:
                        mu = float(params_direct['mu'])
                        sigma = float(params_direct['sigma'])
                    except (TypeError, ValueError, KeyError) as e:
                        raise ValueError(f"'mu' y 'sigma' deben ser numéricos para Lognormal. Error: {e}")
                    if sigma <= 0:
                        raise ValueError("sigma debe ser > 0 para Lognormal.")
                    s = sigma
                    scale = np.exp(mu)
                    distribucion_severidad = lognorm(s=s, scale=scale, loc=loc)

                # Prioridad 3: s/scale nativos SciPy
                elif 's' in params_direct and 'scale' in params_direct:
                    try:
                        s = float(params_direct['s'])
                        scale = float(params_direct['scale'])
                    except (TypeError, ValueError, KeyError) as e:
                        raise ValueError(f"'s' y 'scale' deben ser numéricos para Lognormal. Error: {e}")
                    if s <= 0: 
                        raise ValueError("Shape (s) debe ser positivo.")
                    if scale <= 0: 
                        raise ValueError("Scale debe ser positivo.")
                    distribucion_severidad = lognorm(s=s, scale=scale, loc=loc)
                else:
                    raise ValueError("Para Lognormal direct: provee ('mean','std') o ('mu','sigma') o ('s','scale').")
            elif input_method == 'min_mode_max':
                 # Validar que Min/Mode/Max no sean None si se usa este método
                if minimo is None or mas_probable is None or maximo is None:
                     raise ValueError("Min/Mode/Max requeridos para Lognormal con este método.")
                mu, sigma = obtener_parametros_lognormal(minimo, mas_probable, maximo) # Llama a la función antigua
                distribucion_severidad = lognorm(s=sigma, scale=np.exp(mu))
            else:
                raise ValueError(f"Método de entrada '{input_method}' no válido para {dist_nombre}.")

        # --- Lógica para GPD (opcion == 4) ---
        elif opcion == 4:
            dist_nombre = "GPD (Pareto Generalizada)"
            if input_method == 'direct':
                if not params_direct or 'c' not in params_direct or 'scale' not in params_direct or 'loc' not in params_direct:
                     raise ValueError("Parámetros directos 'c', 'scale' y 'loc' requeridos para GPD.")
                c = params_direct['c']
                scale = params_direct['scale']
                loc = params_direct['loc']
                if scale <= 0: raise ValueError("Scale (beta) debe ser positivo.")
                
                # Validaciones adicionales para GPD
                if c < 0:
                    # Cola finita: soporte es [loc, loc - scale/c]
                    max_support = loc - scale / c
                    import warnings
                    warnings.warn(
                        f"GPD con cola finita (c={c:.3f}). "
                        f"Soporte: [{loc:.2f}, {max_support:.2f}]. "
                        f"Valores fuera de este rango tendrán probabilidad 0.",
                        UserWarning
                    )
                elif c > 0.5:
                    import warnings
                    warnings.warn(
                        f"GPD con cola muy pesada (c={c:.3f}). "
                        f"La media solo existe si c < 1, la varianza si c < 0.5.",
                        UserWarning
                    )
                
                # Usar TruncatedGPD para truncar al P99.9 cuando xi > 0 (cola infinita)
                distribucion_severidad = TruncatedGPD(c=c, scale=scale, loc=loc)
            elif input_method == 'min_mode_max':
                # Validar que Min/Mode/Max no sean None si se usa este método
                if minimo is None or mas_probable is None or maximo is None:
                     raise ValueError("Min/Mode/Max requeridos para GPD con este método.")
                xi, beta_param, mu = obtener_parametros_gpd(minimo, mas_probable, maximo) # Llama a la función antigua
                distribucion_severidad = TruncatedGPD(c=xi, scale=beta_param, loc=mu)
            else:
                raise ValueError(f"Método de entrada '{input_method}' no válido para {dist_nombre}.")

        # --- Lógica para otras distribuciones (usan solo Min/Mode/Max implícitamente) ---
        elif opcion == 5: # Uniforme
             dist_nombre = "Uniforme"
             if minimo is None or maximo is None: raise ValueError("Min/Max requeridos para Uniforme.")
             loc, scale_unif = obtener_parametros_uniforme(minimo, maximo)
             distribucion_severidad = uniform(loc=loc, scale=scale_unif)
        elif opcion == 1: # Normal
             dist_nombre = "Normal"
             if input_method == 'direct':
                 if not params_direct:
                     raise ValueError("Parámetros directos requeridos para Normal.")
                 # Aceptar 'mean'/'std' o sinónimos 'mu'/'sigma'
                 if 'mean' in params_direct and 'std' in params_direct:
                     try:
                         mean = float(params_direct['mean'])
                         std = float(params_direct['std'])
                     except (TypeError, ValueError, KeyError) as e:
                         raise ValueError(f"'mean' y 'std' deben ser numéricos para Normal. Error: {e}")
                 elif 'mu' in params_direct and 'sigma' in params_direct:
                     try:
                         mean = float(params_direct['mu'])
                         std = float(params_direct['sigma'])
                     except (TypeError, ValueError, KeyError) as e:
                         raise ValueError(f"'mu' y 'sigma' deben ser numéricos para Normal. Error: {e}")
                 else:
                     raise ValueError("Para Normal direct: provee ('mean','std') o ('mu','sigma').")
                 if std <= 0:
                     raise ValueError("Desviación estándar (std) debe ser > 0 para Normal.")
                 a_trunc = (0 - mean) / std
                 distribucion_severidad = truncnorm(a=a_trunc, b=np.inf, loc=mean, scale=std)
             elif input_method == 'min_mode_max':
                 if minimo is None or mas_probable is None or maximo is None: raise ValueError("Min/Mode/Max requeridos para Normal.")
                 mu, sigma = obtener_parametros_normal(minimo, mas_probable, maximo)
                 a_trunc = (0 - mu) / sigma
                 distribucion_severidad = truncnorm(a=a_trunc, b=np.inf, loc=mu, scale=sigma)
             else:
                 raise ValueError(f"Método de entrada '{input_method}' no válido para {dist_nombre}.")
        elif opcion == 3: # PERT (Beta)
             dist_nombre = "PERT (Beta)"
             if minimo is None or mas_probable is None or maximo is None: raise ValueError("Min/Mode/Max requeridos para PERT.")
             a, b = obtener_parametros_pert(minimo, mas_probable, maximo)
             distribucion_severidad = beta(a, b, loc=minimo, scale=maximo - minimo)
        else:
            raise ValueError(f"Opción de distribución de severidad desconocida: {opcion}")

        # Comprobación final
        if distribucion_severidad is None:
             raise ValueError(f"No se pudo crear la distribución {dist_nombre}.")

        return distribucion_severidad

    except ValueError as ve:
        # Re-lanzar el error para que sea capturado por guardar_evento
        raise ValueError(f"Error al generar {dist_nombre}: {ve}")
    except Exception as e:
        # Capturar otros errores inesperados
        raise Exception(f"Error inesperado al generar {dist_nombre}: {e}")

def generar_distribucion_frecuencia(opcion, tasa=None, num_eventos_posibles=None, probabilidad_exito=None, poisson_gamma_params=None, beta_params=None):
    """
    Genera un objeto de distribución de frecuencia.
    
    Args:
        opcion (int): El índice de la distribución (1:Poisson, 2:Binomial, 3:Bernoulli, 4:Poisson-Gamma, 5:Beta).
        tasa (float, optional): Tasa de ocurrencia para Poisson. Default None.
        num_eventos_posibles (int, optional): Número de eventos posibles para Binomial. Default None.
        probabilidad_exito (float, optional): Probabilidad de éxito para Binomial o Bernoulli. Default None.
        poisson_gamma_params (tuple, optional): Parámetros (alpha, beta) para la distribución Poisson-Gamma. Default None.
        beta_params (tuple, optional): Parámetros (alpha, beta) para la distribución Beta de probabilidad anual. Default None.
    
    Returns:
        scipy.stats.rv_frozen, PoissonGammaDistribution o BetaFrequencyDistribution: Objeto de distribución congelado.
    """
    try:
        if opcion == 1:
            if tasa is None or tasa <= 0:
                raise ValueError("La tasa (lambda) para Poisson debe ser un valor positivo.")
            distribucion_frecuencia = poisson(mu=tasa)
        elif opcion == 2:
            if num_eventos_posibles is None or num_eventos_posibles <= 0:
                raise ValueError("El número de eventos posibles para Binomial debe ser un entero positivo.")
            if probabilidad_exito is None or not 0 <= probabilidad_exito <= 1:
                raise ValueError("La probabilidad de éxito para Binomial debe estar entre 0 y 1.")
            distribucion_frecuencia = binom(n=num_eventos_posibles, p=probabilidad_exito)
        elif opcion == 3:
            if probabilidad_exito is None or not 0 <= probabilidad_exito <= 1:
                raise ValueError("La probabilidad de éxito para Bernoulli debe estar entre 0 y 1.")
            distribucion_frecuencia = bernoulli(p=probabilidad_exito)
        elif opcion == 4:  # Poisson-Gamma
            if poisson_gamma_params is None or len(poisson_gamma_params) != 2:
                raise ValueError("Se requieren los parámetros (alpha, beta) para la distribución Poisson-Gamma.")
            alpha, beta = poisson_gamma_params
            if alpha <= 1 or beta <= 0:
                raise ValueError("Los parámetros alpha y beta deben ser positivos, y alpha > 1.")
            distribucion_frecuencia = PoissonGammaDistribution(alpha=alpha, beta=beta)
        elif opcion == 5:  # Beta para probabilidad anual
            if beta_params is None or len(beta_params) != 2:
                raise ValueError("Se requieren los parámetros (alpha, beta) para la distribución Beta.")
            alpha, beta = beta_params
            if alpha <= 0 or beta <= 0:
                raise ValueError("Los parámetros alpha y beta deben ser positivos.")
            distribucion_frecuencia = BetaFrequencyDistribution(alpha=alpha, beta=beta)
        else:
            raise ValueError(f"Opción de distribución de frecuencia desconocida: {opcion}")
            
        return distribucion_frecuencia
    except ValueError as ve:
        raise ve
    except Exception as e:
        raise e

def ordenar_eventos_por_dependencia(eventos_riesgo):
    id_a_evento = {evento['id']: evento for evento in eventos_riesgo}
    visitados = set()
    stack = []

    def dfs(evento_id):
        visitados.add(evento_id)
        evento = id_a_evento[evento_id]

        # Buscar los hijos (eventos que dependen de este)
        hijos_ids = []
        for ev in eventos_riesgo:
            # Verificar en la nueva estructura de vínculos
            if 'vinculos' in ev:
                for vinculo in ev['vinculos']:
                    if vinculo['id_padre'] == evento_id:
                        hijos_ids.append(ev['id'])
                        break
            # Compatibilidad con formato antiguo
            elif 'eventos_padres' in ev and evento_id in ev.get('eventos_padres', []):
                hijos_ids.append(ev['id'])

        for hijo_id in hijos_ids:
            if hijo_id not in visitados:
                dfs(hijo_id)
        stack.append(evento_id)

    for evento in eventos_riesgo:
        if evento['id'] not in visitados:
            dfs(evento['id'])

    stack.reverse()
    return stack

def _aplicar_tabla_escalamiento(occurrence_indices, tabla):
    """Mapea índices ordinales de ocurrencia a multiplicadores según tabla de escalamiento.
    
    Args:
        occurrence_indices: np.array con el número ordinal de cada ocurrencia (1-indexed)
        tabla: list[dict] con claves 'desde', 'hasta' (None=∞), 'multiplicador'
    
    Returns:
        np.array de multiplicadores, mismo tamaño que occurrence_indices
    """
    multiplicadores = np.ones(len(occurrence_indices))
    for fila in tabla:
        desde = fila['desde']
        hasta = fila.get('hasta') or np.inf
        mask = (occurrence_indices >= desde) & (occurrence_indices <= hasta)
        multiplicadores[mask] = fila['multiplicador']
    return multiplicadores

def _crear_seccion_escalamiento_ui(parent_layout, evento_data):
    """Crea la sección colapsable de escalamiento de severidad por frecuencia.
    
    Args:
        parent_layout: QVBoxLayout donde agregar la sección
        evento_data: dict del evento (o None para evento nuevo)
    
    Returns:
        tuple: (config_dict, on_freq_changed_callable)
            - config_dict: dict mutable con campos sev_freq_* (actualizado por UI)
            - on_freq_changed: función(freq_opcion) para habilitar/deshabilitar según distribución
    """
    _s = lambda v, d='': str(v) if v is not None else d
    # Inicializar configuración desde datos existentes o defaults
    config = {
        'sev_freq_activado': False,
        'sev_freq_modelo': 'reincidencia',
        'sev_freq_tipo_escalamiento': 'lineal',
        'sev_freq_tabla': [
            {'desde': 1, 'hasta': 2, 'multiplicador': 1.0},
            {'desde': 3, 'hasta': None, 'multiplicador': 2.0}
        ],
        'sev_freq_paso': 0.5,
        'sev_freq_base': 1.5,
        'sev_freq_factor_max': 5.0,
        'sev_freq_alpha': 0.5,
        'sev_freq_solo_aumento': True,
        'sev_freq_sistemico_factor_max': 3.0,
    }
    if evento_data:
        for key in list(config.keys()):
            if key in evento_data:
                val = evento_data[key]
                if key == 'sev_freq_tabla' and isinstance(val, list):
                    config[key] = copy.deepcopy(val)
                else:
                    config[key] = val

    collapsed = [True]
    freq_aplica = [True]  # False si Bernoulli/Beta

    # --- Frame contenedor ---
    esc_frame = QtWidgets.QFrame()
    esc_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
    esc_frame.setStyleSheet("QFrame { border: 1px solid #aaa; border-radius: 3px; }")
    esc_frame_layout = QtWidgets.QVBoxLayout(esc_frame)
    esc_frame_layout.setContentsMargins(0, 0, 0, 0)
    esc_frame_layout.setSpacing(0)

    # --- Header clickeable ---
    esc_header_btn = QtWidgets.QPushButton()
    esc_header_btn.setStyleSheet("""
        QPushButton {
            background-color: #e8dff5;
            color: #333;
            border: none;
            border-bottom: 1px solid #aaa;
            text-align: left;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #d8cfe5;
        }
    """)
    esc_frame_layout.addWidget(esc_header_btn)

    # --- Contenido colapsable ---
    esc_content = QtWidgets.QWidget()
    esc_content_layout = QtWidgets.QVBoxLayout(esc_content)
    esc_content_layout.setContentsMargins(10, 10, 10, 10)
    esc_content_layout.setSpacing(8)

    # Mensaje de no-aplica (oculto por defecto)
    no_aplica_label = QtWidgets.QLabel(
        "⚠ Esta función no aplica para distribuciones con máximo 1 ocurrencia (Bernoulli/Beta). "
        "Cambie la distribución de frecuencia para activar."
    )
    no_aplica_label.setWordWrap(True)
    no_aplica_label.setStyleSheet("background-color: #fff3cd; padding: 8px; border-radius: 3px; color: #856404;")
    no_aplica_label.hide()
    esc_content_layout.addWidget(no_aplica_label)

    # Checkbox activar
    activar_check = QtWidgets.QCheckBox("Activar escalamiento de severidad por frecuencia")
    activar_check.setChecked(config['sev_freq_activado'])
    esc_content_layout.addWidget(activar_check)

    # Info label
    info_label = QtWidgets.QLabel(
        "💡 Cuando un evento se materializa múltiples veces en un año simulado, "
        "las ocurrencias sucesivas pueden tener un impacto económico mayor."
    )
    info_label.setWordWrap(True)
    info_label.setStyleSheet("background-color: #fffacd; padding: 6px; border-radius: 3px;")
    esc_content_layout.addWidget(info_label)

    # --- Contenedor de parámetros (se habilita/deshabilita) ---
    params_container = QtWidgets.QWidget()
    params_layout = QtWidgets.QVBoxLayout(params_container)
    params_layout.setContentsMargins(0, 0, 0, 0)
    params_layout.setSpacing(6)

    # Combo tipo de modelo
    modelo_layout = QtWidgets.QFormLayout()
    modelo_combo = NoScrollComboBox()
    modelo_combo.addItems(["Impacto progresivo por ocurrencia", "Escalamiento por volumen"])
    modelo_combo.setCurrentIndex(0 if config['sev_freq_modelo'] == 'reincidencia' else 1)
    modelo_layout.addRow("Tipo:", modelo_combo)
    params_layout.addLayout(modelo_layout)

    # --- QStackedWidget para paneles de modelo ---
    modelo_stack = QtWidgets.QStackedWidget()

    # ==================== PANEL REINCIDENCIA ====================
    reincidencia_widget = QtWidgets.QWidget()
    reincidencia_layout = QtWidgets.QVBoxLayout(reincidencia_widget)
    reincidencia_layout.setContentsMargins(0, 5, 0, 0)
    reincidencia_layout.setSpacing(6)

    # Combo modo escalamiento
    modo_form = QtWidgets.QFormLayout()
    modo_combo = NoScrollComboBox()
    modo_combo.addItems(["Lineal: factor = 1 + paso × (n-1)", "Exponencial: factor = base ^ (n-1)", "Tabla personalizada"])
    modo_idx = {'lineal': 0, 'exponencial': 1, 'tabla': 2}.get(config['sev_freq_tipo_escalamiento'], 0)
    modo_combo.setCurrentIndex(modo_idx)
    modo_form.addRow("Modo:", modo_combo)
    reincidencia_layout.addLayout(modo_form)

    # Stack para modos de reincidencia
    modo_stack = QtWidgets.QStackedWidget()

    # --- Página Lineal ---
    lineal_widget = QtWidgets.QWidget()
    lineal_form = QtWidgets.QFormLayout(lineal_widget)
    lineal_form.setContentsMargins(0, 5, 0, 0)
    paso_var = QtWidgets.QLineEdit(_s(config['sev_freq_paso']))
    paso_var.setToolTip("Incremento del multiplicador por cada ocurrencia adicional (0.1 = suave, 1.0 = se duplica)")
    factor_max_lineal_var = QtWidgets.QLineEdit(_s(config['sev_freq_factor_max']))
    factor_max_lineal_var.setToolTip("Multiplicador máximo (cap)")
    lineal_form.addRow("Incremento por ocurrencia:", paso_var)
    lineal_form.addRow("Factor máximo:", factor_max_lineal_var)
    modo_stack.addWidget(lineal_widget)

    # --- Página Exponencial ---
    exp_widget = QtWidgets.QWidget()
    exp_form = QtWidgets.QFormLayout(exp_widget)
    exp_form.setContentsMargins(0, 5, 0, 0)
    base_var = QtWidgets.QLineEdit(_s(config['sev_freq_base']))
    base_var.setToolTip("Base multiplicativa (1.1 = suave, 2.0 = se duplica cada vez)")
    factor_max_exp_var = QtWidgets.QLineEdit(_s(config['sev_freq_factor_max']))
    factor_max_exp_var.setToolTip("Multiplicador máximo (cap)")
    exp_form.addRow("Base multiplicativa:", base_var)
    exp_form.addRow("Factor máximo:", factor_max_exp_var)
    modo_stack.addWidget(exp_widget)

    # --- Página Tabla ---
    tabla_widget = QtWidgets.QWidget()
    tabla_layout_v = QtWidgets.QVBoxLayout(tabla_widget)
    tabla_layout_v.setContentsMargins(0, 5, 0, 0)
    tabla_layout_v.setSpacing(4)

    tabla_table = QtWidgets.QTableWidget()
    tabla_table.setColumnCount(3)
    tabla_table.setHorizontalHeaderLabels(["Desde ocurr.", "Hasta ocurr.", "Multiplicador"])
    tabla_table.horizontalHeader().setStretchLastSection(True)
    tabla_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
    tabla_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
    tabla_table.setMinimumHeight(100)
    tabla_table.setMaximumHeight(180)
    tabla_table.verticalHeader().setVisible(False)
    tabla_layout_v.addWidget(tabla_table)

    # Botones tabla
    tabla_btn_layout = QtWidgets.QHBoxLayout()
    btn_add_row = QtWidgets.QPushButton("+ Agregar fila")
    btn_add_row.setFixedHeight(26)
    btn_remove_row = QtWidgets.QPushButton("Eliminar última")
    btn_remove_row.setFixedHeight(26)
    btn_remove_row.setStyleSheet("QPushButton { color: #dc3545; }")
    tabla_btn_layout.addWidget(btn_add_row)
    tabla_btn_layout.addWidget(btn_remove_row)
    tabla_btn_layout.addStretch()
    tabla_layout_v.addLayout(tabla_btn_layout)
    modo_stack.addWidget(tabla_widget)

    reincidencia_layout.addWidget(modo_stack)
    modelo_stack.addWidget(reincidencia_widget)

    # ==================== PANEL SISTÉMICO ====================
    sistemico_widget = QtWidgets.QWidget()
    sistemico_form = QtWidgets.QFormLayout(sistemico_widget)
    sistemico_form.setContentsMargins(0, 5, 0, 0)
    alpha_var = QtWidgets.QLineEdit(_s(config['sev_freq_alpha']))
    alpha_var.setToolTip("Sensibilidad al z-score de frecuencia (0.1 = sutil, 1.0 = fuerte)")
    solo_aumento_check = QtWidgets.QCheckBox("Solo escalar hacia arriba (recomendado)")
    solo_aumento_check.setChecked(config['sev_freq_solo_aumento'])
    factor_max_sist_var = QtWidgets.QLineEdit(_s(config['sev_freq_sistemico_factor_max']))
    factor_max_sist_var.setToolTip("Multiplicador máximo (cap)")
    sistemico_form.addRow("Sensibilidad (alpha):", alpha_var)
    sistemico_form.addRow("", solo_aumento_check)
    sistemico_form.addRow("Factor máximo:", factor_max_sist_var)

    sist_info = QtWidgets.QLabel(
        "💡 Si la frecuencia total en una simulación es inusualmente alta, "
        "todas las pérdidas se escalan proporcionalmente."
    )
    sist_info.setWordWrap(True)
    sist_info.setStyleSheet("background-color: #e8f4f8; padding: 6px; border-radius: 3px;")
    sistemico_form.addRow(sist_info)
    modelo_stack.addWidget(sistemico_widget)

    params_layout.addWidget(modelo_stack)

    # --- Vista previa ---
    preview_label = QtWidgets.QLabel("")
    preview_label.setWordWrap(True)
    preview_label.setStyleSheet("background-color: #f0f0f0; padding: 6px; border-radius: 3px; color: #333;")
    params_layout.addWidget(preview_label)

    esc_content_layout.addWidget(params_container)
    esc_frame_layout.addWidget(esc_content)
    esc_content.hide()

    # ==================== FUNCIONES INTERNAS ====================

    def _actualizar_preview():
        """Actualiza la vista previa del multiplicador."""
        if not config['sev_freq_activado'] or not freq_aplica[0]:
            preview_label.setText("")
            preview_label.hide()
            return
        preview_label.show()
        modelo = 'reincidencia' if modelo_combo.currentIndex() == 0 else 'sistemico'
        if modelo == 'sistemico':
            try:
                a = float(alpha_var.text())
                preview_label.setText(f"📊 Factor por simulación según z-score de frecuencia (alpha={a})")
            except ValueError:
                preview_label.setText("📊 (parámetros inválidos)")
            return
        # Reincidencia: mostrar multiplicadores para primeras N ocurrencias
        modo_idx_val = modo_combo.currentIndex()
        try:
            if modo_idx_val == 0:  # Lineal
                p = float(paso_var.text())
                fm = float(factor_max_lineal_var.text())
                mults = [min(1 + p * (n - 1), fm) for n in range(1, 8)]
            elif modo_idx_val == 1:  # Exponencial
                b = float(base_var.text())
                fm = float(factor_max_exp_var.text())
                mults = [min(b ** (n - 1), fm) for n in range(1, 8)]
            else:  # Tabla
                mults = []
                for n in range(1, 8):
                    mult = 1.0
                    for fila in config['sev_freq_tabla']:
                        desde = fila.get('desde', 1)
                        hasta = fila.get('hasta') or 999
                        if desde <= n <= hasta:
                            mult = fila.get('multiplicador', 1.0)
                    mults.append(mult)
            parts = [f"Occ.{i+1}: ×{m:.1f}" for i, m in enumerate(mults)]
            preview_label.setText("📊 " + " → ".join(parts) + " ...")
        except (ValueError, ZeroDivisionError):
            preview_label.setText("📊 (parámetros inválidos)")

    def _actualizar_header():
        """Actualiza el texto del header colapsable."""
        arrow = "▷" if collapsed[0] else "▽"
        if not freq_aplica[0]:
            esc_header_btn.setText(f"{arrow} Escalamiento de Severidad por Frecuencia (no aplica)")
            esc_header_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e0e0e0; color: #999;
                    border: none; border-bottom: 1px solid #aaa;
                    text-align: left; padding: 8px; font-weight: bold;
                }
                QPushButton:hover { background-color: #d5d5d5; }
            """)
        elif not config['sev_freq_activado']:
            esc_header_btn.setText(f"{arrow} Escalamiento de Severidad por Frecuencia (desactivado)")
            esc_header_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e8dff5; color: #333;
                    border: none; border-bottom: 1px solid #aaa;
                    text-align: left; padding: 8px; font-weight: bold;
                }
                QPushButton:hover { background-color: #d8cfe5; }
            """)
        else:
            modelo = config['sev_freq_modelo']
            if modelo == 'reincidencia':
                tipo = config['sev_freq_tipo_escalamiento']
                if tipo == 'lineal':
                    desc = f"Lineal ×{config['sev_freq_paso']}/occ"
                elif tipo == 'exponencial':
                    desc = f"Exp. base={config['sev_freq_base']}"
                else:
                    desc = "Tabla personalizada"
                desc += f", máx ×{config['sev_freq_factor_max']}"
            else:
                desc = f"Sistémico alpha={config['sev_freq_alpha']}"
            esc_header_btn.setText(f"{arrow} Escalamiento de Severidad por Frecuencia ({desc})")
            esc_header_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d5e0f5; color: #333;
                    border: none; border-bottom: 1px solid #aaa;
                    text-align: left; padding: 8px; font-weight: bold;
                }
                QPushButton:hover { background-color: #c5d0e5; }
            """)

    def _sync_config():
        """Sincroniza los valores de la UI al config dict."""
        config['sev_freq_activado'] = activar_check.isChecked()
        config['sev_freq_modelo'] = 'reincidencia' if modelo_combo.currentIndex() == 0 else 'sistemico'
        modo_idx_val = modo_combo.currentIndex()
        config['sev_freq_tipo_escalamiento'] = ['lineal', 'exponencial', 'tabla'][modo_idx_val]
        try:
            config['sev_freq_paso'] = float(paso_var.text())
        except ValueError:
            paso_var.setText(str(config.get('sev_freq_paso', 0.5)))
        try:
            config['sev_freq_base'] = float(base_var.text())
        except ValueError:
            base_var.setText(str(config.get('sev_freq_base', 1.5)))
        try:
            if modo_idx_val == 0:
                config['sev_freq_factor_max'] = float(factor_max_lineal_var.text())
            elif modo_idx_val == 1:
                config['sev_freq_factor_max'] = float(factor_max_exp_var.text())
        except ValueError:
            val_max = str(config.get('sev_freq_factor_max', 5.0))
            if modo_idx_val == 0:
                factor_max_lineal_var.setText(val_max)
            elif modo_idx_val == 1:
                factor_max_exp_var.setText(val_max)
        try:
            config['sev_freq_alpha'] = float(alpha_var.text())
        except ValueError:
            alpha_var.setText(str(config.get('sev_freq_alpha', 0.5)))
        config['sev_freq_solo_aumento'] = solo_aumento_check.isChecked()
        try:
            config['sev_freq_sistemico_factor_max'] = float(factor_max_sist_var.text())
        except ValueError:
            factor_max_sist_var.setText(str(config.get('sev_freq_sistemico_factor_max', 3.0)))
        _sync_tabla_from_ui()
        _actualizar_header()
        _actualizar_preview()

    def _sync_tabla_from_ui():
        """Lee las filas de la tabla UI y actualiza config['sev_freq_tabla']."""
        tabla_data = []
        for r in range(tabla_table.rowCount()):
            try:
                desde = int(tabla_table.item(r, 0).text()) if tabla_table.item(r, 0) else 1
                hasta_text = tabla_table.item(r, 1).text() if tabla_table.item(r, 1) else ""
                hasta = None if hasta_text.strip() in ("", "∞", "inf") else int(hasta_text)
                mult = float(tabla_table.item(r, 2).text()) if tabla_table.item(r, 2) else 1.0
                tabla_data.append({'desde': desde, 'hasta': hasta, 'multiplicador': mult})
            except (ValueError, AttributeError):
                pass
        if tabla_data:
            config['sev_freq_tabla'] = tabla_data

    def _poblar_tabla():
        """Llena la tabla UI desde config['sev_freq_tabla']."""
        tabla_table.blockSignals(True)
        tabla_table.setRowCount(0)
        for fila in config['sev_freq_tabla']:
            r = tabla_table.rowCount()
            tabla_table.insertRow(r)
            tabla_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(fila.get('desde', 1))))
            hasta = fila.get('hasta')
            tabla_table.setItem(r, 1, QtWidgets.QTableWidgetItem("∞" if hasta is None else str(hasta)))
            tabla_table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(fila.get('multiplicador', 1.0))))
        tabla_table.blockSignals(False)

    def _agregar_fila_tabla():
        r = tabla_table.rowCount()
        desde_val = 1
        if r > 0:
            try:
                prev_hasta = tabla_table.item(r - 1, 1).text()
                if prev_hasta.strip() in ("", "∞", "inf"):
                    prev_desde = int(tabla_table.item(r - 1, 0).text())
                    tabla_table.setItem(r - 1, 1, QtWidgets.QTableWidgetItem(str(prev_desde + 2)))
                    desde_val = prev_desde + 3
                else:
                    desde_val = int(prev_hasta) + 1
            except (ValueError, AttributeError):
                desde_val = r + 1
        tabla_table.insertRow(r)
        tabla_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(desde_val)))
        tabla_table.setItem(r, 1, QtWidgets.QTableWidgetItem("∞"))
        tabla_table.setItem(r, 2, QtWidgets.QTableWidgetItem("1.0"))
        _sync_config()

    def _eliminar_fila_tabla():
        r = tabla_table.rowCount()
        if r > 1:
            tabla_table.removeRow(r - 1)
            last = tabla_table.rowCount() - 1
            if last >= 0:
                tabla_table.setItem(last, 1, QtWidgets.QTableWidgetItem("∞"))
            _sync_config()

    # --- Conectar señales ---
    def _on_activar_changed(state):
        config['sev_freq_activado'] = bool(state)
        params_container.setEnabled(bool(state) and freq_aplica[0])
        _actualizar_header()
        _actualizar_preview()

    def _on_modelo_changed(idx):
        modelo_stack.setCurrentIndex(idx)
        _sync_config()

    def _on_modo_changed(idx):
        modo_stack.setCurrentIndex(idx)
        _sync_config()

    activar_check.stateChanged.connect(_on_activar_changed)
    modelo_combo.currentIndexChanged.connect(_on_modelo_changed)
    modo_combo.currentIndexChanged.connect(_on_modo_changed)
    btn_add_row.clicked.connect(_agregar_fila_tabla)
    btn_remove_row.clicked.connect(_eliminar_fila_tabla)

    for widget in [paso_var, factor_max_lineal_var, base_var, factor_max_exp_var, alpha_var, factor_max_sist_var]:
        widget.textChanged.connect(lambda _: _sync_config())
    solo_aumento_check.stateChanged.connect(lambda _: _sync_config())
    tabla_table.cellChanged.connect(lambda r, c: _sync_config())

    def _toggle_collapsed():
        collapsed[0] = not collapsed[0]
        esc_content.setVisible(not collapsed[0])
        _actualizar_header()

    esc_header_btn.clicked.connect(_toggle_collapsed)

    def on_freq_changed(freq_opcion):
        """Llamar cuando cambia la distribución de frecuencia.
        freq_opcion: 1=Poisson, 2=Binomial, 3=Bernoulli, 4=Poisson-Gamma, 5=Beta
        """
        aplica = freq_opcion not in (3, 5)
        freq_aplica[0] = aplica
        no_aplica_label.setVisible(not aplica)
        activar_check.setEnabled(aplica)
        params_container.setEnabled(aplica and config['sev_freq_activado'])
        info_label.setVisible(aplica)
        if not aplica and config['sev_freq_activado']:
            activar_check.setChecked(False)
            config['sev_freq_activado'] = False
        _actualizar_header()
        _actualizar_preview()

    # --- Inicialización ---
    _poblar_tabla()
    modelo_stack.setCurrentIndex(0 if config['sev_freq_modelo'] == 'reincidencia' else 1)
    modo_stack.setCurrentIndex(modo_idx)
    params_container.setEnabled(config['sev_freq_activado'])
    _actualizar_header()
    _actualizar_preview()

    parent_layout.addWidget(esc_frame)

    return config, on_freq_changed

# Funciones para generar la LDA y mostrar resultados
def generar_lda_con_secuencialidad(eventos_riesgo, num_simulaciones=10000, orden_eventos_ids=None, rng=None):
    print(f"\n[DEBUG SIMULACION] ========================================")
    print(f"[DEBUG SIMULACION] generar_lda_con_secuencialidad INICIANDO")
    print(f"[DEBUG SIMULACION] Número de eventos recibidos: {len(eventos_riesgo)}")
    print(f"[DEBUG SIMULACION] Número de simulaciones: {num_simulaciones}")
    print(f"[DEBUG SIMULACION] ========================================\n")
    
    id_a_evento = {evento['id']: evento for evento in eventos_riesgo}
    id_a_index = {evento['id']: idx for idx, evento in enumerate(eventos_riesgo)}
    num_eventos = len(eventos_riesgo)
    perdidas_totales = np.zeros(num_simulaciones)
    frecuencias_totales = np.zeros(num_simulaciones, dtype=np.int32)
    perdidas_por_evento = [np.zeros(num_simulaciones) for _ in range(num_eventos)]
    frecuencias_por_evento = [np.zeros(num_simulaciones, dtype=np.int32) for _ in range(num_eventos)]
    
    # DEBUG: Inspeccionar TODOS los eventos
    print(f"[DEBUG EVENTOS] Inspeccionando eventos recibidos:")
    for i, e in enumerate(eventos_riesgo):
        nombre = e.get('nombre', 'Sin nombre')
        tiene_factores = 'factores_ajuste' in e
        factores = e.get('factores_ajuste', [])
        print(f"  [{i}] '{nombre}': tiene_factores={tiene_factores}, factores={factores}")
    
    # DEBUG: Mostrar eventos con factores de ajuste
    eventos_con_ajustes = [e for e in eventos_riesgo if e.get('factores_ajuste')]
    if eventos_con_ajustes:
        print(f"\n[DEBUG] === INICIO SIMULACIÓN ===")
        print(f"[DEBUG] {len(eventos_con_ajustes)} evento(s) con factores de ajuste configurados:")
        for e in eventos_con_ajustes:
            factores = e.get('factores_ajuste', [])
            activos = [f for f in factores if f.get('activo', True)]
            print(f"  - '{e.get('nombre')}': {len(activos)}/{len(factores)} factores activos")
        print(f"[DEBUG] ==========================\n")

    # Ordenar eventos para procesar padres antes que hijos
    if orden_eventos_ids is None:
        orden_eventos_ids = ordenar_eventos_por_dependencia(eventos_riesgo)

    for evento_id in orden_eventos_ids:
        idx = id_a_index[evento_id]
        evento = id_a_evento[evento_id]
        dist_sev = evento['dist_severidad']
        dist_freq = evento['dist_frecuencia']
        
        # Procesando evento para aplicar factores de ajuste si existen
        
        # ====================================================================
        # APLICAR AJUSTES DE PROBABILIDAD SI EXISTEN FACTORES ACTIVOS
        # ====================================================================
        if 'factores_ajuste' in evento and evento['factores_ajuste']:
            try:
                from log_odds_utils import ajustar_probabilidad_por_factores
                
                # Verificar si hay al menos un factor activo
                factores_activos = [f for f in evento['factores_ajuste'] if f.get('activo', True)]
                
                # DEBUG: Informar que se están aplicando ajustes
                nombre_evento = evento.get('nombre', 'Sin nombre')
                if factores_activos:
                    print(f"[DEBUG] Aplicando {len(factores_activos)} factores activos a evento '{nombre_evento}'")
                
                if factores_activos:
                    # Extraer información de la distribución de frecuencia
                    freq_opcion = evento.get('freq_opcion', 3)  # Default Bernoulli
                    
                    # ====================================================================
                    # NUEVO: Determinar si hay factores estocásticos
                    # ====================================================================
                    tiene_estocasticos = any(f.get('tipo_modelo') == 'estocastico' for f in factores_activos)
                    
                    if tiene_estocasticos:
                        # ===== MODELO ESTOCÁSTICO: Generar vector de factores por simulación =====
                        print(f"[DEBUG ESTOCASTICO] Evento '{nombre_evento}' tiene factores estocásticos")
                        
                        # Generar vector de factores multiplicativos (uno por simulación)
                        factores_vector = np.ones(num_simulaciones)
                        factores_severidad_vector = np.ones(num_simulaciones)  # NUEVO: vector para severidad
                        seguros_aplicables = []  # Lista de seguros a aplicar (independiente del modelo)
                        
                        for f in factores_activos:
                            tipo_modelo = f.get('tipo_modelo', 'estatico')
                            
                            if tipo_modelo == 'estocastico':
                                # Samplear estados del control para TODAS las simulaciones
                                confiabilidad = f.get('confiabilidad', 100) / 100.0
                                estados = rng.random(num_simulaciones)  # Vector aleatorio [0, 1]
                                
                                # Determinar qué simulaciones tienen control funcionando
                                funciona = estados < confiabilidad
                                
                                # === Aplicar reducción de FRECUENCIA según estado ===
                                reduccion_efectiva = f.get('reduccion_efectiva', 0) / 100.0
                                reduccion_fallo = f.get('reduccion_fallo', 0) / 100.0
                                # VALIDACIÓN: Clipear reducciones para evitar factores negativos o > 2
                                reduccion_efectiva = np.clip(reduccion_efectiva, -1.0, 0.99)  # Max 99% reducción
                                reduccion_fallo = np.clip(reduccion_fallo, -1.0, 0.99)
                                reducciones = np.where(funciona, reduccion_efectiva, reduccion_fallo)
                                factores_vector *= (1 - reducciones)
                                
                                # === NUEVO: Aplicar reducción de SEVERIDAD según estado ===
                                red_sev_efectiva = f.get('reduccion_severidad_efectiva', 0) / 100.0
                                red_sev_fallo = f.get('reduccion_severidad_fallo', 0) / 100.0
                                # VALIDACIÓN: Clipear reducciones para evitar factores negativos o > 2
                                red_sev_efectiva = np.clip(red_sev_efectiva, -1.0, 0.99)
                                red_sev_fallo = np.clip(red_sev_fallo, -1.0, 0.99)
                                if red_sev_efectiva != 0 or red_sev_fallo != 0:
                                    reducciones_sev = np.where(funciona, red_sev_efectiva, red_sev_fallo)
                                    factores_severidad_vector *= (1 - reducciones_sev)
                                
                                # DEBUG stats
                                num_funciona = np.sum(funciona)
                                pct_funciona = 100 * num_funciona / num_simulaciones
                                print(f"[DEBUG ESTOCASTICO]   Factor '{f['nombre']}': {pct_funciona:.1f}% funciona "
                                      f"(esperado: {confiabilidad*100:.1f}%)")
                            
                            else:  # Estático (mezclado con estocásticos)
                                # Frecuencia: solo si afecta_frecuencia es True
                                if f.get('afecta_frecuencia', True):  # backward compat: True por defecto
                                    impacto_pct = f.get('impacto_porcentual', 0)
                                    # VALIDACIÓN: Clipear impacto para evitar factores <= 0
                                    impacto_pct = max(impacto_pct, -99)
                                    factores_vector *= (1 + impacto_pct / 100.0)
                                
                                # Severidad: solo si afecta_severidad es True
                                if f.get('afecta_severidad', False):
                                    tipo_sev = f.get('tipo_severidad', 'porcentual')
                                    if tipo_sev == 'seguro':
                                        # Guardar seguro para aplicar después
                                        ded_val = float(f.get('seguro_deducible', 0) or 0)
                                        cob_val = float(f.get('seguro_cobertura_pct', 100) or 100)
                                        lim_val = float(f.get('seguro_limite', 0) or 0)
                                        tipo_ded = f.get('seguro_tipo_deducible', 'agregado')
                                        lim_ocurr = float(f.get('seguro_limite_ocurrencia', 0) or 0)
                                        seguros_aplicables.append({
                                            'nombre': f.get('nombre', 'Seguro'),
                                            'deducible': ded_val,
                                            'cobertura_pct': cob_val / 100.0,
                                            'limite': lim_val,
                                            'tipo_deducible': tipo_ded,
                                            'limite_ocurrencia': lim_ocurr
                                        })
                                        print(f"[DEBUG ESTOCASTICO]   Seguro '{f.get('nombre')}': Tipo={tipo_ded}, "
                                              f"Ded=${ded_val:,.0f}, Cob={cob_val:.0f}%, Lím=${lim_val:,.0f}, LímOcurr=${lim_ocurr:,.0f}")
                                    else:
                                        impacto_sev = f.get('impacto_severidad_pct', 0)
                                        # VALIDACIÓN: Clipear impacto para evitar factores <= 0
                                        impacto_sev = max(impacto_sev, -99)
                                        factores_severidad_vector *= (1 + impacto_sev / 100.0)
                        
                        # VALIDACIÓN FINAL: Asegurar vectores en rango razonable [0.01, inf)
                        factores_vector = np.maximum(factores_vector, 0.01)
                        factores_severidad_vector = np.maximum(factores_severidad_vector, 0.01)
                        
                        print(f"[DEBUG ESTOCASTICO]   Factor frecuencia: min={factores_vector.min():.4f}, "
                              f"mean={factores_vector.mean():.4f}, max={factores_vector.max():.4f}")
                        print(f"[DEBUG ESTOCASTICO]   Factor severidad: min={factores_severidad_vector.min():.4f}, "
                              f"mean={factores_severidad_vector.mean():.4f}, max={factores_severidad_vector.max():.4f}")
                        
                        # Guardar vectores para usar al generar muestras
                        evento['_factores_vector'] = factores_vector
                        evento['_factores_severidad_vector'] = factores_severidad_vector  # NUEVO
                        evento['_usa_estocastico'] = True
                        evento['_seguros_aplicables'] = seguros_aplicables  # Seguros se aplican siempre
                        
                        # Flags guardados correctamente para usar en sampleo
                        
                    else:
                        # ===== MODELO ESTÁTICO: Factor único =====
                        factor_multiplicativo = 1.0
                        factor_severidad = 1.0  # Factor porcentual para severidad
                        seguros_aplicables = []  # Lista de seguros a aplicar
                        
                        for f in factores_activos:
                            # Frecuencia: solo si afecta_frecuencia es True
                            if f.get('afecta_frecuencia', True):  # backward compat: True por defecto
                                impacto_pct = f.get('impacto_porcentual', 0)
                                # VALIDACIÓN: Clipear impacto para evitar factores <= 0
                                impacto_pct = max(impacto_pct, -99)  # Max -99% (factor mínimo 0.01)
                                factor_multiplicativo *= (1 + impacto_pct / 100.0)
                            
                            # Severidad: solo si afecta_severidad es True
                            if f.get('afecta_severidad', False):
                                tipo_sev = f.get('tipo_severidad', 'porcentual')
                                if tipo_sev == 'seguro':
                                    # Guardar seguro para aplicar después
                                    ded_val_s = float(f.get('seguro_deducible', 0) or 0)
                                    cob_val_s = float(f.get('seguro_cobertura_pct', 100) or 100)
                                    lim_val_s = float(f.get('seguro_limite', 0) or 0)
                                    tipo_ded_s = f.get('seguro_tipo_deducible', 'agregado')
                                    lim_ocurr_s = float(f.get('seguro_limite_ocurrencia', 0) or 0)
                                    seguros_aplicables.append({
                                        'nombre': f.get('nombre', 'Seguro'),
                                        'deducible': ded_val_s,
                                        'cobertura_pct': cob_val_s / 100.0,
                                        'limite': lim_val_s,
                                        'tipo_deducible': tipo_ded_s,
                                        'limite_ocurrencia': lim_ocurr_s
                                    })
                                    print(f"[DEBUG]   Seguro '{f.get('nombre')}': Tipo={tipo_ded_s}, "
                                          f"Ded=${ded_val_s:,.0f}, Cob={cob_val_s:.0f}%, Lím=${lim_val_s:,.0f}, LímOcurr=${lim_ocurr_s:,.0f}")
                                else:
                                    # Reducción porcentual
                                    impacto_sev = f.get('impacto_severidad_pct', 0)
                                    # VALIDACIÓN: Clipear impacto para evitar factores <= 0
                                    impacto_sev = max(impacto_sev, -99)  # Max -99% (factor mínimo 0.01)
                                    factor_severidad *= (1 + impacto_sev / 100.0)
                        
                        # VALIDACIÓN FINAL: Asegurar factores en rango razonable
                        factor_multiplicativo = max(factor_multiplicativo, 0.01)  # Mínimo 1% de la frecuencia original
                        factor_severidad = max(factor_severidad, 0.01)  # Mínimo 1% de la severidad original
                        
                        print(f"[DEBUG]   Factor frecuencia: {factor_multiplicativo:.4f} ({(factor_multiplicativo-1)*100:+.1f}%)")
                        if factor_severidad != 1.0:
                            print(f"[DEBUG]   Factor severidad porcentual: {factor_severidad:.4f} ({(factor_severidad-1)*100:+.1f}%)")
                        
                        evento['_usa_estocastico'] = False
                        # Guardar factor de severidad porcentual y seguros
                        evento['_factor_severidad_estatico'] = factor_severidad
                        evento['_seguros_aplicables'] = seguros_aplicables
                        
                        # ===== SOLO PARA ESTÁTICO: Ajustar dist_freq una vez =====
                        # Para estocástico, dist_freq se mantiene original y se ajusta al samplear
                        # Aplicar ajuste según el tipo de distribución
                        if freq_opcion == 1:  # Poisson (λ = frecuencia esperada)
                            tasa_original = evento.get('tasa')
                            if tasa_original is not None and tasa_original > 0:
                                # Ajustar la frecuencia esperada directamente
                                tasa_ajustada = tasa_original * factor_multiplicativo
                                tasa_ajustada = max(tasa_ajustada, 0.0001)  # Evitar λ=0
                                dist_freq = poisson(mu=tasa_ajustada)
                                print(f"[DEBUG]   Poisson: λ {tasa_original:.4f} → {tasa_ajustada:.4f}")
                        
                        elif freq_opcion == 2:  # Binomial (n, p)
                            prob_original = evento.get('prob_exito')
                            n = evento.get('num_eventos', 1)
                            if prob_original is not None and 0 < prob_original < 1:
                                # Para probabilidades, usar log-odds
                                from log_odds_utils import ajustar_probabilidad_por_factores
                                prob_ajustada, _ = ajustar_probabilidad_por_factores(prob_original, evento['factores_ajuste'])
                                prob_ajustada = min(max(prob_ajustada, 0.0001), 0.9999)
                                dist_freq = binom(n=n, p=prob_ajustada)
                                print(f"[DEBUG]   Binomial: p {prob_original:.4f} → {prob_ajustada:.4f}")
                        
                        elif freq_opcion == 3:  # Bernoulli (p)
                            prob_original = evento.get('prob_exito')
                            if prob_original is not None and 0 < prob_original < 1:
                                # Para probabilidades, usar log-odds
                                from log_odds_utils import ajustar_probabilidad_por_factores
                                prob_ajustada, _ = ajustar_probabilidad_por_factores(prob_original, evento['factores_ajuste'])
                                prob_ajustada = min(max(prob_ajustada, 0.0001), 0.9999)
                                dist_freq = bernoulli(p=prob_ajustada)
                                print(f"[DEBUG]   Bernoulli: p {prob_original:.4f} → {prob_ajustada:.4f}")
                        
                        elif freq_opcion == 4:  # Poisson-Gamma (distribución sobre λ)
                            # Ajustar el valor más probable (que representa la tasa esperada)
                            mas_probable_original = evento.get('pg_mas_probable')
                            if mas_probable_original is not None and mas_probable_original > 0:
                                mas_probable_ajustado = mas_probable_original * factor_multiplicativo
                                mas_probable_ajustado = max(mas_probable_ajustado, 0.0001)
                                
                                # Recalcular parámetros manteniendo la forma de la distribución
                                minimo = evento.get('pg_minimo', 0)
                                maximo = evento.get('pg_maximo', mas_probable_original * 2)
                                confianza = evento.get('pg_confianza', 0.9)
                                
                                # Ajustar también min y max proporcionalmente
                                minimo_ajustado = minimo * factor_multiplicativo
                                maximo_ajustado = maximo * factor_multiplicativo
                                
                                # Recalcular alpha y beta con valores ajustados
                                try:
                                    from scipy.stats import gamma
                                    mu = (minimo_ajustado + 4 * mas_probable_ajustado + maximo_ajustado) / 6
                                    sigma = (maximo_ajustado - minimo_ajustado) / 6
                                    # Validar sigma razonable
                                    if sigma > 0.001 and mu > 0:
                                        alpha = (mu / sigma) ** 2
                                        beta = mu / (sigma ** 2)
                                        if alpha > 0 and beta > 0 and alpha < 1e6:
                                            dist_freq = nbinom(n=alpha, p=beta/(beta+1))
                                            print(f"[DEBUG]   Poisson-Gamma: Valor más probable {mas_probable_original:.4f} → {mas_probable_ajustado:.4f}")
                                        else:
                                            # Fallback a Poisson simple
                                            dist_freq = poisson(mu=max(mu, 0.0001))
                                            print(f"[DEBUG]   Poisson-Gamma: parámetros extremos, usando Poisson(μ={mu:.4f})")
                                    else:
                                        # Fallback a Poisson simple si sigma es muy pequeño
                                        dist_freq = poisson(mu=max(mu, 0.0001))
                                        print(f"[DEBUG]   Poisson-Gamma: sigma muy pequeño, usando Poisson(μ={mu:.4f})")
                                except Exception as e:
                                    print(f"[DEBUG]   Poisson-Gamma: Error ({e}), usando original")
                        
                        elif freq_opcion == 5:  # Beta (distribución sobre p)
                            # El valor más probable representa una probabilidad
                            mas_probable_original = evento.get('beta_mas_probable')
                            if mas_probable_original is not None:
                                prob_original = mas_probable_original / 100.0
                                if 0 < prob_original < 1:
                                    # Para probabilidades, usar log-odds
                                    from log_odds_utils import ajustar_probabilidad_por_factores
                                    prob_ajustada, _ = ajustar_probabilidad_por_factores(prob_original, evento['factores_ajuste'])
                                    prob_ajustada = min(max(prob_ajustada, 0.0001), 0.9999)
                                    
                                    # Recalcular alpha y beta manteniendo la varianza relativa
                                    minimo = evento.get('beta_minimo', 0) / 100.0
                                    maximo = evento.get('beta_maximo', 100) / 100.0
                                    confianza = evento.get('beta_confianza', 0.9)
                                    
                                    try:
                                        mu_ajustado = prob_ajustada
                                        # Mantener la misma dispersión relativa
                                        sigma_original = (maximo - minimo) / 6
                                        alpha_beta_sum = mu_ajustado * (1 - mu_ajustado) / (sigma_original ** 2) - 1
                                        alpha_ajustado = mu_ajustado * alpha_beta_sum
                                        beta_ajustado = (1 - mu_ajustado) * alpha_beta_sum
                                        
                                        if alpha_ajustado > 0 and beta_ajustado > 0:
                                            # Usar Beta para generar p, luego Bernoulli
                                            # En simulación, samplear de Beta y luego usar ese p
                                            dist_freq = beta(a=alpha_ajustado, b=beta_ajustado)
                                            print(f"[DEBUG]   Beta: p más probable {prob_original:.4f} → {prob_ajustada:.4f}")
                                        else:
                                            print(f"[DEBUG]   Beta: Parámetros inválidos, usando Bernoulli simple")
                                            dist_freq = bernoulli(p=prob_ajustada)
                                    except:
                                        print(f"[DEBUG]   Beta: Error en cálculo, usando Bernoulli simple")
                                        dist_freq = bernoulli(p=prob_ajustada)
            
            except ImportError:
                # Si no está disponible log_odds_utils, usar distribución original
                pass
            except Exception as e:
                # En caso de error, usar distribución original y continuar
                import warnings
                warnings.warn(
                    f"Error al aplicar ajustes de probabilidad para evento '{evento.get('nombre', evento_id)}': {str(e)}. "
                    f"Se usará la distribución original.",
                    RuntimeWarning,
                    stacklevel=2
                )
        # ====================================================================
        # FIN DE APLICACIÓN DE AJUSTES
        # ====================================================================

        # Compatibilidad: verificar si usa la nueva estructura o la antigua
        if 'vinculos' in evento and evento['vinculos']:
            vinculos = evento['vinculos']

            # Inicializar condiciones para cada tipo
            condicion_and = np.ones(num_simulaciones, dtype=bool)
            condicion_or = np.zeros(num_simulaciones, dtype=bool)
            condicion_excluye = np.ones(num_simulaciones, dtype=bool)
            tiene_and = False
            tiene_or = False
            tiene_excluye = False

            # Inicializar acumuladores de factor de severidad por tipo
            factor_sev_and = np.ones(num_simulaciones)   # producto de factores AND
            factor_sev_or_max = np.zeros(num_simulaciones) # máximo de factores OR activados (init 0 para que max funcione con factores < 1.0)
            tiene_factor_sev = False

            # Procesar cada vínculo individualmente con su probabilidad de activación
            for vinculo in vinculos:
                tipo = vinculo.get('tipo', 'AND')
                id_padre = vinculo['id_padre']
                prob = max(0.01, min(1.0, vinculo.get('probabilidad', 100) / 100.0))
                fsev = max(0.10, min(5.0, vinculo.get('factor_severidad', 1.0)))
                umbral = max(0, vinculo.get('umbral_severidad', 0))

                if id_padre not in id_a_index:
                    print(f"[DEBUG] Vínculo ignorado: id_padre {id_padre} no encontrado en id_a_index")
                    continue

                padre_idx = id_a_index[id_padre]
                padre_ocurrio = frecuencias_por_evento[padre_idx] > 0

                # Aplicar umbral de severidad del padre si está configurado
                if umbral > 0:
                    padre_ocurrio = padre_ocurrio & (perdidas_por_evento[padre_idx] >= umbral)

                # Generar vector de activación probabilística
                if prob >= 1.0:
                    activacion = np.ones(num_simulaciones, dtype=bool)
                else:
                    activacion = rng.random(num_simulaciones) < prob

                # Máscara de activación efectiva para este vínculo
                vinculo_activo = padre_ocurrio & activacion

                if tipo == 'AND':
                    tiene_and = True
                    condicion_and = condicion_and & vinculo_activo
                    # Acumular factor de severidad (producto) para simulaciones donde se activa
                    if fsev != 1.0:
                        tiene_factor_sev = True
                        # Solo aplicar factor donde el vínculo se activó
                        factor_sev_and = np.where(vinculo_activo, factor_sev_and * fsev, factor_sev_and)
                elif tipo == 'OR':
                    tiene_or = True
                    condicion_or = condicion_or | vinculo_activo
                    # Siempre acumular max factor para vínculos OR activos (incluye fsev=1.0 para no perder neutralización)
                    factor_sev_or_max = np.where(vinculo_activo, np.maximum(factor_sev_or_max, fsev), factor_sev_or_max)
                    if fsev != 1.0:
                        tiene_factor_sev = True
                elif tipo == 'EXCLUYE':
                    tiene_excluye = True
                    condicion_excluye = condicion_excluye & ~vinculo_activo
                else:
                    print(f"[DEBUG] Tipo de vínculo no reconocido: '{tipo}', ignorando")

            # Combinar condiciones según los tipos presentes
            condicion_final = np.ones(num_simulaciones, dtype=bool)

            if tiene_and:
                condicion_final = condicion_final & condicion_and

            if tiene_or:
                condicion_final = condicion_final & condicion_or

            if tiene_excluye:
                condicion_final = condicion_final & condicion_excluye

            # Calcular factor de severidad combinado para simulaciones activas
            if tiene_factor_sev:
                factor_severidad_vinculos = np.ones(num_simulaciones)
                if tiene_and:
                    factor_severidad_vinculos *= factor_sev_and
                if tiene_or:
                    # Usar condicion_or como guardia: donde ningún OR activó, factor = 1.0 (neutral)
                    factor_sev_or_final = np.where(condicion_or, factor_sev_or_max, 1.0)
                    factor_severidad_vinculos *= factor_sev_or_final
                # Solo aplicar donde condicion_final es True; resto queda 1.0
                factor_severidad_vinculos = np.where(condicion_final, factor_severidad_vinculos, 1.0)
                evento['_factor_severidad_vinculos'] = factor_severidad_vinculos
            else:
                evento['_factor_severidad_vinculos'] = None

            # Simular frecuencia solo para las condiciones que se cumplen
            muestras_frecuencia = np.zeros(num_simulaciones, dtype=int)
            indices_a_simular = np.where(condicion_final)[0]

            if len(indices_a_simular) > 0:
                try:
                    # ====================================================================
                    # Generar muestras con factores estocásticos si aplica
                    # ====================================================================
                    freq_opcion = evento.get('freq_opcion', 3)
                    usa_estocastico = evento.get('_usa_estocastico', False)
                    
                    if usa_estocastico:
                        # MODELO ESTOCÁSTICO: Aplicar factores vectorizados
                        factores_vector = evento.get('_factores_vector')
                        
                        if freq_opcion == 1:  # Poisson
                            tasa_original = evento.get('tasa', 1.0)
                            # Aplicar factores a cada simulación
                            tasas_ajustadas = tasa_original * factores_vector[indices_a_simular]
                            tasas_ajustadas = np.maximum(tasas_ajustadas, 0.0001)  # Evitar λ=0
                            
                            # Generar muestras con tasas individuales
                            muestras_frecuencia_simuladas = np.array([
                                poisson.rvs(mu=lam, random_state=rng) for lam in tasas_ajustadas
                            ], dtype=np.int32)
                            
                        elif freq_opcion == 3:  # Bernoulli
                            from log_odds_utils import aplicar_factor_a_probabilidad
                            prob_original = evento.get('prob_exito', 0.5)
                            
                            # Aplicar factores a cada simulación usando log-odds
                            probs_ajustadas = np.array([
                                aplicar_factor_a_probabilidad(prob_original, factor)
                                for factor in factores_vector[indices_a_simular]
                            ])
                            probs_ajustadas = np.clip(probs_ajustadas, 0.0001, 0.9999)
                            
                            # Generar muestras con probabilidades individuales
                            muestras_frecuencia_simuladas = np.array([
                                bernoulli.rvs(p=p, random_state=rng) for p in probs_ajustadas
                            ], dtype=np.int32)
                        
                        elif freq_opcion == 2:  # Binomial
                            from log_odds_utils import aplicar_factor_a_probabilidad
                            prob_original = evento.get('prob_exito', 0.5)
                            n = evento.get('num_eventos', 1)
                            
                            # Aplicar factores usando log-odds
                            probs_ajustadas = np.array([
                                aplicar_factor_a_probabilidad(prob_original, factor)
                                for factor in factores_vector[indices_a_simular]
                            ])
                            probs_ajustadas = np.clip(probs_ajustadas, 0.0001, 0.9999)
                            
                            # Generar muestras
                            muestras_frecuencia_simuladas = np.array([
                                binom.rvs(n=n, p=p, random_state=rng) for p in probs_ajustadas
                            ], dtype=np.int32)
                        
                        elif freq_opcion == 4:  # Poisson-Gamma (Binomial Negativa)
                            mas_probable_original = evento.get('pg_mas_probable', 1.0)
                            
                            # Aplicar factores multiplicativamente
                            mus_ajustados = mas_probable_original * factores_vector[indices_a_simular]
                            mus_ajustados = np.maximum(mus_ajustados, 0.0001)
                            
                            # Obtener parámetros
                            minimo = evento.get('pg_minimo', 0)
                            maximo = evento.get('pg_maximo', mas_probable_original * 2)
                            
                            muestras_lista = []
                            for mu_ajustado in mus_ajustados:
                                try:
                                    escala = mu_ajustado / mas_probable_original if mas_probable_original > 0 else 1.0
                                    minimo_ajustado = minimo * escala
                                    maximo_ajustado = maximo * escala
                                    
                                    sigma = (maximo_ajustado - minimo_ajustado) / 6
                                    if sigma > 0.001 and mu_ajustado > 0:  # Umbral mínimo para sigma
                                        alpha = (mu_ajustado / sigma) ** 2
                                        beta_param = mu_ajustado / (sigma ** 2)
                                        
                                        # Validar parámetros razonables para nbinom
                                        if alpha > 0 and beta_param > 0 and alpha < 1e6:
                                            p = beta_param / (beta_param + 1)
                                            p = min(max(p, 0.0001), 0.9999)
                                            muestra = nbinom.rvs(n=alpha, p=p, random_state=rng)
                                        else:
                                            # Fallback: usar Poisson simple con μ ajustado
                                            muestra = poisson.rvs(mu=max(mu_ajustado, 0.0001), random_state=rng)
                                    elif mu_ajustado > 0:
                                        # Fallback: usar Poisson simple cuando sigma es muy pequeño
                                        muestra = poisson.rvs(mu=max(mu_ajustado, 0.0001), random_state=rng)
                                    else:
                                        muestra = 0
                                except:
                                    # Fallback seguro en caso de cualquier error
                                    muestra = poisson.rvs(mu=max(mu_ajustado, 0.0001), random_state=rng) if mu_ajustado > 0 else 0
                                
                                muestras_lista.append(muestra)
                            
                            muestras_frecuencia_simuladas = np.array(muestras_lista, dtype=np.int32)
                        
                        elif freq_opcion == 5:  # Beta
                            from log_odds_utils import aplicar_factor_a_probabilidad
                            
                            mas_probable_original = evento.get('beta_mas_probable', 50) / 100.0
                            
                            # Aplicar factores usando log-odds
                            probs_ajustadas = np.array([
                                aplicar_factor_a_probabilidad(mas_probable_original, factor)
                                for factor in factores_vector[indices_a_simular]
                            ])
                            probs_ajustadas = np.clip(probs_ajustadas, 0.0001, 0.9999)
                            
                            # Obtener parámetros
                            minimo = evento.get('beta_minimo', 0) / 100.0
                            maximo = evento.get('beta_maximo', 100) / 100.0
                            sigma_original = (maximo - minimo) / 6
                            
                            muestras_lista = []
                            for prob_ajustada in probs_ajustadas:
                                try:
                                    if sigma_original > 0:
                                        alpha_beta_sum = prob_ajustada * (1 - prob_ajustada) / (sigma_original ** 2) - 1
                                        alpha = prob_ajustada * alpha_beta_sum
                                        beta_param = (1 - prob_ajustada) * alpha_beta_sum
                                        
                                        if alpha > 0 and beta_param > 0:
                                            p_sampled = beta.rvs(a=alpha, b=beta_param, random_state=rng)
                                            muestra = bernoulli.rvs(p=p_sampled, random_state=rng)
                                        else:
                                            muestra = bernoulli.rvs(p=prob_ajustada, random_state=rng)
                                    else:
                                        muestra = bernoulli.rvs(p=prob_ajustada, random_state=rng)
                                except:
                                    muestra = bernoulli.rvs(p=prob_ajustada, random_state=rng)
                                
                                muestras_lista.append(muestra)
                            
                            muestras_frecuencia_simuladas = np.array(muestras_lista, dtype=np.int32)
                        
                        else:
                            # Fallback para distribuciones no soportadas
                            print(f"[ADVERTENCIA] Distribución freq_opcion={freq_opcion} no soporta factores estocásticos. Usando modelo estático.")
                            muestras_frecuencia_simuladas = dist_freq.rvs(size=len(indices_a_simular), random_state=rng)
                            muestras_frecuencia_simuladas = muestras_frecuencia_simuladas.astype(np.int32)
                    
                    else:
                        # MODELO ESTÁTICO O SIN AJUSTES: Usar dist_freq normal
                        muestras_frecuencia_simuladas = dist_freq.rvs(size=len(indices_a_simular), random_state=rng)
                        muestras_frecuencia_simuladas = muestras_frecuencia_simuladas.astype(np.int32)
                    
                    # Manejar posibles valores infinitos o NaN
                    muestras_frecuencia_simuladas = np.nan_to_num(muestras_frecuencia_simuladas, nan=0, posinf=0, neginf=0)
                    # Aplicar límite superior de frecuencia con rejection sampling (solo para distribuciones con conteo > 1)
                    if freq_opcion in (1, 2, 4):  # Poisson, Binomial, Poisson-Gamma
                        freq_cap = evento.get('freq_limite_superior')
                        if freq_cap is not None and freq_cap > 0:
                            mask = muestras_frecuencia_simuladas > freq_cap
                            intentos = 0
                            while np.any(mask) and intentos < 100:
                                muestras_frecuencia_simuladas[mask] = dist_freq.rvs(size=int(np.sum(mask)), random_state=rng).astype(np.int32)
                                mask = muestras_frecuencia_simuladas > freq_cap
                                intentos += 1
                            if np.any(mask):
                                muestras_frecuencia_simuladas[mask] = freq_cap
                    
                    # Asegurar que sean valores no negativos y enteros
                    muestras_frecuencia_simuladas = np.clip(muestras_frecuencia_simuladas, 0, np.iinfo(np.int32).max)
                    muestras_frecuencia_simuladas = muestras_frecuencia_simuladas.astype(np.int32)
                    
                    # Asignar a las posiciones correspondientes
                    muestras_frecuencia[indices_a_simular] = muestras_frecuencia_simuladas
                    
                except Exception as e:
                    import warnings
                    nombre_evento = evento.get('nombre', evento_id)
                    warnings.warn(
                        f"Error al generar muestras de frecuencia para evento '{nombre_evento}': {str(e)}. "
                        f"Asignando frecuencia cero para {len(indices_a_simular)} simulaciones. "
                        f"Esto puede afectar significativamente los resultados.",
                        RuntimeWarning,
                        stacklevel=2
                    )
                    # En caso de error, asignar ceros como fallback
                    muestras_frecuencia[indices_a_simular] = 0

        elif 'eventos_padres' in evento and evento['eventos_padres']:
            evento['_factor_severidad_vinculos'] = None  # Limpiar posible valor stale de simulación anterior
            # Formato antiguo: usar tipo_dependencia único para todos los padres
            eventos_padres = evento.get('eventos_padres', [])
            tipo_dependencia = evento.get('tipo_dependencia', 'AND')

            if eventos_padres:
                # Verificar condiciones según tipo de dependencia
                ocurrencias_padres = np.vstack(
                    [frecuencias_por_evento[id_a_index[padre_id]] > 0 for padre_id in eventos_padres]
                )

                if tipo_dependencia == 'AND':
                    condicion_padres = np.all(ocurrencias_padres, axis=0)
                elif tipo_dependencia == 'OR':
                    condicion_padres = np.any(ocurrencias_padres, axis=0)
                elif tipo_dependencia in ['MUTEX', 'EXCLUYE']:
                    condicion_padres = ~np.any(ocurrencias_padres, axis=0)
                else:
                    condicion_padres = np.ones(num_simulaciones, dtype=bool)

                muestras_frecuencia = np.zeros(num_simulaciones, dtype=int)
                indices_a_simular = np.where(condicion_padres)[0]

                if len(indices_a_simular) > 0:
                    try:
                        # ====================================================================
                        # Generar muestras con factores estocásticos si aplica (formato antiguo)
                        # ====================================================================
                        usa_estocastico = evento.get('_usa_estocastico', False)
                        freq_opcion = evento.get('freq_opcion', 3)
                        
                        if usa_estocastico:
                            # MODELO ESTOCÁSTICO: Aplicar factores vectorizados
                            factores_vector = evento.get('_factores_vector')
                            
                            if freq_opcion == 1:  # Poisson
                                tasa_original = evento.get('tasa', 1.0)
                                tasas_ajustadas = tasa_original * factores_vector[indices_a_simular]
                                tasas_ajustadas = np.maximum(tasas_ajustadas, 0.0001)
                                muestras_frecuencia_simuladas = np.array([
                                    poisson.rvs(mu=lam, random_state=rng) for lam in tasas_ajustadas
                                ], dtype=np.int32)
                            
                            elif freq_opcion == 3:  # Bernoulli
                                from log_odds_utils import aplicar_factor_a_probabilidad
                                prob_original = evento.get('prob_exito', 0.5)
                                probs_ajustadas = np.array([
                                    aplicar_factor_a_probabilidad(prob_original, factor)
                                    for factor in factores_vector[indices_a_simular]
                                ])
                                probs_ajustadas = np.clip(probs_ajustadas, 0.0001, 0.9999)
                                muestras_frecuencia_simuladas = np.array([
                                    bernoulli.rvs(p=p, random_state=rng) for p in probs_ajustadas
                                ], dtype=np.int32)
                            
                            elif freq_opcion == 2:  # Binomial
                                from log_odds_utils import aplicar_factor_a_probabilidad
                                prob_original = evento.get('prob_exito', 0.5)
                                n = evento.get('num_eventos', 1)
                                probs_ajustadas = np.array([
                                    aplicar_factor_a_probabilidad(prob_original, factor)
                                    for factor in factores_vector[indices_a_simular]
                                ])
                                probs_ajustadas = np.clip(probs_ajustadas, 0.0001, 0.9999)
                                muestras_frecuencia_simuladas = np.array([
                                    binom.rvs(n=n, p=p, random_state=rng) for p in probs_ajustadas
                                ], dtype=np.int32)
                            
                            elif freq_opcion == 4:  # Poisson-Gamma
                                mas_probable_original = evento.get('pg_mas_probable', 1.0)
                                mus_ajustados = mas_probable_original * factores_vector[indices_a_simular]
                                mus_ajustados = np.maximum(mus_ajustados, 0.0001)
                                minimo = evento.get('pg_minimo', 0)
                                maximo = evento.get('pg_maximo', mas_probable_original * 2)
                                muestras_lista = []
                                for mu_ajustado in mus_ajustados:
                                    try:
                                        escala = mu_ajustado / mas_probable_original if mas_probable_original > 0 else 1.0
                                        minimo_ajustado = minimo * escala
                                        maximo_ajustado = maximo * escala
                                        sigma = (maximo_ajustado - minimo_ajustado) / 6
                                        if sigma > 0.001 and mu_ajustado > 0:  # Umbral mínimo para sigma
                                            alpha = (mu_ajustado / sigma) ** 2
                                            beta_param = mu_ajustado / (sigma ** 2)
                                            if alpha > 0 and beta_param > 0 and alpha < 1e6:
                                                p = beta_param / (beta_param + 1)
                                                p = min(max(p, 0.0001), 0.9999)
                                                muestra = nbinom.rvs(n=alpha, p=p, random_state=rng)
                                            else:
                                                muestra = poisson.rvs(mu=max(mu_ajustado, 0.0001), random_state=rng)
                                        elif mu_ajustado > 0:
                                            muestra = poisson.rvs(mu=max(mu_ajustado, 0.0001), random_state=rng)
                                        else:
                                            muestra = 0
                                    except:
                                        muestra = poisson.rvs(mu=max(mu_ajustado, 0.0001), random_state=rng) if mu_ajustado > 0 else 0
                                    muestras_lista.append(muestra)
                                muestras_frecuencia_simuladas = np.array(muestras_lista, dtype=np.int32)
                            
                            elif freq_opcion == 5:  # Beta
                                from log_odds_utils import aplicar_factor_a_probabilidad
                                mas_probable_original = evento.get('beta_mas_probable', 50) / 100.0
                                probs_ajustadas = np.array([
                                    aplicar_factor_a_probabilidad(mas_probable_original, factor)
                                    for factor in factores_vector[indices_a_simular]
                                ])
                                probs_ajustadas = np.clip(probs_ajustadas, 0.0001, 0.9999)
                                minimo = evento.get('beta_minimo', 0) / 100.0
                                maximo = evento.get('beta_maximo', 100) / 100.0
                                sigma_original = (maximo - minimo) / 6
                                muestras_lista = []
                                for prob_ajustada in probs_ajustadas:
                                    try:
                                        if sigma_original > 0:
                                            alpha_beta_sum = prob_ajustada * (1 - prob_ajustada) / (sigma_original ** 2) - 1
                                            alpha = prob_ajustada * alpha_beta_sum
                                            beta_param = (1 - prob_ajustada) * alpha_beta_sum
                                            if alpha > 0 and beta_param > 0:
                                                p_sampled = beta.rvs(a=alpha, b=beta_param, random_state=rng)
                                                muestra = bernoulli.rvs(p=p_sampled, random_state=rng)
                                            else:
                                                muestra = bernoulli.rvs(p=prob_ajustada, random_state=rng)
                                        else:
                                            muestra = bernoulli.rvs(p=prob_ajustada, random_state=rng)
                                    except:
                                        muestra = bernoulli.rvs(p=prob_ajustada, random_state=rng)
                                    muestras_lista.append(muestra)
                                muestras_frecuencia_simuladas = np.array(muestras_lista, dtype=np.int32)
                            
                            else:
                                print(f"[ADVERTENCIA] Distribución freq_opcion={freq_opcion} no soporta factores estocásticos. Usando modelo estático.")
                                muestras_frecuencia_simuladas = dist_freq.rvs(size=len(indices_a_simular), random_state=rng)
                                muestras_frecuencia_simuladas = muestras_frecuencia_simuladas.astype(np.int32)
                        
                        else:
                            # MODELO ESTÁTICO O SIN AJUSTES
                            muestras_frecuencia_simuladas = dist_freq.rvs(size=len(indices_a_simular), random_state=rng)
                        
                        # Manejar posibles valores infinitos o NaN
                        muestras_frecuencia_simuladas = np.nan_to_num(muestras_frecuencia_simuladas, nan=0, posinf=0, neginf=0)
                        # Aplicar límite superior de frecuencia con rejection sampling (solo para distribuciones con conteo > 1)
                        if freq_opcion in (1, 2, 4):  # Poisson, Binomial, Poisson-Gamma
                            freq_cap = evento.get('freq_limite_superior')
                            if freq_cap is not None and freq_cap > 0:
                                mask = muestras_frecuencia_simuladas > freq_cap
                                intentos = 0
                                while np.any(mask) and intentos < 100:
                                    muestras_frecuencia_simuladas[mask] = dist_freq.rvs(size=int(np.sum(mask)), random_state=rng).astype(np.int32)
                                    mask = muestras_frecuencia_simuladas > freq_cap
                                    intentos += 1
                                if np.any(mask):
                                    muestras_frecuencia_simuladas[mask] = freq_cap
                        
                        # Asegurar que sean valores no negativos y enteros
                        muestras_frecuencia_simuladas = np.clip(muestras_frecuencia_simuladas, 0, np.iinfo(np.int32).max)
                        muestras_frecuencia_simuladas = muestras_frecuencia_simuladas.astype(np.int32)
                        
                        # Asignar a las posiciones correspondientes
                        muestras_frecuencia[indices_a_simular] = muestras_frecuencia_simuladas
                    except Exception as e:
                        import warnings
                        nombre_evento = evento.get('nombre', evento_id)
                        warnings.warn(
                            f"Error al generar muestras de frecuencia para evento '{nombre_evento}' (formato antiguo): {str(e)}. "
                            f"Asignando frecuencia cero para {len(indices_a_simular)} simulaciones. "
                            f"Esto puede afectar significativamente los resultados.",
                            RuntimeWarning,
                            stacklevel=2
                        )
                        # En caso de error, asignar ceros como fallback
                        muestras_frecuencia[indices_a_simular] = 0
            else:
                # Evento sin padres (formato antiguo), simular normalmente
                try:
                    # ====================================================================
                    # Generar muestras con factores estocásticos si aplica (formato antiguo sin padres)
                    # ====================================================================
                    usa_estocastico = evento.get('_usa_estocastico', False)
                    freq_opcion = evento.get('freq_opcion', 3)
                    
                    if usa_estocastico:
                        # MODELO ESTOCÁSTICO: Aplicar factores vectorizados
                        factores_vector = evento.get('_factores_vector')
                        
                        if freq_opcion == 1:  # Poisson
                            tasa_original = evento.get('tasa', 1.0)
                            tasas_ajustadas = tasa_original * factores_vector
                            tasas_ajustadas = np.maximum(tasas_ajustadas, 0.0001)
                            muestras_frecuencia = np.array([
                                poisson.rvs(mu=lam, random_state=rng) for lam in tasas_ajustadas
                            ], dtype=np.int32)
                        
                        elif freq_opcion == 3:  # Bernoulli
                            from log_odds_utils import aplicar_factor_a_probabilidad
                            prob_original = evento.get('prob_exito', 0.5)
                            probs_ajustadas = np.array([
                                aplicar_factor_a_probabilidad(prob_original, factor)
                                for factor in factores_vector
                            ])
                            probs_ajustadas = np.clip(probs_ajustadas, 0.0001, 0.9999)
                            muestras_frecuencia = np.array([
                                bernoulli.rvs(p=p, random_state=rng) for p in probs_ajustadas
                            ], dtype=np.int32)
                        
                        elif freq_opcion == 2:  # Binomial
                            from log_odds_utils import aplicar_factor_a_probabilidad
                            prob_original = evento.get('prob_exito', 0.5)
                            n = evento.get('num_eventos', 1)
                            probs_ajustadas = np.array([
                                aplicar_factor_a_probabilidad(prob_original, factor)
                                for factor in factores_vector
                            ])
                            probs_ajustadas = np.clip(probs_ajustadas, 0.0001, 0.9999)
                            muestras_frecuencia = np.array([
                                binom.rvs(n=n, p=p, random_state=rng) for p in probs_ajustadas
                            ], dtype=np.int32)
                        
                        elif freq_opcion == 4:  # Poisson-Gamma
                            mas_probable_original = evento.get('pg_mas_probable', 1.0)
                            mus_ajustados = mas_probable_original * factores_vector
                            mus_ajustados = np.maximum(mus_ajustados, 0.0001)
                            minimo = evento.get('pg_minimo', 0)
                            maximo = evento.get('pg_maximo', mas_probable_original * 2)
                            muestras_lista = []
                            for mu_ajustado in mus_ajustados:
                                try:
                                    escala = mu_ajustado / mas_probable_original if mas_probable_original > 0 else 1.0
                                    minimo_ajustado = minimo * escala
                                    maximo_ajustado = maximo * escala
                                    sigma = (maximo_ajustado - minimo_ajustado) / 6
                                    if sigma > 0.001 and mu_ajustado > 0:  # Umbral mínimo para sigma
                                        alpha = (mu_ajustado / sigma) ** 2
                                        beta_param = mu_ajustado / (sigma ** 2)
                                        if alpha > 0 and beta_param > 0 and alpha < 1e6:
                                            p = beta_param / (beta_param + 1)
                                            p = min(max(p, 0.0001), 0.9999)
                                            muestra = nbinom.rvs(n=alpha, p=p, random_state=rng)
                                        else:
                                            muestra = poisson.rvs(mu=max(mu_ajustado, 0.0001), random_state=rng)
                                    elif mu_ajustado > 0:
                                        muestra = poisson.rvs(mu=max(mu_ajustado, 0.0001), random_state=rng)
                                    else:
                                        muestra = 0
                                except:
                                    muestra = poisson.rvs(mu=max(mu_ajustado, 0.0001), random_state=rng) if mu_ajustado > 0 else 0
                                muestras_lista.append(muestra)
                            muestras_frecuencia = np.array(muestras_lista, dtype=np.int32)
                        
                        elif freq_opcion == 5:  # Beta
                            from log_odds_utils import aplicar_factor_a_probabilidad
                            mas_probable_original = evento.get('beta_mas_probable', 50) / 100.0
                            probs_ajustadas = np.array([
                                aplicar_factor_a_probabilidad(mas_probable_original, factor)
                                for factor in factores_vector
                            ])
                            probs_ajustadas = np.clip(probs_ajustadas, 0.0001, 0.9999)
                            minimo = evento.get('beta_minimo', 0) / 100.0
                            maximo = evento.get('beta_maximo', 100) / 100.0
                            sigma_original = (maximo - minimo) / 6
                            muestras_lista = []
                            for prob_ajustada in probs_ajustadas:
                                try:
                                    if sigma_original > 0:
                                        alpha_beta_sum = prob_ajustada * (1 - prob_ajustada) / (sigma_original ** 2) - 1
                                        alpha = prob_ajustada * alpha_beta_sum
                                        beta_param = (1 - prob_ajustada) * alpha_beta_sum
                                        if alpha > 0 and beta_param > 0:
                                            p_sampled = beta.rvs(a=alpha, b=beta_param, random_state=rng)
                                            muestra = bernoulli.rvs(p=p_sampled, random_state=rng)
                                        else:
                                            muestra = bernoulli.rvs(p=prob_ajustada, random_state=rng)
                                    else:
                                        muestra = bernoulli.rvs(p=prob_ajustada, random_state=rng)
                                except:
                                    muestra = bernoulli.rvs(p=prob_ajustada, random_state=rng)
                                muestras_lista.append(muestra)
                            muestras_frecuencia = np.array(muestras_lista, dtype=np.int32)
                        
                        else:
                            print(f"[ADVERTENCIA] Distribución freq_opcion={freq_opcion} no soporta factores estocásticos. Usando modelo estático.")
                            muestras_frecuencia = dist_freq.rvs(size=num_simulaciones, random_state=rng)
                            muestras_frecuencia = muestras_frecuencia.astype(np.int32)
                    
                    else:
                        # MODELO ESTÁTICO O SIN AJUSTES
                        muestras_frecuencia = dist_freq.rvs(size=num_simulaciones, random_state=rng)
                    
                    # Manejar posibles valores infinitos o NaN
                    muestras_frecuencia = np.nan_to_num(muestras_frecuencia, nan=0, posinf=0, neginf=0)
                    # Aplicar límite superior de frecuencia con rejection sampling (solo para distribuciones con conteo > 1)
                    if freq_opcion in (1, 2, 4):  # Poisson, Binomial, Poisson-Gamma
                        freq_cap = evento.get('freq_limite_superior')
                        if freq_cap is not None and freq_cap > 0:
                            mask = muestras_frecuencia > freq_cap
                            intentos = 0
                            while np.any(mask) and intentos < 100:
                                muestras_frecuencia[mask] = dist_freq.rvs(size=int(np.sum(mask)), random_state=rng).astype(np.int32)
                                mask = muestras_frecuencia > freq_cap
                                intentos += 1
                            if np.any(mask):
                                muestras_frecuencia[mask] = freq_cap
                    # Asegurar que sean valores no negativos y enteros con límite superior
                    muestras_frecuencia = np.clip(muestras_frecuencia, 0, np.iinfo(np.int32).max)
                    muestras_frecuencia = muestras_frecuencia.astype(np.int32)
                except Exception as e:
                    import warnings
                    nombre_evento = evento.get('nombre', evento_id)
                    warnings.warn(
                        f"Error al generar muestras de frecuencia para evento '{nombre_evento}' (sin padres): {str(e)}. "
                        f"Asignando frecuencia cero. Esto puede afectar significativamente los resultados.",
                        RuntimeWarning,
                        stacklevel=2
                    )
                    muestras_frecuencia = np.zeros(num_simulaciones, dtype=int)
        else:
            # Evento sin dependencias, simular normalmente
            evento['_factor_severidad_vinculos'] = None  # Limpiar posible valor stale de simulación anterior
            try:
                # ====================================================================
                # Generar muestras con factores estocásticos si aplica
                # ====================================================================
                usa_estocastico = evento.get('_usa_estocastico', False)
                freq_opcion = evento.get('freq_opcion', 3)
                
                if usa_estocastico:
                    # MODELO ESTOCÁSTICO: Aplicar factores vectorizados
                    factores_vector = evento.get('_factores_vector')
                    
                    if freq_opcion == 1:  # Poisson
                        tasa_original = evento.get('tasa', 1.0)
                        # Aplicar factores a cada simulación
                        tasas_ajustadas = tasa_original * factores_vector
                        tasas_ajustadas = np.maximum(tasas_ajustadas, 0.0001)  # Evitar λ=0
                        
                        # Generar muestras con tasas individuales
                        muestras_frecuencia = np.array([
                            poisson.rvs(mu=lam, random_state=rng) for lam in tasas_ajustadas
                        ], dtype=np.int32)
                        
                    elif freq_opcion == 3:  # Bernoulli
                        from log_odds_utils import aplicar_factor_a_probabilidad
                        prob_original = evento.get('prob_exito', 0.5)
                        
                        # Aplicar factores a cada simulación usando log-odds
                        probs_ajustadas = np.array([
                            aplicar_factor_a_probabilidad(prob_original, factor)
                            for factor in factores_vector
                        ])
                        probs_ajustadas = np.clip(probs_ajustadas, 0.0001, 0.9999)
                        
                        # Generar muestras con probabilidades individuales
                        muestras_frecuencia = np.array([
                            bernoulli.rvs(p=p, random_state=rng) for p in probs_ajustadas
                        ], dtype=np.int32)
                    
                    elif freq_opcion == 2:  # Binomial
                        from log_odds_utils import aplicar_factor_a_probabilidad
                        prob_original = evento.get('prob_exito', 0.5)
                        n = evento.get('num_eventos', 1)
                        
                        # Aplicar factores usando log-odds
                        probs_ajustadas = np.array([
                            aplicar_factor_a_probabilidad(prob_original, factor)
                            for factor in factores_vector
                        ])
                        probs_ajustadas = np.clip(probs_ajustadas, 0.0001, 0.9999)
                        
                        # Generar muestras
                        muestras_frecuencia = np.array([
                            binom.rvs(n=n, p=p, random_state=rng) for p in probs_ajustadas
                        ], dtype=np.int32)
                    
                    elif freq_opcion == 4:  # Poisson-Gamma (Binomial Negativa)
                        mas_probable_original = evento.get('pg_mas_probable', 1.0)
                        
                        # Aplicar factores multiplicativamente al valor más probable (mu)
                        mus_ajustados = mas_probable_original * factores_vector
                        mus_ajustados = np.maximum(mus_ajustados, 0.0001)
                        
                        # Obtener parámetros de forma de la distribución
                        minimo = evento.get('pg_minimo', 0)
                        maximo = evento.get('pg_maximo', mas_probable_original * 2)
                        
                        # Calcular parámetros alpha y beta para cada mu ajustada
                        # Usar aproximación PERT: mu ≈ (min + 4*mode + max)/6
                        # sigma ≈ (max - min)/6
                        muestras_lista = []
                        for mu_ajustado in mus_ajustados:
                            try:
                                # Escalar min y max proporcionalmente
                                escala = mu_ajustado / mas_probable_original if mas_probable_original > 0 else 1.0
                                minimo_ajustado = minimo * escala
                                maximo_ajustado = maximo * escala
                                
                                # Calcular parámetros de Binomial Negativa
                                sigma = (maximo_ajustado - minimo_ajustado) / 6
                                if sigma > 0.001 and mu_ajustado > 0:  # Umbral mínimo para sigma
                                    alpha = (mu_ajustado / sigma) ** 2
                                    beta_param = mu_ajustado / (sigma ** 2)
                                    
                                    if alpha > 0 and beta_param > 0 and alpha < 1e6:
                                        p = beta_param / (beta_param + 1)
                                        p = min(max(p, 0.0001), 0.9999)
                                        muestra = nbinom.rvs(n=alpha, p=p, random_state=rng)
                                    else:
                                        # Fallback a Poisson simple
                                        muestra = poisson.rvs(mu=max(mu_ajustado, 0.0001), random_state=rng)
                                elif mu_ajustado > 0:
                                    # Fallback a Poisson simple cuando sigma es muy pequeño
                                    muestra = poisson.rvs(mu=max(mu_ajustado, 0.0001), random_state=rng)
                                else:
                                    muestra = 0
                            except:
                                # Fallback seguro
                                muestra = poisson.rvs(mu=max(mu_ajustado, 0.0001), random_state=rng) if mu_ajustado > 0 else 0
                            
                            muestras_lista.append(muestra)
                        
                        muestras_frecuencia = np.array(muestras_lista, dtype=np.int32)
                    
                    elif freq_opcion == 5:  # Beta
                        from log_odds_utils import aplicar_factor_a_probabilidad
                        
                        # Beta genera probabilidades, luego se usa para eventos binarios
                        mas_probable_original = evento.get('beta_mas_probable', 50) / 100.0
                        
                        # Aplicar factores usando log-odds a la probabilidad más probable
                        probs_ajustadas = np.array([
                            aplicar_factor_a_probabilidad(mas_probable_original, factor)
                            for factor in factores_vector
                        ])
                        probs_ajustadas = np.clip(probs_ajustadas, 0.0001, 0.9999)
                        
                        # Obtener parámetros de forma
                        minimo = evento.get('beta_minimo', 0) / 100.0
                        maximo = evento.get('beta_maximo', 100) / 100.0
                        sigma_original = (maximo - minimo) / 6
                        
                        # Generar eventos usando la distribución Beta ajustada
                        muestras_lista = []
                        for prob_ajustada in probs_ajustadas:
                            try:
                                # Recalcular alpha y beta manteniendo dispersión relativa
                                if sigma_original > 0:
                                    alpha_beta_sum = prob_ajustada * (1 - prob_ajustada) / (sigma_original ** 2) - 1
                                    alpha = prob_ajustada * alpha_beta_sum
                                    beta_param = (1 - prob_ajustada) * alpha_beta_sum
                                    
                                    if alpha > 0 and beta_param > 0:
                                        # Samplear de Beta para obtener p, luego generar evento binario
                                        p_sampled = beta.rvs(a=alpha, b=beta_param, random_state=rng)
                                        muestra = bernoulli.rvs(p=p_sampled, random_state=rng)
                                    else:
                                        # Fallback a Bernoulli directo
                                        muestra = bernoulli.rvs(p=prob_ajustada, random_state=rng)
                                else:
                                    muestra = bernoulli.rvs(p=prob_ajustada, random_state=rng)
                            except:
                                muestra = bernoulli.rvs(p=prob_ajustada, random_state=rng)
                            
                            muestras_lista.append(muestra)
                        
                        muestras_frecuencia = np.array(muestras_lista, dtype=np.int32)
                    
                    else:
                        # Fallback para distribuciones no soportadas
                        print(f"[ADVERTENCIA] Distribución freq_opcion={freq_opcion} no soporta factores estocásticos. Usando modelo estático.")
                        muestras_frecuencia = dist_freq.rvs(size=num_simulaciones, random_state=rng)
                        muestras_frecuencia = muestras_frecuencia.astype(np.int32)
                
                else:
                    # MODELO ESTÁTICO O SIN AJUSTES: Usar dist_freq normal
                    muestras_frecuencia = dist_freq.rvs(size=num_simulaciones, random_state=rng)
                
                # Manejar posibles valores infinitos o NaN
                muestras_frecuencia = np.nan_to_num(muestras_frecuencia, nan=0, posinf=0, neginf=0)
                # Aplicar límite superior de frecuencia con rejection sampling (solo para distribuciones con conteo > 1)
                if freq_opcion in (1, 2, 4):  # Poisson, Binomial, Poisson-Gamma
                    freq_cap = evento.get('freq_limite_superior')
                    if freq_cap is not None and freq_cap > 0:
                        mask = muestras_frecuencia > freq_cap
                        intentos = 0
                        while np.any(mask) and intentos < 100:
                            muestras_frecuencia[mask] = dist_freq.rvs(size=int(np.sum(mask)), random_state=rng).astype(np.int32)
                            mask = muestras_frecuencia > freq_cap
                            intentos += 1
                        if np.any(mask):
                            muestras_frecuencia[mask] = freq_cap
                # Asegurar que sean valores no negativos y enteros con límite superior
                muestras_frecuencia = np.clip(muestras_frecuencia, 0, np.iinfo(np.int32).max)
                muestras_frecuencia = muestras_frecuencia.astype(np.int32)
            except Exception as e:
                import warnings
                nombre_evento = evento.get('nombre', evento_id)
                warnings.warn(
                    f"Error al generar muestras de frecuencia para evento '{nombre_evento}' (sin dependencias): {str(e)}. "
                    f"Asignando frecuencia cero. Esto puede afectar significativamente los resultados.",
                    RuntimeWarning,
                    stacklevel=2
                )
                muestras_frecuencia = np.zeros(num_simulaciones, dtype=int)

        # Guardar frecuencias y calcular pérdidas
        # PASO 1: Determinar las frecuencias finales para este evento (considerando el reescalado)
        #         y almacenar estas frecuencias finales.
        
        # (muestras_frecuencia ya ha sido calculada para el evento actual,
        #  incluyendo la lógica de dependencias)
        
        final_event_frequencies = muestras_frecuencia
        sum_final_event_frequencies = int(final_event_frequencies.sum())
        max_eventos_simulacion = 10000000 # Límite definido anteriormente

        if sum_final_event_frequencies > max_eventos_simulacion:
            print(f"Advertencia: El número total de eventos ({sum_final_event_frequencies}) para el evento {evento_id} excede el límite de {max_eventos_simulacion}. Se reescalará.")
            factor = max_eventos_simulacion / sum_final_event_frequencies
            # Escalar y aplicar redondeo estocástico sin sesgo, preservando la suma exacta al tope
            scaled = final_event_frequencies.astype(np.float64) * factor
            floored = np.floor(scaled).astype(np.int32)
            remainder = int(max_eventos_simulacion - int(floored.sum()))
            if remainder > 0:
                frac = scaled - floored
                # Determinar generador aleatorio a usar
                if isinstance(rng, np.random.Generator) or isinstance(rng, np.random.RandomState):
                    rand = rng
                else:
                    try:
                        rand = np.random.default_rng()
                    except Exception:
                        rand = np.random
                # Indices con fracción positiva
                idx_nonzero = np.flatnonzero(frac > 0)
                if idx_nonzero.size > 0 and remainder <= idx_nonzero.size:
                    probs = frac[idx_nonzero]
                    probs_sum = probs.sum()
                    if probs_sum > 0:
                        probs = probs / probs_sum
                        # Elección sin reemplazo ponderada por fracciones
                        try:
                            chosen = rand.choice(idx_nonzero, size=remainder, replace=False, p=probs)
                        except TypeError:
                            # Compatibilidad si el generador no soporta 'p' en choice: usar módulo numpy
                            chosen = np.random.choice(idx_nonzero, size=remainder, replace=False, p=probs)
                        floored[chosen] += 1
                    else:
                        # Fallback determinista si las fracciones suman 0 por precisión
                        chosen = np.argsort(-scaled)[:remainder]
                        floored[chosen] += 1
                else:
                    # Fallback: asignar a los de mayor 'scaled' para preservar suma exacta
                    chosen = np.argsort(-scaled)[:remainder]
                    floored[chosen] += 1
            final_event_frequencies = floored.astype(np.int32)
            # Actualizar la suma exacta después del reescalado
            sum_final_event_frequencies = int(final_event_frequencies.sum()) 
        
        # Guardar las frecuencias definitivas (originales o reescaladas) que se usaron
        frecuencias_por_evento[idx] = final_event_frequencies
        
        # PASO 2: Generar pérdidas basadas en las frecuencias finales.
        perdidas_para_este_evento = None  # Se asignará vectorizado si hay pérdidas; si no, será un vector de ceros

        if sum_final_event_frequencies > 0:
            try:
                # Generar el número exacto de muestras de severidad necesarias
                total_perdidas_del_evento_concatenadas = dist_sev.rvs(size=sum_final_event_frequencies, random_state=rng)
                total_perdidas_del_evento_concatenadas = np.nan_to_num(total_perdidas_del_evento_concatenadas, nan=0, posinf=1e12, neginf=0)
                total_perdidas_del_evento_concatenadas = np.maximum(total_perdidas_del_evento_concatenadas, 0)
                
                # Aplicar límite superior de severidad por ocurrencia con rejection sampling
                sev_cap = evento.get('sev_limite_superior')
                if sev_cap is not None and sev_cap > 0:
                    mask = total_perdidas_del_evento_concatenadas > sev_cap
                    intentos = 0
                    while np.any(mask) and intentos < 100:
                        nuevas = dist_sev.rvs(size=int(np.sum(mask)), random_state=rng)
                        nuevas = np.nan_to_num(nuevas, nan=0, posinf=1e12, neginf=0)
                        nuevas = np.maximum(nuevas, 0)
                        total_perdidas_del_evento_concatenadas[mask] = nuevas
                        mask = total_perdidas_del_evento_concatenadas > sev_cap
                        intentos += 1
                    if np.any(mask):
                        total_perdidas_del_evento_concatenadas[mask] = sev_cap
                
                # =====================================================
                # ESCALAMIENTO DE SEVERIDAD POR FRECUENCIA
                # Se aplica ANTES de factores de control y seguros
                # =====================================================
                if evento.get('sev_freq_activado', False) and sum_final_event_frequencies > 0:
                    sev_freq_modelo = evento.get('sev_freq_modelo', 'reincidencia')
                    
                    if sev_freq_modelo == 'reincidencia':
                        # Generar índice ordinal de cada pérdida dentro de su simulación
                        _indices_pos = np.flatnonzero(final_event_frequencies > 0)
                        _freqs_pos = final_event_frequencies[_indices_pos]
                        _occurrence_idx = np.concatenate([np.arange(1, f+1) for f in _freqs_pos])
                        
                        tipo_esc = evento.get('sev_freq_tipo_escalamiento', 'lineal')
                        factor_max = float(evento.get('sev_freq_factor_max', 5.0))
                        
                        if tipo_esc == 'tabla':
                            tabla = evento.get('sev_freq_tabla', [])
                            if tabla:
                                _multiplicadores = _aplicar_tabla_escalamiento(_occurrence_idx, tabla)
                            else:
                                _multiplicadores = np.ones(len(_occurrence_idx))
                        elif tipo_esc == 'exponencial':
                            base = float(evento.get('sev_freq_base', 1.5))
                            max_exp = np.log(factor_max) / np.log(base) if base > 1 else 100
                            safe_exponents = np.minimum(_occurrence_idx - 1, max_exp)
                            _multiplicadores = base ** safe_exponents
                            _multiplicadores = np.minimum(_multiplicadores, factor_max)
                        else:  # lineal (default)
                            paso = float(evento.get('sev_freq_paso', 0.5))
                            _multiplicadores = np.minimum(1 + paso * (_occurrence_idx - 1), factor_max)
                        
                        _media_antes = total_perdidas_del_evento_concatenadas.mean()
                        total_perdidas_del_evento_concatenadas *= _multiplicadores
                        _media_despues = total_perdidas_del_evento_concatenadas.mean()
                        nombre_evento = evento.get('nombre', evento_id)
                        print(f"[DEBUG SEV_FREQ] Evento '{nombre_evento}': Reincidencia ({tipo_esc}) aplicado "
                              f"(media: ${_media_antes:,.0f} → ${_media_despues:,.0f}, "
                              f"mult rango: {_multiplicadores.min():.2f}-{_multiplicadores.max():.2f})")
                    
                    elif sev_freq_modelo == 'sistemico':
                        alpha = float(evento.get('sev_freq_alpha', 0.5))
                        solo_aumento = evento.get('sev_freq_solo_aumento', True)
                        factor_max = float(evento.get('sev_freq_sistemico_factor_max', 3.0))
                        freq_mean = final_event_frequencies.mean()
                        freq_std = final_event_frequencies.std()
                        
                        if freq_std > 0.01:
                            z = (final_event_frequencies - freq_mean) / freq_std
                            if solo_aumento:
                                z = np.maximum(z, 0)
                            sev_freq_factor = np.clip(1 + alpha * z, 1.0 / factor_max, factor_max)
                        else:
                            sev_freq_factor = np.ones(num_simulaciones)
                        
                        _indices_pos = np.flatnonzero(final_event_frequencies > 0)
                        _freqs_pos = final_event_frequencies[_indices_pos]
                        _factores_por_perdida = np.repeat(sev_freq_factor[_indices_pos], _freqs_pos)
                        
                        _media_antes = total_perdidas_del_evento_concatenadas.mean()
                        total_perdidas_del_evento_concatenadas *= _factores_por_perdida
                        _media_despues = total_perdidas_del_evento_concatenadas.mean()
                        nombre_evento = evento.get('nombre', evento_id)
                        print(f"[DEBUG SEV_FREQ] Evento '{nombre_evento}': Sistémico (alpha={alpha}) aplicado "
                              f"(media: ${_media_antes:,.0f} → ${_media_despues:,.0f}, "
                              f"factor rango: {sev_freq_factor[_indices_pos].min():.3f}-{sev_freq_factor[_indices_pos].max():.3f})")
                
                # =====================================================
                # APLICAR FACTOR DE SEVERIDAD DE VÍNCULOS (cascada)
                # ANTES de aplicar controles y seguros
                # =====================================================
                factor_sev_vinculos = evento.get('_factor_severidad_vinculos')
                if factor_sev_vinculos is not None and not np.allclose(factor_sev_vinculos, 1.0):
                    indices_con_ocurrencias_v = np.flatnonzero(final_event_frequencies > 0)
                    frecuencias_en_esas_simulaciones_v = final_event_frequencies[indices_con_ocurrencias_v]
                    factores_por_perdida_v = np.repeat(factor_sev_vinculos[indices_con_ocurrencias_v], frecuencias_en_esas_simulaciones_v)
                    perdidas_antes_vinculos = total_perdidas_del_evento_concatenadas.mean()
                    total_perdidas_del_evento_concatenadas = total_perdidas_del_evento_concatenadas * factores_por_perdida_v
                    perdidas_despues_vinculos = total_perdidas_del_evento_concatenadas.mean()
                    factor_min_v = factores_por_perdida_v.min()
                    factor_max_v = factores_por_perdida_v.max()
                    factor_med_v = factores_por_perdida_v.mean()
                    nombre_evento = evento.get('nombre', evento_id)
                    print(f"[DEBUG SEVERIDAD VINCULOS] Evento '{nombre_evento}': factor severidad vínculos aplicado "
                          f"(media: ${perdidas_antes_vinculos:,.0f} → ${perdidas_despues_vinculos:,.0f}, "
                          f"factor rango: {factor_min_v:.2f}x - {factor_max_v:.2f}x, media: {factor_med_v:.2f}x)")

                # =====================================================
                # APLICAR FACTOR DE SEVERIDAD A PÉRDIDAS INDIVIDUALES
                # ANTES de aplicar seguros (los controles mitigan primero)
                # =====================================================
                if evento.get('_usa_estocastico', False):
                    # Modelo estocástico: necesitamos mapear el vector de factores a las pérdidas individuales
                    factores_sev_vector = evento.get('_factores_severidad_vector')
                    if factores_sev_vector is not None and not np.allclose(factores_sev_vector, 1.0):
                        # Mapear factores de simulación a pérdidas individuales
                        indices_con_ocurrencias = np.flatnonzero(final_event_frequencies > 0)
                        frecuencias_en_esas_simulaciones = final_event_frequencies[indices_con_ocurrencias]
                        # Repetir el factor de cada simulación por el número de ocurrencias en esa simulación
                        factores_por_perdida = np.repeat(factores_sev_vector[indices_con_ocurrencias], frecuencias_en_esas_simulaciones)
                        perdidas_antes_factor = total_perdidas_del_evento_concatenadas.mean()
                        total_perdidas_del_evento_concatenadas = total_perdidas_del_evento_concatenadas * factores_por_perdida
                        perdidas_despues_factor = total_perdidas_del_evento_concatenadas.mean()
                        nombre_evento = evento.get('nombre', evento_id)
                        print(f"[DEBUG SEVERIDAD] Evento '{nombre_evento}': factor severidad estocástico aplicado a pérdidas individuales "
                              f"(media: ${perdidas_antes_factor:,.0f} → ${perdidas_despues_factor:,.0f})")
                else:
                    # Modelo estático: aplicar factor único a todas las pérdidas
                    factor_sev_estatico = evento.get('_factor_severidad_estatico', 1.0)
                    if factor_sev_estatico != 1.0:
                        perdidas_antes_factor = total_perdidas_del_evento_concatenadas.mean()
                        total_perdidas_del_evento_concatenadas = total_perdidas_del_evento_concatenadas * factor_sev_estatico
                        perdidas_despues_factor = total_perdidas_del_evento_concatenadas.mean()
                        nombre_evento = evento.get('nombre', evento_id)
                        print(f"[DEBUG SEVERIDAD] Evento '{nombre_evento}': factor severidad estático {factor_sev_estatico:.4f} aplicado a pérdidas individuales "
                              f"(media: ${perdidas_antes_factor:,.0f} → ${perdidas_despues_factor:,.0f})")
                
                # =====================================================
                # APLICAR SEGUROS POR OCURRENCIA a pérdidas mitigadas
                # DESPUÉS de aplicar factor de severidad
                # =====================================================
                seguros_por_ocurrencia = [s for s in evento.get('_seguros_aplicables', []) 
                                          if s.get('tipo_deducible') == 'por_ocurrencia']
                
                # Guardar pagos del seguro por ocurrencia para aplicar límite agregado después
                pagos_seguro_por_ocurrencia = np.zeros_like(total_perdidas_del_evento_concatenadas)
                info_seguros_ocurrencia = []  # Para debug y aplicar límite agregado
                
                for seguro in seguros_por_ocurrencia:
                    deducible = seguro['deducible']
                    cobertura_pct = seguro['cobertura_pct']
                    limite_ocurr = seguro.get('limite_ocurrencia', 0)
                    limite_agregado = seguro.get('limite', 0)  # Límite agregado anual
                    
                    # Calcular pago del seguro para cada pérdida individual (ya mitigada)
                    exceso = np.maximum(total_perdidas_del_evento_concatenadas - deducible, 0)
                    pago_seguro = exceso * cobertura_pct
                    if limite_ocurr > 0:
                        pago_seguro = np.minimum(pago_seguro, limite_ocurr)
                    
                    # Guardar info para aplicar límite agregado después de sumar por simulación
                    info_seguros_ocurrencia.append({
                        'seguro': seguro,
                        'pago_por_ocurrencia': pago_seguro.copy(),
                        'limite_agregado': limite_agregado
                    })
                    
                    # Acumular pagos (se restará después de verificar límite agregado)
                    pagos_seguro_por_ocurrencia += pago_seguro
                    
                    nombre_evento = evento.get('nombre', evento_id)
                    print(f"[DEBUG SEGURO POR OCURRENCIA] Evento '{nombre_evento}': Seguro '{seguro['nombre']}' "
                          f"(Ded=${deducible:,.0f}/ocurr, Cob={cobertura_pct*100:.0f}%, LímOcurr=${limite_ocurr:,.0f}, LímAnual=${limite_agregado:,.0f})")

                # Asignar pérdidas BRUTAS a las simulaciones (sin restar seguro aún)
                indices_con_ocurrencias = np.flatnonzero(final_event_frequencies > 0)
                frecuencias_en_esas_simulaciones = final_event_frequencies[indices_con_ocurrencias]

                if total_perdidas_del_evento_concatenadas.size > 0 and frecuencias_en_esas_simulaciones.size > 0:
                    idx_rep = np.repeat(indices_con_ocurrencias, frecuencias_en_esas_simulaciones)
                    
                    # Pérdidas brutas por simulación
                    perdidas_brutas_por_sim = np.bincount(
                        idx_rep,
                        weights=total_perdidas_del_evento_concatenadas,
                        minlength=num_simulaciones
                    )
                    
                    # Pagos del seguro por simulación (antes de aplicar límite agregado)
                    pagos_seguro_por_sim = np.bincount(
                        idx_rep,
                        weights=pagos_seguro_por_ocurrencia,
                        minlength=num_simulaciones
                    )
                    
                    # Aplicar límite agregado anual si existe
                    for info in info_seguros_ocurrencia:
                        limite_agregado = info['limite_agregado']
                        if limite_agregado > 0:
                            # Si el pago total del año excede el límite, ajustar
                            exceso_sobre_limite = np.maximum(pagos_seguro_por_sim - limite_agregado, 0)
                            pagos_seguro_por_sim = np.minimum(pagos_seguro_por_sim, limite_agregado)
                            
                            # Debug: mostrar cuántas simulaciones excedieron el límite
                            num_excedidas = np.sum(exceso_sobre_limite > 0)
                            if num_excedidas > 0:
                                nombre_evento = evento.get('nombre', evento_id)
                                print(f"[DEBUG SEGURO POR OCURRENCIA]   Límite agregado ${limite_agregado:,.0f}/año aplicado en {num_excedidas} simulaciones")
                    
                    # Pérdidas netas = brutas - pago del seguro (respetando límite agregado)
                    perdidas_para_este_evento = perdidas_brutas_por_sim - pagos_seguro_por_sim
                    perdidas_para_este_evento = np.maximum(perdidas_para_este_evento, 0)
                    
                    # Debug
                    if len(seguros_por_ocurrencia) > 0:
                        nombre_evento = evento.get('nombre', evento_id)
                        print(f"[DEBUG SEGURO POR OCURRENCIA]   Pérdida media anual: ${perdidas_brutas_por_sim.mean():,.0f} → ${perdidas_para_este_evento.mean():,.0f} "
                              f"(Pago medio seguro: ${pagos_seguro_por_sim.mean():,.0f})")
                else:
                    perdidas_para_este_evento = np.zeros(num_simulaciones)

            except Exception as e:
                import warnings
                nombre_evento = evento.get('nombre', evento_id)
                warnings.warn(
                    f"Error INESPERADO al generar/asignar severidad para evento '{nombre_evento}': {str(e)}. "
                    f"Las pérdidas para este evento se establecerán en 0. "
                    f"Esto afectará significativamente los resultados de la simulación.",
                    RuntimeWarning,
                    stacklevel=2
                )

        if perdidas_para_este_evento is None:
            perdidas_para_este_evento = np.zeros(num_simulaciones)
        
        perdidas_para_este_evento = np.clip(perdidas_para_este_evento, 0, 1e12)
        
        # =====================================================
        # NOTA: El factor de severidad ya se aplicó a las pérdidas
        # individuales ANTES de los seguros por ocurrencia (arriba)
        # =====================================================
        
        # =====================================================
        # Aplicar seguros AGREGADOS (transferencia de riesgo)
        # Los seguros "por_ocurrencia" ya se aplicaron antes de agregar
        # =====================================================
        seguros = evento.get('_seguros_aplicables', [])
        # Filtrar solo seguros agregados (los de por_ocurrencia ya se aplicaron arriba)
        seguros_agregados = [s for s in seguros if s.get('tipo_deducible', 'agregado') == 'agregado']
        
        for seguro in seguros_agregados:
            deducible = seguro['deducible']
            cobertura_pct = seguro['cobertura_pct']
            limite = seguro['limite']
            
            # Fórmula: pago_seguro = min((perdida_agregada - deducible) * cobertura%, limite)
            # Si limite == 0, significa sin límite (ilimitado)
            exceso = np.maximum(perdidas_para_este_evento - deducible, 0)
            pago_seguro = exceso * cobertura_pct
            if limite > 0:
                pago_seguro = np.minimum(pago_seguro, limite)
            
            # Restar el pago del seguro de las pérdidas agregadas
            perdidas_antes = perdidas_para_este_evento.mean()
            perdidas_para_este_evento = perdidas_para_este_evento - pago_seguro
            perdidas_para_este_evento = np.maximum(perdidas_para_este_evento, 0)  # No puede ser negativa
            perdidas_despues = perdidas_para_este_evento.mean()
            
            nombre_evento = evento.get('nombre', evento_id)
            print(f"[DEBUG SEGURO AGREGADO] Evento '{nombre_evento}': Seguro '{seguro['nombre']}' "
                  f"(Ded=${deducible:,.0f}/año, Cob={cobertura_pct*100:.0f}%, Lím=${limite:,.0f}/año)")
            print(f"[DEBUG SEGURO AGREGADO]   Pérdida media anual: ${perdidas_antes:,.0f} → ${perdidas_despues:,.0f} "
                  f"(Pago medio seguro: ${pago_seguro.mean():,.0f})")
        
        perdidas_por_evento[idx] = perdidas_para_este_evento
        
        perdidas_totales += perdidas_para_este_evento

    # FIN DEL BUCLE: for evento_id in orden_eventos_ids:

    # PASO 3: Calcular frecuencias_totales una vez, después del bucle.
    if num_eventos > 0: 
        # Usar vstack para evitar dtype=object y acelerar la suma
        frecuencias_totales = np.sum(np.vstack(frecuencias_por_evento), axis=0).astype(np.int32)
    else:
        frecuencias_totales = np.zeros(num_simulaciones, dtype=np.int32)

    return perdidas_totales, frecuencias_totales, perdidas_por_evento, frecuencias_por_evento

# Función para mostrar el resumen ejecutivo con datos en negrita
def obtener_resumen_ejecutivo_texto(media, desviacion_estandar, var_90, opvar_99, opvar, min_freq_total, mode_freq_total, max_freq_total):
    texto = "\nResumen Ejecutivo de Resultados de Pérdidas Agregadas:\n"
    texto += f"Media de Pérdidas Agregadas: {currency_format(round(media))}\n"
    texto += f"Desviación Estándar: {currency_format(round(desviacion_estandar))}\n"
    texto += f"VaR al 90%: {currency_format(round(var_90))}\n"
    texto += f"OpVaR al 99%: {currency_format(round(opvar_99))}\n"
    texto += f"Pérdida Esperada más allá del OpVaR 99%: {currency_format(round(opvar))}\n"
    texto += f"Número mínimo de eventos materializados: {min_freq_total}\n"
    texto += f"Número más probable de eventos materializados: {mode_freq_total}\n"
    texto += f"Número máximo de eventos materializados: {max_freq_total}\n"
    return texto

# Función para mostrar tablas de percentiles con formato
def obtener_tabla_percentiles_texto(percentiles_df, titulo):
    texto = f"\n{titulo}\n\n"
    texto += tabulate(percentiles_df, headers='keys', tablefmt='fancy_grid', showindex=False)
    texto += "\n"
    return texto

class SimulacionThread(QThread):
    # Definir señales
    progreso_actualizado = pyqtSignal(int)
    simulacion_completada = pyqtSignal(object, object, object, object, object)
    error_ocurrido = pyqtSignal(str)

    def __init__(self, eventos_riesgo, num_simulaciones, generar_reporte=False, pdf_filename=None):
        super().__init__()
        
        # DEBUG: Verificar eventos recibidos en el thread
        print(f"\n[DEBUG THREAD INIT] ========================================")
        print(f"[DEBUG THREAD INIT] SimulacionThread.__init__ recibió {len(eventos_riesgo)} eventos")
        for i, e in enumerate(eventos_riesgo):
            nombre = e.get('nombre', 'Sin nombre')
            tiene_factores = 'factores_ajuste' in e
            factores = e.get('factores_ajuste', [])
            print(f"[DEBUG THREAD INIT]   [{i}] '{nombre}': tiene_factores={tiene_factores}, factores={factores}")
        print(f"[DEBUG THREAD INIT] ========================================\n")
        
        self.eventos_riesgo = eventos_riesgo
        self.num_simulaciones = num_simulaciones
        self.generar_reporte = generar_reporte
        self.pdf_filename = pdf_filename
        self.is_running = True

    def run(self):
        try:
            total = self.num_simulaciones
            if total <= 0:
                raise ValueError("El número de simulaciones debe ser mayor que 0")
            # Dividir en hasta 100 chunks, evitando tamaños 0
            num_chunks = min(100, total)
            chunk_edges = np.linspace(0, total, num_chunks + 1, dtype=int)

            # Precomputar y reutilizar el orden de eventos para todos los chunks
            self._orden_eventos_ids = ordenar_eventos_por_dependencia(self.eventos_riesgo)
            # Crear un generador de números aleatorios compartido para toda la simulación
            self._rng = np.random.default_rng()

            # Inicializar los arrays de resultados completos
            perdidas_totales = np.zeros(self.num_simulaciones)
            frecuencias_totales = np.zeros(self.num_simulaciones, dtype=np.int32)
            perdidas_por_evento = None
            frecuencias_por_evento = None

            for i in range(num_chunks):
                if not self.is_running:
                    break
                start = int(chunk_edges[i])
                end = int(chunk_edges[i + 1])
                if end <= start:
                    continue

                # Ejecutar una parte de la simulación
                resultados = generar_lda_con_secuencialidad(
                    self.eventos_riesgo,
                    num_simulaciones=end - start,
                    orden_eventos_ids=self._orden_eventos_ids,
                    rng=self._rng
                )

                # Actualizar los resultados acumulados
                # Actualizar perdidas_totales y frecuencias_totales
                perdidas_totales[start:end] = resultados[0]
                frecuencias_totales[start:end] = resultados[1]

                # Inicializar perdidas_por_evento y frecuencias_por_evento la primera vez
                if perdidas_por_evento is None:
                    num_eventos = len(resultados[2])
                    perdidas_por_evento = [np.zeros(self.num_simulaciones) for _ in range(num_eventos)]
                    frecuencias_por_evento = [np.zeros(self.num_simulaciones, dtype=np.int32) for _ in range(num_eventos)]

                # Acumular perdidas_por_evento y frecuencias_por_evento
                for idx in range(len(perdidas_por_evento)):
                    perdidas_por_evento[idx][start:end] = resultados[2][idx]
                    frecuencias_por_evento[idx][start:end] = resultados[3][idx]

                # Emitir señal de progreso
                progreso = int((i + 1) * 100 / num_chunks)
                self.progreso_actualizado.emit(progreso)

            if not self.is_running:
                return

            self.simulacion_completada.emit(
                perdidas_totales,
                frecuencias_totales,
                perdidas_por_evento,
                frecuencias_por_evento,
                self.eventos_riesgo
            )
        except Exception as e:
            self.error_ocurrido.emit(str(e))

    def stop(self):
        self.is_running = False

class Scenario:
    def __init__(self, nombre, descripcion=""):
        self.nombre = nombre
        self.descripcion = descripcion
        self.eventos_riesgo = []

    def to_dict(self):
        eventos_serializables = []
        for evento in self.eventos_riesgo:
            evt = copy.deepcopy(evento)
            for key in list(evt.keys()):
                if key in ('dist_severidad', 'dist_frecuencia') or key.startswith('_'):
                    del evt[key]
            eventos_serializables.append(evt)
        return {
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'eventos_riesgo': eventos_serializables
        }

    @staticmethod
    def from_dict(data):
        scenario = Scenario(data['nombre'], data.get('descripcion', ''))
        scenario.eventos_riesgo = data.get('eventos_riesgo', [])
        return scenario

# Clase personalizada de QComboBox que ignora el scroll del mouse
class NoScrollComboBox(QtWidgets.QComboBox):
    """QComboBox que no cambia su valor con la rueda del mouse"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
    
    def wheelEvent(self, event):
        # Ignorar el evento de rueda del mouse si no tiene el foco
        if not self.hasFocus():
            event.ignore()
        else:
            # Si tiene el foco, permitir el comportamiento normal
            super().wheelEvent(event)

# Clase EventCard para vista de tarjetas de eventos
class EventCard(QtWidgets.QFrame):
    """Tarjeta visual para mostrar un evento de riesgo."""
    
    # Señales para comunicar acciones
    editRequested = QtCore.pyqtSignal(dict)
    duplicateRequested = QtCore.pyqtSignal(dict)
    deleteRequested = QtCore.pyqtSignal(dict)
    activeChanged = QtCore.pyqtSignal(dict, bool)  # Evento, nuevo estado activo
    
    def __init__(self, evento_data, parent=None, iconos=None):
        super().__init__(parent)
        self.evento_data = evento_data
        self.iconos = iconos if iconos else {}
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz de la tarjeta con diseño Material Design."""
        self.setFixedWidth(260)  # Más ancho para mejor spacing
        self.setMinimumHeight(320)  # Más altura para diseño moderno
        self.setCursor(QtCore.Qt.PointingHandCursor)
        
        # Estilo Material Design con elevación
        self.setStyleSheet("""
            EventCard {
                background: #FFFFFF;
                border: none;
                border-radius: 12px;
                /* Sombra tipo Material Design - elevación 2 */
            }
            EventCard:hover {
                background: #FAFAFA;
                /* Sombra tipo Material Design - elevación 4 */
            }
        """)
        
        # Agregar efecto de sombra (elevation)
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QtGui.QColor(0, 0, 0, 25))  # Negro semi-transparente
        self.setGraphicsEffect(shadow)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === HEADER MODERNO TIPO MATERIAL ===
        header_container = QtWidgets.QWidget()
        header_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667EEA, stop:1 #764BA2
                );
                border-radius: 12px 12px 0px 0px;
            }
        """)
        header_layout = QtWidgets.QHBoxLayout(header_container)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(8)
        
        # Título - Nombre del evento (en header)
        nombre = self.evento_data.get('nombre', 'Sin nombre')
        titulo = QtWidgets.QLabel(nombre)
        titulo.setWordWrap(True)
        titulo.setStyleSheet(f"""
            font-size: {UI_FONT_NORMAL}pt;
            font-weight: 600;
            color: #FFFFFF;
            letter-spacing: 0.2px;
            background: transparent;
        """)
        header_layout.addWidget(titulo, stretch=1)
        
        # Toggle switch para activar/desactivar
        self.toggle_activo = QtWidgets.QCheckBox()
        activo = self.evento_data.get('activo', True)
        self.toggle_activo.setChecked(activo)
        self.toggle_activo.setToolTip("Activar/Desactivar para simulación")
        self.toggle_activo.setStyleSheet("""
            QCheckBox {
                background: transparent;
                spacing: 0px;
            }
            QCheckBox::indicator {
                width: 36px;
                height: 20px;
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.3);
            }
            QCheckBox::indicator:checked {
                background: #5C9F35;
            }
            QCheckBox::indicator:unchecked {
                background: rgba(255, 255, 255, 0.3);
            }
        """)
        self.toggle_activo.stateChanged.connect(self.on_toggle_changed)
        header_layout.addWidget(self.toggle_activo)
        
        layout.addWidget(header_container)
        
        # === CONTENIDO PRINCIPAL ===
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 12)
        content_layout.setSpacing(12)
        
        # Información de IMPACTO (Severidad) - Card dentro de Card
        impacto_info = self.get_impacto_info()
        impacto_label = QtWidgets.QLabel(impacto_info)
        impacto_label.setWordWrap(True)
        impacto_label.setTextFormat(QtCore.Qt.RichText)
        impacto_label.setStyleSheet(f"""
            QLabel {{
                font-size: {UI_FONT_XSMALL}pt;
                color: #37474F;
                padding: 12px;
                background: #F8F9FA;
                border-radius: 8px;
                border-left: 3px solid #667EEA;
            }}
        """)
        content_layout.addWidget(impacto_label)
        
        # Información de FRECUENCIA - Card dentro de Card
        freq_info = self.get_frecuencia_info()
        freq_label = QtWidgets.QLabel(freq_info)
        freq_label.setWordWrap(True)
        freq_label.setTextFormat(QtCore.Qt.RichText)
        freq_label.setStyleSheet(f"""
            QLabel {{
                font-size: {UI_FONT_XSMALL}pt;
                color: #37474F;
                padding: 12px;
                background: #F8F9FA;
                border-radius: 8px;
                border-left: 3px solid #43A047;
            }}
        """)
        content_layout.addWidget(freq_label)
        
        # Vínculos - Chip moderno
        vinculos = self.evento_data.get('vinculos', [])
        if vinculos and len(vinculos) > 0:
            vinculos_text = f"⛓ {len(vinculos)} dependencia(s)"
            chip_bg = "#E8EAF6"
            chip_color = "#3F51B5"
        else:
            vinculos_text = "✓ Independiente"
            chip_bg = "#E8F5E9"
            chip_color = "#2E7D32"
        
        vinculos_label = QtWidgets.QLabel(vinculos_text)
        vinculos_label.setStyleSheet(f"""
            QLabel {{
                font-size: {UI_FONT_XSMALL}pt;
                color: {chip_color};
                background: {chip_bg};
                padding: 6px 12px;
                border-radius: 12px;
                font-weight: 500;
            }}
        """)
        vinculos_label.setAlignment(QtCore.Qt.AlignCenter)
        
        # Tooltip con detalle de cada vínculo y su probabilidad
        if vinculos and len(vinculos) > 0:
            # Resolver nombres de eventos padre desde el parent (main window)
            eventos_ref = []
            if self.parent() and hasattr(self.parent(), 'eventos_riesgo'):
                eventos_ref = self.parent().eventos_riesgo
            tooltip_lines = []
            for v in vinculos:
                nombre_padre = "Desconocido"
                for e in eventos_ref:
                    if e.get('id') == v.get('id_padre'):
                        nombre_padre = e.get('nombre', 'Sin nombre')
                        break
                prob = v.get('probabilidad', 100)
                fsev = v.get('factor_severidad', 1.0)
                umbral = v.get('umbral_severidad', 0)
                detalle = f"{v.get('tipo', '?')} → {nombre_padre} ({prob}%, sev:{fsev:.2f}x"
                if umbral > 0:
                    detalle += f", umbral:${umbral:,}"
                detalle += ")"
                tooltip_lines.append(detalle)
            vinculos_label.setToolTip("\n".join(tooltip_lines))
        
        content_layout.addWidget(vinculos_label)
        
        content_layout.addStretch()
        layout.addWidget(content_widget)
        
        # Botones de acción modernos
        actions_widget = self.crear_botones_accion_modernos()
        layout.addWidget(actions_widget)
    
    def mouseDoubleClickEvent(self, event):
        """Maneja el doble click para editar."""
        self.editRequested.emit(self.evento_data)
        event.accept()
    
    def get_impacto_info(self):
        """Obtiene información formateada del IMPACTO (Severidad)."""
        sev_opcion = self.evento_data.get('sev_opcion', 0)
        sev_input_method = self.evento_data.get('sev_input_method', 'min_mode_max')
        
        info = "<b style='color: #667EEA;'>◆ IMPACTO</b><br>"
        
        try:
            # Normal o Lognormal con parámetros directos
            if sev_opcion in [1, 2]:
                nombre = 'Normal' if sev_opcion == 1 else 'Lognormal'
                
                if sev_input_method == 'params_direct' or sev_input_method == 'direct':
                    # Parámetros avanzados: media y desv directos
                    params = self.evento_data.get('sev_params_direct')
                    if params and isinstance(params, dict):
                        # Intentar diferentes formatos de parámetros
                        media = params.get('mean', params.get('media', params.get('mu', 0)))
                        desv = params.get('std', params.get('desv', params.get('sigma', 0)))
                        
                        # Validar que sean números
                        if isinstance(media, (int, float)) and isinstance(desv, (int, float)):
                            info += f"{nombre}<br>μ: ${media:,.0f} | σ: ${desv:,.0f}"
                        else:
                            info += f"{nombre}<br>Parámetros configurados"
                    else:
                        info += f"{nombre}<br>Parámetros no disponibles"
                else:
                    # Parámetros simplificados: min, mode, max (convertidos internamente)
                    minimo = self.evento_data.get('sev_minimo') or 0
                    mas_prob = self.evento_data.get('sev_mas_probable') or 0
                    maximo = self.evento_data.get('sev_maximo') or 0
                    info += f"{nombre}<br>Min: ${minimo:,.0f}<br>Moda: ${mas_prob:,.0f}<br>Max: ${maximo:,.0f}"
            
            # PERT (opcion 3)
            elif sev_opcion == 3:
                minimo = self.evento_data.get('sev_minimo') or 0
                mas_prob = self.evento_data.get('sev_mas_probable') or 0
                maximo = self.evento_data.get('sev_maximo') or 0
                info += f"PERT<br>Min: ${minimo:,.0f}<br>Moda: ${mas_prob:,.0f}<br>Max: ${maximo:,.0f}"
            
            # Pareto/GPD (opcion 4)
            elif sev_opcion == 4:
                if sev_input_method == 'direct' or sev_input_method == 'params_direct':
                    params = self.evento_data.get('sev_params_direct')
                    if params and isinstance(params, dict):
                        umbral = params.get('umbral', params.get('loc', 0))
                        xi = params.get('xi', params.get('c', 0))
                        if isinstance(umbral, (int, float)) and isinstance(xi, (int, float)):
                            info += f"Pareto/GPD<br>Umbral: ${umbral:,.0f} | ξ: {xi:.3f}"
                        else:
                            info += "Pareto/GPD<br>Parámetros configurados"
                    else:
                        info += "Pareto/GPD<br>Parámetros no disponibles"
                else:
                    minimo = self.evento_data.get('sev_minimo') or 0
                    mas_prob = self.evento_data.get('sev_mas_probable') or 0
                    maximo = self.evento_data.get('sev_maximo') or 0
                    info += f"Pareto/GPD<br>Min: ${minimo:,.0f}<br>Moda: ${mas_prob:,.0f}<br>Max: ${maximo:,.0f}"
            
            # Uniforme (opcion 5)
            elif sev_opcion == 5:
                minimo = self.evento_data.get('sev_minimo') or 0
                maximo = self.evento_data.get('sev_maximo') or 0
                info += f"Uniforme<br>Min: ${minimo:,.0f} | Max: ${maximo:,.0f}"
            
            else:
                info += "No configurada"
        
        except Exception as e:
            info += f"<i>Error de formato</i>"
        
        return info
    
    def get_frecuencia_info(self):
        """Obtiene información formateada de la FRECUENCIA."""
        freq_opcion = self.evento_data.get('freq_opcion', 0)
        
        info = "<b style='color: #43A047;'>◆ FRECUENCIA</b><br>"
        
        try:
            if freq_opcion == 1:  # Poisson
                tasa = self.evento_data.get('tasa') or 0
                info += f"Poisson<br>λ: {tasa:.2f}"
            
            elif freq_opcion == 2:  # Binomial
                n = self.evento_data.get('num_eventos') or 0
                p = self.evento_data.get('prob_exito') or 0
                info += f"Binomial<br>n: {n} | p: {p:.3f}"
            
            elif freq_opcion == 3:  # Bernoulli
                p = self.evento_data.get('prob_exito') or 0
                info += f"Bernoulli<br>p: {p:.3f}"
            
            elif freq_opcion == 4:  # Poisson-Gamma
                pg_min = self.evento_data.get('pg_minimo') or 0
                pg_mode = self.evento_data.get('pg_mas_probable') or 0
                pg_max = self.evento_data.get('pg_maximo') or 0
                pg_conf = self.evento_data.get('pg_confianza') or 0
                info += f"Poisson-Gamma<br>Min: {pg_min:.1f} | Moda: {pg_mode:.1f}<br>Max: {pg_max:.1f} | Conf: {pg_conf:.0f}%"
            
            elif freq_opcion == 5:  # Beta
                beta_min = self.evento_data.get('beta_minimo') or 0
                beta_mode = self.evento_data.get('beta_mas_probable') or 0
                beta_max = self.evento_data.get('beta_maximo') or 0
                beta_conf = self.evento_data.get('beta_confianza') or 0
                info += f"Beta<br>Min: {beta_min:.1f} | Moda: {beta_mode:.1f}<br>Max: {beta_max:.1f} | Conf: {beta_conf:.0f}%"
            
            else:
                info += "No configurada"
        
        except Exception as e:
            info += f"Error: {str(e)[:30]}"
        
        return info
    
    def crear_botones_accion_modernos(self):
        """Crea barra de acciones estilo Material Design compacta."""
        container = QtWidgets.QWidget()
        container.setStyleSheet("""
            QWidget {
                background: #FAFAFA;
                border-radius: 0px 0px 12px 12px;
            }
        """)
        container_layout = QtWidgets.QHBoxLayout(container)
        container_layout.setContentsMargins(12, 8, 12, 8)
        container_layout.setSpacing(6)
        
        # Estilo compacto y limpio - SIN stretch en size policy
        button_style = f"""
            QPushButton {{{{
                background: {{bg_color}};
                border: none;
                color: {{text_color}};
                font-size: {UI_FONT_BODY}pt;
                font-weight: 600;
                border-radius: 5px;
                text-align: center;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
            }}}}
            QPushButton:hover {{{{
                background: {{hover_color}};
            }}}}
            QPushButton:pressed {{{{
                background: {{pressed_color}};
            }}}}
        """
        
        # Botón EDITAR - Compacto
        edit_btn = QtWidgets.QPushButton()
        if "edit" in self.iconos:
            edit_btn.setIcon(self.iconos["edit"])
            edit_btn.setIconSize(QtCore.QSize(16, 16))
        else:
            edit_btn.setText("✎")
        edit_btn.setToolTip("Editar")
        edit_btn.setCursor(QtCore.Qt.PointingHandCursor)
        edit_btn.clicked.connect(lambda: self.editRequested.emit(self.evento_data))
        edit_btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        edit_btn.setStyleSheet(button_style.format(
            bg_color="#2196F3",
            text_color="#FFFFFF",
            hover_color="#1E88E5",
            pressed_color="#1976D2"
        ))
        container_layout.addWidget(edit_btn)
        
        # Botón DUPLICAR - Compacto
        dup_btn = QtWidgets.QPushButton()
        if "copy" in self.iconos:
            dup_btn.setIcon(self.iconos["copy"])
            dup_btn.setIconSize(QtCore.QSize(16, 16))
        else:
            dup_btn.setText("⎘")
        dup_btn.setToolTip("Duplicar")
        dup_btn.setCursor(QtCore.Qt.PointingHandCursor)
        dup_btn.clicked.connect(lambda: self.duplicateRequested.emit(self.evento_data))
        dup_btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        dup_btn.setStyleSheet(button_style.format(
            bg_color="#4CAF50",
            text_color="#FFFFFF",
            hover_color="#43A047",
            pressed_color="#388E3C"
        ))
        container_layout.addWidget(dup_btn)
        
        # Botón ELIMINAR - Compacto
        del_btn = QtWidgets.QPushButton()
        if "delete" in self.iconos:
            del_btn.setIcon(self.iconos["delete"])
            del_btn.setIconSize(QtCore.QSize(16, 16))
        else:
            del_btn.setText("✕")
        del_btn.setToolTip("Eliminar")
        del_btn.setCursor(QtCore.Qt.PointingHandCursor)
        del_btn.clicked.connect(lambda: self.deleteRequested.emit(self.evento_data))
        del_btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        del_btn.setStyleSheet(button_style.format(
            bg_color="#F44336",
            text_color="#FFFFFF",
            hover_color="#E53935",
            pressed_color="#D32F2F"
        ))
        container_layout.addWidget(del_btn)
        
        # Spacer para empujar botones a la izquierda
        container_layout.addStretch()
        
        return container
    
    def on_toggle_changed(self, state):
        """Callback cuando cambia el estado del toggle.
        
        Args:
            state: Nuevo estado (Qt.Checked o Qt.Unchecked)
        """
        activo = (state == QtCore.Qt.Checked)
        # Actualizar el evento_data local
        self.evento_data['activo'] = activo
        # Emitir señal para que el parent actualice el modelo
        self.activeChanged.emit(self.evento_data, activo)
        # Aplicar estilo visual
        self.aplicar_estilo_activo(activo)
    
    def aplicar_estilo_activo(self, activo):
        """Aplica estilo visual según el estado activo/inactivo.
        
        Args:
            activo: True si está activo, False si inactivo
        """
        if activo:
            # Estilo ACTIVO - Sin borde, pero con sombra más pronunciada
            self.setGraphicsEffect(None)
            
            # Estilo normal sin borde
            self.setStyleSheet("""
                EventCard {
                    background: #FFFFFF;
                    border: none;
                    border-radius: 12px;
                }
                EventCard:hover {
                    background: #FAFAFA;
                }
            """)
            
            # Sombra más pronunciada (elevación 6) para tarjetas activas
            shadow = QtWidgets.QGraphicsDropShadowEffect()
            shadow.setBlurRadius(18)
            shadow.setXOffset(0)
            shadow.setYOffset(3)
            shadow.setColor(QtGui.QColor(0, 0, 0, 40))  # Negro semi-transparente más visible
            self.setGraphicsEffect(shadow)
        else:
            # Estilo INACTIVO - Sin borde + opacidad reducida (50%)
            self.setStyleSheet("""
                EventCard {
                    background: #FFFFFF;
                    border: none;
                    border-radius: 12px;
                }
                EventCard:hover {
                    background: #FAFAFA;
                }
            """)
            
            # Opacidad reducida para eventos inactivos
            opacity_effect = QtWidgets.QGraphicsOpacityEffect()
            opacity_effect.setOpacity(0.5)
            self.setGraphicsEffect(opacity_effect)

# Clase para la interfaz gráfica usando PyQt5
class RiskLabApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Risk Lab")

        # Establecer el icono de la aplicación
        try:
            app_icon = QtGui.QIcon()
            # Usar resource_path() para compatibilidad con PyInstaller
            icon_path = resource_path(os.path.join('icons', 'app_icon.ico'))

            if os.path.exists(icon_path):
                app_icon.addFile(icon_path) # Para .ico, addFile es suficiente y maneja múltiples tamaños
                self.setWindowIcon(app_icon)
            else:
                print(f"Advertencia: No se encontró el archivo de icono en {icon_path}")
                # Opcional: Establecer un icono de sistema por defecto si el personalizado no se encuentra
                # self.setWindowIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)) 
        except Exception as e:
            print(f"Error al establecer el icono de la aplicación: {e}")
            
        self.APP_VERSION = "1.10.0"
        self.eventos_riesgo = []
        self.scenarios = []
        self.current_scenario = None  # Escenario actualmente seleccionado
        self.generar_reporte = False
        self.pdf_filename = 'reporte_simulacion.pdf'
        
        # Cargar iconos modernos
        self.cargar_iconos_modernos()
        
        # Establecer traductor para la interfaz
        self.configurar_traductor()
        
        self.setup_ui()
        self.apply_stylesheet()
        
        # Configurar tamaño y posición óptima de la ventana
        self._configurar_ventana_inicial()
        
    def _configurar_ventana_inicial(self):
        """
        Configura el tamaño y posición inicial de la ventana según la pantalla disponible.
        En pantallas pequeñas inicia maximizada para aprovechar todo el espacio.
        """
        try:
            screen = QtWidgets.QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()  # Ya excluye barra de tareas
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            
            print(f"Pantalla disponible (después de escala Qt): {screen_width}x{screen_height}")
            
            # En pantallas pequeñas (< 800px altura disponible), iniciar maximizada
            if screen_height < 800:
                print("Pantalla pequeña detectada, iniciando maximizada")
                self.showMaximized()
                return
            
            # Usar 92% del espacio disponible para dejar margen visual
            window_width = int(screen_width * 0.92)
            window_height = int(screen_height * 0.90)
            
            # Tamaño mínimo adaptativo (menor en pantallas pequeñas)
            min_width = min(900, screen_width - 50)
            min_height = min(600, screen_height - 50)
            window_width = max(window_width, min_width)
            window_height = max(window_height, min_height)
            
            # NO establecer setMaximumSize - permite maximizar libremente
            
            # Centrar en el área disponible (ya considera barra de tareas)
            x = screen_geometry.x() + (screen_width - window_width) // 2
            y = screen_geometry.y() + (screen_height - window_height) // 2
            
            self.setGeometry(x, y, window_width, window_height)
            
            print(f"Ventana configurada: {window_width}x{window_height} en ({x}, {y})")
            
        except Exception as e:
            print(f"Error configurando ventana: {e}")
            # Fallback: usar tamaño que quepa en pantalla
            self.showMaximized()
    
    def _refrescar_ventana_maximizada(self):
        """
        Fuerza una actualización del layout cuando la ventana está maximizada.
        Soluciona el bug de PyQt donde el layout se desalinea después de cambios de contenido.
        Usa la técnica de showNormal/showMaximized que es lo que funciona manualmente.
        """
        if self.isMaximized():
            # Guardar estado y forzar ciclo de restauración
            QtCore.QTimer.singleShot(100, lambda: self._aplicar_refresh_maximizado())
    
    def _aplicar_refresh_maximizado(self):
        """Aplica el refresh de la ventana maximizada mediante ciclo showNormal/showMaximized."""
        try:
            if self.isMaximized():
                # Desmaximizar brevemente y volver a maximizar (simula lo que hace el usuario)
                self.showNormal()
                QtWidgets.QApplication.processEvents()
                QtCore.QTimer.singleShot(50, lambda: self.showMaximized())
        except Exception:
            pass
        
    def configurar_traductor(self):
        """Configura el traductor para asegurar que todos los textos de la interfaz
        estén en español neutro."""
        from PyQt5.QtCore import QTranslator, QLocale, QLibraryInfo
        
        # Crear traductor para botones estándar y diálogos
        translator = QTranslator(self)
        # Configurar traducción de Qt al español
        translator.load("qt_es", QLibraryInfo.location(QLibraryInfo.TranslationsPath))
        QtWidgets.QApplication.instance().installTranslator(translator)
        
        # Diccionario de traducciones personalizadas para textos específicos
        self.traducciones = {
            # Botones estándar
            "OK": "Aceptar",
            "Cancel": "Cancelar",
            "Save": "Guardar",
            "Open": "Abrir",
            "Close": "Cerrar",
            "Yes": "Sí",
            "No": "No",
            "Apply": "Aplicar",
            "Reset": "Reiniciar",
            "Default": "Predeterminado",
            "Restore": "Restaurar",
            "Discard": "Descartar",
            
            # Títulos de diálogos
            "Error": "Error",
            "Warning": "Advertencia",
            "Information": "Información",
            "Critical": "Crítico",
            "Question": "Pregunta",
            
            # Botones con teclas rápidas
            "&Yes": "&Sí",
            "&No": "&No",
            "&Cancel": "&Cancelar",
            "&Close": "&Cerrar",
            "&Save": "&Guardar",
            "&Open": "&Abrir",
            "&Apply": "&Aplicar",
            "&Reset": "&Reiniciar",
            
            # Comandos de edición
            "Copy": "Copiar",
            "Cut": "Cortar",
            "Paste": "Pegar",
            "Delete": "Eliminar",
            "Select All": "Seleccionar Todo",
            "Select": "Seleccionar",
            
            # Navegación
            "Back": "Atrás",
            "Forward": "Adelante",
            "Previous": "Anterior",
            "Next": "Siguiente",
            "Done": "Hecho",
            "Finish": "Finalizar",
            "Help": "Ayuda",
            
            # Términos estadísticos (específicos para Risk Lab)
            "Mean": "Media",
            "Median": "Mediana",
            "Mode": "Moda",
            "Standard Deviation": "Desviación Estándar",
            "Variance": "Varianza",
            "Percentile": "Percentil",
            "Simulation": "Simulación",
            "Results": "Resultados",
            "Configuration": "Configuración",
            "Parameters": "Parámetros",
            "Distribution": "Distribución",
            "Frequency": "Frecuencia",
            "Severity": "Severidad",
            "Correlation": "Correlación",
            "Analysis": "Análisis"
        }
    
    def aplicar_traducciones_a_widgets(self):
        """Aplica traducciones en español neutro a todos los widgets de la interfaz."""
        # Traducir botones estándar de diálogos
        from PyQt5.QtWidgets import QPushButton, QLabel, QTabBar, QAction, QMenu
        
        # Traducir botones
        for button in self.findChildren(QPushButton):
            texto_actual = button.text()
            if texto_actual in self.traducciones:
                button.setText(self.traducciones[texto_actual])
        
        # Traducir etiquetas
        for label in self.findChildren(QLabel):
            texto_actual = label.text()
            if texto_actual in self.traducciones:
                label.setText(self.traducciones[texto_actual])
        
        # Traducir pestañas
        for tab_bar in self.findChildren(QTabBar):
            for i in range(tab_bar.count()):
                texto_actual = tab_bar.tabText(i)
                if texto_actual in self.traducciones:
                    tab_bar.setTabText(i, self.traducciones[texto_actual])
        
        # Traducir acciones de menús
        for action in self.findChildren(QAction):
            texto_actual = action.text()
            if texto_actual in self.traducciones:
                action.setText(self.traducciones[texto_actual])
                
        # Traducir menús
        for menu in self.findChildren(QMenu):
            texto_actual = menu.title()
            if texto_actual in self.traducciones:
                menu.setTitle(self.traducciones[texto_actual])
        
        print("Traducciones en español neutro aplicadas a la interfaz")

    def cargar_iconos_modernos(self):
        """Carga los iconos SVG modernos para la aplicación (blancos y oscuros)."""
        import os
        from PyQt5.QtGui import QIcon, QPixmap, QColor
        from PyQt5.QtCore import QSize, Qt
        
        # Crear diccionarios para almacenar iconos blancos y oscuros
        self.iconos = {}  # Iconos blancos para fondos oscuros
        self.iconos_oscuros = {}  # Iconos oscuros para fondos claros
        # Usar resource_path() para compatibilidad con PyInstaller
        iconos_base_dir = resource_path("icons")
        
        # Mapeo de nombres de iconos a archivos SVG
        iconos_mapa = {
            "add": ("add-white.svg", "add.svg"),  # (Versión blanca, Versión oscura)
            "edit": ("edit-white.svg", "edit.svg"),
            "delete": ("delete-white.svg", "delete.svg"),
            "play": ("play-white.svg", "play.svg"),
            "copy": ("copy-white.svg", "copy.svg"),
            "chart": ("chart-white.svg", "chart.svg"),
            "save": ("save-white.svg", "save.svg"),
            "export": ("export-white.svg", "export.svg")
        }
        
        # Tamaño fijo para todos los iconos
        icon_size = QSize(24, 24)
        
        # Cargar cada icono en sus dos versiones
        for nombre, (archivo_blanco, archivo_oscuro) in iconos_mapa.items():
            # Cargar versión BLANCA
            ruta_blanco = os.path.join(iconos_base_dir, archivo_blanco)
            if os.path.exists(ruta_blanco):
                try:
                    icon_blanco = QIcon(ruta_blanco)
                    if not icon_blanco.isNull():
                        self.iconos[nombre] = icon_blanco
                        print(f"Icono blanco {nombre} cargado correctamente")
                except Exception as e:
                    print(f"Error al cargar icono blanco {ruta_blanco}: {e}")
            
            # Cargar versión OSCURA
            ruta_oscuro = os.path.join(iconos_base_dir, archivo_oscuro)
            if os.path.exists(ruta_oscuro):
                try:
                    icon_oscuro = QIcon(ruta_oscuro)
                    if not icon_oscuro.isNull():
                        self.iconos_oscuros[nombre] = icon_oscuro
                        print(f"Icono oscuro {nombre} cargado correctamente")
                except Exception as e:
                    print(f"Error al cargar icono oscuro {ruta_oscuro}: {e}")
            
            # Si no existe ninguna versión, usar icono de tema o crear uno
            if nombre not in self.iconos and nombre not in self.iconos_oscuros:
                tema_mapa = {
                    "add": "list-add",
                    "edit": "edit",
                    "delete": "edit-delete",
                    "play": "system-run",
                    "copy": "edit-copy",
                    "chart": "x-office-spreadsheet",
                    "save": "document-save",
                    "export": "document-export"
                }
                
                icon_tema = QIcon.fromTheme(tema_mapa.get(nombre, "application-x-executable"))
                if icon_tema.isNull():
                    self.iconos[nombre] = self.crear_icono_texto(nombre, icon_size)
                    self.iconos_oscuros[nombre] = self.crear_icono_texto(nombre, icon_size)
                else:
                    self.iconos[nombre] = icon_tema
                    self.iconos_oscuros[nombre] = icon_tema
                
    def crear_icono_texto(self, texto, size):
        """Crea un icono con texto como respaldo"""
        from PyQt5.QtGui import QIcon, QPixmap, QPainter, QFont, QColor
        from PyQt5.QtCore import Qt
        
        # Crear un QPixmap del tamaño deseado
        pixmap = QPixmap(size)
        pixmap.fill(QColor("transparent"))
        
        # Crear un pintor para dibujar en el pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        
        # Configurar la fuente y el color
        font = QFont("Arial", 10, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor("white"))
        
        # Dibujar el primer carácter del texto centrado
        texto_abreviado = texto[0].upper()
        painter.drawText(pixmap.rect(), Qt.AlignCenter, texto_abreviado)
        
        # Finalizar el pintado
        painter.end()
        
        # Crear y devolver el icono
        return QIcon(pixmap)

    def setup_ui(self):
        # Crear un contenedor principal con layout vertical
        main_container = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Hero Banner global (arriba de todo) - Estilo MercadoLibre
        self.hero_banner_global = self.crear_hero_banner()
        main_layout.addWidget(self.hero_banner_global)
        
        # Widget central con pestañas
        self.central_widget = QtWidgets.QTabWidget()
        self.central_widget.setObjectName("mainTabWidget")  # para aplicar estilos solo a estas pestañas
        main_layout.addWidget(self.central_widget)
        
        # Establecer el contenedor principal como central widget
        self.setCentralWidget(main_container)

        # Pestaña de Simulación
        self.config_tab = QtWidgets.QWidget()
        self.setup_config_tab()
        self.central_widget.addTab(self.config_tab, "Simulación")

        # Pestaña de Escenarios
        self.scenarios_tab = QtWidgets.QWidget()
        self.setup_scenarios_tab()
        self.central_widget.addTab(self.scenarios_tab, "Escenarios")

        # Pestaña de Resultados
        self.results_tab = QtWidgets.QWidget()
        self.setup_results_tab()
        self.central_widget.addTab(self.results_tab, "Resultados")
        
        # Mejoras de pestañas principales: sin truncado, con scroll y no expansivas
        try:
            self.central_widget.setDocumentMode(False)  # Tabs más altas y legibles
            main_tb = self.central_widget.tabBar()
            main_tb.setElideMode(QtCore.Qt.ElideNone)
            main_tb.setUsesScrollButtons(True)
            main_tb.setExpanding(False)
            main_tb.setIconSize(QtCore.QSize(20, 20))

            # Aplicar estilo moderno MercadoLibre a pestañas principales
            self.aplicar_estilo_tab_widget_moderno(self.central_widget)
        except Exception:
            pass

        # Iconos para pestañas principales (si están disponibles)
        try:
            # Usar resource_path() para compatibilidad con PyInstaller
            icon_play = QtGui.QIcon(resource_path(os.path.join('icons', 'play.svg')))
            icon_copy = QtGui.QIcon(resource_path(os.path.join('icons', 'copy.svg')))
            icon_chart = QtGui.QIcon(resource_path(os.path.join('icons', 'chart.svg')))

            # Fallback a iconos ya cargados si no existen variantes
            if icon_play.isNull():
                icon_play = self.iconos.get("play", QtGui.QIcon())
            if icon_copy.isNull():
                icon_copy = self.iconos.get("copy", QtGui.QIcon())
            if icon_chart.isNull():
                icon_chart = self.iconos.get("chart", QtGui.QIcon())

            self.central_widget.setTabIcon(self.central_widget.indexOf(self.config_tab), icon_play)
            self.central_widget.setTabIcon(self.central_widget.indexOf(self.scenarios_tab), icon_copy)
            self.central_widget.setTabIcon(self.central_widget.indexOf(self.results_tab), icon_chart)
        except Exception:
            pass

        # Menú
        menu_bar = self.menuBar()
        # Menú Archivo
        archivo_menu = menu_bar.addMenu("Archivo")

        # Agregar acción Nueva Simulación
        nuevo_action = QtWidgets.QAction("Nueva Simulación", self)
        archivo_menu.addAction(nuevo_action)
        nuevo_action.triggered.connect(self.nueva_simulacion)

        guardar_config_action = QtWidgets.QAction("Guardar Simulación", self)
        cargar_config_action = QtWidgets.QAction("Cargar Simulación", self)
        exportar_pdf_action = QtWidgets.QAction("Exportar Reporte", self)
        salir_action = QtWidgets.QAction("Salir", self)

        archivo_menu.addAction(guardar_config_action)
        archivo_menu.addAction(cargar_config_action)
        archivo_menu.addAction(exportar_pdf_action)
        archivo_menu.addSeparator()
        archivo_menu.addAction(salir_action)

        guardar_config_action.triggered.connect(self.guardar_configuracion)
        cargar_config_action.triggered.connect(self.cargar_configuracion)
        exportar_pdf_action.triggered.connect(self.exportar_a_pdf)
        salir_action.triggered.connect(self.close)

        # Menú Ayuda
        ayuda_menu = menu_bar.addMenu("Ayuda")
        asistente_action = QtWidgets.QAction("Asistente IA", self)
        acerca_de_action = QtWidgets.QAction("Acerca de", self)
        ayuda_menu.addAction(asistente_action)
        ayuda_menu.addAction(acerca_de_action)

        asistente_action.triggered.connect(self.abrir_asistente_ia)
        acerca_de_action.triggered.connect(self.mostrar_acerca_de)
        
        # Aplicar estilos modernos a todos los inputs
        self.aplicar_estilo_inputs_modernos()

    def nueva_simulacion(self):
        respuesta = QtWidgets.QMessageBox.question(
            self,
            "Nueva Simulación",
            "¿Estás seguro de que deseas iniciar una nueva simulación? Se perderán todos los datos actuales.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if respuesta == QtWidgets.QMessageBox.Yes:
            # Limpiar eventos de riesgo
            self.eventos_riesgo.clear()
            self.eventos_table.setRowCount(0)
            self.actualizar_vista_eventos()  # Actualizar vista

            # Limpiar escenarios
            self.scenarios.clear()
            self.scenarios_table.setRowCount(0)
            self.current_scenario = None
            self.selected_scenario_label.setText("Ninguno")
            self.actualizar_vista_escenarios()  # Actualizar vista

            # Limpiar resultados de simulación
            self.resultados_text_edit.clear()
            self.graficos_tab_widget.clear()
            
            # Limpiar el contenedor de Resumen estadístico
            for i in reversed(range(self.resultados_layout.count())): 
                widget = self.resultados_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            self.secciones_resultados = {}
            # Recrear sección de Consulta de Excedencia y dejarla deshabilitada
            try:
                self.agregar_seccion_excedencia_si_falta()
            except Exception:
                pass

            # Restablecer número de simulaciones a un valor por defecto si lo deseas
            self.num_simulaciones_var.setText("10000")
            self.num_simulaciones_var_escenarios.setText("10000")

        # Notificar al usuario que se ha iniciado una nueva simulación en la barra de estado
        self.statusBar().showMessage("Nueva simulación iniciada", 5000)

    def abrir_asistente_ia(self):
        """Función deshabilitada - Asistente IA removido para seguridad."""
        QtWidgets.QMessageBox.information(
            self,
            "Función no disponible",
            "El Asistente IA ha sido deshabilitado en esta versión."
        )

    def mostrar_acerca_de(self):
        # Crear un diálogo personalizado
        about_dialog = QtWidgets.QDialog(self)
        about_dialog.setWindowTitle("Acerca de Risk Lab")
        about_dialog.setMinimumWidth(550)
        about_dialog.setMinimumHeight(450)
        about_dialog.setWindowFlags(about_dialog.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        
        # Establecer fondo claro
        about_dialog.setStyleSheet("background-color: white;")
        
        # Crear layout principal vertical
        main_layout = QtWidgets.QVBoxLayout(about_dialog)
        
        # Área para el logo usando un QLabel
        logo_label = QtWidgets.QLabel()
        
        # Ruta a la imagen del logo
        logo_path = resource_path("images/risk_lab_logo.png")
        
        # Verificar si existe la imagen, si no usar QPixmap vacío
        if os.path.exists(logo_path):
            # Cargar la imagen desde el archivo
            logo_pixmap = QtGui.QPixmap(logo_path)
            
            # Ajustar tamaño para que se vea completa (manteniendo proporción)
            logo_pixmap = logo_pixmap.scaled(400, 250, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        else:
            # Si no existe la imagen, crear un espacio reservado
            logo_pixmap = QtGui.QPixmap(400, 250)
            logo_pixmap.fill(QtCore.Qt.transparent)
        
        # Establecer pixmap en el label
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(QtCore.Qt.AlignCenter)
        
        # Información de la aplicación
        info_text = QtWidgets.QLabel(f"""
        <div style='text-align: center;'>
            <p style='font-size: {UI_FONT_MEDIUM}pt; margin-bottom: 5px;'>Versión {self.APP_VERSION}</p>
            <p style='font-size: {UI_FONT_NORMAL}pt; margin-bottom: 15px;'>Aplicación creada por Hernán Zvirblis</p>
            <p style='font-size: {UI_FONT_BODY}pt;'>Esta aplicación es una herramienta para la simulación de riesgos<br>utilizando el método de Monte Carlo.</p>
            <p style='font-size: {UI_FONT_BODY}pt;'>Permite modelar eventos de riesgo, definir distribuciones<br>de severidad y frecuencia, y generar análisis estadísticos.</p>
        </div>
        """)
        info_text.setTextFormat(QtCore.Qt.RichText)
        info_text.setAlignment(QtCore.Qt.AlignCenter)
        
        # Botón de cerrar
        close_button = QtWidgets.QPushButton("Cerrar")
        close_button.setFixedWidth(120)
        close_button.clicked.connect(about_dialog.accept)
        
        # Añadir widgets al layout
        main_layout.addWidget(logo_label)
        main_layout.addWidget(info_text)
        main_layout.addWidget(close_button, 0, QtCore.Qt.AlignCenter)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Mostrar el diálogo
        about_dialog.exec_()
        
    def verificar_graficos_interactivos(self):
        """
        Verifica que todos los gráficos en la aplicación estén utilizando
        InteractiveFigureCanvas en lugar de FigureCanvas estándar.
        """
        try:
            # Importar el validador de gráficos
            import chart_validator
            
            # Mostrar diálogo de información inicial
            QtWidgets.QMessageBox.information(
                self,
                "Verificación de Gráficos Interactivos",
                "A continuación se realizará una verificación de todos los gráficos\n"
                "para asegurar que utilizan la versión interactiva con tooltips.\n\n"
                "Los resultados se mostrarán en un informe detallado."
            )
            
            # Crear y mostrar un diálogo de progreso
            progress_dialog = QtWidgets.QProgressDialog(
                "Verificando gráficos interactivos...", 
                None, 0, 0, self
            )
            progress_dialog.setWindowTitle("Verificando Gráficos")
            progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
            progress_dialog.show()
            QtWidgets.QApplication.processEvents()
            
            # Ejecutar la validación
            validator = chart_validator.ChartValidator()
            
            # Validar widgets en esta aplicación
            for widget in self.findChildren(QtWidgets.QWidget):
                validator.validate_widget(widget)
                QtWidgets.QApplication.processEvents()  # Mantener la UI responsiva
                
            # Cerrar diálogo de progreso
            progress_dialog.close()
            
            # Generar texto de resultados
            if validator.static_canvases == 0:
                mensaje_principal = "✅ ÉXITO: ¡Todos los gráficos utilizan InteractiveFigureCanvas!"
                titulo = "Verificación Exitosa"
                icono = QtWidgets.QMessageBox.Information
            else:
                mensaje_principal = f"⚠️ ATENCIÓN: Se encontraron {validator.static_canvases} gráficos que aún usan FigureCanvas estándar"
                titulo = "Verificación con Advertencias"
                icono = QtWidgets.QMessageBox.Warning
            
            # Crear mensaje detallado
            mensaje_detallado = f"""
            Resultados de la verificación:
            ----------------------------------------
            Total de canvas encontrados: {validator.total_canvases}
            Canvas interactivos: {validator.interactive_canvases}
            Canvas estáticos: {validator.static_canvases}
            """
            
            # Mostrar resultados en un diálogo
            result_dialog = QtWidgets.QMessageBox(self)
            result_dialog.setWindowTitle(titulo)
            result_dialog.setText(mensaje_principal)
            result_dialog.setDetailedText(mensaje_detallado)
            result_dialog.setIcon(icono)
            result_dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
            result_dialog.exec_()
            
        except Exception as e:
            # Manejar errores durante la validación
            QtWidgets.QMessageBox.critical(
                self,
                "Error en Verificación",
                f"Ocurrió un error durante la verificación de gráficos:\n{str(e)}"
            )

    def aplicar_estilo_boton_primario(self, button):
        """Aplica estilo de botón primario (acciones principales) con paleta MercadoLibre.
        
        Args:
            button: QPushButton al que aplicar el estilo
        """
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {MELI_AZUL};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: {UI_FONT_MEDIUM}pt;
                font-weight: 600;
                text-align: center;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: {MELI_AZUL_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {MELI_AZUL_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {MELI_GRIS_BORDE};
                color: {MELI_GRIS_SECUNDARIO};
            }}
        """)
    
    def aplicar_estilo_boton_secundario(self, button):
        """Aplica estilo de botón secundario (acciones secundarias) con paleta MercadoLibre.
        
        Args:
            button: QPushButton al que aplicar el estilo
        """
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {MELI_AZUL};
                border: 1px solid {MELI_AZUL};
                border-radius: 6px;
                padding: 6px 20px;
                font-size: {UI_FONT_NORMAL}pt;
                font-weight: 600;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {MELI_AZUL_CLARO};
                border-color: {MELI_AZUL_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #D0E7FF;
                border-color: {MELI_AZUL_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {MELI_GRIS_FONDO};
                color: {MELI_GRIS_SECUNDARIO};
                border-color: {MELI_GRIS_BORDE};
            }}
            QPushButton:disabled:hover {{
                background-color: {MELI_GRIS_FONDO};
                color: {MELI_GRIS_SECUNDARIO};
                border-color: {MELI_GRIS_BORDE};
            }}
        """)
    
    def aplicar_estilo_boton_exitoso(self, button):
        """Aplica estilo de botón exitoso/confirmación con verde MercadoLibre.
        
        Args:
            button: QPushButton al que aplicar el estilo
        """
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {MELI_VERDE};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
                font-size: {UI_FONT_NORMAL}pt;
                font-weight: 600;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {MELI_VERDE_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {MELI_VERDE_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {MELI_GRIS_BORDE};
                color: {MELI_GRIS_SECUNDARIO};
            }}
            QPushButton:disabled:hover {{
                background-color: {MELI_GRIS_BORDE};
                color: {MELI_GRIS_SECUNDARIO};
            }}
        """)
    
    def aplicar_estilo_boton_destructivo(self, button):
        """Aplica estilo de botón destructivo (eliminar) con rojo MercadoLibre.
        
        Args:
            button: QPushButton al que aplicar el estilo
        """
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {MELI_ROJO};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
                font-size: {UI_FONT_NORMAL}pt;
                font-weight: 600;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {MELI_ROJO_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #B92736;
            }}
            QPushButton:disabled {{
                background-color: {MELI_GRIS_BORDE};
                color: {MELI_GRIS_SECUNDARIO};
            }}
            QPushButton:disabled:hover {{
                background-color: {MELI_GRIS_BORDE};
                color: {MELI_GRIS_SECUNDARIO};
            }}
        """)
    
    def crear_table_item_con_wrap(self, texto):
        """Crea un QTableWidgetItem configurado para word wrap.
        
        Args:
            texto: Texto a mostrar en el item
        
        Returns:
            QTableWidgetItem configurado con word wrap
        """
        item = QtWidgets.QTableWidgetItem(texto)
        item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        # No es necesario setear flags especiales para word wrap,
        # ya que se configura a nivel de tabla
        return item
    
    def crear_checkbox_activo(self, row, activo=True):
        """Crea un widget con checkbox centrado para la columna 'Activo'.
        
        Args:
            row: Número de fila en la tabla
            activo: Estado inicial del checkbox (True/False)
        
        Returns:
            QWidget contenedor con el checkbox centrado
        """
        # Crear widget contenedor con tamaño máximo fijo
        widget_container = QtWidgets.QWidget()
        widget_container.setMaximumWidth(45)  # Limitar ancho máximo
        layout = QtWidgets.QHBoxLayout(widget_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        
        # Crear checkbox
        checkbox = QtWidgets.QCheckBox()
        checkbox.setChecked(activo)
        checkbox.setToolTip("Activar/Desactivar evento para simulación")
        
        # Conectar cambio de estado para actualizar el modelo
        checkbox.stateChanged.connect(lambda state, r=row: self.on_evento_activo_changed(r, state))
        
        layout.addWidget(checkbox)
        return widget_container
    
    def forzar_ancho_columna_activo(self):
        """Fuerza el ancho de la columna Activo a 45px.
        
        Esta función se llama después de agregar/modificar filas para
        asegurar que la columna mantenga su ancho compacto.
        """
        if hasattr(self, 'eventos_table'):
            self.eventos_table.setColumnWidth(0, 45)
    
    def limpiar_vinculos_huerfanos(self, ids_eliminados):
        """Elimina vínculos que apuntan a eventos eliminados.
        
        Args:
            ids_eliminados (set): Conjunto de IDs de eventos que fueron eliminados.
        """
        for evento in self.eventos_riesgo:
            if 'vinculos' in evento and evento['vinculos']:
                evento['vinculos'] = [
                    v for v in evento['vinculos']
                    if v.get('id_padre') not in ids_eliminados
                ]

    def reconstruir_checkboxes_eventos(self):
        """Recrea los checkboxes de la columna 'Activo' con índices correctos.
        
        Debe llamarse después de eliminar filas para evitar que los lambdas
        apunten a índices desactualizados.
        """
        for row in range(self.eventos_table.rowCount()):
            activo = self.eventos_riesgo[row].get('activo', True)
            self.eventos_table.setCellWidget(row, 0, self.crear_checkbox_activo(row, activo=activo))
        self.forzar_ancho_columna_activo()
    
    def on_evento_activo_changed(self, row, state):
        """Callback cuando cambia el estado del checkbox de un evento.
        
        Args:
            row: Fila de la tabla que cambió
            state: Nuevo estado (Qt.Checked o Qt.Unchecked)
        """
        if 0 <= row < len(self.eventos_riesgo):
            # Actualizar el modelo
            self.eventos_riesgo[row]['activo'] = (state == QtCore.Qt.Checked)
            
            # Aplicar estilo visual a la fila
            self.aplicar_estilo_fila_evento(row)
            
            # Actualizar contador si existe
            self.actualizar_contador_eventos()
            
            # Mensaje en status bar
            nombre = self.eventos_riesgo[row].get('nombre', 'Evento')
            estado_txt = "activado" if state == QtCore.Qt.Checked else "desactivado"
            self.statusBar().showMessage(f"Evento '{nombre}' {estado_txt}", 2000)
    
    def aplicar_estilo_fila_evento(self, row):
        """Aplica estilo visual a una fila según su estado activo/inactivo.
        
        Args:
            row: Número de fila en la tabla
        """
        if 0 <= row < len(self.eventos_riesgo):
            activo = self.eventos_riesgo[row].get('activo', True)
            
            # Aplicar opacidad reducida (gris) para eventos inactivos
            for col in range(self.eventos_table.columnCount()):
                item = self.eventos_table.item(row, col)
                if item:
                    if activo:
                        # Estilo normal
                        item.setForeground(QtGui.QColor(0, 0, 0))
                        font = item.font()
                        font.setItalic(False)
                        item.setFont(font)
                    else:
                        # Estilo inactivo (gris con 50% opacidad)
                        item.setForeground(QtGui.QColor(128, 128, 128))
                        font = item.font()
                        font.setItalic(True)
                        item.setFont(font)
    
    def actualizar_contador_eventos(self):
        """Actualiza el contador de eventos activos/totales en el título del panel."""
        if hasattr(self, 'eventos_panel'):
            total = len(self.eventos_riesgo)
            activos = sum(1 for e in self.eventos_riesgo if e.get('activo', True))
            self.eventos_panel.setTitle(f"📈 Eventos de Riesgo Configurados ({activos} activos / {total} totales)")
    
    def actualizar_vista_eventos(self):
        """FASE 6: Actualiza la vista entre empty state, tabla o tarjetas."""
        
        # Actualizar contador
        self.actualizar_contador_eventos()
        
        # Determinar qué vista está activa
        if hasattr(self, 'cards_view_btn') and self.cards_view_btn.isChecked():
            # Vista de tarjetas activa
            self.actualizar_vista_tarjetas()
            if len(self.eventos_riesgo) == 0:
                self.eventos_stack.setCurrentIndex(0)  # Empty state
            else:
                self.eventos_stack.setCurrentIndex(2)  # Tarjetas
        else:
            # Vista de tabla activa (default)
            if hasattr(self, 'eventos_stack'):
                if len(self.eventos_riesgo) == 0:
                    self.eventos_stack.setCurrentIndex(0)  # Empty state
                else:
                    self.eventos_stack.setCurrentIndex(1)  # Tabla
    
    
    def filtrar_eventos_tabla(self, texto):
        """FASE 5: Filtra eventos en la vista activa (tabla o tarjetas)."""
        if not hasattr(self, 'eventos_table'):
            return
        
        # Determinar vista activa
        if hasattr(self, 'eventos_stack'):
            vista_activa = self.eventos_stack.currentIndex()
        else:
            vista_activa = 1  # Default a tabla
        
        # Convertir texto a minúsculas para búsqueda case-insensitive
        texto = texto.lower().strip()
        
        if vista_activa == 1:  # Vista de tabla
            # Si no hay texto, mostrar todas las filas
            if not texto:
                for row in range(self.eventos_table.rowCount()):
                    self.eventos_table.setRowHidden(row, False)
                return
            
            # Filtrar filas que coincidan con el texto
            for row in range(self.eventos_table.rowCount()):
                item = self.eventos_table.item(row, 1)
                if item:
                    nombre_evento = item.text().lower()
                    # Ocultar fila si no coincide con la búsqueda
                    self.eventos_table.setRowHidden(row, texto not in nombre_evento)
        
        elif vista_activa == 2:  # Vista de tarjetas
            # Actualizar tarjetas con filtro (el filtro se aplica en actualizar_vista_tarjetas)
            self.actualizar_vista_tarjetas()
    
    def actualizar_vista_escenarios(self):
        """Actualiza la vista entre empty state y tabla según haya escenarios.
        También resalta visualmente el escenario actualmente seleccionado.
        """
        if hasattr(self, 'scenarios_stack'):
            if len(self.scenarios) == 0:
                self.scenarios_stack.setCurrentIndex(0)  # Mostrar empty state
            else:
                self.scenarios_stack.setCurrentIndex(1)  # Mostrar tabla
        
        # Resaltar visualmente el escenario activo
        if hasattr(self, 'scenarios_table') and hasattr(self, 'current_scenario'):
            for row in range(self.scenarios_table.rowCount()):
                is_active = (row < len(self.scenarios) and 
                            self.current_scenario is not None and 
                            self.scenarios[row] == self.current_scenario)
                
                for col in range(self.scenarios_table.columnCount()):
                    item = self.scenarios_table.item(row, col)
                    if item:
                        if is_active:
                            # Escenario activo: fondo verde claro y texto en negrita
                            item.setBackground(QtGui.QColor("#e8f5e9"))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                            # Agregar indicador ✓ solo en la primera columna
                            if col == 0 and not item.text().startswith("✓ "):
                                item.setText("✓ " + item.text())
                        else:
                            # Escenario no activo: fondo normal
                            item.setBackground(QtGui.QColor("white"))
                            font = item.font()
                            font.setBold(False)
                            item.setFont(font)
                            # Remover indicador ✓ si existe
                            if col == 0 and item.text().startswith("✓ "):
                                item.setText(item.text()[2:])
        
        # Forzar actualización visual sin afectar el layout de la ventana
        if hasattr(self, 'scenarios_table'):
            # Bloquear señales temporalmente para evitar recálculos de layout
            self.scenarios_table.blockSignals(True)
            self.scenarios_table.viewport().update()
            self.scenarios_table.blockSignals(False)
            # Procesar eventos pendientes de pintura sin afectar geometría
            QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
    
    def crear_badge(self, texto, tipo="info"):
        """Crea un badge estilo MercadoLibre para indicar estados o categorías.
        
        Args:
            texto: Texto a mostrar en el badge
            tipo: Tipo de badge - "info", "success", "warning", "error", "destacado"
        
        Returns:
            QLabel configurado como badge
        """
        colores = {
            "info": (MELI_AZUL, "white"),
            "success": (MELI_VERDE, "white"),
            "warning": (MELI_AMARILLO, MELI_GRIS_TEXTO),
            "error": (MELI_ROJO, "white"),
            "destacado": (MELI_AZUL_CORP, "white"),
            "neutral": (MELI_GRIS_FONDO, MELI_GRIS_TEXTO)
        }
        
        bg_color, text_color = colores.get(tipo, colores["info"])
        
        badge = QtWidgets.QLabel(texto.upper())  # Convertir a mayúsculas en Python
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 4px;
                padding: 4px 10px;
                font-size: {UI_FONT_SMALL}pt;
                font-weight: 600;
            }}
        """)
        badge.setAlignment(QtCore.Qt.AlignCenter)
        badge.setFixedHeight(24)
        return badge
    
    def crear_badge_pill(self, texto, color_fondo=None):
        """Crea un badge tipo pill (más redondeado) estilo MercadoLibre.
        
        Args:
            texto: Texto a mostrar
            color_fondo: Color de fondo personalizado (opcional)
        
        Returns:
            QLabel configurado como badge pill
        """
        if color_fondo is None:
            color_fondo = MELI_AZUL_CLARO
            color_texto = MELI_AZUL
        else:
            color_texto = "white"
        
        badge = QtWidgets.QLabel(texto)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {color_fondo};
                color: {color_texto};
                border-radius: 12px;
                padding: 6px 14px;
                font-size: {UI_FONT_BODY}pt;
                font-weight: 500;
            }}
        """)
        badge.setAlignment(QtCore.Qt.AlignCenter)
        return badge
    
    def crear_empty_state(self, parent, texto_principal, texto_secundario, nombre_boton=None, callback=None, icono="📈"):
        """Crea un widget de empty state atractivo estilo MercadoLibre.
        
        Args:
            parent: Widget padre
            texto_principal: Texto principal del empty state
            texto_secundario: Texto descriptivo secundario
            nombre_boton: Texto del botón de acción (opcional)
            callback: Función a llamar al hacer clic en el botón (opcional)
            icono: Emoji o texto del icono (por defecto "📈")
        """
        empty_widget = QtWidgets.QWidget(parent)
        empty_layout = QtWidgets.QVBoxLayout(empty_widget)
        empty_layout.setAlignment(QtCore.Qt.AlignCenter)
        empty_layout.setSpacing(16)  # Reducido de 24 a 16 para optimizar espacio
        empty_layout.setContentsMargins(40, 40, 40, 40)  # Reducido de 60 a 40
        
        # Contenedor circular para el icono (estilo MercadoLibre)
        icon_container = QtWidgets.QWidget()
        icon_container.setFixedSize(120, 120)
        icon_container.setStyleSheet(f"""
            QWidget {{
                background-color: {MELI_AZUL_CLARO};
                border-radius: 60px;
            }}
        """)
        
        icon_container_layout = QtWidgets.QVBoxLayout(icon_container)
        icon_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Icono grande (usando caracteres Unicode o emoji)
        icon_label = QtWidgets.QLabel(icono)
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        icon_label.setStyleSheet(f"""
            font-size: {UI_FONT_ICON}pt;
            color: {MELI_AZUL};
            padding: 0px;
            background-color: transparent;
        """)
        icon_container_layout.addWidget(icon_label)
        
        empty_layout.addWidget(icon_container, 0, QtCore.Qt.AlignCenter)
        
        # Texto principal
        main_text = QtWidgets.QLabel(texto_principal)
        main_text.setAlignment(QtCore.Qt.AlignCenter)
        main_text.setStyleSheet(f"""
            font-size: {UI_FONT_DISPLAY}pt;
            font-weight: 600;
            color: {MELI_GRIS_TEXTO};
            margin-bottom: 8px;
            background-color: transparent;
            border: none;
            padding: 0px;
        """)
        empty_layout.addWidget(main_text)
        
        # Texto secundario
        secondary_text = QtWidgets.QLabel(texto_secundario)
        secondary_text.setAlignment(QtCore.Qt.AlignCenter)
        secondary_text.setWordWrap(True)
        secondary_text.setMaximumWidth(500)
        secondary_text.setStyleSheet(f"""
            font-size: {UI_FONT_BASE}pt;
            color: {MELI_GRIS_SECUNDARIO};
            margin-bottom: 8px;
            line-height: 1.5;
            background-color: transparent;
            border: none;
            padding: 0px;
        """)
        empty_layout.addWidget(secondary_text)
        
        # Botón de acción (si se proporciona)
        if nombre_boton and callback:
            action_button = QtWidgets.QPushButton(nombre_boton)
            action_button.setMinimumHeight(44)
            action_button.setMinimumWidth(200)
            action_button.setMaximumWidth(350)
            action_button.setCursor(QtCore.Qt.PointingHandCursor)
            action_button.clicked.connect(callback)
            self.aplicar_estilo_boton_primario(action_button)
            empty_layout.addWidget(action_button, 0, QtCore.Qt.AlignCenter)
        
        empty_widget.setStyleSheet(f"""
            QWidget {{
                background-color: white;
                border-radius: 12px;
                border: 1px solid {MELI_GRIS_BORDE};
            }}
            QLabel {{
                border: none;
                background-color: transparent;
            }}
        """)
        
        return empty_widget
    
    def crear_vista_tarjetas(self):
        """Crea la vista de tarjetas para eventos con scroll."""
        
        # Scroll area principal
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: #F9F9F9;
            }
        """)
        
        # Contenedor de tarjetas
        self.cards_container = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QGridLayout(self.cards_container)
        self.cards_layout.setContentsMargins(8, 8, 8, 8)
        self.cards_layout.setSpacing(12)
        self.cards_layout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        
        scroll_area.setWidget(self.cards_container)
        
        return scroll_area
    
    def crear_view_toggle_toolbar(self):
        """Crea toolbar con búsqueda y botones para alternar vistas."""
        
        toolbar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)
        
        # Búsqueda (mover referencia aquí)
        layout.addWidget(self.eventos_search)
        
        # Spacer
        layout.addStretch()
        
        # Label "Vista:"
        label = QtWidgets.QLabel("Vista:")
        label.setStyleSheet(f"font-size: {UI_FONT_SMALL}pt; color: #666;")
        layout.addWidget(label)
        
        # Botón Vista Tabla
        self.tabla_view_btn = QtWidgets.QPushButton("📋 Tabla")
        self.tabla_view_btn.setCheckable(True)
        self.tabla_view_btn.setChecked(True)  # Por defecto tabla
        self.tabla_view_btn.setFixedSize(80, 28)
        self.tabla_view_btn.clicked.connect(lambda: self.cambiar_vista_eventos('tabla'))
        layout.addWidget(self.tabla_view_btn)
        
        # Botón Vista Tarjetas
        self.cards_view_btn = QtWidgets.QPushButton("🎴 Tarjetas")
        self.cards_view_btn.setCheckable(True)
        self.cards_view_btn.setFixedSize(90, 28)
        self.cards_view_btn.clicked.connect(lambda: self.cambiar_vista_eventos('cards'))
        layout.addWidget(self.cards_view_btn)
        
        # Estilo para ambos botones
        btn_style = f"""
            QPushButton {{
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background: white;
                padding: 4px 8px;
                font-size: {UI_FONT_SMALL}pt;
            }}
            QPushButton:checked {{
                background: #3483FA;
                color: white;
                border-color: #3483FA;
                font-weight: bold;
            }}
            QPushButton:hover:!checked {{
                background: #F5F5F5;
            }}
        """
        self.tabla_view_btn.setStyleSheet(btn_style)
        self.cards_view_btn.setStyleSheet(btn_style)
        
        # Grupo exclusivo
        self.view_toggle_group = QtWidgets.QButtonGroup()
        self.view_toggle_group.addButton(self.tabla_view_btn)
        self.view_toggle_group.addButton(self.cards_view_btn)
        self.view_toggle_group.setExclusive(True)
        
        return toolbar
    
    def cambiar_vista_eventos(self, tipo):
        """Cambia entre vista de tabla y tarjetas.
        
        Args:
            tipo: 'tabla' o 'cards'
        """
        if tipo == 'tabla':
            # Mostrar tabla
            if len(self.eventos_riesgo) == 0:
                self.eventos_stack.setCurrentIndex(0)  # Empty state
            else:
                self.eventos_stack.setCurrentIndex(1)  # Tabla
            
            # Actualizar botones
            self.tabla_view_btn.setChecked(True)
            self.cards_view_btn.setChecked(False)
        
        elif tipo == 'cards':
            # Actualizar y mostrar vista de tarjetas
            self.actualizar_vista_tarjetas()
            
            if len(self.eventos_riesgo) == 0:
                self.eventos_stack.setCurrentIndex(0)  # Empty state
            else:
                self.eventos_stack.setCurrentIndex(2)  # Tarjetas
            
            # Actualizar botones
            self.tabla_view_btn.setChecked(False)
            self.cards_view_btn.setChecked(True)
    
    def actualizar_vista_tarjetas(self):
        """Actualiza la vista de tarjetas con los eventos actuales."""
        
        # Limpiar tarjetas existentes
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Obtener texto de búsqueda si existe
        filtro = ""
        if hasattr(self, 'eventos_search'):
            filtro = self.eventos_search.text().lower()
        
        # Agregar tarjetas
        col = 0
        row = 0
        max_cols = self.calcular_columnas_tarjetas()
        
        for evento in self.eventos_riesgo:
            # Filtrar por búsqueda
            if filtro and filtro not in evento['nombre'].lower():
                continue
            
            # Crear tarjeta con iconos
            card = EventCard(evento, self, iconos=self.iconos)
            
            # Conectar señales
            card.editRequested.connect(self.on_edit_card)
            card.duplicateRequested.connect(self.on_dup_card)
            card.deleteRequested.connect(self.on_del_card)
            card.activeChanged.connect(self.on_card_active_changed)
            
            # Aplicar estilo inicial según estado activo
            activo = evento.get('activo', True)
            card.aplicar_estilo_activo(activo)
            
            # Agregar al grid
            self.cards_layout.addWidget(card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def calcular_columnas_tarjetas(self):
        """Calcula cuántas columnas de tarjetas caben según el ancho disponible."""
        if hasattr(self, 'eventos_panel'):
            width = self.eventos_panel.width()
            card_width = 260  # Ancho de tarjeta Material Design
            spacing = 16  # Espaciado aumentado para mejor breathing room
            margin = 20  # Márgenes aumentados
            
            disponible = width - margin
            cols = max(1, disponible // (card_width + spacing))
            return min(cols, 5)  # Máximo 5 columnas
        return 3  # Default
    
    def on_edit_card(self, evento_data):
        """Edita un evento desde la tarjeta directamente."""
        # Buscar índice del evento por ID o nombre
        evento_id = evento_data.get('id')
        evento_nombre = evento_data.get('nombre')
        
        for i, evt in enumerate(self.eventos_riesgo):
            # Buscar por ID preferentemente, o por nombre como fallback
            if (evento_id and evt.get('id') == evento_id) or \
               (not evento_id and evt.get('nombre') == evento_nombre):
                # Editar directamente sin necesidad de selección
                self.editar_evento_popup(new=False, row=i)
                break
    
    def on_dup_card(self, evento_data):
        """Duplica un evento desde la tarjeta directamente."""
        evento_id = evento_data.get('id')
        evento_nombre = evento_data.get('nombre')
        
        for i, evt in enumerate(self.eventos_riesgo):
            if (evento_id and evt.get('id') == evento_id) or \
               (not evento_id and evt.get('nombre') == evento_nombre):
                # Duplicar directamente este evento específico
                import copy
                evento_duplicado = copy.deepcopy(evt)
                evento_duplicado['id'] = str(uuid.uuid4())
                evento_duplicado['nombre'] = f"{evt['nombre']} (Copia)"
                
                # Agregar a la lista
                self.eventos_riesgo.append(evento_duplicado)
                
                # Agregar a la tabla
                row_position = self.eventos_table.rowCount()
                self.eventos_table.insertRow(row_position)
                # Columna 0: checkbox (mantener estado del original)
                activo = evento_duplicado.get('activo', True)
                self.eventos_table.setCellWidget(row_position, 0, self.crear_checkbox_activo(row_position, activo=activo))
                # Columna 1: nombre
                self.eventos_table.setItem(row_position, 1, self.crear_table_item_con_wrap(evento_duplicado['nombre']))
                
                # Actualizar vista
                self.actualizar_vista_eventos()
                self.forzar_ancho_columna_activo()  # Mantener ancho compacto
                n_vinc = len(evento_duplicado.get('vinculos', []))
                if n_vinc > 0:
                    self.statusBar().showMessage(
                        f"Evento '{evt['nombre']}' duplicado ({n_vinc} vínculo(s) heredado(s))", 4000)
                else:
                    self.statusBar().showMessage(f"Evento '{evt['nombre']}' duplicado exitosamente", 3000)
                break
    
    def on_card_active_changed(self, evento_data, activo):
        """Callback cuando cambia el estado activo/inactivo desde una tarjeta.
        
        Args:
            evento_data: Datos del evento
            activo: Nuevo estado (True/False)
        """
        evento_id = evento_data.get('id')
        
        # Buscar y actualizar en el modelo principal
        for i, evt in enumerate(self.eventos_riesgo):
            if evt.get('id') == evento_id:
                self.eventos_riesgo[i]['activo'] = activo
                
                # Actualizar checkbox en la tabla también
                checkbox_widget = self.eventos_table.cellWidget(i, 0)
                if checkbox_widget:
                    # Encontrar el checkbox dentro del widget contenedor
                    checkbox = checkbox_widget.findChild(QtWidgets.QCheckBox)
                    if checkbox:
                        checkbox.blockSignals(True)  # Evitar loop infinito
                        checkbox.setChecked(activo)
                        checkbox.blockSignals(False)
                
                # Aplicar estilo en la tabla
                self.aplicar_estilo_fila_evento(i)
                
                # Actualizar contador
                self.actualizar_contador_eventos()
                
                # Mensaje en status bar
                nombre = evento_data.get('nombre', 'Evento')
                estado_txt = "activado" if activo else "desactivado"
                self.statusBar().showMessage(f"Evento '{nombre}' {estado_txt}", 2000)
                break
    
    def on_del_card(self, evento_data):
        """Elimina un evento desde la tarjeta."""
        # Confirmar
        respuesta = QtWidgets.QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Está seguro de eliminar el evento '{evento_data['nombre']}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if respuesta == QtWidgets.QMessageBox.Yes:
            evento_id = evento_data.get('id')
            evento_nombre = evento_data.get('nombre')
            
            # Buscar y eliminar
            for i, evt in enumerate(self.eventos_riesgo):
                if (evento_id and evt.get('id') == evento_id) or \
                   (not evento_id and evt.get('nombre') == evento_nombre):
                    del self.eventos_riesgo[i]
                    self.eventos_table.removeRow(i)
                    if evento_id:
                        self.limpiar_vinculos_huerfanos({evento_id})
                    self.reconstruir_checkboxes_eventos()
                    self.actualizar_vista_eventos()
                    break
    
    def agregar_animacion_hover_boton(self, boton):
        """Agrega animación sutil de elevación al hacer hover en un botón."""
        try:
            from PyQt5.QtWidgets import QGraphicsDropShadowEffect
            from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty
            from PyQt5.QtGui import QColor
            
            # Crear efecto de sombra para simular elevación
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(8)
            shadow.setXOffset(0)
            shadow.setYOffset(2)
            shadow.setColor(QColor(0, 0, 0, 40))
            boton.setGraphicsEffect(shadow)
            
            # Guardar referencia al efecto
            boton._shadow_effect = shadow
            
            # Eventos de hover personalizados
            original_enter = boton.enterEvent
            original_leave = boton.leaveEvent
            
            def custom_enter(event):
                # Animar sombra al entrar (solo si está habilitado)
                if boton.isEnabled() and hasattr(boton, '_shadow_effect'):
                    boton._shadow_effect.setBlurRadius(12)
                    boton._shadow_effect.setYOffset(4)
                if original_enter:
                    original_enter(event)
            
            def custom_leave(event):
                # Restaurar sombra al salir
                if hasattr(boton, '_shadow_effect'):
                    boton._shadow_effect.setBlurRadius(8)
                    boton._shadow_effect.setYOffset(2)
                if original_leave:
                    original_leave(event)
            
            boton.enterEvent = custom_enter
            boton.leaveEvent = custom_leave
            
        except Exception as e:
            print(f"No se pudo aplicar animación de hover: {e}")
    
    def agregar_animacion_fade_in(self, widget, duracion=300):
        """Agrega animación de fade-in a un widget."""
        try:
            from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
            from PyQt5.QtWidgets import QGraphicsOpacityEffect
            
            # Crear efecto de opacidad
            opacity_effect = QGraphicsOpacityEffect()
            widget.setGraphicsEffect(opacity_effect)
            
            # Crear animación
            animation = QPropertyAnimation(opacity_effect, b"opacity")
            animation.setDuration(duracion)
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
            animation.setEasingCurve(QEasingCurve.InOutQuad)
            
            # Iniciar animación
            animation.start()
            
            # Guardar referencia para evitar garbage collection
            widget._fade_animation = animation
            widget._opacity_effect = opacity_effect
            
        except Exception as e:
            print(f"No se pudo aplicar fade-in: {e}")
    
    def agregar_animacion_card_hover(self, card):
        """Agrega animación de elevación al hacer hover en una card."""
        try:
            from PyQt5.QtWidgets import QGraphicsDropShadowEffect
            from PyQt5.QtGui import QColor
            
            # Ya tiene sombra de aplicar_estilo_card_moderno, sólo agregamos comportamiento hover
            original_enter = card.enterEvent if hasattr(card, 'enterEvent') else None
            original_leave = card.leaveEvent if hasattr(card, 'leaveEvent') else None
            
            def custom_enter(event):
                # Aumentar sombra al entrar
                effect = card.graphicsEffect()
                if effect and isinstance(effect, QGraphicsDropShadowEffect):
                    effect.setBlurRadius(20)
                    effect.setYOffset(4)
                if original_enter:
                    original_enter(event)
            
            def custom_leave(event):
                # Restaurar sombra al salir
                effect = card.graphicsEffect()
                if effect and isinstance(effect, QGraphicsDropShadowEffect):
                    effect.setBlurRadius(15)
                    effect.setYOffset(2)
                if original_leave:
                    original_leave(event)
            
            card.enterEvent = custom_enter
            card.leaveEvent = custom_leave
            
        except Exception as e:
            print(f"No se pudo aplicar animación de card: {e}")
    
    def agregar_tab_animado(self, tab_widget, widget, label):
        """Agrega un tab con animación fade-in sutil."""
        try:
            # Agregar el tab normalmente
            tab_widget.addTab(widget, label)
            
            # Agregar fade-in muy sutil al widget (solo si es el primer tab o recién agregado)
            self.agregar_animacion_fade_in(widget, duracion=250)
        except Exception as e:
            # Si falla la animación, agregar sin animación
            tab_widget.addTab(widget, label)
    
    def aplicar_estilo_progress_bar_moderno(self):
        """Aplica estilo moderno MercadoLibre y animado a la barra de progreso."""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {MELI_GRIS_FONDO};
                    border: 1px solid {MELI_GRIS_BORDE};
                    border-radius: 10px;
                    text-align: center;
                    font-size: {UI_FONT_NORMAL}pt;
                    font-weight: 600;
                    color: {MELI_GRIS_TEXTO};
                    height: 36px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 {MELI_VERDE},
                        stop:0.5 #00D45A,
                        stop:1 {MELI_VERDE}
                    );
                    border-radius: 9px;
                    margin: 1px;
                }}
            """)
            
            # Configurar animación suave
            self.progress_bar.setMinimumHeight(36)
            
            # Timer para animación de pulso (opcional)
            if not hasattr(self, 'progress_animation_timer'):
                self.progress_animation_timer = QtCore.QTimer()
                self.progress_animation_timer.timeout.connect(self._animar_progress_bar)
                self.progress_animation_phase = 0
    
    def _animar_progress_bar(self):
        """Anima la barra de progreso con un efecto de pulso sutil."""
        if hasattr(self, 'progress_bar') and self.progress_bar.value() > 0 and self.progress_bar.value() < 100:
            self.progress_animation_phase = (self.progress_animation_phase + 1) % 100
            
            # Efecto de gradiente animado
            if self.progress_animation_phase % 2 == 0:
                self.progress_bar.setStyleSheet(f"""
                    QProgressBar {{
                        background-color: {MELI_GRIS_FONDO};
                        border: 1px solid {MELI_GRIS_BORDE};
                        border-radius: 10px;
                        text-align: center;
                        font-size: {UI_FONT_NORMAL}pt;
                        font-weight: 600;
                        color: {MELI_GRIS_TEXTO};
                        height: 36px;
                    }}
                    QProgressBar::chunk {{
                        background: qlineargradient(
                            x1:0, y1:0, x2:1, y2:0,
                            stop:0 {MELI_VERDE},
                            stop:0.5 #00E064,
                            stop:1 {MELI_VERDE}
                        );
                        border-radius: 9px;
                        margin: 1px;
                    }}
                """)
    
    def crear_progress_bar_estilo_meli(self, color_chunk=None, altura=36):
        """Crea una barra de progreso estilo MercadoLibre personalizable.
        
        Args:
            color_chunk: Color del chunk/relleno (por defecto MELI_VERDE)
            altura: Altura de la barra en pixels (por defecto 36)
        
        Returns:
            QProgressBar configurado con estilo MercadoLibre
        """
        if color_chunk is None:
            color_chunk = MELI_VERDE
        
        progress = QtWidgets.QProgressBar()
        progress.setMaximum(100)
        progress.setValue(0)
        progress.setTextVisible(True)
        progress.setMinimumHeight(altura)
        
        progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {MELI_GRIS_FONDO};
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: {altura // 4}px;
                text-align: center;
                font-size: {UI_FONT_BODY}pt;
                font-weight: 600;
                color: {MELI_GRIS_TEXTO};
            }}
            QProgressBar::chunk {{
                background-color: {color_chunk};
                border-radius: {altura // 4 - 1}px;
                margin: 1px;
            }}
        """)
        
        return progress
    
    def crear_metric_card(self, titulo, valor, subtitulo=None, icono=None, color_acento=None):
        """Crea una card para mostrar métricas clave estilo MercadoLibre.
        
        Args:
            titulo: Título de la métrica (ej: "Pérdida Promedio")
            valor: Valor principal a mostrar (ej: "$1,234,567")
            subtitulo: Texto descriptivo adicional (opcional)
            icono: Emoji o texto del icono (opcional)
            color_acento: Color de acento para el icono (por defecto MELI_AZUL)
        
        Returns:
            QFrame configurado como metric card
        """
        if color_acento is None:
            color_acento = MELI_AZUL
        
        # Card principal
        card = QtWidgets.QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 12px;
                padding: 0px;
            }}
            QFrame:hover {{
                border-color: {MELI_AZUL};
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            }}
        """)
        
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)
        
        # Header con icono y título
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(12)
        
        if icono:
            # Contenedor circular para el icono
            icon_container = QtWidgets.QLabel(icono)
            icon_container.setAlignment(QtCore.Qt.AlignCenter)
            icon_container.setFixedSize(48, 48)
            icon_container.setStyleSheet(f"""
                QLabel {{
                    background-color: {color_acento}22;
                    border-radius: 24px;
                    font-size: {UI_FONT_XLARGE}pt;
                    color: {color_acento};
                }}
            """)
            header_layout.addWidget(icon_container)
        
        # Título
        titulo_label = QtWidgets.QLabel(titulo)
        titulo_label.setStyleSheet(f"""
            QLabel {{
                font-size: {UI_FONT_NORMAL}pt;
                font-weight: 500;
                color: {MELI_GRIS_SECUNDARIO};
                background-color: transparent;
            }}
        """)
        titulo_label.setWordWrap(True)
        header_layout.addWidget(titulo_label, 1)
        
        card_layout.addLayout(header_layout)
        
        # Valor principal (grande y destacado)
        valor_label = QtWidgets.QLabel(str(valor))
        valor_label.setStyleSheet(f"""
            QLabel {{
                font-size: {UI_FONT_HERO}pt;
                font-weight: 600;
                color: {MELI_GRIS_TEXTO};
                background-color: transparent;
            }}
        """)
        valor_label.setWordWrap(True)
        card_layout.addWidget(valor_label)
        
        # Subtítulo (si existe)
        if subtitulo:
            subtitulo_label = QtWidgets.QLabel(subtitulo)
            subtitulo_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {UI_FONT_BODY}pt;
                    color: {MELI_GRIS_SECUNDARIO};
                    background-color: transparent;
                }}
            """)
            subtitulo_label.setWordWrap(True)
            card_layout.addWidget(subtitulo_label)
        
        card_layout.addStretch()
        
        return card
    
    def crear_icono_circular(self, texto, color_fondo=None, color_texto=None, tamaño=56):
        """Crea un widget con icono circular estilo MercadoLibre.
        
        Args:
            texto: Texto o emoji a mostrar
            color_fondo: Color de fondo del círculo (por defecto MELI_AZUL_CLARO)
            color_texto: Color del texto/icono (por defecto MELI_AZUL)
            tamaño: Tamaño del círculo en pixels (por defecto 56)
        
        Returns:
            QLabel configurado como icono circular
        """
        if color_fondo is None:
            color_fondo = MELI_AZUL_CLARO
        if color_texto is None:
            color_texto = MELI_AZUL
        
        icono = QtWidgets.QLabel(texto)
        icono.setAlignment(QtCore.Qt.AlignCenter)
        icono.setFixedSize(tamaño, tamaño)
        icono.setStyleSheet(f"""
            QLabel {{
                background-color: {color_fondo};
                border-radius: {tamaño // 2}px;
                font-size: {tamaño // 2}px;
                color: {color_texto};
            }}
        """)
        
        return icono
    
    def crear_card_container(self, titulo=None, contenido_widget=None, acciones=None):
        """Crea un contenedor card estilo MercadoLibre para envolver contenido.
        
        Args:
            titulo: Título opcional de la card
            contenido_widget: Widget a mostrar en el contenido (opcional)
            acciones: Lista de botones para mostrar en el header (opcional)
        
        Returns:
            Tupla (card, content_layout) donde content_layout es donde agregar contenido
        """
        # Card principal
        card = QtWidgets.QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 12px;
            }}
        """)
        
        card_main_layout = QtWidgets.QVBoxLayout(card)
        card_main_layout.setContentsMargins(0, 0, 0, 0)
        card_main_layout.setSpacing(0)
        
        # Header (si hay título o acciones)
        if titulo or acciones:
            header = QtWidgets.QWidget()
            header.setStyleSheet("background-color: transparent;")
            header_layout = QtWidgets.QHBoxLayout(header)
            header_layout.setContentsMargins(20, 16, 20, 16)
            header_layout.setSpacing(12)
            
            if titulo:
                titulo_label = QtWidgets.QLabel(titulo)
                titulo_label.setStyleSheet(f"""
                    QLabel {{
                        font-size: {UI_FONT_SUBTITLE}pt;
                        font-weight: 600;
                        color: {MELI_GRIS_TEXTO};
                        background-color: transparent;
                    }}
                """)
                header_layout.addWidget(titulo_label)
            
            header_layout.addStretch()
            
            if acciones:
                for accion in acciones:
                    header_layout.addWidget(accion)
            
            card_main_layout.addWidget(header)
            
            # Divider
            divider = self.crear_divider()
            card_main_layout.addWidget(divider)
        
        # Contenido
        content_container = QtWidgets.QWidget()
        content_container.setStyleSheet("background-color: transparent;")
        content_layout = QtWidgets.QVBoxLayout(content_container)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)
        
        if contenido_widget:
            content_layout.addWidget(contenido_widget)
        
        card_main_layout.addWidget(content_container)
        
        return card, content_layout
    
    def crear_divider(self, orientacion="horizontal", color=None):
        """Crea un separador visual estilo MercadoLibre.
        
        Args:
            orientacion: "horizontal" o "vertical"
            color: Color del divider (por defecto MELI_GRIS_BORDE)
        
        Returns:
            QFrame configurado como divider
        """
        if color is None:
            color = MELI_GRIS_BORDE
        
        divider = QtWidgets.QFrame()
        
        if orientacion == "horizontal":
            divider.setFrameShape(QtWidgets.QFrame.HLine)
            divider.setFixedHeight(1)
        else:
            divider.setFrameShape(QtWidgets.QFrame.VLine)
            divider.setFixedWidth(1)
        
        divider.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border: none;
            }}
        """)
        
        return divider
    
    def crear_seccion_titulo(self, texto, icono=None, nivel=1):
        """Crea un título de sección estilo MercadoLibre.
        
        Args:
            texto: Texto del título
            icono: Emoji o icono opcional
            nivel: Nivel del título (1=principal, 2=secundario, 3=terciario)
        
        Returns:
            QWidget con el título formateado
        """
        container = QtWidgets.QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Configuración según nivel
        sizes = {
            1: {"font": 24, "weight": 600, "icon": 32},
            2: {"font": 20, "weight": 600, "icon": 28},
            3: {"font": 16, "weight": 600, "icon": 24}
        }
        
        config = sizes.get(nivel, sizes[1])
        
        if icono:
            icon_label = QtWidgets.QLabel(icono)
            icon_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {config['icon']}px;
                    background-color: transparent;
                }}
            """)
            layout.addWidget(icon_label)
        
        titulo = QtWidgets.QLabel(texto)
        titulo.setStyleSheet(f"""
            QLabel {{
                font-size: {config['font']}px;
                font-weight: {config['weight']};
                color: {MELI_GRIS_TEXTO};
                background-color: transparent;
            }}
        """)
        layout.addWidget(titulo)
        layout.addStretch()
        
        return container
    
    def crear_contador_badge(self, numero):
        """Crea un badge contador estilo MercadoLibre (para pestañas, notificaciones).
        
        Args:
            numero: Número a mostrar en el contador
        
        Returns:
            QLabel configurado como contador badge
        """
        badge = QtWidgets.QLabel(str(numero))
        badge.setAlignment(QtCore.Qt.AlignCenter)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {MELI_ROJO};
                color: white;
                border-radius: 10px;
                padding: 2px 8px;
                font-size: {UI_FONT_XSMALL}pt;
                font-weight: 700;
                min-width: 20px;
            }}
        """)
        return badge
    
    def aplicar_estilo_tab_widget_graficos(self, tab_widget):
        """Aplica estilo compacto a las pestañas de gráficos con width adaptable."""
        tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 8px;
                background-color: white;
                padding: 0px;
            }}
            
            QTabBar::tab {{
                background-color: {MELI_GRIS_FONDO};
                color: {MELI_GRIS_SECUNDARIO};
                border: 1px solid {MELI_GRIS_BORDE};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 12px;
                margin-right: 2px;
                font-size: {UI_FONT_XSMALL}pt;
                font-weight: 500;
            }}
            
            QTabBar::tab:hover {{
                background-color: white;
                color: {MELI_GRIS_TEXTO};
            }}
            
            QTabBar::tab:selected {{
                background-color: white;
                color: {MELI_AZUL};
                border-bottom: 3px solid {MELI_AZUL};
                font-weight: 600;
            }}
            
            QTabBar::tab:!selected {{
                margin-top: 3px;
            }}
        """)
    
    def aplicar_estilo_tab_widget_moderno(self, tab_widget):
        """Aplica estilo moderno MercadoLibre a un QTabWidget.
        
        Args:
            tab_widget: QTabWidget al que aplicar el estilo
        """
        tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 8px;
                background-color: white;
                padding: 0px;
            }}
            
            QTabBar::tab {{
                background-color: {MELI_GRIS_FONDO};
                color: {MELI_GRIS_SECUNDARIO};
                border: 1px solid {MELI_GRIS_BORDE};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 12px 24px;
                margin-right: 2px;
                font-size: {UI_FONT_NORMAL}pt;
                font-weight: 500;
                min-width: 60px;
            }}
            
            QTabBar::tab:hover {{
                background-color: white;
                color: {MELI_GRIS_TEXTO};
            }}
            
            QTabBar::tab:selected {{
                background-color: white;
                color: {MELI_AZUL};
                border-bottom: 3px solid {MELI_AZUL};
                font-weight: 600;
            }}
            
            QTabBar::tab:!selected {{
                margin-top: 3px;
            }}
        """)
    
    def crear_info_banner(self, mensaje, tipo="info", icono=None):
        """Crea un banner informativo estilo MercadoLibre.
        
        Args:
            mensaje: Mensaje a mostrar
            tipo: Tipo de banner - "info", "success", "warning", "error"
            icono: Emoji o icono opcional
        
        Returns:
            QFrame configurado como banner
        """
        colores = {
            "info": (f"{MELI_AZUL}15", MELI_AZUL, "ℹ️"),
            "success": (f"{MELI_VERDE}15", MELI_VERDE, "✓"),
            "warning": (f"{MELI_AMARILLO}30", MELI_GRIS_TEXTO, "⚠️"),
            "error": (f"{MELI_ROJO}15", MELI_ROJO, "✕")
        }
        
        bg_color, border_color, icono_default = colores.get(tipo, colores["info"])
        if icono is None:
            icono = icono_default
        
        banner = QtWidgets.QFrame()
        banner.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-left: 4px solid {border_color};
                border-radius: 6px;
                padding: 0px;
            }}
        """)
        
        layout = QtWidgets.QHBoxLayout(banner)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Icono
        icon_label = QtWidgets.QLabel(icono)
        icon_label.setStyleSheet(f"""
            font-size: {UI_FONT_LARGE}pt;
            color: {border_color};
            background-color: transparent;
        """)
        layout.addWidget(icon_label)
        
        # Mensaje
        mensaje_label = QtWidgets.QLabel(mensaje)
        mensaje_label.setWordWrap(True)
        mensaje_label.setStyleSheet(f"""
            font-size: {UI_FONT_NORMAL}pt;
            color: {MELI_GRIS_TEXTO};
            background-color: transparent;
        """)
        layout.addWidget(mensaje_label, 1)
        
        return banner
    
    def crear_spinner_widget(self, tamaño=48, color=None, mensaje=None):
        """Crea un widget spinner de carga estilo MercadoLibre.
        
        Args:
            tamaño: Tamaño del spinner en pixels (por defecto 48)
            color: Color del spinner (por defecto MELI_AZUL)
            mensaje: Mensaje opcional a mostrar debajo del spinner
        
        Returns:
            QWidget con el spinner y mensaje opcional
        """
        if color is None:
            color = MELI_AZUL
        
        container = QtWidgets.QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QtWidgets.QVBoxLayout(container)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setSpacing(16)
        
        # Spinner (usando QLabel con animación de puntos)
        spinner_label = QtWidgets.QLabel("●●●")
        spinner_label.setAlignment(QtCore.Qt.AlignCenter)
        spinner_label.setFixedHeight(tamaño)
        spinner_label.setStyleSheet(f"""
            QLabel {{
                font-size: {tamaño//2}px;
                color: {color};
                background-color: transparent;
                letter-spacing: 8px;
            }}
        """)
        
        # Animación con timer (alternando puntos)
        spinner_states = ["●○○", "○●○", "○○●", "○●○"]
        spinner_index = [0]
        
        def update_spinner():
            spinner_index[0] = (spinner_index[0] + 1) % len(spinner_states)
            spinner_label.setText(spinner_states[spinner_index[0]])
        
        timer = QtCore.QTimer()
        timer.timeout.connect(update_spinner)
        timer.start(300)  # Actualizar cada 300ms
        
        # Guardar referencia para evitar garbage collection
        spinner_label._timer = timer
        
        layout.addWidget(spinner_label)
        
        # Mensaje opcional
        if mensaje:
            mensaje_label = QtWidgets.QLabel(mensaje)
            mensaje_label.setAlignment(QtCore.Qt.AlignCenter)
            mensaje_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {UI_FONT_NORMAL}pt;
                    color: {MELI_GRIS_SECUNDARIO};
                    background-color: transparent;
                }}
            """)
            mensaje_label.setWordWrap(True)
            layout.addWidget(mensaje_label)
        
        return container
    
    def mostrar_loading_overlay(self, mensaje="Cargando..."):
        """Muestra un overlay de carga sobre la ventana principal.
        
        Args:
            mensaje: Mensaje a mostrar en el overlay
        """
        # Crear overlay
        self.loading_overlay = QtWidgets.QWidget(self)
        self.loading_overlay.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(0, 0, 0, 0.5);
            }}
        """)
        self.loading_overlay.setGeometry(self.rect())
        
        # Layout del overlay
        overlay_layout = QtWidgets.QVBoxLayout(self.loading_overlay)
        overlay_layout.setAlignment(QtCore.Qt.AlignCenter)
        
        # Card de carga
        loading_card = QtWidgets.QFrame()
        loading_card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 12px;
                padding: 40px;
            }}
        """)
        
        card_layout = QtWidgets.QVBoxLayout(loading_card)
        card_layout.setAlignment(QtCore.Qt.AlignCenter)
        card_layout.setSpacing(20)
        
        # Spinner
        spinner = self.crear_spinner_widget(tamaño=64, mensaje=mensaje)
        card_layout.addWidget(spinner)
        
        overlay_layout.addWidget(loading_card)
        
        self.loading_overlay.show()
        self.loading_overlay.raise_()
    
    def ocultar_loading_overlay(self):
        """Oculta el overlay de carga."""
        if hasattr(self, 'loading_overlay') and self.loading_overlay:
            self.loading_overlay.hide()
            self.loading_overlay.deleteLater()
            self.loading_overlay = None
    
    def crear_dialogo_moderno(self, titulo, mensaje, tipo="info", botones=None):
        """Crea un diálogo modal moderno estilo MercadoLibre.
        
        Args:
            titulo: Título del diálogo
            mensaje: Mensaje principal
            tipo: Tipo - "info", "success", "warning", "error", "question"
            botones: Lista de tuplas (texto, callback) o None para usar botones por defecto
        
        Returns:
            QDialog configurado
        """
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(titulo)
        dialog.setModal(True)
        dialog.setMinimumWidth(450)
        
        # Layout principal
        main_layout = QtWidgets.QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header con color según tipo
        colores = {
            "info": MELI_AZUL,
            "success": MELI_VERDE,
            "warning": MELI_AMARILLO,
            "error": MELI_ROJO,
            "question": MELI_AZUL
        }
        
        iconos = {
            "info": "ℹ️",
            "success": "✓",
            "warning": "⚠️",
            "error": "✕",
            "question": "❓"
        }
        
        color_header = colores.get(tipo, MELI_AZUL)
        icono = iconos.get(tipo, "ℹ️")
        
        # Header
        header = QtWidgets.QWidget()
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {color_header};
                padding: 20px;
            }}
        """)
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setSpacing(12)
        
        # Icono
        icon_label = QtWidgets.QLabel(icono)
        icon_label.setStyleSheet(f"""
            font-size: {UI_FONT_HERO}pt;
            color: white;
            background-color: transparent;
        """)
        header_layout.addWidget(icon_label)
        
        # Título
        titulo_label = QtWidgets.QLabel(titulo)
        titulo_label.setStyleSheet(f"""
            font-size: {UI_FONT_LARGE}pt;
            font-weight: 600;
            color: white;
            background-color: transparent;
        """)
        header_layout.addWidget(titulo_label, 1)
        
        main_layout.addWidget(header)
        
        # Contenido
        content = QtWidgets.QWidget()
        content.setStyleSheet("background-color: white;")
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)
        
        # Mensaje
        mensaje_label = QtWidgets.QLabel(mensaje)
        mensaje_label.setWordWrap(True)
        mensaje_label.setStyleSheet(f"""
            font-size: {UI_FONT_NORMAL}pt;
            color: {MELI_GRIS_TEXTO};
            line-height: 1.6;
            background-color: transparent;
        """)
        content_layout.addWidget(mensaje_label)
        
        # Botones
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.addStretch()
        
        if botones is None:
            # Botón por defecto: Aceptar
            btn_ok = QtWidgets.QPushButton("Aceptar")
            btn_ok.setMinimumHeight(40)
            btn_ok.setMinimumWidth(120)
            btn_ok.setCursor(QtCore.Qt.PointingHandCursor)
            self.aplicar_estilo_boton_primario(btn_ok)
            btn_ok.clicked.connect(dialog.accept)
            buttons_layout.addWidget(btn_ok)
        else:
            for texto, callback in botones:
                btn = QtWidgets.QPushButton(texto)
                btn.setMinimumHeight(40)
                btn.setMinimumWidth(120)
                btn.setCursor(QtCore.Qt.PointingHandCursor)
                
                # Estilo según si es botón primario o secundario
                if "cancelar" in texto.lower() or "no" in texto.lower():
                    self.aplicar_estilo_boton_secundario(btn)
                else:
                    self.aplicar_estilo_boton_primario(btn)
                
                btn.clicked.connect(callback)
                buttons_layout.addWidget(btn)
        
        content_layout.addLayout(buttons_layout)
        main_layout.addWidget(content)
        
        # Estilo del diálogo
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: white;
                border-radius: 12px;
            }}
        """)
        
        return dialog
    
    def aplicar_tooltip_moderno(self, widget, texto):
        """Aplica un tooltip estilizado a un widget.
        
        Args:
            widget: Widget al que aplicar el tooltip
            texto: Texto del tooltip
        """
        widget.setToolTip(texto)
        widget.setStyleSheet(widget.styleSheet() + f"""
            QToolTip {{
                background-color: {MELI_GRIS_TEXTO};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: {UI_FONT_BODY}pt;
                opacity: 230;
            }}
        """)
    
    def aplicar_estilo_menu_contextual(self, menu):
        """Aplica estilo moderno MercadoLibre a un QMenu contextual.
        
        Args:
            menu: QMenu al que aplicar el estilo
        """
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: white;
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 8px;
                padding: 8px 0px;
            }}
            
            QMenu::item {{
                background-color: transparent;
                padding: 10px 20px 10px 16px;
                color: {MELI_GRIS_TEXTO};
                font-size: {UI_FONT_NORMAL}pt;
            }}
            
            QMenu::item:selected {{
                background-color: {MELI_AZUL_CLARO};
                color: {MELI_AZUL};
            }}
            
            QMenu::item:disabled {{
                color: {MELI_GRIS_SECUNDARIO};
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {MELI_GRIS_BORDE};
                margin: 8px 0px;
            }}
            
            QMenu::icon {{
                padding-left: 10px;
            }}
        """)
    
    def crear_skeleton_loader(self, ancho=None, alto=40, tipo="rect"):
        """Crea un skeleton loader para indicar carga de contenido.
        
        Args:
            ancho: Ancho del skeleton (None para expandir)
            alto: Alto del skeleton en pixels
            tipo: Tipo - "rect" (rectángulo), "circle" (círculo), "text" (línea de texto)
        
        Returns:
            QFrame configurado como skeleton
        """
        skeleton = QtWidgets.QFrame()
        
        if tipo == "circle":
            skeleton.setFixedSize(alto, alto)
            radius = alto // 2
            skeleton.setStyleSheet(f"""
                QFrame {{
                    background-color: {MELI_GRIS_FONDO};
                    border-radius: {radius}px;
                }}
            """)
        elif tipo == "text":
            if ancho:
                skeleton.setFixedSize(ancho, alto)
            else:
                skeleton.setMinimumHeight(alto)
            skeleton.setStyleSheet(f"""
                QFrame {{
                    background-color: {MELI_GRIS_FONDO};
                    border-radius: 4px;
                }}
            """)
        else:  # rect
            if ancho:
                skeleton.setFixedSize(ancho, alto)
            else:
                skeleton.setMinimumHeight(alto)
            skeleton.setStyleSheet(f"""
                QFrame {{
                    background-color: {MELI_GRIS_FONDO};
                    border-radius: 8px;
                }}
            """)
        
        # Animación de pulso
        skeleton._opacity = 1.0
        skeleton._direction = -1
        
        def animate_skeleton():
            skeleton._opacity += skeleton._direction * 0.05
            if skeleton._opacity <= 0.3:
                skeleton._direction = 1
            elif skeleton._opacity >= 1.0:
                skeleton._direction = -1
            
            # Actualizar opacidad (simulado con cambio de color)
            opacity_value = int(255 * skeleton._opacity)
            color_hex = f"#{opacity_value:02x}{opacity_value:02x}{opacity_value:02x}"
            
            if tipo == "circle":
                radius = alto // 2
                skeleton.setStyleSheet(f"""
                    QFrame {{
                        background-color: {MELI_GRIS_FONDO};
                        border-radius: {radius}px;
                        opacity: {skeleton._opacity};
                    }}
                """)
            else:
                border_radius = 4 if tipo == "text" else 8
                skeleton.setStyleSheet(f"""
                    QFrame {{
                        background-color: {MELI_GRIS_FONDO};
                        border-radius: {border_radius}px;
                        opacity: {skeleton._opacity};
                    }}
                """)
        
        timer = QtCore.QTimer()
        timer.timeout.connect(animate_skeleton)
        timer.start(50)
        
        skeleton._timer = timer
        
        return skeleton
    
    def crear_skeleton_card(self):
        """Crea un skeleton card completo para simular carga de una metric card.
        
        Returns:
            QWidget con skeleton de una card
        """
        card = QtWidgets.QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        
        layout = QtWidgets.QVBoxLayout(card)
        layout.setSpacing(12)
        
        # Header con círculo y línea
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(12)
        
        circle_skeleton = self.crear_skeleton_loader(tipo="circle", alto=48)
        header_layout.addWidget(circle_skeleton)
        
        title_skeleton = self.crear_skeleton_loader(ancho=120, alto=20, tipo="text")
        header_layout.addWidget(title_skeleton)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Valor grande
        value_skeleton = self.crear_skeleton_loader(ancho=200, alto=32, tipo="text")
        layout.addWidget(value_skeleton)
        
        # Subtítulo
        subtitle_skeleton = self.crear_skeleton_loader(ancho=150, alto=16, tipo="text")
        layout.addWidget(subtitle_skeleton)
        
        layout.addStretch()
        
        return card
    
    def actualizar_status_bar_moderno(self, mensaje, tipo="info", duracion=0):
        """Actualiza la barra de estado con estilo moderno.
        
        Args:
            mensaje: Mensaje a mostrar
            tipo: Tipo - "info", "success", "warning", "error"
            duracion: Duración en ms (0 para permanente)
        """
        if not hasattr(self, 'statusBar'):
            return
        
        colores = {
            "info": (MELI_AZUL, "ℹ️"),
            "success": (MELI_VERDE, "✓"),
            "warning": (MELI_AMARILLO, "⚠️"),
            "error": (MELI_ROJO, "✕")
        }
        
        color, icono = colores.get(tipo, colores["info"])
        
        # Formatear mensaje con icono
        mensaje_completo = f"{icono}  {mensaje}"
        
        # Aplicar estilo
        self.statusBar().setStyleSheet(f"""
            QStatusBar {{
                background-color: {MELI_GRIS_FONDO};
                color: {color};
                border-top: 1px solid {MELI_GRIS_BORDE};
                font-size: {UI_FONT_BODY}pt;
                padding: 6px 12px;
            }}
        """)
        
        if duracion > 0:
            self.statusBar().showMessage(mensaje_completo, duracion)
        else:
            self.statusBar().showMessage(mensaje_completo)
    
    def crear_chip(self, texto, color=None, icono=None, removible=False, on_remove=None):
        """Crea un chip/tag interactivo estilo MercadoLibre.
        
        Args:
            texto: Texto del chip
            color: Color de fondo (por defecto MELI_AZUL_CLARO)
            icono: Emoji o icono opcional al inicio
            removible: Si True, muestra botón X para remover
            on_remove: Callback cuando se remueve el chip
        
        Returns:
            QWidget configurado como chip
        """
        if color is None:
            color = MELI_AZUL_CLARO
        
        chip = QtWidgets.QFrame()
        chip.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 16px;
                padding: 6px 12px;
            }}
        """)
        
        layout = QtWidgets.QHBoxLayout(chip)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        # Icono opcional
        if icono:
            icon_label = QtWidgets.QLabel(icono)
            icon_label.setStyleSheet(f"""
                font-size: {UI_FONT_NORMAL}pt;
                color: {MELI_AZUL};
                background-color: transparent;
            """)
            layout.addWidget(icon_label)
        
        # Texto
        text_label = QtWidgets.QLabel(texto)
        text_label.setStyleSheet(f"""
            font-size: {UI_FONT_BODY}pt;
            font-weight: 500;
            color: {MELI_AZUL};
            background-color: transparent;
        """)
        layout.addWidget(text_label)
        
        # Botón remover opcional
        if removible:
            remove_btn = QtWidgets.QPushButton("✕")
            remove_btn.setFixedSize(16, 16)
            remove_btn.setCursor(QtCore.Qt.PointingHandCursor)
            remove_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {MELI_AZUL};
                    font-size: {UI_FONT_NORMAL}pt;
                    font-weight: bold;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    color: {MELI_ROJO};
                }}
            """)
            
            if on_remove:
                remove_btn.clicked.connect(lambda: on_remove(chip))
            else:
                remove_btn.clicked.connect(chip.deleteLater)
            
            layout.addWidget(remove_btn)
        
        return chip
    
    def crear_input_con_icono(self, placeholder="", icono="🔍", tipo="line"):
        """Crea un input con icono integrado estilo MercadoLibre.
        
        Args:
            placeholder: Texto placeholder
            icono: Emoji o icono a mostrar
            tipo: "line" para QLineEdit, "combo" para QComboBox
        
        Returns:
            Tupla (container, input_widget) donde container es el QWidget y input_widget es el campo
        """
        container = QtWidgets.QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: white;
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 8px;
            }}
            QWidget:focus-within {{
                border: 2px solid {MELI_AZUL};
            }}
        """)
        
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # Icono
        icon_label = QtWidgets.QLabel(icono)
        icon_label.setStyleSheet(f"""
            font-size: {UI_FONT_SUBTITLE}pt;
            color: {MELI_GRIS_SECUNDARIO};
            background-color: transparent;
        """)
        layout.addWidget(icon_label)
        
        # Input field
        if tipo == "combo":
            input_widget = QtWidgets.QComboBox()
        else:
            input_widget = QtWidgets.QLineEdit()
            input_widget.setPlaceholderText(placeholder)
        
        input_widget.setStyleSheet(f"""
            QLineEdit, QComboBox {{
                border: none;
                background-color: transparent;
                font-size: {UI_FONT_NORMAL}pt;
                color: {MELI_GRIS_TEXTO};
                padding: 0px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                outline: none;
            }}
        """)
        
        layout.addWidget(input_widget, 1)
        
        return container, input_widget
    
    def aplicar_estilo_inputs_modernos(self):
        """Aplica estilo moderno MercadoLibre a todos los campos de entrada de la aplicación."""
        estilo_global = f"""
            /* QLineEdit - Campos de texto */
            QLineEdit {{
                background-color: white;
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 6px;
                padding: 12px;
                font-size: {UI_FONT_NORMAL}pt;
                color: {MELI_GRIS_TEXTO};
                selection-background-color: {MELI_AZUL_CLARO};
            }}
            QLineEdit:hover {{
                border-color: {MELI_AZUL};
            }}
            QLineEdit:focus {{
                border: 2px solid {MELI_AZUL};
                background-color: white;
            }}
            QLineEdit:disabled {{
                background-color: {MELI_GRIS_FONDO};
                color: {MELI_GRIS_SECUNDARIO};
                border-color: {MELI_GRIS_BORDE};
            }}
            
            /* QSpinBox y QDoubleSpinBox - Campos numéricos */
            QSpinBox, QDoubleSpinBox {{
                background-color: white;
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 6px;
                padding: 12px;
                font-size: {UI_FONT_NORMAL}pt;
                color: {MELI_GRIS_TEXTO};
                selection-background-color: {MELI_AZUL_CLARO};
            }}
            QSpinBox:hover, QDoubleSpinBox:hover {{
                border-color: {MELI_AZUL};
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {MELI_AZUL};
                background-color: white;
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                background-color: {MELI_GRIS_FONDO};
                border-left: 1px solid {MELI_GRIS_BORDE};
                border-radius: 0 5px 0 0;
                width: 20px;
            }}
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
                background-color: {MELI_AZUL_CLARO};
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                background-color: {MELI_GRIS_FONDO};
                border-left: 1px solid {MELI_GRIS_BORDE};
                border-radius: 0 0 5px 0;
                width: 20px;
            }}
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
                background-color: {MELI_AZUL_CLARO};
            }}
            QSpinBox:disabled, QDoubleSpinBox:disabled {{
                background-color: {MELI_GRIS_FONDO};
                color: {MELI_GRIS_SECUNDARIO};
                border-color: {MELI_GRIS_BORDE};
            }}
            
            /* QComboBox - Listas desplegables */
            QComboBox {{
                background-color: white;
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 6px;
                padding: 12px 32px 12px 12px;
                font-size: {UI_FONT_NORMAL}pt;
                color: {MELI_GRIS_TEXTO};
                selection-background-color: {MELI_AZUL_CLARO};
            }}
            QComboBox:hover {{
                border-color: {MELI_AZUL};
            }}
            QComboBox:focus {{
                border: 2px solid {MELI_AZUL};
                background-color: white;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {MELI_AZUL};
                margin-right: 8px;
            }}
            QComboBox:disabled {{
                background-color: {MELI_GRIS_FONDO};
                color: {MELI_GRIS_SECUNDARIO};
                border-color: {MELI_GRIS_BORDE};
            }}
            QComboBox QAbstractItemView {{
                background-color: white;
                border: 2px solid {MELI_AZUL};
                border-radius: 6px;
                selection-background-color: {MELI_AZUL_CLARO};
                selection-color: {MELI_GRIS_TEXTO};
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 10px 12px;
                border-radius: 4px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {MELI_GRIS_FONDO};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {MELI_AZUL_CLARO};
            }}
            
            /* QTextEdit - Áreas de texto */
            QTextEdit {{
                background-color: white;
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 6px;
                padding: 12px;
                font-size: {UI_FONT_NORMAL}pt;
                color: {MELI_GRIS_TEXTO};
                selection-background-color: {MELI_AZUL_CLARO};
            }}
            QTextEdit:hover {{
                border-color: {MELI_AZUL};
            }}
            QTextEdit:focus {{
                border: 2px solid {MELI_AZUL};
                background-color: white;
            }}
            
            /* QRadioButton - Botones de radio */
            QRadioButton {{
                spacing: 8px;
                font-size: {UI_FONT_NORMAL}pt;
                color: {MELI_GRIS_TEXTO};
            }}
            QRadioButton::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid {MELI_GRIS_BORDE};
                background-color: white;
            }}
            QRadioButton::indicator:hover {{
                border-color: {MELI_AZUL};
            }}
            QRadioButton::indicator:checked {{
                border-color: {MELI_AZUL};
                background-color: white;
            }}
            QRadioButton::indicator:checked::after {{
                width: 10px;
                height: 10px;
                border-radius: 5px;
                background-color: {MELI_AZUL};
            }}
            
            /* QCheckBox - Casillas de verificación */
            QCheckBox {{
                spacing: 8px;
                font-size: {UI_FONT_NORMAL}pt;
                color: {MELI_GRIS_TEXTO};
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid {MELI_GRIS_BORDE};
                background-color: white;
            }}
            QCheckBox::indicator:hover {{
                border-color: {MELI_AZUL};
            }}
            QCheckBox::indicator:checked {{
                border-color: {MELI_AZUL};
                background-color: {MELI_AZUL};
                image: none;
            }}
            QCheckBox::indicator:checked::after {{
                content: "✓";
                color: white;
            }}
        """
        
        # Aplicar el estilo global a la aplicación
        self.setStyleSheet(self.styleSheet() + estilo_global)
    
    def aplicar_estilo_tabla_moderno(self, table):
        """Aplica estilo moderno MercadoLibre a una QTableWidget con hover states.
        
        Args:
            table: QTableWidget al que aplicar el estilo
        """
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: white;
                alternate-background-color: {MELI_GRIS_CLARO};
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 6px;
                gridline-color: {MELI_GRIS_BORDE};
                selection-background-color: {MELI_AZUL_CLARO};
                selection-color: {MELI_GRIS_TEXTO};
                font-size: {UI_FONT_NORMAL}pt;
                outline: none;
                show-decoration-selected: 0;
            }}
            QTableWidget::item {{
                padding: 12px 8px;
                border: none;
                outline: none;
            }}
            QTableWidget::item:hover {{
                background-color: {MELI_GRIS_FONDO};
            }}
            QTableWidget::item:selected {{
                background-color: {MELI_AZUL_CLARO};
                color: {MELI_GRIS_TEXTO};
                border: none;
                outline: none;
            }}
            QTableWidget::item:selected:hover {{
                background-color: #D0E7FF;
            }}
            QTableWidget::item:focus {{
                outline: none;
                border: none;
            }}
            QHeaderView::section {{
                background-color: white;
                color: {MELI_GRIS_TEXTO};
                font-weight: 600;
                font-size: {UI_FONT_NORMAL}pt;
                padding: 14px 8px;
                border: none;
                border-bottom: 2px solid {MELI_GRIS_BORDE};
            }}
            QHeaderView::section:hover {{
                background-color: {MELI_GRIS_FONDO};
            }}
        """)
    
    def aplicar_estilo_card_moderno(self, groupbox):
        """Aplica estilo de card moderna MercadoLibre a un QGroupBox.
        
        Args:
            groupbox: QGroupBox al que aplicar el estilo
        """
        groupbox.setStyleSheet(f"""
            QGroupBox {{
                background-color: white;
                border: 1px solid {MELI_GRIS_BORDE};
                border-radius: 8px;
                padding: 12px;
                margin-top: 6px;
                font-weight: 600;
                font-size: {UI_FONT_NORMAL}pt;
                color: {MELI_GRIS_TEXTO};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                padding: 6px 10px;
                background-color: white;
                border-radius: 4px;
                color: {MELI_GRIS_TEXTO};
                font-weight: 600;
                font-size: {UI_FONT_NORMAL}pt;
            }}
        """)
        
        # Aplicar sombra usando QGraphicsDropShadowEffect
        try:
            from PyQt5.QtWidgets import QGraphicsDropShadowEffect
            from PyQt5.QtGui import QColor
            
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15)
            shadow.setXOffset(0)
            shadow.setYOffset(2)
            shadow.setColor(QColor(0, 0, 0, 30))  # Negro con 30 de opacidad
            groupbox.setGraphicsEffect(shadow)
        except Exception as e:
            print(f"No se pudo aplicar sombra: {e}")
    
    def crear_hero_banner(self, titulo="Risk Lab", subtitulo="Plataforma de Simulación de Riesgos"):
        """Crea un hero banner moderno y compacto con accent bar amarillo.
        
        Mejoras aplicadas:
        - Altura reducida de 70px a 60px (ahorro del 14%)
        - Fondo blanco limpio con accent bar amarillo como identidad de marca
        - Logo a 46px con padding mínimo (garantiza visualización completa)
        - Mejor jerarquía visual con tipografía optimizada
        
        Args:
            titulo: Texto principal del banner
            subtitulo: Texto descriptivo secundario
        """
        # Wrapper para contener header + accent bar
        header_wrapper = QtWidgets.QWidget()
        wrapper_layout = QtWidgets.QVBoxLayout(header_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        
        # Contenedor principal del banner (header)
        hero_container = QtWidgets.QWidget()
        hero_container.setObjectName("heroBanner")
        hero_layout = QtWidgets.QHBoxLayout(hero_container)
        hero_layout.setContentsMargins(14, 7, 14, 7)  # Márgenes ajustados para 60px
        hero_layout.setSpacing(12)
        
        # Logo de Risk Lab (lado izquierdo) - Tamaño aumentado para verse completo
        logo_label = QtWidgets.QLabel()
        logo_path = resource_path("images/risk_lab_logo.png")
        
        if os.path.exists(logo_path):
            logo_pixmap = QtGui.QPixmap(logo_path)
            # Escalar logo a 46px - tamaño que garantiza que se vea completo
            logo_pixmap = logo_pixmap.scaledToHeight(46, QtCore.Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            # Fondo gris muy claro en lugar de negro para mejor integración
            logo_label.setStyleSheet("""
                QLabel {
                    background-color: #F8F8F8;
                    border-radius: 4px;
                    padding: 0px;
                }
            """)
        else:
            # Fallback: texto si no hay logo
            logo_label.setText("RL")
            logo_label.setStyleSheet(f"""
                font-size: {UI_FONT_XLARGE}pt;
                font-weight: bold;
                color: #2D3277;
                background-color: #F8F8F8;
                border-radius: 4px;
                padding: 6px 10px;
            """)
        
        logo_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        hero_layout.addWidget(logo_label)
        
        # Contenedor de texto (centro)
        text_container = QtWidgets.QWidget()
        text_container.setStyleSheet("background-color: transparent;")
        text_layout = QtWidgets.QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        
        # Título principal - Jerarquía mejorada
        titulo_label = QtWidgets.QLabel(titulo)
        titulo_label.setObjectName("heroTitle")
        titulo_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        titulo_label.setStyleSheet(f"""
            font-size: {UI_FONT_SUBHEAD}pt;
            font-weight: 600;
            color: #2D3277;
            background-color: transparent;
            padding: 0;
            margin: 0;
            letter-spacing: -0.2px;
        """)
        text_layout.addWidget(titulo_label)
        
        # Subtítulo - Más sutil y refinado
        tagline_label = QtWidgets.QLabel(subtitulo)
        tagline_label.setObjectName("heroTagline")
        tagline_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        tagline_label.setStyleSheet(f"""
            font-size: {UI_FONT_XSMALL}pt;
            font-weight: 400;
            color: #888888;
            background-color: transparent;
            padding: 0;
            margin: 0;
        """)
        text_layout.addWidget(tagline_label)
        
        hero_layout.addWidget(text_container, 1)
        
        # Etiqueta de versión - Refinada
        version_label = QtWidgets.QLabel(f"v{self.APP_VERSION}")
        version_label.setObjectName("heroVersion")
        version_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        version_label.setStyleSheet(f"""
            font-size: {UI_FONT_XSMALL}pt;
            font-weight: 500;
            color: #999999;
            background-color: #F5F5F5;
            border: 1px solid #E8E8E8;
            border-radius: 10px;
            padding: 3px 10px;
        """)
        hero_layout.addWidget(version_label)
        
        # Fondo blanco limpio para el header
        hero_container.setStyleSheet("""
            QWidget#heroBanner {
                background-color: #FFFFFF;
                border: none;
            }
        """)
        
        # Altura a 60px para que el logo de 46px se vea completo sin cortes
        hero_container.setMinimumHeight(60)
        hero_container.setMaximumHeight(60)
        
        # Agregar header al wrapper
        wrapper_layout.addWidget(hero_container)
        
        # Accent bar amarillo (3px) - Identidad de marca sutil
        accent_bar = QtWidgets.QWidget()
        accent_bar.setFixedHeight(3)
        accent_bar.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FFE600,
                    stop:0.5 #FFD000,
                    stop:1 #FFC700
                );
            }
        """)
        wrapper_layout.addWidget(accent_bar)
        
        return header_wrapper
    
    def setup_config_tab(self):
        # Layout principal del tab (solo contiene el scroll area)
        tab_layout = QtWidgets.QVBoxLayout(self.config_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)
        
        # Scroll area para permitir scroll en pantallas pequeñas
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #F5F7FA;
            }
        """)
        
        # Widget contenedor con el contenido scrolleable
        content_widget = QtWidgets.QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #F5F7FA;
            }
        """)
        
        # Usamos un QGridLayout como layout del contenido
        layout = QtWidgets.QGridLayout(content_widget)
        layout.setContentsMargins(8, 8, 8, 8)  # Reducido de 10 a 8
        layout.setSpacing(8)  # Reducido de 10 a 8
        current_row = 0
        
        # Panel de configuración con número de simulaciones
        config_panel = QtWidgets.QWidget()
        config_layout = QtWidgets.QHBoxLayout(config_panel)
        config_layout.setContentsMargins(8, 8, 8, 8)  # Reducido de 10 a 8
        
        simulaciones_label = QtWidgets.QLabel("Número de simulaciones:")
        simulaciones_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        simulaciones_label.setToolTip("Define cuántas iteraciones realizará la simulación Monte Carlo")
        simulaciones_label.setStyleSheet(f"font-size: {UI_FONT_BASE}pt;")  # Mismo tamaño que en Escenarios
        config_layout.addWidget(simulaciones_label)
        
        self.num_simulaciones_var = QtWidgets.QLineEdit("10000")
        self.num_simulaciones_var.setFixedWidth(100)
        self.num_simulaciones_var.setToolTip("Recomendado: 10000 o más para mayor precisión")
        config_layout.addWidget(self.num_simulaciones_var)
        config_layout.addStretch()
        
        layout.addWidget(config_panel, current_row, 0, 1, 4)
        current_row += 1
        
        # Botón para agregar evento - ocupa las 4 columnas
        agregar_evento_button = QtWidgets.QPushButton(" Agregar Evento de Riesgo")
        agregar_evento_button.setIcon(self.iconos["add"])  # Usar icono SVG moderno
        agregar_evento_button.clicked.connect(self.agregar_evento_popup)
        agregar_evento_button.setFixedHeight(40)  # Altura fija optimizada
        agregar_evento_button.setToolTip("Añadir un nuevo evento de riesgo a la simulación")
        self.aplicar_estilo_boton_primario(agregar_evento_button)  # Estilo Mercado Libre
        self.agregar_animacion_hover_boton(agregar_evento_button)  # Animación hover
        layout.addWidget(agregar_evento_button, current_row, 0, 1, 4)
        current_row += 1
        
        # Lista de eventos - panel con título y tabla (Card moderna)
        self.eventos_panel = QtWidgets.QGroupBox("📈 Eventos de Riesgo Configurados")
        self.aplicar_estilo_card_moderno(self.eventos_panel)
        self.agregar_animacion_card_hover(self.eventos_panel)  # Animación hover en card
        eventos_layout = QtWidgets.QVBoxLayout(self.eventos_panel)
        eventos_layout.setContentsMargins(8, 8, 8, 8)  # Márgenes compactos
        eventos_layout.setSpacing(6)  # Espaciado reducido
        
        # Quick Win 2: Barra de búsqueda
        self.eventos_search = QtWidgets.QLineEdit()
        self.eventos_search.setPlaceholderText("🔍 Buscar eventos por nombre...")
        self.eventos_search.setClearButtonEnabled(True)
        self.eventos_search.setFixedHeight(32)
        self.eventos_search.textChanged.connect(self.filtrar_eventos_tabla)
        self.eventos_search.setStyleSheet(f"""
            QLineEdit {{
                padding: 6px 10px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: {UI_FONT_NORMAL}pt;
                background-color: white;
            }}
            QLineEdit:focus {{
                border: 1px solid #3483FA;
                background-color: #F5F9FF;
            }}
        """)
        
        # FASE 2: Usar toolbar con toggle de vistas en lugar de solo búsqueda
        toolbar = self.crear_view_toggle_toolbar()
        eventos_layout.addWidget(toolbar)
        
        # Contenedor con stack para tabla y empty state
        self.eventos_stack = QtWidgets.QStackedWidget()
        
        # Tabla de eventos
        self.eventos_table = QtWidgets.QTableWidget(0, 2)
        self.eventos_table.setHorizontalHeaderLabels(["Activo", "Nombre del Evento"])
        # IMPORTANTE: Permitir secciones más pequeñas
        self.eventos_table.horizontalHeader().setMinimumSectionSize(30)
        # Establecer columna 0 como ResizeToContents (se ajusta al contenido)
        self.eventos_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        # Establecer columna 1 como Stretch (ocupa todo el espacio restante)
        self.eventos_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.eventos_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.eventos_table.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        # Deshabilitar la edición directa de celdas - se usará solo el formulario de edición
        self.eventos_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.eventos_table.setToolTip("Lista de eventos de riesgo configurados. Doble clic para editar el evento en el formulario.")
        self.eventos_table.setAlternatingRowColors(False)  # Desactivar alternancia (se usará hover)
        self.eventos_table.verticalHeader().setVisible(False)  # Ocultar cabecera vertical
        self.eventos_table.setMinimumHeight(150)  # Reducido de 200 a 150 para aprovechar espacio
        self.eventos_table.setMouseTracking(True)  # Habilitar tracking para hover
        
        # Configuración para visualización correcta del texto
        self.eventos_table.setWordWrap(True)  # Permitir ajuste de línea del texto
        self.eventos_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)  # Ajustar altura de filas al contenido
        
        self.aplicar_estilo_tabla_moderno(self.eventos_table)  # Aplicar estilo Mercado Libre
        
        # Empty state para eventos
        self.eventos_empty_state = self.crear_empty_state(
            self.eventos_stack,
            "No hay eventos de riesgo configurados",
            "Comienza agregando tu primer evento para iniciar el análisis de riesgos",
            "➕ Agregar Primer Evento",
            self.agregar_evento_popup,
            icono="📊"
        )
        
        # Añadir ambos al stack
        self.eventos_stack.addWidget(self.eventos_empty_state)  # índice 0
        self.eventos_stack.addWidget(self.eventos_table)  # índice 1
        
        # FASE 1: Agregar vista de tarjetas al stack
        self.eventos_cards_view = self.crear_vista_tarjetas()
        self.eventos_stack.addWidget(self.eventos_cards_view)  # índice 2
        
        # Mostrar empty state inicialmente si no hay eventos
        if len(self.eventos_riesgo) == 0:
            self.eventos_stack.setCurrentIndex(0)
        else:
            self.eventos_stack.setCurrentIndex(1)
        
        eventos_layout.addWidget(self.eventos_stack)
        
        # Conectar señal de doble clic
        self.eventos_table.cellDoubleClicked.connect(self.editar_evento_desde_tabla)
        
        # Conectar señal de selección para habilitar/deshabilitar botones
        self.eventos_table.itemSelectionChanged.connect(self.actualizar_estado_botones_eventos)
        
        # Ocupar 4 columnas para la tabla de eventos
        layout.addWidget(self.eventos_panel, current_row, 0, 1, 4)
        layout.setRowStretch(current_row, 10)  # Dar mayor peso a la fila de la tabla para que se expanda
        current_row += 1
        
        # Panel de botones de acción con grid layout (2x2)
        botones_panel = QtWidgets.QWidget()
        botones_layout = QtWidgets.QGridLayout(botones_panel)
        botones_layout.setContentsMargins(0, 2, 0, 2)  # Reducido para ahorrar espacio
        
        # Fila 1 de botones
        self.editar_evento_button = QtWidgets.QPushButton("Editar Evento")
        self.editar_evento_button.setIcon(self.iconos_oscuros.get("edit", self.iconos["edit"]))  # Usar icono oscuro
        self.editar_evento_button.clicked.connect(self.editar_evento_popup)
        self.editar_evento_button.setFixedHeight(36)  # Altura FIJA para botones de acción
        self.editar_evento_button.setToolTip("Editar el evento seleccionado")
        self.aplicar_estilo_boton_secundario(self.editar_evento_button)  # Estilo Mercado Libre
        self.agregar_animacion_hover_boton(self.editar_evento_button)  # Animación hover
        botones_layout.addWidget(self.editar_evento_button, 0, 0)
        
        self.duplicar_evento_button = QtWidgets.QPushButton("Duplicar Evento(s)")
        self.duplicar_evento_button.setIcon(self.iconos_oscuros.get("copy", self.iconos["copy"]))  # Usar icono oscuro
        self.duplicar_evento_button.clicked.connect(self.duplicar_eventos)
        self.duplicar_evento_button.setFixedHeight(36)  # Altura FIJA para botones de acción
        self.duplicar_evento_button.setToolTip("Crear copias de los eventos seleccionados")
        self.aplicar_estilo_boton_secundario(self.duplicar_evento_button)  # Estilo Mercado Libre
        self.agregar_animacion_hover_boton(self.duplicar_evento_button)  # Animación hover
        botones_layout.addWidget(self.duplicar_evento_button, 0, 1)
        
        # Fila 2 de botones
        self.eliminar_evento_button = QtWidgets.QPushButton("Eliminar Evento(s)")
        self.eliminar_evento_button.setIcon(self.iconos_oscuros.get("delete", self.iconos["delete"]))  # Usar icono oscuro
        self.eliminar_evento_button.clicked.connect(self.eliminar_evento)
        self.eliminar_evento_button.setFixedHeight(36)  # Altura FIJA para botones de acción
        self.eliminar_evento_button.setToolTip("Eliminar los eventos seleccionados")
        self.aplicar_estilo_boton_secundario(self.eliminar_evento_button)  # Estilo secundario (igual que Editar/Duplicar)
        self.agregar_animacion_hover_boton(self.eliminar_evento_button)  # Animación hover
        botones_layout.addWidget(self.eliminar_evento_button, 1, 0)
        
        simular_button = QtWidgets.QPushButton("Ejecutar Simulación")
        simular_button.setIcon(self.iconos["play"])  # Usar icono SVG moderno
        simular_button.clicked.connect(self.ejecutar_simulacion)
        simular_button.setFixedHeight(36)  # Altura FIJA para botones de acción
        simular_button.setToolTip("Ejecutar la simulación con los eventos configurados")
        self.aplicar_estilo_boton_exitoso(simular_button)  # Estilo Mercado Libre
        self.agregar_animacion_hover_boton(simular_button)  # Animación hover
        botones_layout.addWidget(simular_button, 1, 1)
        
        # Añadir el panel de botones al layout principal
        layout.addWidget(botones_panel, current_row, 0, 1, 4)
        layout.setRowStretch(current_row, 1)  # Peso menor para los botones
        
        # Estado inicial: botones deshabilitados (no hay selección)
        self.actualizar_estado_botones_eventos()
        
        # Conectar el scroll area con el contenido y agregarlo al tab
        scroll_area.setWidget(content_widget)
        tab_layout.addWidget(scroll_area)

    def actualizar_estado_botones_eventos(self):
        """Actualiza el estado habilitado/deshabilitado de los botones según la selección en la tabla."""
        hay_seleccion = len(self.eventos_table.selectedItems()) > 0
        
        # Editar solo se habilita con exactamente una fila seleccionada
        filas_seleccionadas = set(item.row() for item in self.eventos_table.selectedItems())
        una_seleccion = len(filas_seleccionadas) == 1
        
        self.editar_evento_button.setEnabled(una_seleccion)
        self.duplicar_evento_button.setEnabled(hay_seleccion)
        self.eliminar_evento_button.setEnabled(hay_seleccion)
    
    # FUNCIÓN OBSOLETA COMENTADA - Se usa la versión de línea ~8296
    '''
    def ejecutar_simulacion(self):
        """Ejecuta la simulación de Monte Carlo con los eventos de riesgo configurados."""
        # Verificar que haya eventos de riesgo configurados
        if not self.eventos_riesgo:
            QtWidgets.QMessageBox.warning(self, "Advertencia", "No hay eventos de riesgo configurados para simular.")
            return
            
        try:
            # Validar número de simulaciones (función centralizada)
            num_simulaciones = validar_num_simulaciones(self.num_simulaciones_var.text())
                
            # Desactivar la interfaz durante la simulación
            self.set_interfaz_activa(False)
            self.progress_bar.setValue(0)
            
            # Iniciar animación de la barra de progreso
            if hasattr(self, 'progress_animation_timer'):
                self.progress_animation_timer.start(100)  # Actualizar cada 100ms
            
            # Cambiar a la pestaña de resultados
            self.central_widget.setCurrentWidget(self.results_tab)
            
            # DEBUG: Inspeccionar self.eventos_riesgo justo antes de pasar al thread
            print(f"\n[DEBUG PRE-THREAD] ========================================")
            print(f"[DEBUG PRE-THREAD] Inspeccionando self.eventos_riesgo antes de crear thread")
            print(f"[DEBUG PRE-THREAD] Total de eventos: {len(self.eventos_riesgo)}")
            for i, e in enumerate(self.eventos_riesgo):
                nombre = e.get('nombre', 'Sin nombre')
                tiene_factores = 'factores_ajuste' in e
                factores = e.get('factores_ajuste', [])
                print(f"[DEBUG PRE-THREAD]   [{i}] '{nombre}': tiene_factores={tiene_factores}, factores={factores}")
            print(f"[DEBUG PRE-THREAD] ========================================\n")
            
            # Crear y configurar el hilo de simulación
            self.thread_simulacion = SimulacionThread(self.eventos_riesgo, num_simulaciones)
            self.thread_simulacion.progreso_actualizado.connect(self.actualizar_progreso)
            self.thread_simulacion.simulacion_completada.connect(self.simulacion_completada)
            self.thread_simulacion.error_ocurrido.connect(self.simulacion_error)
            
            # Iniciar la simulación
            self.thread_simulacion.start()
            
        except ValueError as ve:
            QtWidgets.QMessageBox.critical(self, "Error", str(ve))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Error al iniciar la simulación: {e}")
    '''
    # FIN FUNCIÓN OBSOLETA COMENTADA

    def setup_results_tab(self):
        # Fondo sutil para resaltar las cards
        self.results_tab.setStyleSheet("""
            QWidget {
                background-color: #F5F7FA;
            }
        """)
        
        # Usamos un QGridLayout como layout principal
        layout = QtWidgets.QGridLayout(self.results_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        current_row = 0
        
        # Barra de progreso con etiqueta informativa
        progress_panel = QtWidgets.QWidget()
        progress_layout = QtWidgets.QGridLayout(progress_panel)
        progress_layout.setContentsMargins(10, 10, 10, 10)
        
        progress_label = QtWidgets.QLabel("Progreso de la simulación:")
        progress_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        progress_label.setToolTip("Muestra el avance de la simulación")
        progress_layout.addWidget(progress_label, 0, 0)
        
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)  # Mostrar porcentaje en texto
        self.progress_bar.setFormat("%p%")      # Formato de texto de porcentaje
        self.progress_bar.setToolTip("Porcentaje de avance de la simulación")
        self.aplicar_estilo_progress_bar_moderno()  # Aplicar estilo moderno
        progress_layout.addWidget(self.progress_bar, 0, 1, 1, 3)
        
        layout.addWidget(progress_panel, current_row, 0, 1, 4)
        current_row += 1
        
        # Panel de resultados (splitter horizontal)
        results_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        # Panel de resultados estadísticos con jerarquía visual (panel izquierdo)
        text_panel = QtWidgets.QWidget()
        text_layout = QtWidgets.QVBoxLayout(text_panel)
        
        resultados_label = QtWidgets.QLabel("Resumen Estadístico:")
        resultados_label.setFont(QtGui.QFont("Helvetica", 12, QtGui.QFont.Bold))
        resultados_label.setToolTip("Estadísticas de los resultados de la simulación")
        text_layout.addWidget(resultados_label)
        
        # Contenedor fijo para mantener la sección de Excedencia siempre arriba
        self.excedencia_holder = QtWidgets.QWidget()
        self.excedencia_holder_layout = QtWidgets.QVBoxLayout(self.excedencia_holder)
        self.excedencia_holder_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.addWidget(self.excedencia_holder)
        
        # Sección: Consulta de Excedencia (siempre arriba del resumen)
        try:
            excedencia_sec = self.crear_seccion_colapsable("Consulta de Excedencia", parent_layout=self.excedencia_holder_layout)
            excedencia_layout = excedencia_sec["contenido_layout"]
            # Guardar referencia para poder reemplazarla al regenerar
            self.excedencia_section_widget = excedencia_sec["seccion"]

            # Controles
            self.excedencia_controls_container = QtWidgets.QWidget()
            ctrls_layout = QtWidgets.QHBoxLayout(self.excedencia_controls_container)
            ctrls_layout.setContentsMargins(0, 0, 0, 0)

            tol_label = QtWidgets.QLabel("Tolerancia ($):")
            self.tolerancia_ex_spin = NoScrollDoubleSpinBox()
            self.tolerancia_ex_spin.setDecimals(0)
            self.tolerancia_ex_spin.setRange(0, 1000000000000)
            self.tolerancia_ex_spin.setSingleStep(10000)
            self.tolerancia_ex_spin.setPrefix("$")
            self.tolerancia_ex_spin.setToolTip("Monto de tolerancia para calcular P[Impacto > T]")

            res_text_label = QtWidgets.QLabel("Probabilidad de excedencia:")
            self.exceedance_value_label = QtWidgets.QLabel("-")
            font_val = self.exceedance_value_label.font()
            font_val.setBold(True)
            self.exceedance_value_label.setFont(font_val)
            self.exceedance_value_label.setStyleSheet("color: #2F5597;")

            ctrls_layout.addWidget(tol_label)
            ctrls_layout.addWidget(self.tolerancia_ex_spin)
            ctrls_layout.addSpacing(12)
            ctrls_layout.addWidget(res_text_label)
            ctrls_layout.addWidget(self.exceedance_value_label)
            ctrls_layout.addStretch()

            excedencia_layout.addWidget(self.excedencia_controls_container)
            self.excedencia_controls_container.setEnabled(False)

            self.tolerancia_ex_spin.valueChanged.connect(self.actualizar_probabilidad_excedencia)
        except Exception:
            pass
        
        # Scroll area para los resultados estadísticos
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setMinimumWidth(420)  # Reducimos ancho mínimo para dar más espacio a gráficos
        
        # Widget contenedor para las secciones de resultados
        self.resultados_container = QtWidgets.QWidget()
        self.resultados_layout = QtWidgets.QVBoxLayout(self.resultados_container)
        self.resultados_layout.setAlignment(QtCore.Qt.AlignTop)
        self.resultados_layout.setSpacing(10)
        self.resultados_layout.setContentsMargins(5, 5, 5, 5)
        
        # Añadimos el contenedor al área de scroll
        scroll_area.setWidget(self.resultados_container)
        text_layout.addWidget(scroll_area)
        
        # Mantenemos el texto edit oculto para compatibilidad con código existente
        self.resultados_text_edit = QtWidgets.QTextEdit()
        self.resultados_text_edit.setVisible(False)
        text_layout.addWidget(self.resultados_text_edit)
        
        results_splitter.addWidget(text_panel)
        
        # Pestañas para los gráficos (panel derecho)
        graphs_panel = QtWidgets.QWidget()
        graphs_layout = QtWidgets.QVBoxLayout(graphs_panel)
        
        graficos_label = QtWidgets.QLabel("Visualización:")
        graficos_label.setFont(QtGui.QFont("Helvetica", 12, QtGui.QFont.Bold))
        graficos_label.setToolTip("Gráficos de los resultados de la simulación")
        graphs_layout.addWidget(graficos_label)
        
        self.graficos_tab_widget = QtWidgets.QTabWidget()
        self.graficos_tab_widget.setDocumentMode(False)  # Tabs más altas y legibles
        self.graficos_tab_widget.setTabPosition(QtWidgets.QTabWidget.North)
        
        # Dar más espacio y mejor comportamiento a las solapas de los gráficos
        self.graficos_tab_widget.setObjectName("graficosTabWidget")
        tb = self.graficos_tab_widget.tabBar()
        tb.setElideMode(QtCore.Qt.ElideNone)        # No cortar texto
        tb.setUsesScrollButtons(True)                # Scroll si hay muchas pestañas
        tb.setExpanding(False)                       # Tamaño según contenido
        tb.setDrawBase(False)                        # Mejor renderizado
        tb.setMovable(True)                          # Permite reordenar

        # Aplicar estilo compacto a pestañas de gráficos
        self.aplicar_estilo_tab_widget_graficos(self.graficos_tab_widget)
        
        graphs_layout.addWidget(self.graficos_tab_widget)
        
        results_splitter.addWidget(graphs_panel)
        results_splitter.setStretchFactor(0, 1)  # El panel de texto
        results_splitter.setStretchFactor(1, 3)  # Dar aún más espacio a los gráficos
        results_splitter.setSizes([500, 950])    # Tamaño inicial privilegiando el panel derecho
        
        # Añadir splitter al layout principal
        layout.addWidget(results_splitter, current_row, 0, 1, 4)
        layout.setRowStretch(current_row, 10)  # Dar mayor peso de estiramiento a la fila de resultados
        
        # Diccionario para almacenar referencias a las secciones creadas
        self.secciones_resultados = {}

    def actualizar_probabilidad_excedencia(self):
        """Calcula y muestra P[Impacto > T] basado en la tolerancia actual y los resultados."""
        try:
            if not hasattr(self, 'resultados_simulacion') or self.resultados_simulacion is None:
                self.exceedance_value_label.setText("-")
                return
            
            T = float(self.tolerancia_ex_spin.value()) if hasattr(self, 'tolerancia_ex_spin') else 0.0
            
            perdidas_totales = self.resultados_simulacion['perdidas_totales']
            if perdidas_totales is None or len(perdidas_totales) == 0:
                self.exceedance_value_label.setText("-")
                return
            
            # Cálculo vectorizado
            prob = float(np.mean(perdidas_totales > T))
            self.exceedance_value_label.setText(percentage_format(prob))
            # Actualizar líneas de tolerancia en gráficos si existen
            try:
                self.actualizar_linea_tolerancia_graficos()
            except Exception:
                pass
        except Exception:
            # Falla silenciosa para no afectar UX
            try:
                self.exceedance_value_label.setText("-")
            except Exception:
                pass

    def actualizar_linea_tolerancia_graficos(self):
        """Sincroniza la posición y visibilidad de las líneas de tolerancia en los gráficos.
        - Histograma (Distribución Agregada): línea vertical en x=T
        - Curva de Excedencia: línea horizontal en y=T
        """
        try:
            T = None
            if hasattr(self, 'tolerancia_ex_spin') and self.tolerancia_ex_spin is not None:
                try:
                    T = float(self.tolerancia_ex_spin.value())
                except Exception:
                    T = None

            # Distribución: mover/mostrar línea vertical
            try:
                if getattr(self, 'ax_distrib_tol_line', None) is not None:
                    visible = True
                    if getattr(self, 'cb_tol_line_distrib', None) is not None:
                        visible = bool(self.cb_tol_line_distrib.isChecked())
                    self.ax_distrib_tol_line.set_visible(visible)
                    # Actualizar posición de la línea y etiqueta
                    if T is not None:
                        try:
                            self.ax_distrib_tol_line.set_xdata([T, T])
                            if getattr(self, 'ax_distrib_tol_label', None) is not None:
                                ax = self.ax_distrib_tol_line.axes
                                x_left, x_right = ax.get_xlim()
                                x_range = max(1e-9, x_right - x_left)
                                dx = 0.01 * x_range
                                y_bottom, y_top = ax.get_ylim()
                                y_pos = y_bottom + 0.9 * (y_top - y_bottom)
                                self.ax_distrib_tol_label.set_position((T + dx, y_pos))
                        except Exception:
                            pass
                    if getattr(self, 'ax_distrib_tol_label', None) is not None:
                        self.ax_distrib_tol_label.set_visible(visible)
                    if getattr(self, 'canvas_distrib', None) is not None:
                        self.canvas_distrib.draw_idle()
            except Exception:
                pass

            # Excedencia: mover/mostrar línea horizontal
            try:
                if getattr(self, 'ax_exceed_tol_line', None) is not None:
                    visible = True
                    if getattr(self, 'cb_tol_line_exceed', None) is not None:
                        visible = bool(self.cb_tol_line_exceed.isChecked())
                    self.ax_exceed_tol_line.set_visible(visible)
                    if T is not None:
                        try:
                            self.ax_exceed_tol_line.set_ydata([T, T])
                            if getattr(self, 'ax_exceed_tol_label', None) is not None:
                                ax = self.ax_exceed_tol_line.axes
                                x_left, x_right = ax.get_xlim()
                                x_range = max(1e-3, x_right - x_left)
                                x_pos = x_left + 0.98 * x_range
                                self.ax_exceed_tol_label.set_position((x_pos, T))
                        except Exception:
                            pass
                    if getattr(self, 'ax_exceed_tol_label', None) is not None:
                        self.ax_exceed_tol_label.set_visible(visible)
                    if getattr(self, 'canvas_exceed', None) is not None:
                        self.canvas_exceed.draw_idle()
            except Exception:
                pass
            
            # Distribución sin eventos en cero: mover/mostrar línea vertical
            try:
                if getattr(self, 'ax_distrib_sin_cero_tol_line', None) is not None:
                    visible2 = True
                    if getattr(self, 'cb_tol_line_distrib_sin_cero', None) is not None:
                        visible2 = bool(self.cb_tol_line_distrib_sin_cero.isChecked())
                    self.ax_distrib_sin_cero_tol_line.set_visible(visible2)
                    # Actualizar posición de la línea y etiqueta
                    if T is not None:
                        try:
                            self.ax_distrib_sin_cero_tol_line.set_xdata([T, T])
                            if getattr(self, 'ax_distrib_sin_cero_tol_label', None) is not None:
                                ax = self.ax_distrib_sin_cero_tol_line.axes
                                x_left2, x_right2 = ax.get_xlim()
                                x_range2 = max(1e-9, x_right2 - x_left2)
                                dx2 = 0.01 * x_range2
                                y_bottom2, y_top2 = ax.get_ylim()
                                y_pos2 = y_bottom2 + 0.9 * (y_top2 - y_bottom2)
                                self.ax_distrib_sin_cero_tol_label.set_position((T + dx2, y_pos2))
                        except Exception:
                            pass
                    if getattr(self, 'ax_distrib_sin_cero_tol_label', None) is not None:
                        self.ax_distrib_sin_cero_tol_label.set_visible(visible2)
                    if getattr(self, 'canvas_distrib_sin_cero', None) is not None:
                        self.canvas_distrib_sin_cero.draw_idle()
            except Exception:
                pass
            
            # Escenarios: mover/mostrar línea vertical
            try:
                if getattr(self, 'ax_escenarios_tol_line', None) is not None:
                    visible3 = True
                    if getattr(self, 'cb_tol_line_escenarios', None) is not None:
                        visible3 = bool(self.cb_tol_line_escenarios.isChecked())
                    self.ax_escenarios_tol_line.set_visible(visible3)
                    if T is not None:
                        try:
                            self.ax_escenarios_tol_line.set_xdata([T, T])
                            if getattr(self, 'ax_escenarios_tol_label', None) is not None:
                                self.ax_escenarios_tol_label.set_position((T, -0.6))
                                self.ax_escenarios_tol_label.set_text(f'Tolerancia\n{currency_format(T)}')
                        except Exception:
                            pass
                    if getattr(self, 'ax_escenarios_tol_label', None) is not None:
                        self.ax_escenarios_tol_label.set_visible(visible3)
                    if getattr(self, 'canvas_escenarios', None) is not None:
                        self.canvas_escenarios.draw_idle()
            except Exception:
                pass
        except Exception:
            pass

    def actualizar_grafico_contribucion(self):
        """Actualiza el gráfico de contribución según el percentil seleccionado.
        
        Implementa contribución marginal: identifica las simulaciones donde la pérdida
        total está en el rango del percentil seleccionado y calcula la contribución
        promedio de cada evento en esas simulaciones específicas.
        """
        try:
            # Verificar que existen los datos necesarios
            if not hasattr(self, 'resultados_simulacion') or self.resultados_simulacion is None:
                return
            if not hasattr(self, 'combo_percentil_contrib') or self.combo_percentil_contrib is None:
                return
            if not hasattr(self, 'ax_contribucion') or self.ax_contribucion is None:
                return
            
            perdidas_totales = self.resultados_simulacion.get('perdidas_totales')
            perdidas_por_evento = self.resultados_simulacion.get('perdidas_por_evento')
            eventos_riesgo = self.resultados_simulacion.get('eventos_riesgo')
            
            if perdidas_totales is None or perdidas_por_evento is None or eventos_riesgo is None:
                return
            
            # Obtener el percentil seleccionado
            idx_seleccion = self.combo_percentil_contrib.currentIndex()
            texto_seleccion = self.combo_percentil_contrib.currentText()
            
            # Mapeo de índice a percentil (Media=0, P75=1, P80=2, P90=3, P95=4, P99=5)
            percentiles_map = {0: None, 1: 75, 2: 80, 3: 90, 4: 95, 5: 99}
            percentil = percentiles_map.get(idx_seleccion, None)
            
            # Calcular contribuciones según el método seleccionado
            contribuciones = []
            nombres_eventos = []
            
            if percentil is None:
                # Media: contribución promedio de cada evento
                for idx, perdidas_evento in enumerate(perdidas_por_evento):
                    contribucion = np.mean(perdidas_evento)
                    contribuciones.append(contribucion)
                    nombres_eventos.append(eventos_riesgo[idx]['nombre'])
                titulo_metrica = "Media"
                etiqueta_eje = "Contribución a la Pérdida Media ($)"
            else:
                # Contribución marginal al percentil:
                # 1. Encontrar el valor del percentil de pérdidas totales
                valor_percentil = np.percentile(perdidas_totales, percentil)
                
                # 2. Identificar simulaciones cercanas a ese percentil (±2.5%)
                margen_inferior = percentil - 2.5
                margen_superior = percentil + 2.5
                
                # Asegurar que los márgenes estén en rango válido
                margen_inferior = max(0, margen_inferior)
                margen_superior = min(100, margen_superior)
                
                umbral_inferior = np.percentile(perdidas_totales, margen_inferior)
                umbral_superior = np.percentile(perdidas_totales, margen_superior)
                
                # 3. Obtener índices de simulaciones en ese rango
                mascara = (perdidas_totales >= umbral_inferior) & (perdidas_totales <= umbral_superior)
                indices_percentil = np.where(mascara)[0]
                
                # Si hay muy pocas simulaciones, ampliar el rango
                if len(indices_percentil) < 50:
                    margen_inferior = max(0, percentil - 5)
                    margen_superior = min(100, percentil + 5)
                    umbral_inferior = np.percentile(perdidas_totales, margen_inferior)
                    umbral_superior = np.percentile(perdidas_totales, margen_superior)
                    mascara = (perdidas_totales >= umbral_inferior) & (perdidas_totales <= umbral_superior)
                    indices_percentil = np.where(mascara)[0]
                
                # 4. Calcular contribución promedio de cada evento en esas simulaciones
                for idx, perdidas_evento in enumerate(perdidas_por_evento):
                    if len(indices_percentil) > 0:
                        contribucion = np.mean(perdidas_evento[indices_percentil])
                    else:
                        contribucion = np.percentile(perdidas_evento, percentil)
                    contribuciones.append(contribucion)
                    nombres_eventos.append(eventos_riesgo[idx]['nombre'])
                
                titulo_metrica = f"P{percentil}"
                etiqueta_eje = f"Contribución al {titulo_metrica} ($)"
            
            # Limpiar el eje actual
            ax = self.ax_contribucion
            ax.clear()
            
            # Filtrar eventos sin contribución
            if not any(c > 0 for c in contribuciones):
                ax.text(0.5, 0.5, "No hay contribuciones para mostrar",
                       ha='center', va='center', transform=ax.transAxes, fontsize=12)
                self.canvas_contribucion.draw_idle()
                return
            
            # Crear DataFrame para el gráfico
            tornado_df = pd.DataFrame({
                'Evento de Riesgo': nombres_eventos,
                'Contribución': contribuciones
            })
            tornado_df = tornado_df[tornado_df['Contribución'] > 0]
            tornado_df['Porcentaje'] = (tornado_df['Contribución'] / tornado_df['Contribución'].sum()) * 100
            
            # Ordenar para el gráfico de tornado
            tornado_df.sort_values('Contribución', inplace=True, ascending=True)
            
            # Limitar a los 10 eventos más significativos
            if len(tornado_df) > 10:
                top_eventos = tornado_df.tail(10).copy()
                otros_eventos = tornado_df.head(len(tornado_df)-10)
                suma_otros = {
                    'Evento de Riesgo': f'Otros eventos ({len(otros_eventos)})',
                    'Contribución': otros_eventos['Contribución'].sum(),
                    'Porcentaje': otros_eventos['Porcentaje'].sum()
                }
                tornado_df = pd.concat([pd.DataFrame([suma_otros]), top_eventos])
                tornado_df.reset_index(drop=True, inplace=True)
            
            # Crear colores
            num_eventos = len(tornado_df)
            colores_eventos = []
            for i in range(num_eventos):
                if i == num_eventos - 1:
                    colores_eventos.append(MELI_AMARILLO)
                elif i == num_eventos - 2:
                    colores_eventos.append(MELI_AZUL_CORP)
                elif i == 0 and 'Otros eventos' in str(tornado_df.iloc[0]['Evento de Riesgo']):
                    colores_eventos.append('#CCCCCC')
                else:
                    ratio = i / max(1, num_eventos - 1)
                    colores_eventos.append(f'#{blend_colors(MELI_AZUL, MELI_AMARILLO, ratio)}')
            
            # Crear barras horizontales
            bars = ax.barh(tornado_df['Evento de Riesgo'], 
                          tornado_df['Contribución'], 
                          color=colores_eventos, 
                          edgecolor='white', 
                          alpha=0.85,
                          height=0.65)
            
            # Añadir etiquetas con valor y porcentaje
            for i, (bar, valor, porcentaje) in enumerate(zip(bars, 
                                                    tornado_df['Contribución'],
                                                    tornado_df['Porcentaje'])):
                width = bar.get_width()
                label_x_pos = width * 1.01
                
                if porcentaje >= 1.0:
                    label_text = f"{currency_format(valor)} ({porcentaje:.1f}%)"
                else:
                    label_text = f"{currency_format(valor)}"
                
                ax.text(label_x_pos, 
                       bar.get_y() + bar.get_height()/2, 
                       label_text, 
                       va='center',
                       fontsize=8,
                       fontweight='bold' if i >= num_eventos - 3 else 'normal', 
                       bbox=dict(facecolor='white', alpha=0.9, edgecolor=None))
            
            # Añadir línea vertical para la media de contribuciones
            mean_contrib = tornado_df['Contribución'].mean()
            ax.axvline(x=mean_contrib, color=MELI_ROJO, linestyle='--', alpha=0.7, 
                      label=f'Media: {currency_format(mean_contrib)}')
            
            # Resumen de contribuciones
            total_contrib = tornado_df['Contribución'].sum()
            top3_contrib = tornado_df.nlargest(3, 'Contribución')['Contribución'].sum()
            top3_pct = (top3_contrib / total_contrib) * 100 if total_contrib > 0 else 0
            
            # Texto resumen
            resumen_text = f"Total: {currency_format(total_contrib)}\nTop 3: {top3_pct:.0f}%"
            ax.text(0.02, 0.97, resumen_text, transform=ax.transAxes, 
                    fontsize=8, va='top', ha='left',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
            
            # Título y etiquetas
            ax.set_title(f'Contribución por Evento de Riesgo ({titulo_metrica})')
            ax.set_xlabel(etiqueta_eje)
            ax.set_ylabel('Evento de Riesgo')
            
            # Formatear el eje X para moneda
            ax.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
            
            # Aplicar estilo
            aplicar_estilo_meli(ax, tipo='barh')
            
            # Grid horizontal
            ax.grid(axis='x', linestyle='--', alpha=0.3)
            
            # Leyenda
            ax.legend(loc='lower right', fontsize=8, framealpha=0.9)
            
            # Ajustar layout
            self.fig_contribucion.tight_layout()
            
            # Redibujar
            self.canvas_contribucion.draw_idle()
            
        except Exception as e:
            print(f"[DEBUG] Error al actualizar gráfico de contribución: {e}")
            import traceback
            traceback.print_exc()

    def toggle_escala_log_excedencia(self, checked):
        """Cambia la escala del eje Y del gráfico de Excedencia entre lineal y logarítmica.
        
        Args:
            checked: True para escala logarítmica, False para lineal
        """
        try:
            if not hasattr(self, 'ax_exceed') or self.ax_exceed is None:
                return
            
            ax = self.ax_exceed
            
            if checked:
                # Cambiar a escala logarítmica
                ax.set_yscale('log')
                
                # Obtener los límites actuales del eje Y
                y_min, y_max = ax.get_ylim()
                
                # Generar ticks manuales en valores "redondos" para escala log
                import math
                # Encontrar el orden de magnitud
                if y_min > 0:
                    min_order = math.floor(math.log10(max(y_min, 1)))
                else:
                    min_order = 3  # Default $1,000
                max_order = math.ceil(math.log10(max(y_max, 1)))
                
                # Crear ticks en valores redondos
                ticks = []
                for order in range(min_order, max_order + 1):
                    base = 10 ** order
                    for mult in [1, 2, 5]:
                        val = base * mult
                        if y_min <= val <= y_max:
                            ticks.append(val)
                
                # Si hay muy pocos ticks, agregar más
                if len(ticks) < 4:
                    ticks = [y_min, (y_min * y_max) ** 0.5, y_max]
                
                # Establecer ticks manuales
                ax.set_yticks(ticks)
                
                # Crear etiquetas formateadas manualmente
                labels = [currency_format(t) for t in ticks]
                ax.set_yticklabels(labels)
                
                # Desactivar minor ticks para evitar más números
                ax.yaxis.set_minor_locator(plt.NullLocator())
                
            else:
                # Volver a escala lineal
                from matplotlib.ticker import AutoLocator
                ax.set_yscale('linear')
                ax.yaxis.set_major_locator(AutoLocator())
                ax.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
                ax.yaxis.set_minor_locator(AutoLocator())
            
            # Forzar actualización del layout
            if hasattr(self, 'fig_exceed') and self.fig_exceed is not None:
                self.fig_exceed.tight_layout()
            
            # Redibujar el canvas
            if hasattr(self, 'canvas_exceed') and self.canvas_exceed is not None:
                self.canvas_exceed.draw_idle()
                
        except Exception as e:
            print(f"[DEBUG] Error al cambiar escala de excedencia: {e}")

    def agregar_seccion_excedencia_si_falta(self):
        """Crea la sección 'Consulta de Excedencia' si no existe (o fue eliminada al limpiar resultados)."""
        try:
            # Si había un contenedor previo, eliminarlo para evitar referencias obsoletas
            existente = getattr(self, 'excedencia_controls_container', None)
            if existente is not None:
                try:
                    existente.setParent(None)
                    existente.deleteLater()
                except Exception:
                    pass

            # Si había una sección previa completa, eliminarla también
            existente_sec = getattr(self, 'excedencia_section_widget', None)
            if existente_sec is not None:
                try:
                    existente_sec.setParent(None)
                    existente_sec.deleteLater()
                except Exception:
                    pass

            # Crear nuevamente la sección en el contenedor fijo superior (holder)
            excedencia_sec = self.crear_seccion_colapsable("Consulta de Excedencia", parent_layout=self.excedencia_holder_layout)
            excedencia_layout = excedencia_sec["contenido_layout"]
            self.excedencia_section_widget = excedencia_sec["seccion"]
            # Asegurar que el holder esté debajo del título
            try:
                if hasattr(self, 'excedencia_holder') and self.excedencia_holder is not None:
                    parent_widget = self.excedencia_holder.parentWidget()
                    if parent_widget is not None and hasattr(parent_widget, 'layout'):
                        pl = parent_widget.layout()
                        if pl is not None:
                            pl.removeWidget(self.excedencia_holder)
                            pl.insertWidget(1, self.excedencia_holder)
            except Exception:
                pass

            self.excedencia_controls_container = QtWidgets.QWidget()
            ctrls_layout = QtWidgets.QHBoxLayout(self.excedencia_controls_container)
            ctrls_layout.setContentsMargins(0, 0, 0, 0)

            tol_label = QtWidgets.QLabel("Tolerancia ($):")
            self.tolerancia_ex_spin = NoScrollDoubleSpinBox()
            self.tolerancia_ex_spin.setDecimals(0)
            self.tolerancia_ex_spin.setRange(0, 1000000000000)
            self.tolerancia_ex_spin.setSingleStep(10000)
            self.tolerancia_ex_spin.setPrefix("$")
            self.tolerancia_ex_spin.setToolTip("Monto de tolerancia para calcular P[Impacto > T]")

            res_text_label = QtWidgets.QLabel("Probabilidad de excedencia:")
            self.exceedance_value_label = QtWidgets.QLabel("-")
            font_val = self.exceedance_value_label.font()
            font_val.setBold(True)
            self.exceedance_value_label.setFont(font_val)
            self.exceedance_value_label.setStyleSheet("color: #2F5597;")

            ctrls_layout.addWidget(tol_label)
            ctrls_layout.addWidget(self.tolerancia_ex_spin)
            ctrls_layout.addSpacing(12)
            ctrls_layout.addWidget(res_text_label)
            ctrls_layout.addWidget(self.exceedance_value_label)
            ctrls_layout.addStretch()

            excedencia_layout.addWidget(self.excedencia_controls_container)
            self.excedencia_controls_container.setEnabled(False)

            self.tolerancia_ex_spin.valueChanged.connect(self.actualizar_probabilidad_excedencia)
        except Exception:
            pass

    def apply_stylesheet(self):
        """Aplica un tema personalizado con mejor contraste y accesibilidad."""
        import os
        
        # Usar resource_path() para compatibilidad con PyInstaller
        enhanced_theme_path = resource_path(os.path.join("styles", "enhanced_theme.qss"))
        
        # Estilos adicionales para iconos y correcciones
        icon_styles = ""
        css_files = [
            resource_path(os.path.join("icons", "button-icon-fix.qss")),
            resource_path(os.path.join("icons", "icon-colors.css")),
            resource_path(os.path.join("icons", "button-fix.css")),
            resource_path(os.path.join("icons", "menu-styles.css")),
            # Nota: animations.css removido - no existe en el sistema
        ]
        
        # Cargar nuestro tema personalizado mejorado desde el archivo
        if os.path.exists(enhanced_theme_path):
            try:
                with open(enhanced_theme_path, 'r') as f:
                    theme_content = f.read()
                print("Tema mejorado cargado correctamente desde archivo")
                mercado_theme = theme_content
            except Exception as e:
                print(f"Error al cargar tema mejorado: {e}")
                # Como respaldo, usar tema incrustado
                mercado_theme = self._get_default_theme()
        else:
            print("Archivo de tema mejorado no encontrado, usando tema incrustado")
            mercado_theme = self._get_default_theme()
        
        # Cargar cada archivo CSS/QSS adicional para iconos y animaciones
        for css_file in css_files:
            if os.path.exists(css_file):
                try:
                    with open(css_file, 'r') as f:
                        icon_styles += "\n" + f.read()
                    print(f"Archivo de estilos cargado: {css_file}")
                except Exception as e:
                    print(f"Error al cargar archivo de estilos {css_file}: {e}")
            else:
                print(f"Archivo de estilos no encontrado: {css_file}")
        
        # Aplicar el estilo combinado a la aplicación
        self.setStyleSheet(mercado_theme + icon_styles)
        
        # Aplicar efectos animados usando nuestras clases personalizadas (opcional)
        # NOTA: ui_effects es un módulo opcional que no es crítico para la aplicación
        try:
            # Importar las clases de efectos UI
            from ui_effects import apply_hover_effects, AnimatedProgressBar, ResponsiveUI, RippleButton, FadeAnimation
            
            # Aplicar efectos de hover a botones (excepto los botones que ya tienen efecto de onda)
            apply_hover_effects(self)
            
            # Configurar UI responsiva
            self.responsive_ui = ResponsiveUI(self)
            
            # Registrar elementos importantes para UI responsiva
            for title_label in self.findChildren(QtWidgets.QLabel):
                if title_label.property("fontSizeHint") == "title":
                    self.responsive_ui.register_element('title', title_label)
                    
            # Reemplazar barra de progreso con versión animada
            old_progress_bar = self.progress_bar
            self.progress_bar = AnimatedProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setTextVisible(True)
            self.progress_bar.setFormat("%p%")
            parent_layout = old_progress_bar.parent().layout()
            for i in range(parent_layout.count()):
                item = parent_layout.itemAt(i)
                if item.widget() == old_progress_bar:
                    parent_layout.replaceWidget(old_progress_bar, self.progress_bar)
                    old_progress_bar.deleteLater()
                    break
                    
            # Reemplazar algunos botones principales con botones de efecto de onda
            main_buttons = []
            for button in self.findChildren(QtWidgets.QPushButton):
                if button.property("primary") == "true":
                    main_buttons.append(button)
                    
            for button in main_buttons:
                parent_layout = button.parent().layout()
                ripple_button = RippleButton(button.text())
                ripple_button.setIcon(button.icon())
                ripple_button.setProperty("primary", "true")
                ripple_button.clicked.connect(button.clicked.disconnect())
                
                for i in range(parent_layout.count()):
                    item = parent_layout.itemAt(i)
                    if item.widget() == button:
                        parent_layout.replaceWidget(button, ripple_button)
                        button.deleteLater()
                        break
                        
            print("Efectos de UI responsiva y animaciones aplicados correctamente")
            
        except ImportError as e:
            print(f"Módulo ui_effects no encontrado (opcional): {e}")
            # Los efectos avanzados no son críticos, la aplicación funciona sin ellos
        except Exception as e:
            print(f"Error al aplicar efectos UI avanzados: {e}")
            # Los efectos avanzados no son críticos, la aplicación funciona sin ellos
            
        # Aplicar traducciones en español neutro a todos los widgets
        self.aplicar_traducciones_a_widgets()
        
    def _get_default_theme(self):
        """Proporciona un tema por defecto en caso de que falle la carga del tema principal."""
        return """/* Estilo general para todos los widgets */
        QWidget {
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            font-size: {UI_FONT_MEDIUM}pt;
            color: #333333;
            background-color: #FFFFFF;
        }
        
        QMainWindow, QDialog {
            background-color: #FFFFFF;
        }
        
        /* Botones estándar con mejor contraste */
        QPushButton {
            background-color: #2F5597;  /* Azul corporativo */
            color: white;
            border: none;
            border-radius: 3px;
            padding: 10px 16px 10px 36px;  /* Espacio para el icono */
            font-size: {UI_FONT_NORMAL}pt;
            font-weight: 500;
            text-align: left;
            min-height: 35px;
            min-width: 120px;  /* Ancho mínimo para consistencia */
        }
        
        QPushButton:hover {
            background-color: #1F4287;  /* Azul más oscuro al pasar el mouse */
        }
        
        QPushButton:pressed {
            background-color: #0F3177;  /* Azul aún más oscuro al presionar */
        }
        
        QPushButton:disabled {
            background-color: #CCCCCC;
            color: #707070;  /* Mayor contraste en texto desactivado */
        }
        
        /* Botones de acción principal (ej. Ejecutar Simulación) */
        QPushButton[primary="true"] {
            background-color: #5C9F35;  /* Verde corporativo */
            color: white;
            font-weight: bold;
            min-height: 40px;  /* Botones principales ligeramente más grandes */
        }
        
        QPushButton[primary="true"]:hover {
            background-color: #4C8F25;  /* Verde más oscuro al pasar el mouse */
        }
        
        QPushButton[primary="true"]:pressed {
            background-color: #3C7F15;  /* Verde aún más oscuro al presionar */
        }
        
        /* Botones destructivos (ej. Eliminar) */
        QPushButton[destructive="true"] {
            background-color: #D9534F;  /* Rojo corporativo */
            color: white;
        }
        
        QPushButton[destructive="true"]:hover {
            background-color: #C9433F;  /* Rojo más oscuro al pasar el mouse */
        }
        
        QPushButton[destructive="true"]:pressed {
            background-color: #B9332F;  /* Rojo aún más oscuro al presionar */
        }
        
        /* Campos de entrada más claros */
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            padding: 8px;
            border: 1px solid #C0C0C0;
            border-radius: 3px;
            background-color: white;
            font-size: {UI_FONT_NORMAL}pt;
            selection-background-color: #2F5597;
            selection-color: white;
        }
        
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border: 1px solid #2F5597;
            background-color: #FAFAFA;
        }
        
        /* Combobox con mejor presentación */
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid #C0C0C0;
            background-color: #F5F5F5;
        }
        
        QComboBox::down-arrow {
            image: url(icons/arrow-down.png);
            width: 12px;
            height: 12px;
        }
        
        QComboBox QAbstractItemView {
            border: 1px solid #C0C0C0;
            selection-background-color: #2F5597;
            selection-color: white;
            outline: 0;
        }
        
        /* Encabezados y títulos */
        QLabel[fontSizeHint="title"] {
            font-size: {UI_FONT_HEADING}pt;
            font-weight: bold;
            color: #333333;
            padding: 10px;
        }
        
        /* Pestañas con estilo plano y moderno */
        QTabWidget::pane {
            border: none;
            background-color: white;
            border-radius: 4px;
        }
        
        QTabBar::tab {
            background: transparent;
            border: none;
            padding: 12px 16px;
            font-size: {UI_FONT_MEDIUM}pt;
            margin-right: 4px;
        }
        
        QTabBar::tab:selected {
            color: #0078D7;
        }
        
        /* Las definiciones de CSS se han migrado completamente a archivos externos */
        
        /* Scroll bars más discretos */
        QScrollBar:vertical {
            border: none;
            background: #F0F0F0;
            width: 12px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background: #C0C0C0;
            min-height: 20px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical:hover {
            background: #A0A0A0;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        
        /* Mejoras para tablas de percentiles */
        QTableView, QTableWidget {
            gridline-color: #E0E0E0;
            background-color: white;
            selection-background-color: #E9F2FD;
            selection-color: #0064c8;
            border: 1px solid #E0E0E0;
            border-radius: 2px;
            alternate-background-color: #F9F9F9;  /* Color alterno para facilitar la lectura de filas */
        }
        
        QTableView::item, QTableWidget::item {
            padding: 10px;
            font-size: {UI_FONT_NORMAL}pt;
        }
        
        QHeaderView::section {
            background-color: #F2F2F2;
            border: 1px solid #E0E0E0;
            padding: 12px 24px;
            font-weight: bold;
            color: #1F497D;  /* Azul más oscuro para encabezados */
        }
        
        /* Aumentar espacio para mostrar datos completos */
        QTableView QHeaderView {
            font-size: {UI_FONT_NORMAL}pt;
        }
        
        /* Secciones colapsables mejoradas */
        QGroupBox {
            border: 1px solid #D0D0D0;
            border-radius: 3px;
            margin-top: 14px;
            padding-top: 14px;
            font-weight: bold;
            color: #2F5597;  /* Color corporativo azul */
            background-color: #FDFDFD;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 5px;
            background-color: white;
        }
        
        /* Tooltips más informativos */
        QToolTip {
            font-size: {UI_FONT_BODY}pt;
            padding: 8px;
            border: 1px solid #D0D0D0;
            background-color: #FFFFEE;  /* Amarillo muy claro */
            color: #333333;
            border-radius: 2px;
            max-width: 300px;  /* Ancho máximo para tooltips largos */
        }
        """
        # Aplicar el estilo combinado a la aplicación
        self.setStyleSheet(mercado_theme + icon_styles)

    def agregar_evento_popup(self):
        self.editar_evento_popup(new=True)

    def editar_evento_desde_tabla(self, row, column):
        """Método para manejar el doble clic en un evento de la tabla.
        Deselecciona todos los eventos seleccionados y luego llama a editar_evento_popup."""
        # Deseleccionar todas las filas seleccionadas
        self.eventos_table.clearSelection()
        
        # Seleccionar solo la fila que se va a editar (opcional)
        self.eventos_table.selectRow(row)
        
        # Llamar a la función de edición con la fila correspondiente
        self.editar_evento_popup(new=False, row=row)

    def editar_evento_popup(self, new=False, row=None):
        """Método para agregar o editar un evento de riesgo."""
        evento_data = None

        if not new:
            if row is not None:
                # Llamado por doble clic (o similar pasando 'row')
                if 0 <= row < len(self.eventos_riesgo): 
                    evento_data = self.eventos_riesgo[row]
                else:
                    print(f"Error: La fila {row} está fuera de rango.")
                    return
            else:
                # Seleccionado mediante el botón editar
                selected_items = self.eventos_table.selectedItems()
                if not selected_items:
                    QtWidgets.QMessageBox.warning(self, "Advertencia", "Seleccione un evento para editar.")
                    return
                if len(selected_items) > 1:
                    QtWidgets.QMessageBox.warning(self, "Advertencia", "Seleccione solo UN evento para editar con el botón.")
                    return
                # Si llegamos aquí, hay exactamente una fila seleccionada
                row = selected_items[0].row()
                evento_data = self.eventos_riesgo[row]

        else: # new es True, esto no cambia
            evento_data = None # Para un evento nuevo, no hay datos previos

        _s = lambda v, d='': str(v) if v is not None else d

        # Crear diálogo con tamaño optimizado y scroll
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Agregar Evento de Riesgo" if new else "Editar Evento de Riesgo")
        dialog.setMinimumWidth(670)  # Ancho ligeramente mayor para scroll
        dialog.setMinimumHeight(650)  # Altura aumentada
        dialog.resize(670, 750)  # Tamaño inicial recomendado
        
        # Estilo moderno para ComboBox
        combobox_style = """
            QComboBox {
                border: 2px solid #d0d0d0;
                border-radius: 6px;
                padding: 6px 10px;
                background-color: white;
                min-height: 26px;
                font-size: {UI_FONT_BODY}pt;
                selection-background-color: #2F5597;
            }
            QComboBox:hover {
                border: 2px solid #2F5597;
                background-color: #f8f9fa;
            }
            QComboBox:focus {
                border: 2px solid #2F5597;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
                background: transparent;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #666;
                margin-right: 10px;
            }
            QComboBox::down-arrow:hover {
                border-top-color: #2F5597;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #d0d0d0;
                border-radius: 6px;
                background-color: white;
                selection-background-color: #2F5597;
                selection-color: white;
                padding: 4px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 10px;
                border-radius: 3px;
                min-height: 25px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e8f0fe;
                color: #2F5597;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #2F5597;
                color: white;
            }
        """
        dialog.setStyleSheet(combobox_style)
        
        # Layout principal del diálogo
        dialog_main_layout = QtWidgets.QVBoxLayout(dialog)
        dialog_main_layout.setSpacing(5)
        dialog_main_layout.setContentsMargins(10, 10, 10, 10)

        # Nombre del Evento (arriba, fuera del scroll) - Con mayor prominencia
        nombre_label = QtWidgets.QLabel("Nombre del Evento:")
        nombre_label.setStyleSheet("font-size: {UI_FONT_BASE}pt; font-weight: bold; color: #2F5597;")
        dialog_main_layout.addWidget(nombre_label)
        
        nombre_var = QtWidgets.QLineEdit(evento_data['nombre'] if evento_data else "")
        nombre_var.setMinimumWidth(200)  # Ancho ajustado para ventana más estrecha
        nombre_var.setStyleSheet("font-size: {UI_FONT_BASE}pt; padding: 6px;")
        nombre_var.setPlaceholderText("Ej: Falla de servidor principal")
        dialog_main_layout.addWidget(nombre_var)
        dialog_main_layout.addSpacing(10)  # Espacio después del nombre
        
        # Crear scroll area para el contenido principal
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        # Widget contenedor del scroll
        scroll_content = QtWidgets.QWidget()
        dialog_layout = QtWidgets.QVBoxLayout(scroll_content)
        dialog_layout.setSpacing(10)
        dialog_layout.setContentsMargins(0, 0, 10, 0)  # Margen derecho para scroll

        # Distribución de Severidad
        sev_group = QtWidgets.QGroupBox("¿Cuál es el IMPACTO cuando ocurre?")
        sev_group.setStyleSheet("QGroupBox::title { font-weight: bold; font-size: {UI_FONT_BODY}pt; }")
        sev_layout = QtWidgets.QVBoxLayout(sev_group)

        opciones_severidad = [("Normal", 1), ("LogNormal", 2), ("PERT", 3), ("Pareto", 4), ("Uniforme", 5)]
        distribuciones_severidad = [op[0] for op in opciones_severidad]
        distribucion_severidad_label = QtWidgets.QLabel("Tipo de distribución:")
        sev_layout.addWidget(distribucion_severidad_label)
        sev_combobox = NoScrollComboBox()
        sev_combobox.addItems(distribuciones_severidad)
        if evento_data:
            sev_combobox.setCurrentIndex(evento_data['sev_opcion'] - 1)
        sev_layout.addWidget(sev_combobox)

        # --- Botón Modo Avanzado ---
        modo_avanzado_activo = [False]  # Usamos lista para permitir modificación en closure
        # Si estamos editando un evento con parámetros directos, activar modo avanzado
        if evento_data and evento_data.get('sev_input_method') == 'direct':
            modo_avanzado_activo[0] = True
        
        modo_avanzado_btn = QtWidgets.QPushButton("⚙ Modo Avanzado")
        modo_avanzado_btn.setStyleSheet("""
            QPushButton {
                background-color: #d0d0d0;
                color: #333;
                border: 1px solid #aaa;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
        """)
        sev_layout.addWidget(modo_avanzado_btn)

        # --- Selector de Método de Entrada (Solo visible en Modo Avanzado) ---
        sev_input_method_label = QtWidgets.QLabel("Método de Entrada de Parámetros:")
        sev_input_method_combo = NoScrollComboBox()
        sev_input_method_combo.addItems(["Mínimo / Más Probable / Máximo", "Parámetros Directos"])
        # Leer el método guardado si estamos editando
        current_input_method_index = 0 # Por defecto: Min/Mode/Max
        if evento_data and evento_data.get('sev_input_method') == 'direct':
             current_input_method_index = 1
        sev_input_method_combo.setCurrentIndex(current_input_method_index)

        sev_layout.addWidget(sev_input_method_label)
        sev_layout.addWidget(sev_input_method_combo)
        
        # Ocultar por defecto (se mostrarán solo en modo avanzado para ciertas distribuciones)
        sev_input_method_label.hide()
        sev_input_method_combo.hide()

        # --- MODIFICADO: Usaremos un QStackedWidget para cambiar entre los grupos de parámetros ---
        sev_params_stack = QtWidgets.QStackedWidget()
        sev_params_stack.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        
        # Función para ajustar el tamaño del stack al widget visible
        def adjust_sev_stack_size():
            current_widget = sev_params_stack.currentWidget()
            if current_widget:
                # Forzar actualización de layout antes de calcular tamaño
                current_widget.updateGeometry()
                # Obtener el tamaño mínimo necesario del widget actual
                height = current_widget.sizeHint().height()
                # Establecer altura fija basada en el contenido
                sev_params_stack.setMaximumHeight(max(height + 10, 50))  # +10 padding
                sev_params_stack.setMinimumHeight(max(height + 10, 50))
                sev_params_stack.updateGeometry()
        
        sev_layout.addWidget(sev_params_stack) # Añadimos el StackedWidget al layout principal de severidad

        # --- Grupo 0: Parámetros Min/Mode/Max  ---
        min_mode_max_widget = QtWidgets.QWidget()
        min_mode_max_layout = QtWidgets.QFormLayout(min_mode_max_widget)
        min_mode_max_layout.setContentsMargins(0, 5, 0, 5)

        sev_min_var = QtWidgets.QLineEdit(_s(evento_data.get('sev_minimo')) if evento_data else "")
        sev_mas_probable_var = QtWidgets.QLineEdit(_s(evento_data.get('sev_mas_probable')) if evento_data else "")
        sev_max_var = QtWidgets.QLineEdit(_s(evento_data.get('sev_maximo')) if evento_data else "")

        min_mode_max_layout.addRow("Valor Mínimo:", sev_min_var)
        sev_mas_probable_label = QtWidgets.QLabel("Valor Más Probable:") # Guardamos referencia para ocultar/mostrar
        min_mode_max_layout.addRow(sev_mas_probable_label, sev_mas_probable_var)
        min_mode_max_layout.addRow("Valor Máximo:", sev_max_var)
        
        sev_params_stack.addWidget(min_mode_max_widget) # Añadimos este widget al stack (índice 0)

        # --- Grupo 1: Parámetros Directos Lognormal ---
        direct_ln_widget = QtWidgets.QWidget()
        direct_ln_layout = QtWidgets.QFormLayout(direct_ln_widget)
        # Obtener valores guardados si existen
        ln_params = evento_data.get('sev_params_direct', {}) if evento_data and evento_data.get('sev_input_method') == 'direct' and sev_combobox.currentText() == "LogNormal" else {}

        # Selector de tipo de parametrización
        sev_ln_param_mode_combo = NoScrollComboBox()
        sev_ln_param_mode_combo.addItems(["s/scale (SciPy)", "mean/std", "mu/sigma (ln X)"])
        # Inferir modo desde claves existentes
        inicial_mode_index = 0
        if 'mean' in ln_params and 'std' in ln_params:
            inicial_mode_index = 1
        elif 'mu' in ln_params and 'sigma' in ln_params:
            inicial_mode_index = 2
        sev_ln_param_mode_combo.setCurrentIndex(inicial_mode_index)

        # Stacked con campos por modo
        sev_ln_stack = QtWidgets.QStackedWidget()
        # Modo 0: s/scale
        ln_mode0_widget = QtWidgets.QWidget()
        ln_mode0_layout = QtWidgets.QFormLayout(ln_mode0_widget)
        sev_ln_s_var = QtWidgets.QLineEdit(_s(ln_params.get('s')))
        sev_ln_scale_var = QtWidgets.QLineEdit(_s(ln_params.get('scale')))
        ln_mode0_layout.addRow("Shape (s o sigma):", sev_ln_s_var)
        ln_mode0_layout.addRow("Scale (exp(mu)):", sev_ln_scale_var)
        sev_ln_stack.addWidget(ln_mode0_widget)
        # Modo 1: mean/std
        ln_mode1_widget = QtWidgets.QWidget()
        ln_mode1_layout = QtWidgets.QFormLayout(ln_mode1_widget)
        sev_ln_mean_var = QtWidgets.QLineEdit(_s(ln_params.get('mean')))
        sev_ln_std_var = QtWidgets.QLineEdit(_s(ln_params.get('std')))
        ln_mode1_layout.addRow("Media (mean):", sev_ln_mean_var)
        ln_mode1_layout.addRow("Desviación (std):", sev_ln_std_var)
        sev_ln_stack.addWidget(ln_mode1_widget)
        # Modo 2: mu/sigma
        ln_mode2_widget = QtWidgets.QWidget()
        ln_mode2_layout = QtWidgets.QFormLayout(ln_mode2_widget)
        sev_ln_mu_var = QtWidgets.QLineEdit(_s(ln_params.get('mu')))
        sev_ln_sigma_var = QtWidgets.QLineEdit(_s(ln_params.get('sigma')))
        ln_mode2_layout.addRow("mu (ln X):", sev_ln_mu_var)
        ln_mode2_layout.addRow("sigma (ln X):", sev_ln_sigma_var)
        sev_ln_stack.addWidget(ln_mode2_widget)

        sev_ln_stack.setCurrentIndex(inicial_mode_index)
        sev_ln_param_mode_combo.currentIndexChanged.connect(sev_ln_stack.setCurrentIndex)

        # Campo común loc
        sev_ln_loc_var = QtWidgets.QLineEdit(_s(ln_params.get('loc'), '0'))

        direct_ln_layout.addRow("Tipo de parametrización:", sev_ln_param_mode_combo)
        direct_ln_layout.addRow(sev_ln_stack)
        direct_ln_layout.addRow("Location (loc, opcional):", sev_ln_loc_var)
        sev_params_stack.addWidget(direct_ln_widget) # Añadimos este widget al stack (índice 1)

        # --- Grupo 2: Parámetros Directos GPD ---
        direct_gpd_widget = QtWidgets.QWidget()
        direct_gpd_layout = QtWidgets.QFormLayout(direct_gpd_widget)
        # Obtener valores guardados si existen
        gpd_params = evento_data.get('sev_params_direct', {}) if evento_data and evento_data.get('sev_input_method') == 'direct' and sev_combobox.currentText() == "Pareto" else {}

        sev_gpd_c_var = QtWidgets.QLineEdit(_s(gpd_params.get('c')))
        sev_gpd_scale_var = QtWidgets.QLineEdit(_s(gpd_params.get('scale')))
        sev_gpd_loc_var = QtWidgets.QLineEdit(_s(gpd_params.get('loc')))

        direct_gpd_layout.addRow("Shape (c o xi):", sev_gpd_c_var)
        direct_gpd_layout.addRow("Scale (beta):", sev_gpd_scale_var)
        direct_gpd_layout.addRow("Location (loc o umbral):", sev_gpd_loc_var)
        sev_params_stack.addWidget(direct_gpd_widget) # Añadimos este widget al stack (índice 2)

        # --- Grupo 3: Parámetros Directos Normal (mean/std) ---
        direct_norm_widget = QtWidgets.QWidget()
        direct_norm_layout = QtWidgets.QFormLayout(direct_norm_widget)
        norm_params = evento_data.get('sev_params_direct', {}) if evento_data and evento_data.get('sev_input_method') == 'direct' and sev_combobox.currentText() == "Normal" else {}
        sev_norm_mean_var = QtWidgets.QLineEdit(_s(norm_params.get('mean', norm_params.get('mu'))))
        sev_norm_std_var = QtWidgets.QLineEdit(_s(norm_params.get('std', norm_params.get('sigma'))))
        direct_norm_layout.addRow("Media (mean):", sev_norm_mean_var)
        direct_norm_layout.addRow("Desviación (std):", sev_norm_std_var)
        sev_params_stack.addWidget(direct_norm_widget) # Índice 3

        # --- Límite superior de severidad (opcional) ---
        sev_limite_layout = QtWidgets.QHBoxLayout()
        sev_limite_label = QtWidgets.QLabel("Límite superior por ocurrencia ($):")
        sev_limite_label.setToolTip("Máximo impacto posible por ocurrencia individual. Dejar vacío = sin límite.")
        sev_limite_var = QtWidgets.QLineEdit(
            str(evento_data.get('sev_limite_superior', '')) if evento_data and evento_data.get('sev_limite_superior') is not None else ""
        )
        sev_limite_var.setPlaceholderText("Sin límite")
        sev_limite_var.setToolTip("Dejar vacío = sin límite")
        sev_limite_layout.addWidget(sev_limite_label)
        sev_limite_layout.addWidget(sev_limite_var)
        sev_layout.addLayout(sev_limite_layout)

        # Creamos layout vertical para las distribuciones (apiladas)
        distribuciones_layout = QtWidgets.QVBoxLayout()
        distribuciones_layout.addWidget(sev_group)  # Añadimos distribución de impacto arriba

        # --- Función para toggle Modo Avanzado ---
        def toggle_modo_avanzado():
            modo_avanzado_activo[0] = not modo_avanzado_activo[0]
            if modo_avanzado_activo[0]:
                modo_avanzado_btn.setText("◄ Modo Simple")
                modo_avanzado_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #5C9F35;
                        color: white;
                        border: 1px solid #4a7d2a;
                        padding: 5px 10px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #4a7d2a;
                    }
                """)
            else:
                modo_avanzado_btn.setText("⚙ Modo Avanzado")
                modo_avanzado_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #d0d0d0;
                        color: #333;
                        border: 1px solid #aaa;
                        padding: 5px 10px;
                        border-radius: 3px;
                        font-weight: normal;
                    }
                    QPushButton:hover {
                        background-color: #c0c0c0;
                    }
                """)
                # Al salir del modo avanzado, forzar método Min/Mode/Max
                sev_input_method_combo.setCurrentIndex(0)
            # Actualizar visibilidad de parámetros
            actualizar_parametros_severidad()

        # --- MODIFICADO: Función para actualizar visibilidad de parámetros de Severidad ---
        def actualizar_parametros_severidad():
            dist_seleccionada_index = sev_combobox.currentIndex()
            dist_nombre = opciones_severidad[dist_seleccionada_index][0] # "Normal", "LogNormal", etc.
            input_method_index = sev_input_method_combo.currentIndex() # 0: Min/Mode/Max, 1: Directo

            # Ocultar/Mostrar selector de método SOLO si modo avanzado está activo
            if modo_avanzado_activo[0] and dist_nombre in ["Normal", "LogNormal", "Pareto"]:
                sev_input_method_label.show()
                sev_input_method_combo.show()
            else:
                sev_input_method_label.hide()
                sev_input_method_combo.hide()

            # Cambiar el widget visible en el StackedWidget
            if modo_avanzado_activo[0] and dist_nombre == "LogNormal" and input_method_index == 1: # LogNormal Directo
                sev_params_stack.setCurrentIndex(1)
            elif modo_avanzado_activo[0] and dist_nombre == "Pareto" and input_method_index == 1: # GPD Directo
                 sev_params_stack.setCurrentIndex(2)
            elif modo_avanzado_activo[0] and dist_nombre == "Normal" and input_method_index == 1: # Normal Directo
                 sev_params_stack.setCurrentIndex(3)
            else: # Cualquier otra distribución o Lognormal/GPD con Min/Mode/Max
                sev_params_stack.setCurrentIndex(0)
                # Adicionalmente, ocultar 'Mas Probable' para Uniforme dentro del widget Min/Mode/Max
                if dist_nombre == "Uniforme":
                    sev_mas_probable_label.hide()
                    sev_mas_probable_var.hide()
                else:
                    sev_mas_probable_label.show()
                    sev_mas_probable_var.show()
                
                # Forzar actualización después de ocultar/mostrar
                min_mode_max_widget.adjustSize()
            
            # Forzar actualización del widget y ajuste de tamaño
            QtCore.QTimer.singleShot(20, adjust_sev_stack_size)

        # Conectar señales para actualizar la UI cuando cambie la distribución o el método
        modo_avanzado_btn.clicked.connect(toggle_modo_avanzado)
        sev_combobox.currentIndexChanged.connect(actualizar_parametros_severidad)
        sev_input_method_combo.currentIndexChanged.connect(actualizar_parametros_severidad)
        
        # Inicializar estado del botón si modo avanzado está activo
        if modo_avanzado_activo[0]:
            modo_avanzado_btn.setText("◄ Modo Simple")
            modo_avanzado_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5C9F35;
                    color: white;
                    border: 1px solid #4a7d2a;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #4a7d2a;
                }
            """)
        
        # Llamada inicial para configurar la UI correctamente al abrir el diálogo
        actualizar_parametros_severidad()

        # Distribución de Frecuencia
        freq_group = QtWidgets.QGroupBox("¿Con qué FRECUENCIA ocurre?")
        freq_group.setStyleSheet("QGroupBox::title { font-weight: bold; font-size: {UI_FONT_BODY}pt; }")
        freq_layout = QtWidgets.QVBoxLayout(freq_group)

        opciones_frecuencia = [("Poisson", 1), ("Binomial", 2), ("Bernoulli", 3), ("Poisson-Gamma", 4), ("Beta", 5)]
        distribuciones_frecuencia = [op[0] for op in opciones_frecuencia]
        distribucion_frecuencia_label = QtWidgets.QLabel("Tipo de distribución:")
        freq_layout.addWidget(distribucion_frecuencia_label)
        freq_combobox = NoScrollComboBox()
        freq_combobox.addItems(distribuciones_frecuencia)
        if evento_data:
            freq_combobox.setCurrentIndex(evento_data['freq_opcion'] - 1)
        freq_layout.addWidget(freq_combobox)

        # Parámetros de Frecuencia
        freq_params_stack = QtWidgets.QStackedWidget()
        freq_params_stack.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        
        # Función para ajustar el tamaño del stack al widget visible
        def adjust_freq_stack_size():
            current_widget = freq_params_stack.currentWidget()
            if current_widget:
                # Forzar actualización de layout antes de calcular tamaño
                current_widget.updateGeometry()
                # Obtener el tamaño mínimo necesario del widget actual
                height = current_widget.sizeHint().height()
                # Establecer altura fija basada en el contenido
                freq_params_stack.setMaximumHeight(max(height + 10, 50))  # +10 padding
                freq_params_stack.setMinimumHeight(max(height + 10, 50))
                freq_params_stack.updateGeometry()

        # Parámetros Poisson
        poisson_widget = QtWidgets.QWidget()
        poisson_layout = QtWidgets.QFormLayout(poisson_widget)
        poisson_layout.setContentsMargins(0, 5, 0, 5)
        tasa_var = QtWidgets.QLineEdit(_s(evento_data.get('tasa')) if evento_data else "")
        poisson_layout.addRow("Tasa Media (λ):", tasa_var)
        freq_params_stack.addWidget(poisson_widget)

        # Parámetros Binomial
        binomial_widget = QtWidgets.QWidget()
        binomial_layout = QtWidgets.QFormLayout(binomial_widget)
        binomial_layout.setContentsMargins(0, 5, 0, 5)
        num_eventos_var = QtWidgets.QLineEdit(_s(evento_data.get('num_eventos')) if evento_data else "")
        prob_exito_var = QtWidgets.QLineEdit(_s(evento_data.get('prob_exito')) if evento_data else "")
        binomial_layout.addRow("Número de Eventos Posibles (n):", num_eventos_var)
        binomial_layout.addRow("Probabilidad de Éxito (p):", prob_exito_var)
        freq_params_stack.addWidget(binomial_widget)

        # Parámetros Bernoulli
        bernoulli_widget = QtWidgets.QWidget()
        bernoulli_layout = QtWidgets.QFormLayout(bernoulli_widget)
        bernoulli_layout.setContentsMargins(0, 5, 0, 5)
        prob_exito_var_bern = QtWidgets.QLineEdit(_s(evento_data.get('prob_exito')) if evento_data else "")
        bernoulli_layout.addRow("Probabilidad de Éxito (p):", prob_exito_var_bern)
        freq_params_stack.addWidget(bernoulli_widget)
        
        # Parámetros Poisson-Gamma
        poisson_gamma_widget = QtWidgets.QWidget()
        poisson_gamma_layout = QtWidgets.QFormLayout(poisson_gamma_widget)
        poisson_gamma_layout.setContentsMargins(0, 5, 0, 5)
        
        # Extraer valores previos si existen
        pg_minimo_var = QtWidgets.QLineEdit(_s(evento_data.get('pg_minimo')) if evento_data else "")
        pg_mas_probable_var = QtWidgets.QLineEdit(_s(evento_data.get('pg_mas_probable')) if evento_data else "")
        pg_maximo_var = QtWidgets.QLineEdit(_s(evento_data.get('pg_maximo')) if evento_data else "")
        pg_confianza_var = QtWidgets.QLineEdit(_s(evento_data.get('pg_confianza'), '80') if evento_data else "80")
        
        # Campos para Poisson-Gamma
        poisson_gamma_layout.addRow("Valor mínimo de ocurrencia:", pg_minimo_var)
        poisson_gamma_layout.addRow("Valor más probable de ocurrencia:", pg_mas_probable_var)
        poisson_gamma_layout.addRow("Valor máximo de ocurrencia:", pg_maximo_var)
        poisson_gamma_layout.addRow("Confianza asociada al rango (%):", pg_confianza_var)
        
        freq_params_stack.addWidget(poisson_gamma_widget)
        
        # Parámetros Beta para probabilidad anual
        beta_widget = QtWidgets.QWidget()
        beta_layout = QtWidgets.QFormLayout(beta_widget)
        beta_layout.setContentsMargins(0, 5, 0, 5)
        
        # Extraer valores previos si existen
        beta_minimo_var = QtWidgets.QLineEdit(_s(evento_data.get('beta_minimo')) if evento_data else "")
        beta_mas_probable_var = QtWidgets.QLineEdit(_s(evento_data.get('beta_mas_probable')) if evento_data else "")
        beta_maximo_var = QtWidgets.QLineEdit(_s(evento_data.get('beta_maximo')) if evento_data else "")
        beta_confianza_var = QtWidgets.QLineEdit(_s(evento_data.get('beta_confianza'), '80') if evento_data else "80")
        
        # Campos para distribución Beta
        beta_layout.addRow("Probabilidad mínima razonable (%):", beta_minimo_var)
        beta_layout.addRow("Probabilidad más probable (%):", beta_mas_probable_var)
        beta_layout.addRow("Probabilidad máxima razonable (%):", beta_maximo_var)
        beta_layout.addRow("Confianza asociada al rango (%):", beta_confianza_var)
        
        freq_params_stack.addWidget(beta_widget)

        freq_layout.addWidget(freq_params_stack)

        # --- Límite superior de frecuencia (opcional) ---
        freq_limite_layout = QtWidgets.QHBoxLayout()
        freq_limite_label = QtWidgets.QLabel("Máximo de ocurrencias por año:")
        freq_limite_label.setToolTip("Máximo número de ocurrencias posibles por año. Dejar vacío = sin límite.")
        freq_limite_var = QtWidgets.QLineEdit(
            str(evento_data.get('freq_limite_superior', '')) if evento_data and evento_data.get('freq_limite_superior') is not None else ""
        )
        freq_limite_var.setPlaceholderText("Sin límite")
        freq_limite_var.setToolTip("Dejar vacío = sin límite")
        freq_limite_layout.addWidget(freq_limite_label)
        freq_limite_layout.addWidget(freq_limite_var)
        freq_layout.addLayout(freq_limite_layout)

        distribuciones_layout.addWidget(freq_group)  # Añadimos distribución de frecuencia abajo
        
        # Añadir el layout vertical de distribuciones al layout principal
        dialog_layout.addLayout(distribuciones_layout)

        # Función para actualizar parámetros de Frecuencia
        def actualizar_parametros_frecuencia():
            opcion = freq_combobox.currentIndex() + 1
            if opcion == 1:
                freq_params_stack.setCurrentIndex(0)  # Poisson
            elif opcion == 2:
                freq_params_stack.setCurrentIndex(1)  # Binomial
            elif opcion == 3:
                freq_params_stack.setCurrentIndex(2)  # Bernoulli
            elif opcion == 4:
                freq_params_stack.setCurrentIndex(3)  # Poisson-Gamma
            elif opcion == 5:
                freq_params_stack.setCurrentIndex(4)  # Beta
            
            # Mostrar/ocultar límite de frecuencia según distribución
            freq_limite_visible = opcion in (1, 2, 4)  # Poisson, Binomial, Poisson-Gamma
            freq_limite_label.setVisible(freq_limite_visible)
            freq_limite_var.setVisible(freq_limite_visible)
            
            # Forzar actualización del widget y ajuste de tamaño
            QtCore.QTimer.singleShot(10, adjust_freq_stack_size)
        freq_combobox.currentIndexChanged.connect(actualizar_parametros_frecuencia)
        actualizar_parametros_frecuencia()

        # ====================================================================
        # SECCIÓN: ESCALAMIENTO DE SEVERIDAD POR FRECUENCIA
        # ====================================================================
        sev_freq_config, _on_freq_dist_changed = _crear_seccion_escalamiento_ui(dialog_layout, evento_data)
        
        # Conectar cambio de distribución de frecuencia para habilitar/deshabilitar
        def _actualizar_escalamiento_por_freq():
            freq_opcion = freq_combobox.currentIndex() + 1
            _on_freq_dist_changed(freq_opcion)
        freq_combobox.currentIndexChanged.connect(_actualizar_escalamiento_por_freq)
        # Inicializar estado según distribución actual
        _actualizar_escalamiento_por_freq()

        # Guardar los vínculos existentes (movido antes para contar)
        vinculos_existentes = []
        if evento_data and 'vinculos' in evento_data:
            vinculos_existentes = copy.deepcopy(evento_data['vinculos'])
        elif evento_data and 'eventos_padres' in evento_data:
            # Convertir formato antiguo al nuevo
            tipo = evento_data.get('tipo_dependencia', 'AND')
            for padre_id in evento_data['eventos_padres']:
                vinculos_existentes.append({'id_padre': padre_id, 'tipo': tipo, 'probabilidad': 100, 'factor_severidad': 1.0, 'umbral_severidad': 0})
        
        # Sección de vínculos colapsable
        vinculos_collapsed = [True]  # Colapsado por defecto
        
        # Frame contenedor para vínculos
        vinculos_frame = QtWidgets.QFrame()
        vinculos_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        vinculos_frame.setStyleSheet("QFrame { border: 1px solid #aaa; border-radius: 3px; }")
        vinculos_frame_layout = QtWidgets.QVBoxLayout(vinculos_frame)
        vinculos_frame_layout.setContentsMargins(0, 0, 0, 0)
        vinculos_frame_layout.setSpacing(0)
        
        # Header clickeable
        vinculos_header_btn = QtWidgets.QPushButton()
        num_vinculos = len(vinculos_existentes)
        vinculos_header_btn.setText(f"▷ Vínculos con otros eventos ({num_vinculos})")
        vinculos_header_btn.setStyleSheet("""
            QPushButton {
                background-color: #d5d5d5;
                color: #333;
                border: none;
                border-bottom: 1px solid #aaa;
                text-align: left;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c5c5c5;
            }
        """)
        vinculos_frame_layout.addWidget(vinculos_header_btn)
        
        # Contenedor de contenido (colapsable)
        vinculos_content_widget = QtWidgets.QWidget()
        vinculos_layout = QtWidgets.QVBoxLayout(vinculos_content_widget)
        vinculos_layout.setContentsMargins(10, 10, 10, 10)
        
        # Explicación compacta con tooltip
        explicacion_vinculos = QtWidgets.QLabel(
            "💡 <b>AND</b>: requiere el vinculado | <b>OR</b>: al menos uno | <b>EXCLUYE</b>: solo si NO ocurre. <b>Prob</b>: % activación. <b>Sev</b>: multiplicador severidad. <b>Umbral</b>: pérdida mínima del padre."
        )
        explicacion_vinculos.setWordWrap(True)
        explicacion_vinculos.setStyleSheet("background-color: #fffacd; padding: 5px; border-radius: 3px; font-size: {UI_FONT_BODY}pt;")
        vinculos_layout.addWidget(explicacion_vinculos)
        
        # Tabla para gestionar vínculos con tamaño adecuado
        vinculos_table = QtWidgets.QTableWidget()
        vinculos_table.setColumnCount(6)
        vinculos_table.setHorizontalHeaderLabels(["Evento", "Tipo", "Prob.(%)", "Sev.(x)", "Umbral($)", "Eliminar"])
        vinculos_table.horizontalHeader().setStretchLastSection(False)
        vinculos_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)  # Primera columna elástica
        vinculos_table.setColumnWidth(1, 140)  # Ancho para 'Tipo'
        vinculos_table.setColumnWidth(2, 80)   # Ancho para 'Prob.(%)'
        vinculos_table.setColumnWidth(3, 80)   # Ancho para 'Sev.(x)'
        vinculos_table.setColumnWidth(4, 110)  # Ancho para 'Umbral($)'
        vinculos_table.setColumnWidth(5, 80)   # Ancho para 'Eliminar'
        vinculos_table.setMinimumHeight(180)  # Más altura para ver varios vínculos
        # Configurar altura de filas y otros parámetros
        vinculos_table.verticalHeader().setDefaultSectionSize(36)  # Altura de fila aumentada más
        vinculos_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)  # Fijar altura de filas
        # Eliminar espacio entre celdas
        vinculos_table.setShowGrid(True)
        vinculos_table.setStyleSheet("QTableWidget::item { padding: 0px; }")
        vinculos_layout.addWidget(vinculos_table)
        
        # Panel de botones para vínculos con mejor organización
        vinculos_btn_layout = QtWidgets.QHBoxLayout()
        add_vinculo_btn = QtWidgets.QPushButton("Añadir Vínculo")
        vinculos_btn_layout.addWidget(add_vinculo_btn)
        vinculos_btn_layout.addStretch()
        vinculos_layout.addLayout(vinculos_btn_layout)
        
        # Agregar contenido al frame y ocultar por defecto
        vinculos_frame_layout.addWidget(vinculos_content_widget)
        vinculos_content_widget.hide()  # Colapsado por defecto
        
        # Función para toggle del colapso de vínculos
        def toggle_vinculos():
            vinculos_collapsed[0] = not vinculos_collapsed[0]
            if vinculos_collapsed[0]:
                vinculos_content_widget.hide()
                num_vinculos = len(vinculos_existentes)
                vinculos_header_btn.setText(f"▷ Vínculos con otros eventos ({num_vinculos})")
            else:
                vinculos_content_widget.show()
                num_vinculos = len(vinculos_existentes)
                vinculos_header_btn.setText(f"▽ Vínculos con otros eventos ({num_vinculos})")
        
        vinculos_header_btn.clicked.connect(toggle_vinculos)
        
        # Añadir el frame al layout principal
        dialog_layout.addWidget(vinculos_frame)

        # Función para añadir un vínculo a la tabla
        def añadir_vinculo():
            # Crear diálogo para seleccionar evento y tipo
            sel_dialog = QtWidgets.QDialog(dialog)
            sel_dialog.setWindowTitle("Añadir Vínculo")
            sel_dialog.setMinimumWidth(300)
            sel_layout = QtWidgets.QVBoxLayout(sel_dialog)

            # Lista de eventos disponibles (excluir el actual y los ya vinculados)
            eventos_disponibles = []
            vinculos_ids = [v['id_padre'] for v in vinculos_existentes]
            for e in self.eventos_riesgo:
                if (new or e != evento_data) and e['id'] not in vinculos_ids:
                    eventos_disponibles.append(e)

            if not eventos_disponibles:
                QtWidgets.QMessageBox.warning(sel_dialog, "Advertencia",
                                              "No hay eventos disponibles para vincular.")
                return

            # Selección de evento
            sel_layout.addWidget(QtWidgets.QLabel("Seleccionar evento:"))
            evento_combo = NoScrollComboBox()
            for e in eventos_disponibles:
                evento_combo.addItem(e['nombre'], e['id'])
            sel_layout.addWidget(evento_combo)

            # Selección de tipo de vínculo
            sel_layout.addWidget(QtWidgets.QLabel("Tipo de vínculo:"))
            tipo_combo = NoScrollComboBox()
            tipo_combo.addItems(["AND", "OR", "EXCLUYE"])
            sel_layout.addWidget(tipo_combo)

            # Función para habilitar/deshabilitar factor severidad según tipo
            def on_tipo_changed_dialog(texto):
                es_excluye = (texto == "EXCLUYE")
                factor_sev_spinbox.setEnabled(not es_excluye)
                if es_excluye:
                    factor_sev_spinbox.setValue(1.00)
            tipo_combo.currentTextChanged.connect(on_tipo_changed_dialog)

            # Probabilidad de activación del vínculo
            sel_layout.addWidget(QtWidgets.QLabel("Probabilidad de activación (%):"))
            prob_spinbox = QtWidgets.QSpinBox()
            prob_spinbox.setRange(1, 100)
            prob_spinbox.setValue(100)
            prob_spinbox.setSuffix("%")
            prob_spinbox.setToolTip("Probabilidad de que este vínculo se active cuando la condición se cumple. 100% = siempre (comportamiento actual)")
            sel_layout.addWidget(prob_spinbox)

            # Factor de severidad condicional
            sel_layout.addWidget(QtWidgets.QLabel("Factor de severidad:"))
            factor_sev_spinbox = QtWidgets.QDoubleSpinBox()
            factor_sev_spinbox.setRange(0.10, 5.00)
            factor_sev_spinbox.setValue(1.00)
            factor_sev_spinbox.setSingleStep(0.01)
            factor_sev_spinbox.setDecimals(2)
            factor_sev_spinbox.setSuffix("x")
            factor_sev_spinbox.setToolTip("Multiplica la severidad del hijo cuando este vínculo se activa. 1.0x = sin cambio.")
            sel_layout.addWidget(factor_sev_spinbox)

            # Umbral de severidad del padre
            sel_layout.addWidget(QtWidgets.QLabel("Umbral de severidad del padre ($):"))
            umbral_sev_spinbox = QtWidgets.QSpinBox()
            umbral_sev_spinbox.setRange(0, 999999999)
            umbral_sev_spinbox.setValue(0)
            umbral_sev_spinbox.setSingleStep(1000)
            umbral_sev_spinbox.setPrefix("$")
            umbral_sev_spinbox.setToolTip("El vínculo solo se evalúa si la pérdida NETA del padre (post-controles y seguros) supera este monto. $0 = siempre evaluar.")
            sel_layout.addWidget(umbral_sev_spinbox)

            # Botones de aceptar/cancelar
            buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                QtWidgets.QDialogButtonBox.Cancel)
            # Ajustar tamaño de botones
            ok_btn = buttons.button(QtWidgets.QDialogButtonBox.Ok)
            ok_btn.setFixedHeight(35)
            cancel_btn = buttons.button(QtWidgets.QDialogButtonBox.Cancel)
            cancel_btn.setFixedHeight(35)
            buttons.accepted.connect(sel_dialog.accept)
            buttons.rejected.connect(sel_dialog.reject)
            sel_layout.addWidget(buttons)

            # Mostrar diálogo y procesar resultado
            if sel_dialog.exec_() == QtWidgets.QDialog.Accepted:
                evento_id = evento_combo.currentData()
                tipo = tipo_combo.currentText()

                # Agregar a la lista de vínculos existentes
                vinculos_existentes.append({
                    'id_padre': evento_id,
                    'tipo': tipo,
                    'probabilidad': prob_spinbox.value(),
                    'factor_severidad': factor_sev_spinbox.value(),
                    'umbral_severidad': umbral_sev_spinbox.value()
                })

                # Actualizar la tabla
                actualizar_tabla_vinculos()

        # Función para actualizar la tabla de vínculos
        def actualizar_tabla_vinculos():
            # Limpiar tabla
            vinculos_table.setRowCount(0)

            # Agregar vínculos existentes
            for idx, vinculo in enumerate(vinculos_existentes):
                vinculos_table.insertRow(idx)

                # Nombre del evento padre
                nombre_padre = "Desconocido"
                for e in self.eventos_riesgo:
                    if e['id'] == vinculo['id_padre']:
                        nombre_padre = e['nombre']
                        break

                # Celda con nombre del evento
                item_evento = QtWidgets.QTableWidgetItem(nombre_padre)
                item_evento.setFlags(item_evento.flags() & ~QtCore.Qt.ItemIsEditable)
                vinculos_table.setItem(idx, 0, item_evento)

                # Celda con combo para tipo de vínculo - directamente sin contenedor
                tipo_combo = NoScrollComboBox()
                tipo_combo.addItems(["AND", "OR", "EXCLUYE"])
                tipo_combo.setCurrentText(vinculo['tipo'])
                tipo_combo.setFixedHeight(30)  # Altura fija para el combo
                tipo_combo.setStyleSheet("QComboBox { padding: 1px; margin: 0px; border: 1px solid #aaa; }")
                tipo_combo.currentTextChanged.connect(lambda text, row=idx: actualizar_tipo_vinculo(row, text))
                vinculos_table.setCellWidget(idx, 1, tipo_combo)

                # Spinbox para probabilidad de activación
                prob_spin = QtWidgets.QSpinBox()
                prob_spin.setRange(1, 100)
                prob_spin.setValue(max(1, min(100, vinculo.get('probabilidad', 100))))
                prob_spin.setSuffix("%")
                prob_spin.setFixedHeight(30)
                prob_spin.setStyleSheet("QSpinBox { padding: 1px; margin: 0px; border: 1px solid #aaa; }")
                prob_spin.valueChanged.connect(lambda val, row=idx: actualizar_probabilidad_vinculo(row, val))
                vinculos_table.setCellWidget(idx, 2, prob_spin)

                # DoubleSpinbox para factor de severidad
                factor_sev_spin = QtWidgets.QDoubleSpinBox()
                factor_sev_spin.setRange(0.10, 5.00)
                factor_sev_spin.setValue(max(0.10, min(5.00, vinculo.get('factor_severidad', 1.0))))
                factor_sev_spin.setSingleStep(0.01)
                factor_sev_spin.setDecimals(2)
                factor_sev_spin.setSuffix("x")
                factor_sev_spin.setFixedHeight(30)
                factor_sev_spin.setStyleSheet("QDoubleSpinBox { padding: 1px; margin: 0px; border: 1px solid #aaa; }")
                factor_sev_spin.valueChanged.connect(lambda val, row=idx: actualizar_factor_severidad_vinculo(row, val))
                # Deshabilitar factor severidad para EXCLUYE (no tiene efecto en simulación)
                if vinculo['tipo'] == 'EXCLUYE':
                    factor_sev_spin.setEnabled(False)
                    factor_sev_spin.setValue(1.00)
                vinculos_table.setCellWidget(idx, 3, factor_sev_spin)

                # Spinbox para umbral de severidad del padre
                umbral_spin = QtWidgets.QSpinBox()
                umbral_spin.setRange(0, 999999999)
                umbral_spin.setValue(max(0, vinculo.get('umbral_severidad', 0)))
                umbral_spin.setSingleStep(1000)
                umbral_spin.setPrefix("$")
                umbral_spin.setFixedHeight(30)
                umbral_spin.setStyleSheet("QSpinBox { padding: 1px; margin: 0px; border: 1px solid #aaa; }")
                umbral_spin.setToolTip("Pérdida NETA mínima del padre (post-controles y seguros) para activar este vínculo. $0 = siempre evaluar.")
                umbral_spin.valueChanged.connect(lambda val, row=idx: actualizar_umbral_severidad_vinculo(row, val))
                vinculos_table.setCellWidget(idx, 4, umbral_spin)

                # Botón para eliminar con icono de cesto de basura y color rojo - sin contenedor
                delete_btn = QtWidgets.QPushButton()
                delete_btn.setIcon(self.iconos["delete"])  # Usar el icono de eliminar ya cargado
                delete_btn.setToolTip("Eliminar vínculo")
                delete_btn.setFixedSize(70, 30)  # Tamaño fijo para el botón
                delete_btn.setStyleSheet("QPushButton { background-color: #ff5555; color: white; border: none; margin: 0px; padding: 0px; }"
                                     "QPushButton:hover { background-color: #ff3333; }")
                delete_btn.clicked.connect(lambda _, row=idx: eliminar_vinculo(row))
                
                # Colocar directamente el botón sin contenedor
                vinculos_table.setCellWidget(idx, 5, delete_btn)
            
            # Actualizar contador en el header
            num_vinculos = len(vinculos_existentes)
            if vinculos_collapsed[0]:
                vinculos_header_btn.setText(f"▷ Vínculos con otros eventos ({num_vinculos})")
            else:
                vinculos_header_btn.setText(f"▽ Vínculos con otros eventos ({num_vinculos})")

        # Función para actualizar el tipo de un vínculo
        def actualizar_tipo_vinculo(row, nuevo_tipo):
            vinculos_existentes[row]['tipo'] = nuevo_tipo
            # Habilitar/deshabilitar factor severidad según tipo
            factor_widget = vinculos_table.cellWidget(row, 3)
            if factor_widget is not None:
                es_excluye = (nuevo_tipo == 'EXCLUYE')
                factor_widget.setEnabled(not es_excluye)
                if es_excluye:
                    factor_widget.setValue(1.00)
                    vinculos_existentes[row]['factor_severidad'] = 1.0

        # Función para actualizar la probabilidad de un vínculo
        def actualizar_probabilidad_vinculo(row, valor):
            vinculos_existentes[row]['probabilidad'] = valor

        # Función para actualizar el factor de severidad de un vínculo
        def actualizar_factor_severidad_vinculo(row, valor):
            vinculos_existentes[row]['factor_severidad'] = valor

        # Función para actualizar el umbral de severidad de un vínculo
        def actualizar_umbral_severidad_vinculo(row, valor):
            vinculos_existentes[row]['umbral_severidad'] = valor

        # Función para eliminar un vínculo
        def eliminar_vinculo(row):
            del vinculos_existentes[row]
            actualizar_tabla_vinculos()

        # Conectar botón para añadir vínculo
        add_vinculo_btn.clicked.connect(añadir_vinculo)

        # Inicializar la tabla
        actualizar_tabla_vinculos()
        
        # ====================================================================
        # SECCIÓN: AJUSTES DE PROBABILIDAD
        # ====================================================================
        
        # Función helper para normalizar factores (migración automática de formato legacy)
        def normalizar_factor(factor):
            """Asegura que el factor tenga todos los campos necesarios (backward compatibility)"""
            factor_norm = factor.copy()
            
            # Si no tiene tipo_modelo, es formato legacy → migrar a estático
            if 'tipo_modelo' not in factor_norm:
                factor_norm['tipo_modelo'] = 'estatico'
            
            # Asegurar campos para modelo estático
            if 'impacto_porcentual' not in factor_norm:
                factor_norm['impacto_porcentual'] = 0
            
            # Asegurar campos para modelo estocástico (valores por defecto)
            if 'confiabilidad' not in factor_norm:
                # Si migra de estático, usar 100% confiabilidad
                factor_norm['confiabilidad'] = 100
            
            if 'reduccion_efectiva' not in factor_norm:
                # Usar el valor absoluto del impacto como reducción efectiva
                factor_norm['reduccion_efectiva'] = abs(factor_norm.get('impacto_porcentual', 0))
            
            if 'reduccion_fallo' not in factor_norm:
                # Por defecto, sin reducción cuando falla
                factor_norm['reduccion_fallo'] = 0
            
            # Asegurar campo activo
            if 'activo' not in factor_norm:
                factor_norm['activo'] = True
            
            # ====================================================================
            # NUEVOS CAMPOS: Impacto en frecuencia y severidad (backward compatible)
            # ====================================================================
            
            # afecta_frecuencia: True por defecto si impacto_porcentual != 0 (backward compat)
            if 'afecta_frecuencia' not in factor_norm:
                factor_norm['afecta_frecuencia'] = factor_norm.get('impacto_porcentual', 0) != 0
            
            # afecta_severidad: False por defecto para mantener comportamiento existente
            if 'afecta_severidad' not in factor_norm:
                factor_norm['afecta_severidad'] = False
            
            # Para modelo ESTÁTICO: impacto porcentual en severidad
            if 'impacto_severidad_pct' not in factor_norm:
                factor_norm['impacto_severidad_pct'] = 0
            
            # Para modelo ESTOCÁSTICO: reducción de severidad cuando funciona/falla
            if 'reduccion_severidad_efectiva' not in factor_norm:
                factor_norm['reduccion_severidad_efectiva'] = 0
            
            if 'reduccion_severidad_fallo' not in factor_norm:
                factor_norm['reduccion_severidad_fallo'] = 0
            
            # ================================================================
            # MODELO DE SEGURO/TRANSFERENCIA (para severidad)
            # ================================================================
            # tipo_severidad: 'porcentual' (default) o 'seguro'
            if 'tipo_severidad' not in factor_norm:
                factor_norm['tipo_severidad'] = 'porcentual'
            
            # Campos de seguro (solo usados si tipo_severidad == 'seguro')
            if 'seguro_deducible' not in factor_norm:
                factor_norm['seguro_deducible'] = 0
            
            if 'seguro_cobertura_pct' not in factor_norm:
                factor_norm['seguro_cobertura_pct'] = 100
            
            if 'seguro_limite' not in factor_norm:
                factor_norm['seguro_limite'] = 0  # 0 = sin límite agregado
            
            # NUEVO: Tipo de deducible - 'agregado' o 'por_ocurrencia'
            if 'seguro_tipo_deducible' not in factor_norm:
                factor_norm['seguro_tipo_deducible'] = 'agregado'
            
            # NUEVO: Límite por ocurrencia
            if 'seguro_limite_ocurrencia' not in factor_norm:
                factor_norm['seguro_limite_ocurrencia'] = 0
            
            return factor_norm
        
        # Cargar factores de ajuste existentes desde el evento
        factores_ajuste_existentes = []
        if evento_data and 'factores_ajuste' in evento_data:
            # Cargar y normalizar factores (migración automática)
            factores_raw = copy.deepcopy(evento_data['factores_ajuste'])
            factores_ajuste_existentes = [normalizar_factor(f) for f in factores_raw]
            
            # DEBUG: Verificar que los factores se cargaron
            if factores_ajuste_existentes:
                print(f"[DEBUG CARGAR] Cargados {len(factores_ajuste_existentes)} factores:")
                for f in factores_ajuste_existentes:
                    tipo = f.get('tipo_modelo', 'estatico')
                    if tipo == 'estocastico':
                        print(f"  - {f.get('nombre')}: Estocástico (conf={f.get('confiabilidad')}%, "
                              f"red={f.get('reduccion_efectiva')}/{f.get('reduccion_fallo')}%) (activo: {f.get('activo')})")
                    else:
                        print(f"  - {f.get('nombre')}: Estático ({f.get('impacto_porcentual')}%) (activo: {f.get('activo')})")
        
        # Sección de ajustes colapsable
        ajustes_collapsed = [True]  # Colapsado por defecto
        
        # Frame contenedor para ajustes
        ajustes_frame = QtWidgets.QFrame()
        ajustes_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        ajustes_frame.setStyleSheet("QFrame { border: 1px solid #aaa; border-radius: 3px; }")
        ajustes_frame_layout = QtWidgets.QVBoxLayout(ajustes_frame)
        ajustes_frame_layout.setContentsMargins(0, 0, 0, 0)
        ajustes_frame_layout.setSpacing(0)
        
        # Header clickeable
        ajustes_header_btn = QtWidgets.QPushButton()
        num_ajustes = len(factores_ajuste_existentes)
        ajustes_header_btn.setText(f"▷ Ajustar probabilidad según controles/factores ({num_ajustes})")
        ajustes_header_btn.setStyleSheet("""
            QPushButton {
                background-color: #d5e8f5;
                color: #333;
                border: none;
                border-bottom: 1px solid #aaa;
                text-align: left;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c5d8e5;
            }
        """)
        ajustes_frame_layout.addWidget(ajustes_header_btn)
        
        # Contenedor de contenido (colapsable)
        ajustes_content_widget = QtWidgets.QWidget()
        ajustes_layout = QtWidgets.QVBoxLayout(ajustes_content_widget)
        ajustes_layout.setContentsMargins(10, 10, 10, 10)
        
        # Explicación simple para el usuario
        explicacion_ajustes = QtWidgets.QLabel(
            "💡 Los <b>controles</b> reducen el riesgo (valores positivos, ej: 30% = reduce 30%). "
            "Los <b>factores de riesgo</b> lo aumentan (valores negativos, ej: -50% = aumenta 50%). "
            "Puede afectar la <b>frecuencia</b> (probabilidad de ocurrencia), la <b>severidad</b> (impacto económico), o ambas."
        )
        explicacion_ajustes.setWordWrap(True)
        explicacion_ajustes.setStyleSheet("background-color: #e8f4f8; padding: 8px; border-radius: 3px; font-size: {UI_FONT_BODY}pt;")
        ajustes_layout.addWidget(explicacion_ajustes)
        
        # Tabla para gestionar ajustes
        ajustes_table = QtWidgets.QTableWidget()
        ajustes_table.setColumnCount(5)
        ajustes_table.setHorizontalHeaderLabels(["Activo", "Nombre", "Tipo", "Configuración", "Eliminar"])
        ajustes_table.horizontalHeader().setStretchLastSection(False)
        ajustes_table.setColumnWidth(0, 60)   # Checkbox activo
        ajustes_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # Nombre elástico
        ajustes_table.setColumnWidth(2, 100)  # Tipo
        ajustes_table.setColumnWidth(3, 240)  # Configuración (ampliado para severidad)
        ajustes_table.setColumnWidth(4, 80)   # Botón eliminar
        ajustes_table.setMinimumHeight(150)
        ajustes_table.verticalHeader().setDefaultSectionSize(36)
        ajustes_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        ajustes_table.setShowGrid(True)
        ajustes_table.setStyleSheet("QTableWidget::item { padding: 0px; }")
        ajustes_layout.addWidget(ajustes_table)
        
        # Panel de botones y vista previa
        ajustes_btn_layout = QtWidgets.QHBoxLayout()
        add_ajuste_btn = QtWidgets.QPushButton("Agregar Factor/Control")
        ajustes_btn_layout.addWidget(add_ajuste_btn)
        ajustes_btn_layout.addStretch()
        
        # Label para mostrar probabilidad ajustada en tiempo real
        prob_ajustada_label = QtWidgets.QLabel("")
        prob_ajustada_label.setStyleSheet("""
            QLabel {
                background-color: #fff4cc;
                border: 1px solid #ffc107;
                border-radius: 4px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: {UI_FONT_BODY}pt;
            }
        """)
        ajustes_btn_layout.addWidget(prob_ajustada_label)
        
        ajustes_layout.addLayout(ajustes_btn_layout)
        
        # Agregar contenido al frame y ocultar por defecto
        ajustes_frame_layout.addWidget(ajustes_content_widget)
        ajustes_content_widget.hide()  # Colapsado por defecto
        
        # Función para toggle del colapso de ajustes
        def toggle_ajustes():
            ajustes_collapsed[0] = not ajustes_collapsed[0]
            if ajustes_collapsed[0]:
                ajustes_content_widget.hide()
                num_ajustes = len(factores_ajuste_existentes)
                ajustes_header_btn.setText(f"▷ Ajustar probabilidad según controles/factores ({num_ajustes})")
            else:
                ajustes_content_widget.show()
                num_ajustes = len(factores_ajuste_existentes)
                ajustes_header_btn.setText(f"▽ Ajustar probabilidad según controles/factores ({num_ajustes})")
        
        ajustes_header_btn.clicked.connect(toggle_ajustes)
        
        # Función para actualizar la visualización de probabilidad/frecuencia ajustada
        def actualizar_probabilidad_ajustada():
            """Calcula y muestra el parámetro ajustado en tiempo real según la distribución"""
            try:
                # Verificar si hay factores activos
                factores_activos = [f for f in factores_ajuste_existentes if f.get('activo', True)]
                if not factores_activos:
                    prob_ajustada_label.setText("")
                    return
                
                # Calcular factor multiplicativo total
                factor_multiplicativo = 1.0
                for f in factores_activos:
                    impacto_pct = f.get('impacto_porcentual', 0)
                    factor_multiplicativo *= (1 + impacto_pct / 100.0)
                
                # Obtener tipo de distribución de frecuencia
                freq_opcion = freq_combobox.currentIndex() + 1
                tipo_dist_nombres = ['Poisson', 'Binomial', 'Bernoulli', 'Poisson-Gamma', 'Beta']
                tipo_dist = tipo_dist_nombres[freq_opcion - 1] if freq_opcion <= len(tipo_dist_nombres) else 'Bernoulli'
                
                # Calcular y mostrar ajuste según el tipo de distribución
                if tipo_dist == 'Poisson':
                    # Para Poisson: ajustar λ (frecuencia) directamente
                    tasa_text = tasa_var.text().strip()
                    if tasa_text:
                        try:
                            tasa_original = float(tasa_text)
                            if tasa_original > 0:
                                tasa_ajustada = tasa_original * factor_multiplicativo
                                cambio_pct = (factor_multiplicativo - 1) * 100
                                prob_ajustada_label.setText(
                                    f"λ base: {tasa_original:.3f} → Ajustada: {tasa_ajustada:.3f} ({cambio_pct:+.1f}%)"
                                )
                                return
                        except:
                            pass
                
                elif tipo_dist == 'Binomial':
                    # Para Binomial: ajustar p (probabilidad) con log-odds
                    prob_text = prob_exito_var.text().strip()
                    if prob_text:
                        try:
                            prob_original = float(prob_text)
                            if 0 < prob_original < 1:
                                from log_odds_utils import ajustar_probabilidad_por_factores
                                prob_ajustada, _ = ajustar_probabilidad_por_factores(prob_original, factores_ajuste_existentes)
                                cambio_pct = ((prob_ajustada / prob_original) - 1) * 100
                                prob_ajustada_label.setText(
                                    f"p base: {prob_original:.2%} → Ajustada: {prob_ajustada:.2%} ({cambio_pct:+.1f}%)"
                                )
                                return
                        except:
                            pass
                
                elif tipo_dist == 'Bernoulli':
                    # Para Bernoulli: ajustar p (probabilidad) con log-odds
                    prob_text = prob_exito_var_bern.text().strip()
                    if prob_text:
                        try:
                            prob_original = float(prob_text)
                            if 0 < prob_original < 1:
                                from log_odds_utils import ajustar_probabilidad_por_factores
                                prob_ajustada, _ = ajustar_probabilidad_por_factores(prob_original, factores_ajuste_existentes)
                                cambio_pct = ((prob_ajustada / prob_original) - 1) * 100
                                prob_ajustada_label.setText(
                                    f"p base: {prob_original:.2%} → Ajustada: {prob_ajustada:.2%} ({cambio_pct:+.1f}%)"
                                )
                                return
                        except:
                            pass
                
                elif tipo_dist == 'Poisson-Gamma':
                    # Para Poisson-Gamma: ajustar el valor más probable (frecuencia)
                    mas_prob_text = pg_mas_probable_var.text().strip()
                    if mas_prob_text:
                        try:
                            mas_prob_original = float(mas_prob_text)
                            if mas_prob_original > 0:
                                mas_prob_ajustado = mas_prob_original * factor_multiplicativo
                                cambio_pct = (factor_multiplicativo - 1) * 100
                                prob_ajustada_label.setText(
                                    f"Valor más probable: {mas_prob_original:.3f} → {mas_prob_ajustado:.3f} ({cambio_pct:+.1f}%)"
                                )
                                return
                        except:
                            pass
                
                elif tipo_dist == 'Beta':
                    # Para Beta: ajustar el valor más probable (probabilidad) con log-odds
                    mas_prob_text = beta_mas_probable_var.text().strip()
                    if mas_prob_text:
                        try:
                            mas_prob_original = float(mas_prob_text)
                            prob_original = mas_prob_original / 100.0
                            if 0 < prob_original < 1:
                                from log_odds_utils import ajustar_probabilidad_por_factores
                                prob_ajustada, _ = ajustar_probabilidad_por_factores(prob_original, factores_ajuste_existentes)
                                mas_prob_ajustado = prob_ajustada * 100
                                cambio_pct = ((prob_ajustada / prob_original) - 1) * 100
                                prob_ajustada_label.setText(
                                    f"p más probable: {mas_prob_original:.1f}% → {mas_prob_ajustado:.1f}% ({cambio_pct:+.1f}%)"
                                )
                                return
                        except:
                            pass
                
                # Si llegamos aquí, no se pudo calcular el ajuste
                prob_ajustada_label.setText("")
                
            except ImportError:
                prob_ajustada_label.setText("⚠️ Falta archivo log_odds_utils.py")
            except Exception as e:
                prob_ajustada_label.setText(f"⚠️ Error: {str(e)[:40]}")
        
        # Función para añadir un factor de ajuste
        def añadir_ajuste():
            # Crear diálogo para agregar factor con soporte estocástico
            ajuste_dialog = QtWidgets.QDialog(dialog)
            ajuste_dialog.setWindowTitle("Agregar Control/Factor de Riesgo")
            ajuste_dialog.resize(550, 700)  # Tamaño inicial adecuado
            ajuste_dialog.setMinimumSize(500, 550)
            ajuste_dialog.setMaximumHeight(int(QtWidgets.QApplication.primaryScreen().availableGeometry().height() * 0.9))
            
            # Layout principal con scroll
            main_layout = QtWidgets.QVBoxLayout(ajuste_dialog)
            main_layout.setContentsMargins(0, 0, 0, 0)
            
            scroll_area = QtWidgets.QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
            scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            
            scroll_content = QtWidgets.QWidget()
            ajuste_layout = QtWidgets.QVBoxLayout(scroll_content)
            ajuste_layout.setContentsMargins(15, 15, 15, 15)
            
            # Nombre del factor
            nombre_layout = QtWidgets.QFormLayout()
            nombre_factor_var = QtWidgets.QLineEdit()
            nombre_factor_var.setPlaceholderText("Ej: Firewall actualizado, Personal capacitado...")
            nombre_layout.addRow("Nombre:", nombre_factor_var)
            ajuste_layout.addLayout(nombre_layout)
            
            # Separador
            ajuste_layout.addWidget(QtWidgets.QLabel("<hr>"))
            
            # Radio buttons para seleccionar tipo de modelo
            ajuste_layout.addWidget(QtWidgets.QLabel("<b>Tipo de modelo:</b>"))
            tipo_grupo = QtWidgets.QButtonGroup(ajuste_dialog)
            tipo_estatico_radio = QtWidgets.QRadioButton("Estático (reducción fija)")
            tipo_estocastico_radio = QtWidgets.QRadioButton("Estocástico (confiabilidad variable)")
            tipo_estatico_radio.setChecked(True)  # Por defecto estático
            tipo_grupo.addButton(tipo_estatico_radio)
            tipo_grupo.addButton(tipo_estocastico_radio)
            
            radio_layout = QtWidgets.QVBoxLayout()
            radio_layout.addWidget(tipo_estatico_radio)
            radio_layout.addWidget(tipo_estocastico_radio)
            ajuste_layout.addLayout(radio_layout)
            
            ajuste_layout.addSpacing(10)
            
            # ===== FRAME PARA MODELO ESTÁTICO =====
            estatico_frame = QtWidgets.QGroupBox("Configuración Estática")
            estatico_layout = QtWidgets.QFormLayout(estatico_frame)
            
            # --- Reducción en FRECUENCIA (opcional) ---
            afecta_frecuencia_check = QtWidgets.QCheckBox("Afecta frecuencia (probabilidad de ocurrencia)")
            afecta_frecuencia_check.setChecked(True)  # Por defecto activado
            afecta_frecuencia_check.setToolTip("Si está marcado, el control afectará la probabilidad de que ocurra el evento")
            estatico_layout.addRow(afecta_frecuencia_check)
            
            impacto_var = NoScrollSpinBox()
            impacto_var.setRange(-200, 99)  # Positivo reduce (máx 99%), negativo aumenta
            impacto_var.setValue(30)  # Por defecto 30% reducción
            impacto_var.setSuffix("%")
            impacto_var.setToolTip("Positivo reduce la frecuencia (0-99%), negativo la aumenta")
            estatico_layout.addRow("   Reducción frecuencia (%):", impacto_var)
            
            # Conectar checkbox para habilitar/deshabilitar campo de frecuencia
            afecta_frecuencia_check.toggled.connect(impacto_var.setEnabled)
            
            # --- Reducción en SEVERIDAD (opcional) ---
            estatico_layout.addRow(QtWidgets.QLabel(""))  # Separador visual
            
            afecta_severidad_check = QtWidgets.QCheckBox("Afecta severidad (impacto económico)")
            afecta_severidad_check.setChecked(False)  # Por defecto desactivado
            afecta_severidad_check.setToolTip("Si está marcado, el control afectará el impacto económico del evento")
            estatico_layout.addRow(afecta_severidad_check)
            
            # Contenedor para opciones de severidad
            severidad_container = QtWidgets.QWidget()
            severidad_container_layout = QtWidgets.QVBoxLayout(severidad_container)
            severidad_container_layout.setContentsMargins(20, 0, 0, 0)
            severidad_container.setEnabled(False)
            
            # Radio buttons para tipo de severidad
            tipo_sev_grupo = QtWidgets.QButtonGroup(ajuste_dialog)
            tipo_sev_porcentual = QtWidgets.QRadioButton("Reducción porcentual")
            tipo_sev_seguro = QtWidgets.QRadioButton("Seguro/Transferencia")
            tipo_sev_porcentual.setChecked(True)
            tipo_sev_grupo.addButton(tipo_sev_porcentual)
            tipo_sev_grupo.addButton(tipo_sev_seguro)
            
            tipo_sev_layout = QtWidgets.QHBoxLayout()
            tipo_sev_layout.addWidget(tipo_sev_porcentual)
            tipo_sev_layout.addWidget(tipo_sev_seguro)
            tipo_sev_layout.addStretch()
            severidad_container_layout.addLayout(tipo_sev_layout)
            
            # --- Frame para reducción porcentual ---
            porcentual_frame = QtWidgets.QWidget()
            porcentual_layout = QtWidgets.QFormLayout(porcentual_frame)
            porcentual_layout.setContentsMargins(0, 5, 0, 0)
            
            impacto_severidad_var = NoScrollSpinBox()
            impacto_severidad_var.setRange(-200, 99)
            impacto_severidad_var.setValue(25)
            impacto_severidad_var.setSuffix("%")
            impacto_severidad_var.setToolTip("Positivo reduce el impacto económico (0-99%), negativo lo aumenta")
            porcentual_layout.addRow("Reducción (%):", impacto_severidad_var)
            
            severidad_container_layout.addWidget(porcentual_frame)
            
            # --- Frame para modelo de seguro ---
            seguro_frame = QtWidgets.QWidget()
            seguro_layout = QtWidgets.QFormLayout(seguro_frame)
            seguro_layout.setContentsMargins(0, 5, 0, 0)
            
            # Tipo de deducible (por ocurrencia vs agregado)
            tipo_ded_group = QtWidgets.QButtonGroup(seguro_frame)
            tipo_ded_layout = QtWidgets.QHBoxLayout()
            tipo_ded_ocurrencia = QtWidgets.QRadioButton("Por ocurrencia")
            tipo_ded_ocurrencia.setToolTip("El deducible se aplica a cada siniestro individual")
            tipo_ded_agregado = QtWidgets.QRadioButton("Agregado anual")
            tipo_ded_agregado.setToolTip("El deducible se aplica a la pérdida total del año")
            tipo_ded_agregado.setChecked(True)  # Default: agregado (backward compat)
            tipo_ded_group.addButton(tipo_ded_ocurrencia)
            tipo_ded_group.addButton(tipo_ded_agregado)
            tipo_ded_layout.addWidget(tipo_ded_ocurrencia)
            tipo_ded_layout.addWidget(tipo_ded_agregado)
            tipo_ded_layout.addStretch()
            seguro_layout.addRow("Tipo deducible:", tipo_ded_layout)
            
            seguro_deducible_var = NoScrollSpinBox()
            seguro_deducible_var.setRange(0, 999999999)
            seguro_deducible_var.setValue(50000)
            seguro_deducible_var.setPrefix("$ ")
            seguro_deducible_var.setToolTip("Monto mínimo que NO cubre el seguro (el asegurado paga)")
            seguro_layout.addRow("Deducible:", seguro_deducible_var)
            
            seguro_cobertura_var = NoScrollSpinBox()
            seguro_cobertura_var.setRange(1, 100)
            seguro_cobertura_var.setValue(80)
            seguro_cobertura_var.setSuffix("%")
            seguro_cobertura_var.setToolTip("% del exceso sobre deducible que cubre el seguro")
            seguro_layout.addRow("Cobertura (%):", seguro_cobertura_var)
            
            # Límite por ocurrencia (nuevo)
            seguro_limite_ocurrencia_var = NoScrollSpinBox()
            seguro_limite_ocurrencia_var.setRange(0, 999999999)
            seguro_limite_ocurrencia_var.setValue(0)
            seguro_limite_ocurrencia_var.setPrefix("$ ")
            seguro_limite_ocurrencia_var.setToolTip("Máximo que paga el seguro por siniestro (0 = sin límite por ocurrencia)")
            seguro_layout.addRow("Límite por siniestro:", seguro_limite_ocurrencia_var)
            
            seguro_limite_var = NoScrollSpinBox()
            seguro_limite_var.setRange(0, 999999999)
            seguro_limite_var.setValue(1000000)
            seguro_limite_var.setPrefix("$ ")
            seguro_limite_var.setToolTip("Máximo agregado anual que paga el seguro (0 = sin límite)")
            seguro_layout.addRow("Límite agregado:", seguro_limite_var)
            
            seguro_help = QtWidgets.QLabel(
                "💡 <b>Por ocurrencia:</b> Deducible/límite se aplica a cada siniestro.<br>"
                "<b>Agregado:</b> Deducible/límite se aplica al total anual.<br>"
                "Ej: 3 siniestros de $30K c/u, Ded $25K por ocurrencia → Paga 3×$5K"
            )
            seguro_help.setWordWrap(True)
            seguro_help.setStyleSheet("color: #666; font-size: 9pt; padding: 3px;")
            seguro_layout.addRow(seguro_help)
            
            seguro_frame.setVisible(False)
            severidad_container_layout.addWidget(seguro_frame)
            
            # Función para alternar entre porcentual y seguro
            def toggle_tipo_severidad():
                porcentual_frame.setVisible(tipo_sev_porcentual.isChecked())
                seguro_frame.setVisible(tipo_sev_seguro.isChecked())
            
            tipo_sev_porcentual.toggled.connect(toggle_tipo_severidad)
            
            estatico_layout.addRow(severidad_container)
            
            # Conectar checkbox para habilitar/deshabilitar contenedor de severidad
            afecta_severidad_check.toggled.connect(severidad_container.setEnabled)
            
            estatico_help = QtWidgets.QLabel(
                "💡 Valores positivos = reducción (control), negativos = aumento (factor de riesgo).<br>"
                "Ej: Firewall 30% reduce frecuencia, Seguro transfiere impacto económico."
            )
            estatico_help.setWordWrap(True)
            estatico_help.setStyleSheet("color: #666; font-size: {UI_FONT_SMALL}pt; padding: 5px;")
            estatico_layout.addRow(estatico_help)
            
            ajuste_layout.addWidget(estatico_frame)
            
            # ===== FRAME PARA MODELO ESTOCÁSTICO =====
            estocastico_frame = QtWidgets.QGroupBox("Configuración Estocástica")
            estocastico_layout = QtWidgets.QFormLayout(estocastico_frame)
            
            confiabilidad_var = NoScrollSpinBox()
            confiabilidad_var.setRange(0, 100)
            confiabilidad_var.setValue(70)
            confiabilidad_var.setSuffix("%")
            confiabilidad_var.setToolTip("% del tiempo que el control funciona correctamente")
            estocastico_layout.addRow("Confiabilidad (%):", confiabilidad_var)
            
            # --- SI FUNCIONA ---
            estocastico_layout.addRow(QtWidgets.QLabel("<b>─── Si funciona ───</b>"))
            
            reduccion_efectiva_var = NoScrollSpinBox()
            reduccion_efectiva_var.setRange(-100, 99)  # Máx 99% reducción para evitar factor negativo
            reduccion_efectiva_var.setValue(80)
            reduccion_efectiva_var.setSuffix("%")
            reduccion_efectiva_var.setToolTip("Reducción de frecuencia cuando funciona (0-99%, negativo aumenta)")
            estocastico_layout.addRow("Reducción frecuencia (%):", reduccion_efectiva_var)
            
            reduccion_sev_efectiva_var = NoScrollSpinBox()
            reduccion_sev_efectiva_var.setRange(-100, 99)  # Máx 99% reducción para evitar factor negativo
            reduccion_sev_efectiva_var.setValue(50)
            reduccion_sev_efectiva_var.setSuffix("%")
            reduccion_sev_efectiva_var.setToolTip("Reducción de severidad cuando funciona (0-99%, negativo aumenta)")
            estocastico_layout.addRow("Reducción severidad (%):", reduccion_sev_efectiva_var)
            
            # --- SI FALLA ---
            estocastico_layout.addRow(QtWidgets.QLabel("<b>─── Si falla ───</b>"))
            
            reduccion_fallo_var = NoScrollSpinBox()
            reduccion_fallo_var.setRange(-100, 99)  # Máx 99% reducción para evitar factor negativo
            reduccion_fallo_var.setValue(10)
            reduccion_fallo_var.setSuffix("%")
            reduccion_fallo_var.setToolTip("Reducción de frecuencia cuando falla (0-99%, negativo aumenta)")
            estocastico_layout.addRow("Reducción frecuencia (%):", reduccion_fallo_var)
            
            reduccion_sev_fallo_var = NoScrollSpinBox()
            reduccion_sev_fallo_var.setRange(-100, 99)  # Máx 99% reducción para evitar factor negativo
            reduccion_sev_fallo_var.setValue(5)
            reduccion_sev_fallo_var.setSuffix("%")
            reduccion_sev_fallo_var.setToolTip("Reducción de severidad cuando falla (0-99%, negativo aumenta)")
            estocastico_layout.addRow("Reducción severidad (%):", reduccion_sev_fallo_var)
            
            estocastico_help = QtWidgets.QLabel(
                "💡 En cada simulación, el control funciona o falla aleatoriamente.<br>"
                "Afecta tanto frecuencia como severidad según el estado.<br>"
                "Ej: 70% conf → 70% aplica reducciones 'funciona', 30% aplica 'falla'"
            )
            estocastico_help.setWordWrap(True)
            estocastico_help.setStyleSheet("color: #666; font-size: {UI_FONT_SMALL}pt; padding: 5px;")
            estocastico_layout.addRow(estocastico_help)
            
            ajuste_layout.addWidget(estocastico_frame)
            
            # Función para alternar visibilidad de frames
            def toggle_frames():
                estatico_frame.setVisible(tipo_estatico_radio.isChecked())
                estocastico_frame.setVisible(tipo_estocastico_radio.isChecked())
                
                # Forzar actualización del layout y ajuste del tamaño del diálogo
                ajuste_dialog.layout().activate()
                ajuste_dialog.adjustSize()
                
                # Establecer tamaño mínimo para evitar compresión
                ajuste_dialog.setMinimumHeight(0)
                ajuste_dialog.updateGeometry()
            
            tipo_estatico_radio.toggled.connect(toggle_frames)
            toggle_frames()  # Estado inicial
            
            # Conectar scroll area con contenido
            scroll_area.setWidget(scroll_content)
            main_layout.addWidget(scroll_area)
            
            # Botones (fuera del scroll para que siempre sean visibles)
            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
            )
            def validar_y_aceptar_ajuste():
                nombre = nombre_factor_var.text().strip()
                if not nombre:
                    QtWidgets.QMessageBox.warning(ajuste_dialog, "Advertencia", "El nombre no puede estar vacío.")
                    return
                if tipo_estatico_radio.isChecked():
                    if not afecta_frecuencia_check.isChecked() and not afecta_severidad_check.isChecked():
                        QtWidgets.QMessageBox.warning(ajuste_dialog, "Advertencia", 
                            "Debe seleccionar al menos una opción: frecuencia o severidad.")
                        return
                ajuste_dialog.accept()

            buttons.accepted.connect(validar_y_aceptar_ajuste)
            buttons.rejected.connect(ajuste_dialog.reject)
            main_layout.addWidget(buttons)
            
            # Mostrar diálogo
            if ajuste_dialog.exec_() == QtWidgets.QDialog.Accepted:
                nombre = nombre_factor_var.text().strip()
                
                # Crear factor según el tipo seleccionado
                if tipo_estatico_radio.isChecked():
                    
                    # NOTA: En UI positivo = reducción, internamente negativo = reducción
                    # Invertimos el signo al guardar para mantener compatibilidad con lógica de simulación
                    
                    # Determinar tipo de severidad
                    es_seguro = afecta_severidad_check.isChecked() and tipo_sev_seguro.isChecked()
                    
                    nuevo_factor = {
                        'nombre': nombre,
                        'tipo_modelo': 'estatico',
                        # Frecuencia: solo si está marcado
                        'afecta_frecuencia': afecta_frecuencia_check.isChecked(),
                        'impacto_porcentual': -impacto_var.value() if afecta_frecuencia_check.isChecked() else 0,
                        'activo': True,
                        # Campos estocásticos con valores por defecto (para migración futura)
                        'confiabilidad': 100,
                        'reduccion_efectiva': impacto_var.value() if afecta_frecuencia_check.isChecked() else 0,
                        'reduccion_fallo': 0,
                        # Severidad: solo si está marcado
                        'afecta_severidad': afecta_severidad_check.isChecked(),
                        # Tipo de severidad: 'porcentual' o 'seguro'
                        'tipo_severidad': 'seguro' if es_seguro else 'porcentual',
                        # Campos porcentuales (usados si tipo_severidad == 'porcentual')
                        'impacto_severidad_pct': -impacto_severidad_var.value() if (afecta_severidad_check.isChecked() and not es_seguro) else 0,
                        'reduccion_severidad_efectiva': impacto_severidad_var.value() if (afecta_severidad_check.isChecked() and not es_seguro) else 0,
                        'reduccion_severidad_fallo': 0,
                        # Campos de seguro (usados si tipo_severidad == 'seguro')
                        'seguro_deducible': seguro_deducible_var.value() if es_seguro else 0,
                        'seguro_cobertura_pct': seguro_cobertura_var.value() if es_seguro else 100,
                        'seguro_limite': seguro_limite_var.value() if es_seguro else 0,
                        'seguro_tipo_deducible': 'por_ocurrencia' if (es_seguro and tipo_ded_ocurrencia.isChecked()) else 'agregado',
                        'seguro_limite_ocurrencia': seguro_limite_ocurrencia_var.value() if es_seguro else 0
                    }
                else:  # Estocástico
                    nuevo_factor = {
                        'nombre': nombre,
                        'tipo_modelo': 'estocastico',
                        'confiabilidad': confiabilidad_var.value(),
                        'reduccion_efectiva': reduccion_efectiva_var.value(),
                        'reduccion_fallo': reduccion_fallo_var.value(),
                        'activo': True,
                        # Campo estático por compatibilidad (no se usa en estocástico)
                        'impacto_porcentual': -reduccion_efectiva_var.value(),
                        # NUEVOS: Campos de severidad (estocástico siempre afecta severidad si hay valores)
                        'afecta_severidad': (reduccion_sev_efectiva_var.value() != 0 or reduccion_sev_fallo_var.value() != 0),
                        'impacto_severidad_pct': 0,
                        'reduccion_severidad_efectiva': reduccion_sev_efectiva_var.value(),
                        'reduccion_severidad_fallo': reduccion_sev_fallo_var.value()
                    }
                
                # Agregar a la lista
                factores_ajuste_existentes.append(nuevo_factor)
                
                # Actualizar tabla y probabilidad ajustada
                actualizar_tabla_ajustes()
                actualizar_probabilidad_ajustada()
        
        # Función para actualizar la tabla de ajustes
        def actualizar_tabla_ajustes():
            ajustes_table.setRowCount(0)
            
            for idx, factor in enumerate(factores_ajuste_existentes):
                ajustes_table.insertRow(idx)
                
                # Checkbox de activo
                checkbox = QtWidgets.QCheckBox()
                checkbox.setChecked(factor.get('activo', True))
                # Usar valores por defecto para capturar idx correctamente
                checkbox.stateChanged.connect(
                    lambda state, row=idx: actualizar_activo_ajuste(row, state)
                )
                checkbox_container = QtWidgets.QWidget()
                checkbox_layout = QtWidgets.QHBoxLayout(checkbox_container)
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                ajustes_table.setCellWidget(idx, 0, checkbox_container)
                
                # Nombre del factor
                item_nombre = QtWidgets.QTableWidgetItem(factor['nombre'])
                item_nombre.setFlags(item_nombre.flags() & ~QtCore.Qt.ItemIsEditable)
                item_nombre.setToolTip("Doble click para editar")
                ajustes_table.setItem(idx, 1, item_nombre)
                
                # Tipo de modelo
                tipo_modelo = factor.get('tipo_modelo', 'estatico')
                if tipo_modelo == 'estocastico':
                    item_tipo = QtWidgets.QTableWidgetItem("Estocástico")
                    item_tipo.setForeground(QtGui.QColor("#0066cc"))
                else:
                    item_tipo = QtWidgets.QTableWidgetItem("Estático")
                    item_tipo.setForeground(QtGui.QColor("#666666"))
                item_tipo.setFlags(item_tipo.flags() & ~QtCore.Qt.ItemIsEditable)
                item_tipo.setToolTip("Doble click para editar")
                ajustes_table.setItem(idx, 2, item_tipo)
                
                # Configuración según tipo (incluye severidad si aplica)
                if tipo_modelo == 'estocastico':
                    # Frecuencia
                    freq_text = f"F:{factor.get('reduccion_efectiva', 0)}/{factor.get('reduccion_fallo', 0)}%"
                    # Severidad (si hay valores no-cero)
                    sev_efe = factor.get('reduccion_severidad_efectiva', 0)
                    sev_fal = factor.get('reduccion_severidad_fallo', 0)
                    if sev_efe != 0 or sev_fal != 0:
                        sev_text = f" S:{sev_efe}/{sev_fal}%"
                    else:
                        sev_text = ""
                    conf_text = f"{factor.get('confiabilidad', 0)}% → {freq_text}{sev_text}"
                else:
                    # Estático: frecuencia (si afecta)
                    # NOTA: Internamente negativo = reducción, pero mostramos positivo = reducción
                    parts = []
                    if factor.get('afecta_frecuencia', True):  # backward compat: True por defecto
                        valor_freq = -factor.get('impacto_porcentual', 0)  # Invertir para mostrar
                        parts.append(f"F:{valor_freq:+d}%")
                    # Severidad (si afecta)
                    if factor.get('afecta_severidad', False):
                        tipo_sev = factor.get('tipo_severidad', 'porcentual')
                        if tipo_sev == 'seguro':
                            # Modelo de seguro: mostrar tipo, deducible/cobertura/límite
                            tipo_ded = factor.get('seguro_tipo_deducible', 'agregado')
                            ded = factor.get('seguro_deducible', 0)
                            cob = factor.get('seguro_cobertura_pct', 100)
                            lim = factor.get('seguro_limite', 0)
                            lim_ocurr = factor.get('seguro_limite_ocurrencia', 0)
                            # Formatear montos
                            ded_str = f"${ded:,.0f}" if ded > 0 else "$0"
                            if tipo_ded == 'por_ocurrencia':
                                tipo_str = "p/ocurr"
                                lim_str = f"${lim_ocurr:,.0f}/ocurr" if lim_ocurr > 0 else "∞/ocurr"
                                if lim > 0:
                                    lim_str += f" ${lim:,.0f}/año"
                            else:
                                tipo_str = "agreg"
                                lim_str = f"${lim:,.0f}" if lim > 0 else "∞"
                            parts.append(f"🛡️ {tipo_str} Ded:{ded_str} Cob:{cob}% Lím:{lim_str}")
                        else:
                            # Reducción porcentual
                            valor_sev = -factor.get('impacto_severidad_pct', 0)  # Invertir para mostrar
                            parts.append(f"S:{valor_sev:+d}%")
                    conf_text = " ".join(parts) if parts else "Sin efecto"
                
                item_config = QtWidgets.QTableWidgetItem(conf_text)
                item_config.setFlags(item_config.flags() & ~QtCore.Qt.ItemIsEditable)
                item_config.setToolTip("F=Frecuencia, S=Severidad. Positivo=reducción. Doble click para editar")
                ajustes_table.setItem(idx, 3, item_config)
                
                # Botón eliminar
                delete_btn = QtWidgets.QPushButton()
                delete_btn.setIcon(self.iconos["delete"])
                delete_btn.setToolTip("Eliminar factor")
                delete_btn.setFixedSize(70, 30)
                delete_btn.setStyleSheet(
                    "QPushButton { background-color: #ff5555; color: white; border: none; }"
                    "QPushButton:hover { background-color: #ff3333; }"
                )
                # Usar valores por defecto para capturar idx correctamente
                delete_btn.clicked.connect(lambda checked=False, row=idx: eliminar_ajuste(row))
                ajustes_table.setCellWidget(idx, 4, delete_btn)
            
            # Actualizar contador en el header
            num_ajustes = len(factores_ajuste_existentes)
            if ajustes_collapsed[0]:
                ajustes_header_btn.setText(f"▷ Ajustar probabilidad según controles/factores ({num_ajustes})")
            else:
                ajustes_header_btn.setText(f"▽ Ajustar probabilidad según controles/factores ({num_ajustes})")
        
        # Funciones de actualización
        def actualizar_activo_ajuste(row, state):
            factores_ajuste_existentes[row]['activo'] = (state == QtCore.Qt.Checked)
            actualizar_probabilidad_ajustada()
        
        def actualizar_impacto_ajuste(row, valor):
            factores_ajuste_existentes[row]['impacto_porcentual'] = valor
            actualizar_probabilidad_ajustada()
        
        def eliminar_ajuste(row):
            del factores_ajuste_existentes[row]
            actualizar_tabla_ajustes()
            actualizar_probabilidad_ajustada()
        
        def editar_ajuste(row):
            """Editar un factor existente"""
            if row < 0 or row >= len(factores_ajuste_existentes):
                return
            
            factor_actual = factores_ajuste_existentes[row]
            
            # Crear diálogo para editar factor
            ajuste_dialog = QtWidgets.QDialog(dialog)
            ajuste_dialog.setWindowTitle("Editar Control/Factor de Riesgo")
            ajuste_dialog.resize(550, 700)  # Tamaño inicial adecuado
            ajuste_dialog.setMinimumSize(500, 550)
            ajuste_dialog.setMaximumHeight(int(QtWidgets.QApplication.primaryScreen().availableGeometry().height() * 0.9))
            
            # Layout principal con scroll
            main_layout_edit = QtWidgets.QVBoxLayout(ajuste_dialog)
            main_layout_edit.setContentsMargins(0, 0, 0, 0)
            
            scroll_area_edit = QtWidgets.QScrollArea()
            scroll_area_edit.setWidgetResizable(True)
            scroll_area_edit.setFrameShape(QtWidgets.QFrame.NoFrame)
            scroll_area_edit.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            
            scroll_content_edit = QtWidgets.QWidget()
            ajuste_layout = QtWidgets.QVBoxLayout(scroll_content_edit)
            ajuste_layout.setContentsMargins(15, 15, 15, 15)
            
            # Nombre del factor
            nombre_layout = QtWidgets.QFormLayout()
            nombre_factor_var = QtWidgets.QLineEdit()
            nombre_factor_var.setText(factor_actual['nombre'])  # Pre-cargar nombre
            nombre_factor_var.setPlaceholderText("Ej: Firewall actualizado, Personal capacitado...")
            nombre_layout.addRow("Nombre:", nombre_factor_var)
            ajuste_layout.addLayout(nombre_layout)
            
            # Separador
            ajuste_layout.addWidget(QtWidgets.QLabel("<hr>"))
            
            # Radio buttons para seleccionar tipo de modelo
            ajuste_layout.addWidget(QtWidgets.QLabel("<b>Tipo de modelo:</b>"))
            tipo_grupo = QtWidgets.QButtonGroup(ajuste_dialog)
            tipo_estatico_radio = QtWidgets.QRadioButton("Estático (reducción fija)")
            tipo_estocastico_radio = QtWidgets.QRadioButton("Estocástico (confiabilidad variable)")
            
            # Pre-seleccionar tipo actual
            tipo_actual = factor_actual.get('tipo_modelo', 'estatico')
            if tipo_actual == 'estocastico':
                tipo_estocastico_radio.setChecked(True)
            else:
                tipo_estatico_radio.setChecked(True)
            
            tipo_grupo.addButton(tipo_estatico_radio)
            tipo_grupo.addButton(tipo_estocastico_radio)
            
            radio_layout = QtWidgets.QVBoxLayout()
            radio_layout.addWidget(tipo_estatico_radio)
            radio_layout.addWidget(tipo_estocastico_radio)
            ajuste_layout.addLayout(radio_layout)
            
            ajuste_layout.addSpacing(10)
            
            # ===== FRAME PARA MODELO ESTÁTICO =====
            estatico_frame = QtWidgets.QGroupBox("Configuración Estática")
            estatico_layout = QtWidgets.QFormLayout(estatico_frame)
            
            # --- Reducción en FRECUENCIA (opcional) ---
            # Backward compat: si no existe afecta_frecuencia, asumir True si impacto_porcentual != 0
            afecta_frecuencia_default = factor_actual.get('afecta_frecuencia', factor_actual.get('impacto_porcentual', 0) != 0)
            
            afecta_frecuencia_check = QtWidgets.QCheckBox("Afecta frecuencia (probabilidad de ocurrencia)")
            afecta_frecuencia_check.setChecked(afecta_frecuencia_default)
            afecta_frecuencia_check.setToolTip("Si está marcado, el control afectará la probabilidad de que ocurra el evento")
            estatico_layout.addRow(afecta_frecuencia_check)
            
            impacto_var = NoScrollSpinBox()
            impacto_var.setRange(-200, 99)  # Positivo reduce (máx 99%), negativo aumenta
            # Invertir signo al cargar: internamente negativo = reducción, UI positivo = reducción
            impacto_var.setValue(-factor_actual.get('impacto_porcentual', -30))  # Pre-cargar valor invertido
            impacto_var.setSuffix("%")
            impacto_var.setToolTip("Positivo reduce la frecuencia (0-99%), negativo la aumenta")
            impacto_var.setEnabled(afecta_frecuencia_default)  # Habilitar según estado
            estatico_layout.addRow("   Reducción frecuencia (%):", impacto_var)
            
            # Conectar checkbox para habilitar/deshabilitar campo de frecuencia
            afecta_frecuencia_check.toggled.connect(impacto_var.setEnabled)
            
            # --- Reducción en SEVERIDAD (opcional) ---
            estatico_layout.addRow(QtWidgets.QLabel(""))  # Separador visual
            
            afecta_severidad_check = QtWidgets.QCheckBox("Afecta severidad (impacto económico)")
            afecta_severidad_check.setChecked(factor_actual.get('afecta_severidad', False))
            afecta_severidad_check.setToolTip("Si está marcado, el control afectará el impacto económico del evento")
            estatico_layout.addRow(afecta_severidad_check)
            
            # Contenedor para opciones de severidad
            severidad_container_edit = QtWidgets.QWidget()
            severidad_container_layout_edit = QtWidgets.QVBoxLayout(severidad_container_edit)
            severidad_container_layout_edit.setContentsMargins(20, 0, 0, 0)
            severidad_container_edit.setEnabled(factor_actual.get('afecta_severidad', False))
            
            # Radio buttons para tipo de severidad
            tipo_sev_grupo_edit = QtWidgets.QButtonGroup(ajuste_dialog)
            tipo_sev_porcentual_edit = QtWidgets.QRadioButton("Reducción porcentual")
            tipo_sev_seguro_edit = QtWidgets.QRadioButton("Seguro/Transferencia")
            
            # Pre-seleccionar según tipo actual
            tipo_sev_actual = factor_actual.get('tipo_severidad', 'porcentual')
            if tipo_sev_actual == 'seguro':
                tipo_sev_seguro_edit.setChecked(True)
            else:
                tipo_sev_porcentual_edit.setChecked(True)
            
            tipo_sev_grupo_edit.addButton(tipo_sev_porcentual_edit)
            tipo_sev_grupo_edit.addButton(tipo_sev_seguro_edit)
            
            tipo_sev_layout_edit = QtWidgets.QHBoxLayout()
            tipo_sev_layout_edit.addWidget(tipo_sev_porcentual_edit)
            tipo_sev_layout_edit.addWidget(tipo_sev_seguro_edit)
            tipo_sev_layout_edit.addStretch()
            severidad_container_layout_edit.addLayout(tipo_sev_layout_edit)
            
            # --- Frame para reducción porcentual ---
            porcentual_frame_edit = QtWidgets.QWidget()
            porcentual_layout_edit = QtWidgets.QFormLayout(porcentual_frame_edit)
            porcentual_layout_edit.setContentsMargins(0, 5, 0, 0)
            
            impacto_severidad_var = NoScrollSpinBox()
            impacto_severidad_var.setRange(-200, 99)
            impacto_severidad_var.setValue(-factor_actual.get('impacto_severidad_pct', -25))
            impacto_severidad_var.setSuffix("%")
            impacto_severidad_var.setToolTip("Positivo reduce el impacto económico (0-99%), negativo lo aumenta")
            porcentual_layout_edit.addRow("Reducción (%):", impacto_severidad_var)
            
            severidad_container_layout_edit.addWidget(porcentual_frame_edit)
            
            # --- Frame para modelo de seguro ---
            seguro_frame_edit = QtWidgets.QWidget()
            seguro_layout_edit = QtWidgets.QFormLayout(seguro_frame_edit)
            seguro_layout_edit.setContentsMargins(0, 5, 0, 0)
            
            # Tipo de deducible (por ocurrencia vs agregado)
            tipo_ded_group_edit = QtWidgets.QButtonGroup(seguro_frame_edit)
            tipo_ded_layout_edit = QtWidgets.QHBoxLayout()
            tipo_ded_ocurrencia_edit = QtWidgets.QRadioButton("Por ocurrencia")
            tipo_ded_ocurrencia_edit.setToolTip("El deducible se aplica a cada siniestro individual")
            tipo_ded_agregado_edit = QtWidgets.QRadioButton("Agregado anual")
            tipo_ded_agregado_edit.setToolTip("El deducible se aplica a la pérdida total del año")
            # Pre-seleccionar según valor actual
            tipo_ded_actual = factor_actual.get('seguro_tipo_deducible', 'agregado')
            if tipo_ded_actual == 'por_ocurrencia':
                tipo_ded_ocurrencia_edit.setChecked(True)
            else:
                tipo_ded_agregado_edit.setChecked(True)
            tipo_ded_group_edit.addButton(tipo_ded_ocurrencia_edit)
            tipo_ded_group_edit.addButton(tipo_ded_agregado_edit)
            tipo_ded_layout_edit.addWidget(tipo_ded_ocurrencia_edit)
            tipo_ded_layout_edit.addWidget(tipo_ded_agregado_edit)
            tipo_ded_layout_edit.addStretch()
            seguro_layout_edit.addRow("Tipo deducible:", tipo_ded_layout_edit)
            
            seguro_deducible_var_edit = NoScrollSpinBox()
            seguro_deducible_var_edit.setRange(0, 999999999)
            seguro_deducible_var_edit.setValue(factor_actual.get('seguro_deducible', 50000))
            seguro_deducible_var_edit.setPrefix("$ ")
            seguro_deducible_var_edit.setToolTip("Monto mínimo que NO cubre el seguro (el asegurado paga)")
            seguro_layout_edit.addRow("Deducible:", seguro_deducible_var_edit)
            
            seguro_cobertura_var_edit = NoScrollSpinBox()
            seguro_cobertura_var_edit.setRange(1, 100)
            seguro_cobertura_var_edit.setValue(factor_actual.get('seguro_cobertura_pct', 80))
            seguro_cobertura_var_edit.setSuffix("%")
            seguro_cobertura_var_edit.setToolTip("% del exceso sobre deducible que cubre el seguro")
            seguro_layout_edit.addRow("Cobertura (%):", seguro_cobertura_var_edit)
            
            # Límite por ocurrencia (nuevo)
            seguro_limite_ocurrencia_var_edit = NoScrollSpinBox()
            seguro_limite_ocurrencia_var_edit.setRange(0, 999999999)
            seguro_limite_ocurrencia_var_edit.setValue(factor_actual.get('seguro_limite_ocurrencia', 0))
            seguro_limite_ocurrencia_var_edit.setPrefix("$ ")
            seguro_limite_ocurrencia_var_edit.setToolTip("Máximo que paga el seguro por siniestro (0 = sin límite por ocurrencia)")
            seguro_layout_edit.addRow("Límite por siniestro:", seguro_limite_ocurrencia_var_edit)
            
            seguro_limite_var_edit = NoScrollSpinBox()
            seguro_limite_var_edit.setRange(0, 999999999)
            seguro_limite_var_edit.setValue(factor_actual.get('seguro_limite', 1000000))
            seguro_limite_var_edit.setPrefix("$ ")
            seguro_limite_var_edit.setToolTip("Máximo agregado anual que paga el seguro (0 = sin límite)")
            seguro_layout_edit.addRow("Límite agregado:", seguro_limite_var_edit)
            
            seguro_help_edit = QtWidgets.QLabel(
                "💡 <b>Por ocurrencia:</b> Deducible/límite se aplica a cada siniestro.<br>"
                "<b>Agregado:</b> Deducible/límite se aplica al total anual.<br>"
                "Ej: 3 siniestros de $30K c/u, Ded $25K por ocurrencia → Paga 3×$5K"
            )
            seguro_help_edit.setWordWrap(True)
            seguro_help_edit.setStyleSheet("color: #666; font-size: 9pt; padding: 3px;")
            seguro_layout_edit.addRow(seguro_help_edit)
            
            # Visibilidad inicial según tipo
            porcentual_frame_edit.setVisible(tipo_sev_actual != 'seguro')
            seguro_frame_edit.setVisible(tipo_sev_actual == 'seguro')
            severidad_container_layout_edit.addWidget(seguro_frame_edit)
            
            # Función para alternar entre porcentual y seguro
            def toggle_tipo_severidad_edit():
                porcentual_frame_edit.setVisible(tipo_sev_porcentual_edit.isChecked())
                seguro_frame_edit.setVisible(tipo_sev_seguro_edit.isChecked())
            
            tipo_sev_porcentual_edit.toggled.connect(toggle_tipo_severidad_edit)
            
            estatico_layout.addRow(severidad_container_edit)
            
            # Conectar checkbox para habilitar/deshabilitar contenedor de severidad
            afecta_severidad_check.toggled.connect(severidad_container_edit.setEnabled)
            
            estatico_help = QtWidgets.QLabel(
                "💡 Valores positivos = reducción (control), negativos = aumento (factor de riesgo).<br>"
                "Ej: Firewall 30% reduce frecuencia, Seguro transfiere impacto económico."
            )
            estatico_help.setWordWrap(True)
            estatico_help.setStyleSheet("color: #666; font-size: {UI_FONT_SMALL}pt; padding: 5px;")
            estatico_layout.addRow(estatico_help)
            
            ajuste_layout.addWidget(estatico_frame)
            
            # ===== FRAME PARA MODELO ESTOCÁSTICO =====
            estocastico_frame = QtWidgets.QGroupBox("Configuración Estocástica")
            estocastico_layout = QtWidgets.QFormLayout(estocastico_frame)
            
            confiabilidad_var = NoScrollSpinBox()
            confiabilidad_var.setRange(0, 100)
            confiabilidad_var.setValue(factor_actual.get('confiabilidad', 70))  # Pre-cargar valor
            confiabilidad_var.setSuffix("%")
            confiabilidad_var.setToolTip("% del tiempo que el control funciona correctamente")
            estocastico_layout.addRow("Confiabilidad (%):", confiabilidad_var)
            
            # --- SI FUNCIONA ---
            estocastico_layout.addRow(QtWidgets.QLabel("<b>─── Si funciona ───</b>"))
            
            reduccion_efectiva_var = NoScrollSpinBox()
            reduccion_efectiva_var.setRange(-100, 99)  # Máx 99% reducción para evitar factor negativo
            reduccion_efectiva_var.setValue(factor_actual.get('reduccion_efectiva', 80))  # Pre-cargar valor
            reduccion_efectiva_var.setSuffix("%")
            reduccion_efectiva_var.setToolTip("Reducción de frecuencia cuando funciona (0-99%, negativo aumenta)")
            estocastico_layout.addRow("Reducción frecuencia (%):", reduccion_efectiva_var)
            
            reduccion_sev_efectiva_var = NoScrollSpinBox()
            reduccion_sev_efectiva_var.setRange(-100, 99)  # Máx 99% reducción para evitar factor negativo
            reduccion_sev_efectiva_var.setValue(factor_actual.get('reduccion_severidad_efectiva', 50))  # Pre-cargar
            reduccion_sev_efectiva_var.setSuffix("%")
            reduccion_sev_efectiva_var.setToolTip("Reducción de severidad cuando funciona (0-99%, negativo aumenta)")
            estocastico_layout.addRow("Reducción severidad (%):", reduccion_sev_efectiva_var)
            
            # --- SI FALLA ---
            estocastico_layout.addRow(QtWidgets.QLabel("<b>─── Si falla ───</b>"))
            
            reduccion_fallo_var = NoScrollSpinBox()
            reduccion_fallo_var.setRange(-100, 99)  # Máx 99% reducción para evitar factor negativo
            reduccion_fallo_var.setValue(factor_actual.get('reduccion_fallo', 10))  # Pre-cargar valor
            reduccion_fallo_var.setSuffix("%")
            reduccion_fallo_var.setToolTip("Reducción de frecuencia cuando falla (0-99%, negativo aumenta)")
            estocastico_layout.addRow("Reducción frecuencia (%):", reduccion_fallo_var)
            
            reduccion_sev_fallo_var = NoScrollSpinBox()
            reduccion_sev_fallo_var.setRange(-100, 99)  # Máx 99% reducción para evitar factor negativo
            reduccion_sev_fallo_var.setValue(factor_actual.get('reduccion_severidad_fallo', 5))  # Pre-cargar
            reduccion_sev_fallo_var.setSuffix("%")
            reduccion_sev_fallo_var.setToolTip("Reducción de severidad cuando falla (0-99%, negativo aumenta)")
            estocastico_layout.addRow("Reducción severidad (%):", reduccion_sev_fallo_var)
            
            estocastico_help = QtWidgets.QLabel(
                "💡 En cada simulación, el control funciona o falla aleatoriamente.<br>"
                "Afecta tanto frecuencia como severidad según el estado.<br>"
                "Ej: 70% conf → 70% aplica reducciones 'funciona', 30% aplica 'falla'"
            )
            estocastico_help.setWordWrap(True)
            estocastico_help.setStyleSheet("color: #666; font-size: {UI_FONT_SMALL}pt; padding: 5px;")
            estocastico_layout.addRow(estocastico_help)
            
            ajuste_layout.addWidget(estocastico_frame)
            
            # Función para alternar visibilidad de frames
            def toggle_frames():
                estatico_frame.setVisible(tipo_estatico_radio.isChecked())
                estocastico_frame.setVisible(tipo_estocastico_radio.isChecked())
                
                # Forzar actualización del layout y ajuste del tamaño del diálogo
                ajuste_dialog.layout().activate()
                ajuste_dialog.adjustSize()
                
                # Establecer tamaño mínimo para evitar compresión
                ajuste_dialog.setMinimumHeight(0)
                ajuste_dialog.updateGeometry()
            
            tipo_estatico_radio.toggled.connect(toggle_frames)
            toggle_frames()  # Estado inicial
            
            # Conectar scroll area con contenido
            scroll_area_edit.setWidget(scroll_content_edit)
            main_layout_edit.addWidget(scroll_area_edit)
            
            # Botones (fuera del scroll para que siempre sean visibles)
            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
            )
            def validar_y_aceptar_edicion():
                nombre = nombre_factor_var.text().strip()
                if not nombre:
                    QtWidgets.QMessageBox.warning(ajuste_dialog, "Advertencia", "El nombre no puede estar vacío.")
                    return
                if tipo_estatico_radio.isChecked():
                    if not afecta_frecuencia_check.isChecked() and not afecta_severidad_check.isChecked():
                        QtWidgets.QMessageBox.warning(ajuste_dialog, "Advertencia", 
                            "Debe seleccionar al menos una opción: frecuencia o severidad.")
                        return
                ajuste_dialog.accept()

            buttons.accepted.connect(validar_y_aceptar_edicion)
            buttons.rejected.connect(ajuste_dialog.reject)
            main_layout_edit.addWidget(buttons)
            
            # Mostrar diálogo
            if ajuste_dialog.exec_() == QtWidgets.QDialog.Accepted:
                nombre = nombre_factor_var.text().strip()
                
                # Actualizar factor según el tipo seleccionado
                if tipo_estatico_radio.isChecked():
                    
                    # NOTA: En UI positivo = reducción, internamente negativo = reducción
                    # Invertimos el signo al guardar para mantener compatibilidad con lógica de simulación
                    
                    # Determinar tipo de severidad
                    es_seguro_edit = afecta_severidad_check.isChecked() and tipo_sev_seguro_edit.isChecked()
                    
                    factores_ajuste_existentes[row] = {
                        'nombre': nombre,
                        'tipo_modelo': 'estatico',
                        # Frecuencia: solo si está marcado
                        'afecta_frecuencia': afecta_frecuencia_check.isChecked(),
                        'impacto_porcentual': -impacto_var.value() if afecta_frecuencia_check.isChecked() else 0,
                        'activo': factor_actual.get('activo', True),  # Preservar estado activo
                        # Campos estocásticos con valores por defecto (para migración futura)
                        'confiabilidad': 100,
                        'reduccion_efectiva': impacto_var.value() if afecta_frecuencia_check.isChecked() else 0,
                        'reduccion_fallo': 0,
                        # Severidad: solo si está marcado
                        'afecta_severidad': afecta_severidad_check.isChecked(),
                        # Tipo de severidad: 'porcentual' o 'seguro'
                        'tipo_severidad': 'seguro' if es_seguro_edit else 'porcentual',
                        # Campos porcentuales
                        'impacto_severidad_pct': -impacto_severidad_var.value() if (afecta_severidad_check.isChecked() and not es_seguro_edit) else 0,
                        'reduccion_severidad_efectiva': impacto_severidad_var.value() if (afecta_severidad_check.isChecked() and not es_seguro_edit) else 0,
                        'reduccion_severidad_fallo': 0,
                        # Campos de seguro
                        'seguro_deducible': seguro_deducible_var_edit.value() if es_seguro_edit else 0,
                        'seguro_cobertura_pct': seguro_cobertura_var_edit.value() if es_seguro_edit else 100,
                        'seguro_limite': seguro_limite_var_edit.value() if es_seguro_edit else 0,
                        'seguro_tipo_deducible': 'por_ocurrencia' if (es_seguro_edit and tipo_ded_ocurrencia_edit.isChecked()) else 'agregado',
                        'seguro_limite_ocurrencia': seguro_limite_ocurrencia_var_edit.value() if es_seguro_edit else 0
                    }
                else:  # Estocástico
                    factores_ajuste_existentes[row] = {
                        'nombre': nombre,
                        'tipo_modelo': 'estocastico',
                        'confiabilidad': confiabilidad_var.value(),
                        'reduccion_efectiva': reduccion_efectiva_var.value(),
                        'reduccion_fallo': reduccion_fallo_var.value(),
                        'activo': factor_actual.get('activo', True),  # Preservar estado activo
                        # Campo estático por compatibilidad (no se usa en estocástico)
                        'impacto_porcentual': -reduccion_efectiva_var.value(),
                        # NUEVOS: Campos de severidad (estocástico siempre afecta severidad si hay valores)
                        'afecta_severidad': (reduccion_sev_efectiva_var.value() != 0 or reduccion_sev_fallo_var.value() != 0),
                        'impacto_severidad_pct': 0,
                        'reduccion_severidad_efectiva': reduccion_sev_efectiva_var.value(),
                        'reduccion_severidad_fallo': reduccion_sev_fallo_var.value()
                    }
                
                # Actualizar tabla y probabilidad ajustada
                actualizar_tabla_ajustes()
                actualizar_probabilidad_ajustada()
        
        # Función para manejar doble click en la tabla
        def on_table_double_click(item):
            if item is not None:
                row = item.row()
                # No permitir edición si se hace doble click en la columna de eliminar (columna 4)
                if item.column() != 4:
                    editar_ajuste(row)
        
        # Conectar botón para añadir factor
        add_ajuste_btn.clicked.connect(añadir_ajuste)
        
        # Conectar doble click en la tabla para editar
        ajustes_table.itemDoubleClicked.connect(on_table_double_click)
        
        # Inicializar la tabla
        actualizar_tabla_ajustes()
        
        # Conectar cambios en parámetros de frecuencia para actualizar probabilidad ajustada en tiempo real
        freq_combobox.currentIndexChanged.connect(actualizar_probabilidad_ajustada)
        tasa_var.textChanged.connect(actualizar_probabilidad_ajustada)
        prob_exito_var.textChanged.connect(actualizar_probabilidad_ajustada)
        prob_exito_var_bern.textChanged.connect(actualizar_probabilidad_ajustada)
        pg_mas_probable_var.textChanged.connect(actualizar_probabilidad_ajustada)
        beta_mas_probable_var.textChanged.connect(actualizar_probabilidad_ajustada)
        
        # Añadir el frame al layout principal (dentro del scroll)
        dialog_layout.addWidget(ajustes_frame)

        # Finalizar el contenido del scroll
        scroll_area.setWidget(scroll_content)
        dialog_main_layout.addWidget(scroll_area)
        
        # Separador visual antes de los botones (fuera del scroll)
        separador = QtWidgets.QFrame()
        separador.setFrameShape(QtWidgets.QFrame.HLine)
        separador.setFrameShadow(QtWidgets.QFrame.Sunken)
        separador.setStyleSheet("QFrame { color: #ccc; }")
        dialog_main_layout.addWidget(separador)
        
        # Botón aceptar/cancelar con mejor alineación y estilo (fuera del scroll)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        guardar_btn = button_box.button(QtWidgets.QDialogButtonBox.Ok)
        guardar_btn.setText("✔ Guardar")
        guardar_btn.setFixedHeight(35)  # Altura consistente con botones principales
        guardar_btn.setStyleSheet("""
            QPushButton {
                background-color: #5C9F35;
                color: white;
                padding: 5px 15px;
                font-weight: bold;
                border-radius: 3px;
                min-height: 35px;
            }
            QPushButton:hover {
                background-color: #4a7d2a;
            }
        """)
        cancelar_btn = button_box.button(QtWidgets.QDialogButtonBox.Cancel)
        cancelar_btn.setText("✖ Cancelar")
        cancelar_btn.setFixedHeight(35)  # Altura consistente con botones principales
        cancelar_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                padding: 5px 15px;
                border: 1px solid #aaa;
                border-radius: 3px;
                min-height: 35px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        def on_guardar_clicked():
            self.guardar_evento(
                dialog, new, row, nombre_var,
                sev_combobox, sev_input_method_combo,
                sev_min_var, sev_mas_probable_var, sev_max_var,
                sev_norm_mean_var, sev_norm_std_var,
                sev_ln_param_mode_combo, sev_ln_s_var, sev_ln_scale_var, sev_ln_mean_var, sev_ln_std_var, sev_ln_mu_var, sev_ln_sigma_var, sev_ln_loc_var,
                sev_gpd_c_var, sev_gpd_scale_var, sev_gpd_loc_var,
                freq_combobox, tasa_var, num_eventos_var,
                prob_exito_var, prob_exito_var_bern, 
                pg_minimo_var, pg_mas_probable_var, pg_maximo_var, pg_confianza_var,
                beta_minimo_var, beta_mas_probable_var, beta_maximo_var, beta_confianza_var,
                vinculos_existentes, factores_ajuste_existentes,
                sev_freq_config,
                sev_limite_var, freq_limite_var)
        
        button_box.accepted.connect(on_guardar_clicked)
        button_box.rejected.connect(dialog.reject)
        
        # Añadir espacio antes de los botones para mejor presentación (fuera del scroll)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(button_box)
        dialog_main_layout.addLayout(button_layout)
        
        # Mostrar el diálogo
        dialog.exec_()

    # --- MODIFICADO: Añadir los nuevos parámetros a la firma de la función ---
    def guardar_evento(self, dialog, new, row, nombre_var,
                     sev_combobox, sev_input_method_combo, # <- Añadido combo método
                     sev_min_var, sev_mas_probable_var, sev_max_var,
                     sev_norm_mean_var, sev_norm_std_var,
                     sev_ln_param_mode_combo, sev_ln_s_var, sev_ln_scale_var, sev_ln_mean_var, sev_ln_std_var, sev_ln_mu_var, sev_ln_sigma_var, sev_ln_loc_var, # <- Params LN
                     sev_gpd_c_var, sev_gpd_scale_var, sev_gpd_loc_var, # <- Añadidos params GPD
                     freq_combobox, tasa_var, num_eventos_var,
                     prob_exito_var, prob_exito_var_bern, 
                     pg_minimo_var, pg_mas_probable_var, pg_maximo_var, pg_confianza_var, # <- Añadidos params Poisson-Gamma
                     beta_minimo_var, beta_mas_probable_var, beta_maximo_var, beta_confianza_var, # <- Añadidos params Beta
                     vinculos_existentes, factores_ajuste_existentes=None,
                     sev_freq_config=None,
                     sev_limite_var=None, freq_limite_var=None):
        try:
            nombre_evento = nombre_var.text().strip()
            if not nombre_evento:
                raise ValueError("El nombre del evento no puede estar vacío.")
            if len(nombre_evento) > 50:
                raise ValueError("El nombre del evento no puede tener más de 50 caracteres.")

            # Severidad
            # --- NUEVA LÓGICA PARA SEVERIDAD ---
            sev_opcion = sev_combobox.currentIndex() + 1
            dist_nombre_sev = sev_combobox.currentText() # "Normal", "LogNormal", etc.

            # Determinar el método de entrada
            sev_input_method = 'min_mode_max' # Por defecto
            if dist_nombre_sev in ["Normal", "LogNormal", "Pareto"] and sev_input_method_combo.currentIndex() == 1:
                sev_input_method = 'direct'

            # Inicializar variables para guardar
            sev_minimo = None
            sev_mas_probable = None
            sev_maximo = None
            sev_params_direct = {} # Diccionario para parámetros directos

            dist_sev = None # Inicializamos la distribución

            if sev_input_method == 'direct':
                # --- Leer y Validar Parámetros Directos ---
                if dist_nombre_sev == "LogNormal":
                    # Determinar modo de parametrización: 0=s/scale, 1=mean/std, 2=mu/sigma
                    ln_mode = sev_ln_param_mode_combo.currentIndex()
                    try:
                        loc = float(sev_ln_loc_var.text() if sev_ln_loc_var.text() else '0')
                    except Exception:
                        raise ValueError("loc debe ser numérico para Lognormal.")

                    if ln_mode == 0:
                        # s/scale (SciPy)
                        if not sev_ln_s_var.text():
                            raise ValueError("'s' no puede estar vacío para Lognormal.")
                        if not sev_ln_scale_var.text():
                            raise ValueError("'scale' no puede estar vacío para Lognormal.")
                        try:
                            s = float(sev_ln_s_var.text())
                            scale = float(sev_ln_scale_var.text())
                        except Exception:
                            raise ValueError("'s' y 'scale' deben ser numéricos para Lognormal.")
                        if s <= 0:
                            raise ValueError("Shape (s) debe ser positivo para Lognormal.")
                        if scale <= 0:
                            raise ValueError("Scale debe ser positivo para Lognormal.")
                        sev_params_direct = {'s': s, 'scale': scale, 'loc': loc}
                    elif ln_mode == 1:
                        # mean/std (en X)
                        if not sev_ln_mean_var.text():
                            raise ValueError("'mean' no puede estar vacío para Lognormal.")
                        if not sev_ln_std_var.text():
                            raise ValueError("'std' no puede estar vacío para Lognormal.")
                        try:
                            mean = float(sev_ln_mean_var.text())
                            std = float(sev_ln_std_var.text())
                        except Exception:
                            raise ValueError("'mean' y 'std' deben ser numéricos para Lognormal.")
                        if mean <= 0:
                            raise ValueError("mean debe ser > 0 para Lognormal.")
                        if std <= 0:
                            raise ValueError("std debe ser > 0 para Lognormal.")
                        sev_params_direct = {'mean': mean, 'std': std, 'loc': loc}
                    else:
                        # mu/sigma (de ln X)
                        if not sev_ln_mu_var.text():
                            raise ValueError("'mu' no puede estar vacío para Lognormal.")
                        if not sev_ln_sigma_var.text():
                            raise ValueError("'sigma' no puede estar vacío para Lognormal.")
                        try:
                            mu = float(sev_ln_mu_var.text())
                            sigma = float(sev_ln_sigma_var.text())
                        except Exception:
                            raise ValueError("'mu' y 'sigma' deben ser numéricos para Lognormal.")
                        if sigma <= 0:
                            raise ValueError("sigma debe ser > 0 para Lognormal.")
                        sev_params_direct = {'mu': mu, 'sigma': sigma, 'loc': loc}

                    # Validar creando la distribución mediante la función general
                    dist_sev = generar_distribucion_severidad(sev_opcion, None, None, None, input_method='direct', params_direct=sev_params_direct)
                elif dist_nombre_sev == "Normal":
                    # Normal directo: mean/std (o mu/sigma como sinónimos)
                    if not sev_norm_mean_var.text():
                        raise ValueError("'mean' no puede estar vacío para Normal.")
                    if not sev_norm_std_var.text():
                        raise ValueError("'std' no puede estar vacío para Normal.")
                    try:
                        mean = float(sev_norm_mean_var.text())
                        std = float(sev_norm_std_var.text())
                    except Exception:
                        raise ValueError("'mean' y 'std' deben ser numéricos para Normal.")
                    if std <= 0:
                        raise ValueError("Desviación estándar (std) debe ser > 0 para Normal.")
                    sev_params_direct = {'mean': mean, 'std': std}
                    dist_sev = generar_distribucion_severidad(sev_opcion, None, None, None, input_method='direct', params_direct=sev_params_direct)
                elif dist_nombre_sev == "Pareto": # GPD
                    if not sev_gpd_c_var.text().strip():
                        raise ValueError("'c' (shape) no puede estar vacío para GPD.")
                    if not sev_gpd_scale_var.text().strip():
                        raise ValueError("'scale' no puede estar vacío para GPD.")
                    if not sev_gpd_loc_var.text().strip():
                        raise ValueError("'loc' no puede estar vacío para GPD.")
                    try:
                        c = float(sev_gpd_c_var.text())
                        scale = float(sev_gpd_scale_var.text())
                        loc = float(sev_gpd_loc_var.text())
                    except (ValueError, TypeError):
                        raise ValueError("Los parámetros de GPD deben ser numéricos.")
                    if scale <= 0: raise ValueError("Scale (beta) debe ser positivo para GPD.")
                    sev_params_direct = {'c': c, 'scale': scale, 'loc': loc}
                    dist_sev = genpareto(c=c, scale=scale, loc=loc)

            else: # sev_input_method == 'min_mode_max'
                # --- Leer y Validar Parámetros Min/Mode/Max (como antes) ---
                try:
                    if not sev_min_var.text(): raise ValueError("Mínimo vacío.")
                    sev_minimo = float(sev_min_var.text())
                    if not sev_max_var.text(): raise ValueError("Máximo vacío.")
                    sev_maximo = float(sev_max_var.text())

                    # Más probable solo necesario si no es Uniforme
                    if dist_nombre_sev != "Uniforme":
                        if not sev_mas_probable_var.text(): raise ValueError("Más probable vacío.")
                        sev_mas_probable = float(sev_mas_probable_var.text())
                    else:
                        sev_mas_probable = None # No se usa para Uniforme

                    # Generar distribución usando el método antiguo (que llama a obtener_parametros_...)
                    # La función generar_distribucion_severidad ya valida Min <= Mode <= Max etc.
                    dist_sev = generar_distribucion_severidad(sev_opcion, sev_minimo, sev_mas_probable, sev_maximo)

                except ValueError as e:
                     raise ValueError(f"Error en parámetros Min/Mode/Max: {e}")

            # Si dist_sev no se pudo crear por alguna razón (debería haber lanzado error antes)
            if dist_sev is None:
                raise ValueError("No se pudo crear la distribución de severidad.")

            # Frecuencia
            freq_opcion = freq_combobox.currentIndex() + 1
            tasa = None
            num_eventos = None
            prob_exito = None
            dist_freq = None
            # Inicialización de parámetros específicos de frecuencia que se guardarán
            pg_minimo_ui, pg_mas_probable_ui, pg_maximo_ui, pg_confianza_ui = None, None, None, None
            beta_minimo_ui, beta_mas_probable_ui, beta_maximo_ui, beta_confianza_ui = None, None, None, None
            calculated_alpha, calculated_beta = None, None

            if freq_opcion == 1: # Poisson
                 if not tasa_var.text(): raise ValueError("La tasa media (λ) no puede estar vacía.")
                 tasa = float(tasa_var.text())
                 if tasa <= 0: raise ValueError("La tasa media (λ) debe ser mayor que cero.")
                 dist_freq = generar_distribucion_frecuencia(freq_opcion, tasa=tasa)
            elif freq_opcion == 2: # Binomial
                if not num_eventos_var.text(): raise ValueError("El número de eventos posibles (n) no puede estar vacío.")
                if not prob_exito_var.text(): raise ValueError("La probabilidad de éxito (p) no puede estar vacía.")
                num_eventos = int(float(num_eventos_var.text()))
                prob_exito = float(prob_exito_var.text())
                if num_eventos <= 0: raise ValueError("El número de eventos posibles (n) debe ser mayor que cero.")
                if not 0 <= prob_exito <= 1: raise ValueError("La probabilidad de éxito (p) debe estar entre 0 y 1.")
                dist_freq = generar_distribucion_frecuencia(freq_opcion, num_eventos_posibles=num_eventos, probabilidad_exito=prob_exito)
            elif freq_opcion == 3: # Bernoulli
                if not prob_exito_var_bern.text(): raise ValueError("La probabilidad de éxito (p) no puede estar vacía.")
                prob_exito = float(prob_exito_var_bern.text())
                if not 0 <= prob_exito <= 1: raise ValueError("La probabilidad de éxito (p) debe estar entre 0 y 1.")
                dist_freq = generar_distribucion_frecuencia(freq_opcion, probabilidad_exito=prob_exito)
            elif freq_opcion == 4: # Poisson-Gamma
                if not pg_minimo_var.text(): raise ValueError("El valor mínimo de ocurrencia no puede estar vacío.")
                if not pg_mas_probable_var.text(): raise ValueError("El valor más probable de ocurrencia no puede estar vacío.")
                if not pg_maximo_var.text(): raise ValueError("El valor máximo de ocurrencia no puede estar vacío.")
                if not pg_confianza_var.text(): raise ValueError("La confianza asociada al rango no puede estar vacía.")
                
                pg_minimo_ui = float(pg_minimo_var.text())
                pg_mas_probable_ui = float(pg_mas_probable_var.text())
                pg_maximo_ui = float(pg_maximo_var.text())
                pg_confianza_ui = float(pg_confianza_var.text()) # Valor en %
                
                pg_confianza_calc = pg_confianza_ui / 100
                
                if pg_minimo_ui <= 0: raise ValueError("El valor mínimo para Poisson-Gamma debe ser mayor que cero.")
                if pg_mas_probable_ui <= 0: raise ValueError("El valor más probable para Poisson-Gamma debe ser mayor que cero.")
                if pg_maximo_ui <= 0: raise ValueError("El valor máximo para Poisson-Gamma debe ser mayor que cero.")
                if not (pg_minimo_ui < pg_mas_probable_ui < pg_maximo_ui): 
                    raise ValueError("Para Poisson-Gamma, debe cumplirse: mínimo < más probable < máximo.")
                if not (0 < pg_confianza_calc < 1 or pg_confianza_calc == 0 or pg_confianza_calc == 1):
                     raise ValueError("La confianza para Poisson-Gamma debe estar entre 0% y 100%.")
                
                calculated_alpha, calculated_beta = obtener_parametros_gamma_para_poisson(
                    pg_minimo_ui, pg_mas_probable_ui, pg_maximo_ui, pg_confianza_calc)
                dist_freq = generar_distribucion_frecuencia(freq_opcion, poisson_gamma_params=(calculated_alpha, calculated_beta))
            elif freq_opcion == 5: # Beta para probabilidad anual
                if not beta_minimo_var.text(): raise ValueError("La probabilidad mínima no puede estar vacía.")
                if not beta_mas_probable_var.text(): raise ValueError("La probabilidad más probable no puede estar vacía.")
                if not beta_maximo_var.text(): raise ValueError("La probabilidad máxima no puede estar vacía.")
                if not beta_confianza_var.text(): raise ValueError("La confianza asociada al rango no puede estar vacía.")
                
                beta_minimo_ui = float(beta_minimo_var.text())
                beta_mas_probable_ui = float(beta_mas_probable_var.text())
                beta_maximo_ui = float(beta_maximo_var.text())
                beta_confianza_ui = float(beta_confianza_var.text())

                beta_minimo_calc = beta_minimo_ui / 100
                beta_mas_probable_calc = beta_mas_probable_ui / 100
                beta_maximo_calc = beta_maximo_ui / 100
                beta_confianza_calc = beta_confianza_ui / 100
                
                if not (0 <= beta_minimo_calc < beta_mas_probable_calc < beta_maximo_calc <= 1): 
                    raise ValueError("Para Beta, debe cumplirse: 0% ≤ mínimo < más probable < máximo ≤ 100% y en el orden correcto.")
                if not (0 < beta_confianza_calc < 1 or beta_confianza_calc == 0 or beta_confianza_calc == 1):
                    raise ValueError("La confianza para Beta debe estar entre 0% y 100%.")
                
                calculated_alpha, calculated_beta = obtener_parametros_beta_frecuencia(
                    beta_minimo_calc, beta_mas_probable_calc, beta_maximo_calc, beta_confianza_calc)
                dist_freq = generar_distribucion_frecuencia(freq_opcion, beta_params=(calculated_alpha, calculated_beta))

            if dist_freq is None:
                 raise ValueError("No se pudo crear la distribución de frecuencia.")

            # Parsear límites superiores opcionales
            sev_limite_superior = None
            if sev_limite_var is not None:
                sev_limite_text = sev_limite_var.text().strip()
                if sev_limite_text:
                    try:
                        sev_limite_superior = float(sev_limite_text)
                        if sev_limite_superior <= 0:
                            raise ValueError("El límite superior de severidad debe ser mayor que cero.")
                    except ValueError as e:
                        if "mayor que cero" in str(e):
                            raise
                        raise ValueError(f"El límite superior de severidad debe ser un número válido: {sev_limite_text}")
            
            freq_limite_superior = None
            freq_limite_text = freq_limite_var.text().strip() if freq_limite_var is not None else ""
            if freq_limite_text:
                try:
                    freq_limite_superior = int(float(freq_limite_text))
                    if freq_limite_superior <= 0:
                        raise ValueError("El máximo de ocurrencias por año debe ser mayor que cero.")
                except ValueError as e:
                    if "mayor que cero" in str(e):
                        raise
                    raise ValueError(f"El máximo de ocurrencias por año debe ser un número entero válido: {freq_limite_text}")

            evento_temp = {
                'nombre': nombre_evento,
                'id': str(uuid.uuid4()) if new else self.eventos_riesgo[row]['id'],
                'activo': True if new else self.eventos_riesgo[row].get('activo', True),  # Nuevo campo para activar/desactivar
                'sev_opcion': sev_opcion,
                'sev_input_method': sev_input_method,
                'sev_minimo': sev_minimo,
                'sev_mas_probable': sev_mas_probable,
                'sev_maximo': sev_maximo,
                'sev_params_direct': sev_params_direct,
                'sev_limite_superior': sev_limite_superior,
                'freq_opcion': freq_opcion,
                'freq_limite_superior': freq_limite_superior,
                'tasa': tasa,
                'num_eventos': num_eventos,
                'prob_exito': prob_exito,
                'pg_minimo': pg_minimo_ui,
                'pg_mas_probable': pg_mas_probable_ui,
                'pg_maximo': pg_maximo_ui,
                'pg_confianza': pg_confianza_ui,
                'pg_alpha': calculated_alpha if freq_opcion == 4 else None, 
                'pg_beta': calculated_beta if freq_opcion == 4 else None,
                'beta_minimo': beta_minimo_ui,
                'beta_mas_probable': beta_mas_probable_ui,
                'beta_maximo': beta_maximo_ui,
                'beta_confianza': beta_confianza_ui,
                'beta_alpha': calculated_alpha if freq_opcion == 5 else None, 
                'beta_beta': calculated_beta if freq_opcion == 5 else None,
                
                'dist_severidad': dist_sev, # Objeto distribución creado
                'dist_frecuencia': dist_freq, # Objeto distribución creado

                # Vínculos
                'vinculos': copy.deepcopy(vinculos_existentes) if vinculos_existentes else [],
                
                # Factores de ajuste de probabilidad (log-odds)
                'factores_ajuste': copy.deepcopy(factores_ajuste_existentes) if factores_ajuste_existentes else [],
                
                # Escalamiento de severidad por frecuencia
                'sev_freq_activado': False,
                'sev_freq_modelo': 'reincidencia',
                'sev_freq_tipo_escalamiento': 'lineal',
                'sev_freq_tabla': [{'desde': 1, 'hasta': 2, 'multiplicador': 1.0}, {'desde': 3, 'hasta': None, 'multiplicador': 2.0}],
                'sev_freq_paso': 0.5,
                'sev_freq_base': 1.5,
                'sev_freq_factor_max': 5.0,
                'sev_freq_alpha': 0.5,
                'sev_freq_solo_aumento': True,
                'sev_freq_sistemico_factor_max': 3.0,
            }
            
            # Override sev_freq_* fields from UI config if provided
            if sev_freq_config and isinstance(sev_freq_config, dict):
                for key, value in sev_freq_config.items():
                    if key.startswith('sev_freq_'):
                        evento_temp[key] = value
            
            # DEBUG: Verificar que los factores se guardaron
            if factores_ajuste_existentes:
                print(f"[DEBUG GUARDAR] Guardando {len(factores_ajuste_existentes)} factores para '{nombre_evento}':")
                for f in factores_ajuste_existentes:
                    print(f"  - {f.get('nombre')}: {f.get('impacto_porcentual')}% (activo: {f.get('activo')})")

            # Asignar un ID al evento
            if not new:
                # Obtener el ID existente
                evento_temp['id'] = self.eventos_riesgo[row]['id']
            else:
                # Asignar un nuevo ID único
                evento_temp['id'] = str(uuid.uuid4())

            # Validar que no se formen ciclos en las dependencias
            eventos_temp = self.eventos_riesgo.copy()
            if new:
                eventos_temp.append(evento_temp)
            else:
                eventos_temp[row] = evento_temp

            if self.tiene_ciclo(eventos_temp):
                raise ValueError("Agregar estos eventos vinculados genera un error de dependencia cíclica.")

            # Guardar evento
            if new:
                self.eventos_riesgo.append(evento_temp)
                row_position = self.eventos_table.rowCount()
                self.eventos_table.insertRow(row_position)
                # Columna 0: checkbox activo
                self.eventos_table.setCellWidget(row_position, 0, self.crear_checkbox_activo(row_position, activo=True))
                # Columna 1: nombre del evento
                self.eventos_table.setItem(row_position, 1, self.crear_table_item_con_wrap(nombre_evento))
                self.actualizar_vista_eventos()  # Actualizar vista
                
                # Evento guardado exitosamente
            else:
                self.eventos_riesgo[row] = evento_temp
                # Actualizar checkbox (mantener estado actual)
                activo_actual = evento_temp.get('activo', True)
                self.eventos_table.setCellWidget(row, 0, self.crear_checkbox_activo(row, activo=activo_actual))
                # Actualizar nombre
                self.eventos_table.setItem(row, 1, self.crear_table_item_con_wrap(nombre_evento))
                # Aplicar estilo según estado activo
                self.aplicar_estilo_fila_evento(row)
                self.actualizar_vista_eventos()  # Actualizar vista (incluye tarjetas si están activas)
                
                # Evento actualizado exitosamente

            dialog.accept()

        except ValueError as ve:
            QtWidgets.QMessageBox.critical(dialog, "Error de Validación", str(ve)) # Usar 'dialog' como parent
        except Exception as e:
            error_message = traceback.format_exc()
            QtWidgets.QMessageBox.critical(dialog, "Error Inesperado", f"No se pudo guardar el evento:\n{error_message}") # Usar 'dialog'

    def tiene_ciclo(self, eventos_riesgo):
        id_a_evento = {evento['id']: evento for evento in eventos_riesgo}
        visited = set()
        rec_stack = set()

        def is_cyclic_util(evento_id):
            visited.add(evento_id)
            rec_stack.add(evento_id)
            evento = id_a_evento[evento_id]

            # Obtener IDs de padres desde la nueva estructura
            padres_ids = []
            if 'vinculos' in evento:
                padres_ids = [vinculo['id_padre'] for vinculo in evento['vinculos']]
            elif 'eventos_padres' in evento:
                # Compatibilidad con formato antiguo
                padres_ids = evento.get('eventos_padres', [])

            for padre_id in padres_ids:
                if padre_id not in visited:
                    if is_cyclic_util(padre_id):
                        return True
                elif padre_id in rec_stack:
                    return True
            rec_stack.remove(evento_id)
            return False

        for evento in eventos_riesgo:
            if evento['id'] not in visited:
                if is_cyclic_util(evento['id']):
                    return True
        return False

    def eliminar_evento(self):
        selected_items = self.eventos_table.selectionModel().selectedRows()
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "Advertencia", "Seleccione al menos un evento para eliminar.")
            return

        # Confirmar eliminación múltiple
        respuesta = QtWidgets.QMessageBox.question(
            self,
            "Eliminar Eventos",
            f"¿Estás seguro de que deseas eliminar {len(selected_items)} evento(s)?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if respuesta == QtWidgets.QMessageBox.Yes:
            # Ordenar los índices de fila en orden descendente para evitar problemas al eliminar filas
            rows = sorted([index.row() for index in selected_items], reverse=True)
            ids_eliminados = {self.eventos_riesgo[row].get('id') for row in rows}
            for row in rows:
                del self.eventos_riesgo[row]
                self.eventos_table.removeRow(row)
            self.limpiar_vinculos_huerfanos(ids_eliminados)
            self.reconstruir_checkboxes_eventos()
            self.actualizar_vista_eventos()  # Actualizar vista

    def duplicar_eventos(self):
        selected_items = self.eventos_table.selectionModel().selectedRows()
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "Advertencia", "Seleccione al menos un evento para duplicar.")
            return

        # Mapeo entre IDs originales y nuevos IDs para los eventos duplicados
        id_original_a_nuevo = {}
        # Lista para almacenar los nuevos eventos duplicados
        nuevos_eventos = []
        eventos_a_duplicar = []

        for index in selected_items:
            row = index.row()
            evento_original = self.eventos_riesgo[row]
            eventos_a_duplicar.append(evento_original)

        # Primero asignamos nuevos IDs
        for evento_original in eventos_a_duplicar:
            evento_nuevo = copy.deepcopy(evento_original)
            nuevo_id = str(uuid.uuid4())
            id_original_a_nuevo[evento_original['id']] = nuevo_id
            evento_nuevo['id'] = nuevo_id
            # Añadir un prefijo o sufijo al nombre para indicar que es una copia
            evento_nuevo['nombre'] = evento_nuevo['nombre'] + " (Copia)"
            nuevos_eventos.append(evento_nuevo)

        # Actualizar las dependencias de los eventos duplicados
        for evento_nuevo in nuevos_eventos:
            # Manejar la nueva estructura de vínculos
            if 'vinculos' in evento_nuevo:
                vinculos_actualizados = []
                for vinculo in evento_nuevo.get('vinculos', []):
                    padre_id = vinculo['id_padre']
                    tipo = vinculo['tipo']
                    prob = vinculo.get('probabilidad', 100)
                    fsev = vinculo.get('factor_severidad', 1.0)
                    umbral = vinculo.get('umbral_severidad', 0)
                    # Si el evento padre fue duplicado, usamos el nuevo ID
                    if padre_id in id_original_a_nuevo:
                        vinculos_actualizados.append({
                            'id_padre': id_original_a_nuevo[padre_id],
                            'tipo': tipo,
                            'probabilidad': prob,
                            'factor_severidad': fsev,
                            'umbral_severidad': umbral
                        })
                    else:
                        # Si no, mantenemos el ID original
                        vinculos_actualizados.append({
                            'id_padre': padre_id,
                            'tipo': tipo,
                            'probabilidad': prob,
                            'factor_severidad': fsev,
                            'umbral_severidad': umbral
                        })
                evento_nuevo['vinculos'] = vinculos_actualizados

            # Compatibilidad con formato antiguo
            elif 'eventos_padres' in evento_nuevo:
                eventos_padres_originales = evento_nuevo.get('eventos_padres', [])
                eventos_padres_actualizados = []
                for padre_id in eventos_padres_originales:
                    # Si el evento padre fue duplicado, usamos el nuevo ID
                    if padre_id in id_original_a_nuevo:
                        eventos_padres_actualizados.append(id_original_a_nuevo[padre_id])
                    else:
                        # Si no, mantenemos el ID original
                        eventos_padres_actualizados.append(padre_id)
                evento_nuevo['eventos_padres'] = eventos_padres_actualizados

        # Añadir los nuevos eventos a la lista y a la tabla
        for evento_nuevo in nuevos_eventos:
            self.eventos_riesgo.append(evento_nuevo)
            row_position = self.eventos_table.rowCount()
            self.eventos_table.insertRow(row_position)
            # Columna 0: checkbox (mantener estado del original)
            activo = evento_nuevo.get('activo', True)
            self.eventos_table.setCellWidget(row_position, 0, self.crear_checkbox_activo(row_position, activo=activo))
            # Columna 1: nombre
            self.eventos_table.setItem(row_position, 1, self.crear_table_item_con_wrap(evento_nuevo['nombre']))
        
        self.actualizar_vista_eventos()  # Actualizar vista
        self.statusBar().showMessage(f"Se han duplicado {len(nuevos_eventos)} evento(s)", 5000)

    def crear_seccion_colapsable(self, titulo, parent_layout=None):
        """Crea una sección colapsable para mostrar resultados estadísticos."""
        if parent_layout is None:
            parent_layout = self.resultados_layout
        
        # Crear widget contenedor de sección
        seccion = QtWidgets.QWidget()
        seccion_layout = QtWidgets.QVBoxLayout(seccion)
        seccion_layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear cabecera con botón para colapsar/expandir
        header = QtWidgets.QWidget()
        header.setProperty("class", "seccion-header")
        header.setCursor(QtCore.Qt.PointingHandCursor)
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Botón expandir/colapsar (más compacto y discreto)
        toggle_button = QtWidgets.QPushButton()
        toggle_button.setProperty("class", "toggle-button")
        toggle_button.setFixedSize(18, 18)  # Tamaño reducido pero visible
        toggle_button.setText("▼")
        toggle_button.setToolTip("Colapsar/Expandir sección")
        # Estilo discreto pero no transparente
        toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #F2F2F2; /* Gris muy claro */
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                padding: 0px;
                margin: 0px;
                font-size: {UI_FONT_XSMALL}pt;
                min-width: 18px;
                max-width: 18px;
            }
            QPushButton:hover {
                background-color: #E6E6E6;
            }
        """)
        header_layout.addWidget(toggle_button)
        
        # Título de la sección
        title_label = QtWidgets.QLabel(titulo)
        title_label.setFont(QtGui.QFont("Helvetica", 11, QtGui.QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Contenedor para el contenido de la sección
        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(25, 10, 10, 10)
        
        # Añadir componentes a la sección
        seccion_layout.addWidget(header)
        seccion_layout.addWidget(content)
        
        # Añadir la sección al layout padre
        parent_layout.addWidget(seccion)
        
        # Conectar señales y controlar estado
        toggle_button.clicked.connect(lambda: self.toggle_seccion(content, toggle_button))
        header.mousePressEvent = lambda event: self.toggle_seccion(content, toggle_button)
        
        # Agregar animación fade-in sutil a la sección
        try:
            self.agregar_animacion_fade_in(seccion, duracion=400)
        except Exception:
            pass
        
        # Devolver componentes para su posterior manipulación
        return {
            "seccion": seccion,
            "contenido": content,
            "contenido_layout": content_layout,
            "toggle_button": toggle_button,
            "titulo": title_label
        }
    
    def toggle_seccion(self, content_widget, toggle_button):
        """Alterna la visibilidad de una sección colapsable."""
        # Estilo base compartido
        base_style = """
            QPushButton {
                background-color: #F2F2F2; /* Gris muy claro */
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                padding: 0px;
                margin: 0px;
                font-size: {UI_FONT_XSMALL}pt;
                min-width: 18px;
                max-width: 18px;
            }
            QPushButton:hover {
                background-color: #E6E6E6;
            }
        """
        
        if content_widget.isVisible():
            content_widget.hide()
            toggle_button.setText("▶")  # Triángulo hacia la derecha
            toggle_button.setStyleSheet(base_style)
        else:
            content_widget.show()
            toggle_button.setText("▼")  # Triángulo hacia abajo
            toggle_button.setStyleSheet(base_style)
    
    def crear_display_valor(self, etiqueta, valor, es_destacado=False, parent_layout=None):
        """Crea un widget para mostrar un par etiqueta-valor."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 3, 0, 3)
        
        # Etiqueta
        label = QtWidgets.QLabel(etiqueta + ":")
        if es_destacado:
            font = label.font()
            font.setBold(True)
            label.setFont(font)
        layout.addWidget(label)
        
        # Valor
        value_label = QtWidgets.QLabel(valor)
        if es_destacado:
            font = value_label.font()
            font.setBold(True)
            value_label.setFont(font)
            value_label.setStyleSheet("color: #2E86C1;")  # Azul para destacar
        layout.addWidget(value_label)
        layout.addStretch()
        
        if parent_layout is not None:
            parent_layout.addWidget(widget)
        
        return widget
    
    def crear_tabla_datos(self, df, titulo=None, parent_layout=None):
        """Crea una tabla a partir de un DataFrame para mostrar datos estadísticos."""
        # Widget contenedor de la tabla
        table_widget = QtWidgets.QWidget()
        table_layout = QtWidgets.QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 5, 0, 5)
        
        # Añadir título si se proporciona
        if titulo:
            title_label = QtWidgets.QLabel(titulo)
            title_label.setFont(QtGui.QFont("Helvetica", 10, QtGui.QFont.Bold))
            table_layout.addWidget(title_label)
        
        # Crear tabla
        table = QtWidgets.QTableWidget()
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))
        
        # Establecer encabezados
        table.setHorizontalHeaderLabels(df.columns)
        
        # Rellenar datos
        for i, row in enumerate(df.itertuples(index=False)):
            for j, val in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(val))
                table.setItem(i, j, item)
        
        # Ajustar tamaño de las columnas al contenido
        table.resizeColumnsToContents()
        table.resizeRowsToContents()

        # Configurar el modo de redimensionado: una sola columna se ajusta al contenido
        # Preferimos 'Valor de Pérdida' si existe; de lo contrario, la última columna
        header = table.horizontalHeader()
        try:
            headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
        except Exception:
            headers = []
        if 'Valor de Pérdida' in headers:
            auto_col = headers.index('Valor de Pérdida')
        elif table.columnCount() > 0:
            auto_col = table.columnCount() - 1
        else:
            auto_col = 0
        for j in range(table.columnCount()):
            if j == auto_col:
                header.setSectionResizeMode(j, QtWidgets.QHeaderView.ResizeToContents)
            else:
                header.setSectionResizeMode(j, QtWidgets.QHeaderView.Stretch)
        
        # Estilos y comportamiento
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)  # Sólo lectura
        table.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)
        table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        
        # Aumentar el tamaño de la tabla para mejor visualización
        table.setMinimumHeight(min(30 * (len(df) + 2), 300))  # Altura según número de filas, máximo 300px
        table.setMinimumWidth(400)  # Ancho mínimo para ver bien todas las columnas
        
        # Establecer política de tamaño para que la tabla ocupe más espacio disponible
        table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        
        # Añadir tabla al layout
        table_layout.addWidget(table)
        
        if parent_layout is not None:
            parent_layout.addWidget(table_widget)
        
        return table_widget
    
    def mostrar_resultados_en_interfaz(self, texto):
        # Guardamos el texto original para compatibilidad con código existente
        self.resultados_text_edit.clear()
        self.resultados_text_edit.setPlainText(texto)
        
        # Limpiamos el contenedor de resultados para la nueva visualización
        for i in reversed(range(self.resultados_layout.count())): 
            widget = self.resultados_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        
        self.secciones_resultados = {}
        
        # Parsear texto para obtener los datos estructurados
        lineas = texto.split('\n')
        
        # Creamos la sección de Resumen Ejecutivo
        if "Resumen Ejecutivo" in texto:
            seccion_resumen = self.crear_seccion_colapsable("Resumen Ejecutivo de Resultados")
            layout_resumen = seccion_resumen["contenido_layout"]
            self.secciones_resultados["resumen_ejecutivo"] = seccion_resumen
            
            # Extraer datos del resumen ejecutivo
            en_resumen = False
            for linea in lineas:
                if "Resumen Ejecutivo" in linea:
                    en_resumen = True
                    continue
                elif en_resumen and linea.strip() == "":
                    continue
                elif en_resumen and "Percentiles" in linea:
                    en_resumen = False
                    continue
                
                if en_resumen and ':' in linea:
                    partes = linea.split(':', 1)
                    etiqueta = partes[0].strip()
                    valor = partes[1].strip()
                    
                    # Determinar si el valor debe destacarse
                    es_destacado = any(term in etiqueta for term in ["VaR", "OpVaR", "Media"])
                    
                    self.crear_display_valor(etiqueta, valor, es_destacado, layout_resumen)
        
        # Creamos la sección de Percentiles Agregados
        if "Percentiles de Pérdida Agregada" in texto:
            seccion_percentiles = self.crear_seccion_colapsable("Percentiles de Pérdida Agregada")
            layout_percentiles = seccion_percentiles["contenido_layout"]
            self.secciones_resultados["percentiles_agregados"] = seccion_percentiles
            
            # Extraer datos de percentiles agregados
            # Intentamos reconstruir el DataFrame de percentiles
            percentiles_data = []
            in_percentiles_table = False
            header_row = None
            
            for i, linea in enumerate(lineas):
                if "Percentiles de Pérdida Agregada" in linea:
                    in_percentiles_table = True
                    continue
                
                if in_percentiles_table:
                    if "┌" in linea:
                        continue
                    elif "│" in linea:
                        # Extraer datos de la fila de la tabla
                        cells = [cell.strip() for cell in linea.split("│") if cell.strip()]
                        if len(cells) >= 2:
                            if header_row is None and "Percentil" in linea:
                                header_row = cells
                            elif header_row is not None:
                                percentiles_data.append(cells)
                    elif linea.strip() == "" and in_percentiles_table and len(percentiles_data) > 0:
                        # Fin de la tabla
                        in_percentiles_table = False
                        break
            
            if header_row and percentiles_data:
                # Crear un DataFrame a partir de los datos extraídos
                df_percentiles = pd.DataFrame(percentiles_data, columns=header_row)
                # Crear y agregar la tabla al layout
                self.crear_tabla_datos(df_percentiles, None, layout_percentiles)
        
        # Procesamos las secciones de eventos individuales
        evento_actual = None
        seccion_evento = None
        layout_evento = None
        in_percentiles_evento = False
        percentiles_evento_data = []
        percentiles_header = None
        
        for linea in lineas:
            # Inicio de una sección de evento
            if "Estadísticas para el Evento de Riesgo:" in linea:
                # Si estábamos procesando un evento anterior, añadimos sus percentiles
                if in_percentiles_evento and percentiles_evento_data and percentiles_header and layout_evento:
                    df_percentiles_evento = pd.DataFrame(percentiles_evento_data, columns=percentiles_header)
                    self.crear_tabla_datos(df_percentiles_evento, "Percentiles de Pérdida", layout_evento)
                
                # Iniciamos el nuevo evento
                nombre_evento = linea.split(":", 1)[1].strip()
                seccion_evento = self.crear_seccion_colapsable(f"Evento: {nombre_evento}")
                layout_evento = seccion_evento["contenido_layout"]
                self.secciones_resultados[f"evento_{nombre_evento}"] = seccion_evento
                evento_actual = nombre_evento
                in_percentiles_evento = False
                percentiles_evento_data = []
                percentiles_header = None
            
            # Procesamos líneas con pares etiqueta-valor dentro de un evento
            elif evento_actual and ":" in linea and "Percentiles de Pérdida:" not in linea and not in_percentiles_evento:
                if "┌" not in linea and "│" not in linea and "┐" not in linea:
                    partes = linea.split(':', 1)
                    if len(partes) == 2:
                        etiqueta = partes[0].strip()
                        valor = partes[1].strip()
                        es_destacado = "Media" in etiqueta
                        self.crear_display_valor(etiqueta, valor, es_destacado, layout_evento)
            
            # Detectamos la sección de percentiles dentro de un evento
            elif evento_actual and "Percentiles de Pérdida:" in linea:
                in_percentiles_evento = True
            
            # Procesamos las filas de la tabla de percentiles del evento
            elif in_percentiles_evento and evento_actual:
                if "┌" in linea or "└" in linea:
                    continue
                elif "│" in linea:
                    # Extraer datos de la fila
                    cells = [cell.strip() for cell in linea.split("│") if cell.strip()]
                    if len(cells) >= 2:
                        if percentiles_header is None and "Percentil" in linea:
                            percentiles_header = cells
                        elif percentiles_header is not None:
                            percentiles_evento_data.append(cells)
                elif linea.strip() == "" and len(percentiles_evento_data) > 0:
                    # Fin de la tabla de percentiles del evento, creamos la tabla
                    df_percentiles_evento = pd.DataFrame(percentiles_evento_data, columns=percentiles_header)
                    self.crear_tabla_datos(df_percentiles_evento, "Percentiles de Pérdida", layout_evento)
                    in_percentiles_evento = False
        
        # Si terminamos con un evento en proceso con percentiles pendientes
        if in_percentiles_evento and percentiles_evento_data and percentiles_header and layout_evento:
            df_percentiles_evento = pd.DataFrame(percentiles_evento_data, columns=percentiles_header)
            self.crear_tabla_datos(df_percentiles_evento, "Percentiles de Pérdida", layout_evento)

    def solicitar_ruta_guardado_pdf(self):
        options = QtWidgets.QFileDialog.Options()
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Guardar Informe PDF", "",
                                                            "PDF Files (*.pdf);;All Files (*)", options=options)
        return filepath

    def ejecutar_simulacion(self):
        try:
            # Validar número de simulaciones (función centralizada)
            num_simulaciones = validar_num_simulaciones(self.num_simulaciones_var.text())
            
            if not self.eventos_riesgo:
                raise ValueError("Debe agregar al menos un evento de riesgo.")

            # Siempre usar los eventos de la pestaña Simulación
            # (la pestaña Escenarios tiene su propio flujo via ejecutar_simulacion_escenario)
            eventos = self.eventos_riesgo

            # FILTRAR SOLO EVENTOS ACTIVOS
            # IMPORTANTE: Hacer copia profunda para no modificar los datos originales
            eventos_activos_originales = [e for e in eventos if e.get('activo', True)]
            
            # Validar que haya al menos un evento activo
            if not eventos_activos_originales:
                raise ValueError("Debe activar al menos un evento de riesgo para ejecutar la simulación.")
            
            # Hacer copia profunda para evitar modificar el modelo de datos original
            eventos_activos = copy.deepcopy(eventos_activos_originales)
            
            # Crear un set con los IDs de eventos activos para filtrar vínculos
            ids_eventos_activos = {e['id'] for e in eventos_activos}
            
            # Filtrar vínculos: eliminar vínculos que apuntan a eventos inactivos
            for evento in eventos_activos:
                if 'vinculos' in evento and evento['vinculos']:
                    # Guardar cantidad original para el reporte
                    vinculos_originales = len(evento['vinculos'])
                    
                    # Mantener solo vínculos cuyos padres están activos
                    vinculos_validos = [
                        v for v in evento['vinculos'] 
                        if v.get('id_padre') in ids_eventos_activos
                    ]
                    evento['vinculos'] = vinculos_validos
                    
                    # Informar si se filtraron vínculos
                    vinculos_filtrados = vinculos_originales - len(vinculos_validos)
                    if vinculos_filtrados > 0:
                        print(f"[DEBUG] Evento '{evento['nombre']}': se ignoraron {vinculos_filtrados} vínculo(s) a eventos inactivos")
            
            # Mostrar información en status bar
            total_eventos = len(eventos)
            activos_count = len(eventos_activos)
            if activos_count < total_eventos:
                self.statusBar().showMessage(
                    f"Simulando con {activos_count} de {total_eventos} eventos activos", 
                    3000
                )

            # Por defecto, no generamos reporte automáticamente
            self.generar_reporte = False
            self.pdf_filename = 'reporte_simulacion.pdf'  # Valor por defecto, no se usará
            

            # DEBUG: Confirmar que esta es la versión correcta
            print(f"\n[DEBUG EJECUTAR V2] ========================================")
            print(f"[DEBUG EJECUTAR V2] Usando ejecutar_simulacion línea 8296 (versión que reconstruye eventos)")
            print(f"[DEBUG EJECUTAR V2] Número de eventos originales: {len(eventos)}")
            print(f"[DEBUG EJECUTAR V2] Número de eventos activos: {len(eventos_activos)}")
            
            # Preparar la lista de eventos para la simulación utilizando los eventos activos
            eventos_simulacion = []
            for evento_data in eventos_activos:
                evento = {
                    'id': evento_data['id'],
                    'nombre': evento_data['nombre'],
                    'dist_severidad': evento_data['dist_severidad'],
                    'dist_frecuencia': evento_data['dist_frecuencia']
                }

                # Incluir vínculos si existen
                if 'vinculos' in evento_data:
                    evento['vinculos'] = evento_data['vinculos']

                # Para compatibilidad con formato antiguo
                elif 'eventos_padres' in evento_data:
                    evento['eventos_padres'] = evento_data['eventos_padres']
                    evento['tipo_dependencia'] = evento_data.get('tipo_dependencia', 'AND')
                
                # IMPORTANTE: Incluir factores de ajuste si existen
                if 'factores_ajuste' in evento_data:
                    evento['factores_ajuste'] = copy.deepcopy(evento_data['factores_ajuste'])
                    print(f"[DEBUG EJECUTAR V2]   Evento '{evento_data['nombre']}': copiando {len(evento_data['factores_ajuste'])} factores")
                    for f in evento_data['factores_ajuste']:
                        print(f"[DEBUG EJECUTAR V2]     - {f.get('nombre')}: tipo={f.get('tipo_modelo')}")
                else:
                    print(f"[DEBUG EJECUTAR V2]   Evento '{evento_data['nombre']}': SIN factores_ajuste")
                
                # Incluir todos los parámetros de frecuencia necesarios para el ajuste
                if 'freq_opcion' in evento_data:
                    evento['freq_opcion'] = evento_data['freq_opcion']
                if 'tasa' in evento_data:
                    evento['tasa'] = evento_data['tasa']
                if 'prob_exito' in evento_data:
                    evento['prob_exito'] = evento_data['prob_exito']
                if 'num_eventos' in evento_data:
                    evento['num_eventos'] = evento_data['num_eventos']
                if 'pg_mas_probable' in evento_data:
                    evento['pg_mas_probable'] = evento_data['pg_mas_probable']
                if 'pg_minimo' in evento_data:
                    evento['pg_minimo'] = evento_data['pg_minimo']
                if 'pg_maximo' in evento_data:
                    evento['pg_maximo'] = evento_data['pg_maximo']
                if 'pg_confianza' in evento_data:
                    evento['pg_confianza'] = evento_data['pg_confianza']
                if 'beta_mas_probable' in evento_data:
                    evento['beta_mas_probable'] = evento_data['beta_mas_probable']
                if 'beta_minimo' in evento_data:
                    evento['beta_minimo'] = evento_data['beta_minimo']
                if 'beta_maximo' in evento_data:
                    evento['beta_maximo'] = evento_data['beta_maximo']
                if 'beta_confianza' in evento_data:
                    evento['beta_confianza'] = evento_data['beta_confianza']

                # Copiar configuración de escalamiento severidad-frecuencia
                for key in evento_data:
                    if key.startswith('sev_freq_'):
                        evento[key] = evento_data[key]

                # Copiar límites superiores opcionales
                if 'sev_limite_superior' in evento_data:
                    evento['sev_limite_superior'] = evento_data['sev_limite_superior']
                if 'freq_limite_superior' in evento_data:
                    evento['freq_limite_superior'] = evento_data['freq_limite_superior']

                eventos_simulacion.append(evento)

            # Desactivar la interfaz mientras se ejecuta la simulación
            self.set_interfaz_activa(False)
            self.progress_bar.setValue(0)
            self.central_widget.setCurrentWidget(self.results_tab)

            # Crear y configurar el hilo de simulación usando los eventos preparados
            self.simulation_thread = SimulacionThread(
                eventos_simulacion,
                num_simulaciones,
                self.generar_reporte,
                self.pdf_filename
            )
            self.simulation_thread.progreso_actualizado.connect(self.actualizar_progreso)
            self.simulation_thread.simulacion_completada.connect(self.simulacion_completada)
            self.simulation_thread.error_ocurrido.connect(self.simulacion_error)
            self.simulation_thread.start()

        except ValueError as ve:
            QtWidgets.QMessageBox.critical(self, "Error", str(ve))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Error al ejecutar la simulación: {e}")

    def actualizar_progreso(self, valor):
        """Actualización de progreso de simulación (hilo worker).
        Se escala a 0-70 para reservar 70-100 al post-procesamiento.
        También se asegura monotonía para evitar retrocesos visuales.
        """
        try:
            esc = int(max(0, min(100, valor)) * 0.7)
            actual = self.progress_bar.value()
            if esc < actual:
                esc = actual
            self.progress_bar.setValue(esc)
        except Exception:
            self.progress_bar.setValue(valor)

    def actualizar_progreso_post(self, valor, texto=None):
        """Actualiza la barra de progreso durante el post-procesamiento en el hilo de UI
        sin cambiar la lógica existente. También bombea el event loop para refrescar la UI.
        """
        try:
            if texto is not None:
                self.progress_bar.setFormat(f"{texto} (%p%)")
            # Asegurar progreso monótono (no decrecer)
            nuevo_valor = int(valor)
            valor_actual = self.progress_bar.value()
            if nuevo_valor < valor_actual:
                nuevo_valor = valor_actual
            self.progress_bar.setValue(nuevo_valor)
            QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, 50)
        except Exception:
            # Evitar que errores menores de UI detengan el flujo
            pass

    def simulacion_completada(self, perdidas_totales, frecuencias_totales, perdidas_por_evento, frecuencias_por_evento, eventos):
        # Reactivar la interfaz
        self.set_interfaz_activa(True)
        # Continuar la barra para post-procesamiento a partir de 70-100
        self.actualizar_progreso_post(70, "Procesando resultados")

        # Guardar los resultados para uso posterior (exportación a PDF)
        self.resultados_simulacion = {
            'perdidas_totales': perdidas_totales,
            'frecuencias_totales': frecuencias_totales,
            'perdidas_por_evento': perdidas_por_evento,
            'frecuencias_por_evento': frecuencias_por_evento,
            'eventos_riesgo': eventos
        }

        # Inicializar controles de Excedencia (Paso 1: Agregada)
        try:
            if hasattr(self, 'excedencia_controls_container') and self.excedencia_controls_container is not None:
                self.excedencia_controls_container.setEnabled(True)
                # Sugerir P90 como valor inicial de T
                p90 = float(np.percentile(perdidas_totales, 90)) if perdidas_totales is not None and len(perdidas_totales) > 0 else 0.0
                if hasattr(self, 'tolerancia_ex_spin'):
                    # Ajustar máximos de forma segura
                    max_actual = self.tolerancia_ex_spin.maximum()
                    nuevo_max = max(max_actual, p90 * 5 if p90 > 0 else 1_000_000)
                    self.tolerancia_ex_spin.blockSignals(True)
                    self.tolerancia_ex_spin.setMaximum(nuevo_max)
                    self.tolerancia_ex_spin.setValue(round(p90))
                    self.tolerancia_ex_spin.blockSignals(False)
                # Calcular la probabilidad inicial
                self.actualizar_probabilidad_excedencia()
        except Exception:
            pass


        # Obtener texto de resultados
        self.actualizar_progreso_post(72, "Calculando estadísticas agregadas")
        resultados_texto = self.generar_resultados(
            perdidas_totales,
            frecuencias_totales,
            perdidas_por_evento,
            frecuencias_por_evento,
            eventos,
            generar_reporte=self.generar_reporte,
            pdf_filename=self.pdf_filename
        )

        # Mostrar resultados en la interfaz
        self.mostrar_resultados_en_interfaz(resultados_texto)

        # Graficar resultados en la pestaña de Resultados
        self.actualizar_progreso_post(90, "Generando gráficos")
        self.graficar_resultados(perdidas_totales, frecuencias_totales, perdidas_por_evento, frecuencias_por_evento, eventos)

        # Asegurar que la sección de Excedencia exista y quede habilitada
        try:
            # Si durante la generación de resultados se limpiaron las secciones, recrearla
            if hasattr(self, 'agregar_seccion_excedencia_si_falta'):
                self.agregar_seccion_excedencia_si_falta()
            # Reposicionar el holder justo debajo del título del resumen
            try:
                if hasattr(self, 'excedencia_holder') and self.excedencia_holder is not None:
                    parent_widget = self.excedencia_holder.parentWidget()
                    if parent_widget is not None and hasattr(parent_widget, 'layout'):
                        pl = parent_widget.layout()
                        if pl is not None:
                            pl.removeWidget(self.excedencia_holder)
                            pl.insertWidget(1, self.excedencia_holder)
            except Exception:
                pass
            if hasattr(self, 'excedencia_controls_container') and self.excedencia_controls_container is not None:
                self.excedencia_controls_container.setEnabled(True)
            # Sugerir P90 como valor inicial de T y calcular
            p90 = float(np.percentile(perdidas_totales, 90)) if perdidas_totales is not None and len(perdidas_totales) > 0 else 0.0
            if hasattr(self, 'tolerancia_ex_spin'):
                max_actual = self.tolerancia_ex_spin.maximum()
                nuevo_max = max(max_actual, p90 * 5 if p90 > 0 else 1_000_000)
                self.tolerancia_ex_spin.blockSignals(True)
                self.tolerancia_ex_spin.setMaximum(nuevo_max)
                self.tolerancia_ex_spin.setValue(round(p90))
                self.tolerancia_ex_spin.blockSignals(False)
            if hasattr(self, 'actualizar_probabilidad_excedencia'):
                self.actualizar_probabilidad_excedencia()
        except Exception:
            pass

        # Cambiar a la pestaña de Resultados
        self.central_widget.setCurrentWidget(self.results_tab)
        # Asegurar final al 100% y restaurar formato por defecto
        try:
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("%p%")
            
            # Detener animación
            if hasattr(self, 'progress_animation_timer'):
                self.progress_animation_timer.stop()
        except Exception:
            pass
        
        # Refrescar layout si la ventana está maximizada (fix bug de alineación)
        self._refrescar_ventana_maximizada()

    def simulacion_error(self, mensaje_error):
        # Reactivar la interfaz
        self.set_interfaz_activa(True)
        
        # Detener animación de la barra de progreso
        if hasattr(self, 'progress_animation_timer'):
            self.progress_animation_timer.stop()
        
        # Resetear barra de progreso
        self.progress_bar.setValue(0)
        
        QtWidgets.QMessageBox.critical(self, "Error", f"Error al ejecutar la simulación: {mensaje_error}")

    def set_interfaz_activa(self, estado):
        self.num_simulaciones_var.setEnabled(estado)
        self.eventos_table.setEnabled(estado)
        self.central_widget.setTabEnabled(self.central_widget.indexOf(self.config_tab), estado)

    def generar_resultados(self, perdidas_totales, frecuencias_totales, perdidas_por_evento, frecuencias_por_evento,
                           eventos_riesgo, generar_reporte=False, pdf_filename='reporte_simulacion.pdf'):
        """Calcula estadísticas, muestra resultados y genera gráficos."""
        texto_resultados = ""

        # Calculamos estadísticas para pérdidas agregadas
        percentiles_valores = [10, 20, 30, 40, 50, 60, 70, 75, 80, 85, 90, 92, 95, 99, 99.99]
        percentiles = np.percentile(perdidas_totales, percentiles_valores)
        media = np.mean(perdidas_totales)
        desviacion_estandar = np.std(perdidas_totales)
        # Progreso post-procesamiento: estadísticas agregadas completadas
        self.actualizar_progreso_post(15, "Estadísticas agregadas listas")

        # Estadísticas de frecuencias agregadas
        min_freq_total = int(frecuencias_totales.min())
        max_freq_total = int(frecuencias_totales.max())
        # Modo optimizado para enteros no negativos usando np.bincount (fallback seguro)
        if len(frecuencias_totales) > 0:
            try:
                if max_freq_total <= 100000:
                    mode_freq_total = int(np.argmax(np.bincount(frecuencias_totales.astype(np.int32))))
                else:
                    mode_freq_total = int(stats.mode(frecuencias_totales, keepdims=True).mode[0])
            except Exception:
                mode_freq_total = int(stats.mode(frecuencias_totales, keepdims=True).mode[0])
        else:
            mode_freq_total = 0

        # Creamos DataFrame de percentiles para pérdidas agregadas
        percentiles_df = pd.DataFrame({
            'Percentil (%)': percentiles_valores,
            'Valor de Pérdida': percentiles
        })

        # Formateamos los valores de pérdida sin decimales
        percentiles_df['Valor de Pérdida'] = percentiles_df['Valor de Pérdida'].round(0).astype(int)
        percentiles_df['Valor de Pérdida'] = percentiles_df['Valor de Pérdida'].apply(currency_format)

        # Formateamos los percentiles (%), dejando decimales donde corresponda
        percentiles_df['Percentil (%)'] = percentiles_df['Percentil (%)'].apply(
            lambda x: ('{:.2f}'.format(x).replace('.', ',')) if x != int(x) else ('{:.0f}'.format(x)))

        # Obtener resumen ejecutivo
        var_90 = np.percentile(perdidas_totales, 90)
        opvar_99 = np.percentile(perdidas_totales, 99)
        opvar = perdidas_totales[perdidas_totales >= opvar_99].mean()
        texto_resultados += obtener_resumen_ejecutivo_texto(media, desviacion_estandar, var_90, opvar_99, opvar,
                                                            min_freq_total, mode_freq_total, max_freq_total)

        # Obtener tabla de percentiles
        texto_resultados += obtener_tabla_percentiles_texto(percentiles_df, "Percentiles de Pérdida Agregada")

        # Creamos una lista para almacenar las estadísticas de cada evento para la matriz de riesgos
        estadisticas_eventos = []

        # Agregamos cálculo y muestra de estadísticas para cada evento de riesgo
        for idx, (perdidas_evento, frecuencias_evento) in enumerate(zip(perdidas_por_evento, frecuencias_por_evento)):
            nombre_evento = eventos_riesgo[idx]['nombre']
            media_evento = np.mean(perdidas_evento)
            desviacion_evento = np.std(perdidas_evento)
            percentiles_evento = np.percentile(perdidas_evento, percentiles_valores)
            min_freq = int(frecuencias_evento.min())
            max_freq = int(frecuencias_evento.max())
            # Modo por evento optimizado con guardas de memoria
            if len(frecuencias_evento) > 0:
                try:
                    if max_freq <= 100000:
                        mode_freq = int(np.argmax(np.bincount(frecuencias_evento.astype(np.int32))))
                    else:
                        mode_freq = int(stats.mode(frecuencias_evento, keepdims=True).mode[0])
                except Exception:
                    mode_freq = int(stats.mode(frecuencias_evento, keepdims=True).mode[0])
            else:
                mode_freq = 0
            percentiles_evento_df = pd.DataFrame({
                'Percentil (%)': percentiles_valores,
                'Valor de Pérdida': percentiles_evento
            })
            percentiles_evento_df['Valor de Pérdida'] = percentiles_evento_df['Valor de Pérdida'].round(0).astype(int)
            percentiles_evento_df['Valor de Pérdida'] = percentiles_evento_df['Valor de Pérdida'].apply(currency_format)
            percentiles_evento_df['Percentil (%)'] = percentiles_evento_df['Percentil (%)'].apply(
                lambda x: ('{:.2f}'.format(x).replace('.', ',')) if x != int(x) else ('{:.0f}'.format(x)))

            # Obtenemos el percentil 90 del impacto para el evento
            p90_evento = np.percentile(perdidas_evento, 90)

            # Guardamos las estadísticas en la lista
            estadisticas_eventos.append({
                'nombre': nombre_evento,
                'impacto_medio': media_evento,
                'impacto_p90': p90_evento,
                'frecuencia_modo': mode_freq,
                'frecuencia_maxima': max_freq
            })

            texto_resultados += f"\nEstadísticas para el Evento de Riesgo: {nombre_evento}\n"
            texto_resultados += f"Media de Impacto: {currency_format(round(media_evento))}\n"
            texto_resultados += f"Desviación Estándar: {currency_format(round(desviacion_evento))}\n"
            texto_resultados += f"Número mínimo de eventos materializados: {min_freq}\n"
            texto_resultados += f"Número más probable de eventos materializados: {mode_freq}\n"
            texto_resultados += f"Número máximo de eventos materializados: {max_freq}\n"
            texto_resultados += "Percentiles de Pérdida:\n"
            texto_resultados += tabulate(percentiles_evento_df, headers='keys', tablefmt='fancy_grid', showindex=False)
            texto_resultados += "\n"
            # Progreso por evento (72% -> 88%)
            try:
                total_evt = max(1, len(eventos_riesgo))
                base_start, base_end = 72, 88
                pct = base_start + int((base_end - base_start) * (idx + 1) / total_evt)
                self.actualizar_progreso_post(pct, f"Procesando eventos ({idx + 1}/{total_evt})")
            except Exception:
                pass

        if generar_reporte:
            try:
                # Crear el PDF usando ReportLab
                c = canvas.Canvas(pdf_filename, pagesize=A4)
                ancho_pagina, alto_pagina = A4
                # Establecer un margen
                margen = 2 * cm
                ancho_texto = ancho_pagina - 2 * margen
                alto_texto = alto_pagina - 2 * margen
                # Crear un objeto de texto
                texto_page = c.beginText(margen, alto_pagina - margen)
                texto_page.setFont("Helvetica", 10)

                # Dividir el texto en líneas y agregarlo al PDF
                lineas = texto_resultados.split('\n')
                for linea in lineas:
                    texto_page.textLine(linea)
                    if texto_page.getY() < margen:
                        # Añadir la página de texto y comenzar una nueva
                        c.drawText(texto_page)
                        c.showPage()
                        texto_page = c.beginText(margen, alto_pagina - margen)
                        texto_page.setFont("Helvetica", 10)
                c.drawText(texto_page)
                c.showPage()

                # Generar los gráficos y agregarlos al PDF
                figuras = self.generar_figuras(perdidas_totales, frecuencias_totales, perdidas_por_evento,
                                               frecuencias_por_evento, eventos_riesgo)

                for idx, figura in enumerate(figuras):
                    # Guardar la figura en memoria en lugar de en un archivo
                    img_data = io.BytesIO()
                    figura.savefig(img_data, format='png', dpi=300, bbox_inches='tight')
                    img_data.seek(0)  # Restablece el cursor al inicio del archivo en memoria

                    # Obtener el tamaño de la imagen
                    img_width, img_height = figura.get_size_inches()
                    img_width *= 300  # Convertir tamaño a píxeles (dpi)
                    img_height *= 300

                    # Calcular el escalado para ajustar la imagen al tamaño de la página
                    ratio = min((ancho_texto) / img_width, (alto_texto) / img_height)
                    scaled_width = img_width * ratio
                    scaled_height = img_height * ratio

                    c.drawImage(
                        ImageReader(img_data),
                        margen,
                        (alto_pagina - margen - scaled_height),
                        width=scaled_width,
                        height=scaled_height,
                        preserveAspectRatio=True,
                        anchor='c'
                    )
                    c.showPage()  # Añadir una nueva página para la siguiente imagen

                c.save()

                self.statusBar().showMessage(f"El reporte ha sido guardado exitosamente en {pdf_filename}", 5000)
            except Exception as e:
                error_message = traceback.format_exc()
                QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo generar el reporte PDF:\n{error_message}")

        return texto_resultados

    def setup_scenarios_tab(self):
        # Fondo sutil para resaltar las cards
        self.scenarios_tab.setStyleSheet("""
            QWidget {
                background-color: #F5F7FA;
            }
        """)
        
        # Usamos un QGridLayout como layout principal
        layout = QtWidgets.QGridLayout(self.scenarios_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        current_row = 0
        
        # Panel superior - contiene el botón agregar y escenario seleccionado
        top_panel = QtWidgets.QWidget()
        top_layout = QtWidgets.QGridLayout(top_panel)
        top_layout.setContentsMargins(8, 8, 8, 8)  # Mismo margen que Simulación
        
        # Número de simulaciones (arriba, igual que Simulación)
        simulaciones_label = QtWidgets.QLabel("Número de simulaciones:")
        simulaciones_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        simulaciones_label.setToolTip("Define cuántas iteraciones realizará la simulación")
        simulaciones_label.setStyleSheet(f"font-size: {UI_FONT_BASE}pt;")
        top_layout.addWidget(simulaciones_label, 0, 0)
        
        self.num_simulaciones_var_escenarios = QtWidgets.QLineEdit("10000")
        self.num_simulaciones_var_escenarios.setFixedWidth(100)
        self.num_simulaciones_var_escenarios.setToolTip("Recomendado: 10000 o más para mayor precisión")
        top_layout.addWidget(self.num_simulaciones_var_escenarios, 0, 1)
        
        # Escenario seleccionado - al lado derecho
        escenario_seleccionado_panel = QtWidgets.QWidget()
        escenario_seleccionado_layout = QtWidgets.QHBoxLayout(escenario_seleccionado_panel)
        escenario_seleccionado_layout.setContentsMargins(20, 0, 0, 0)
        
        escenario_seleccionado_label = QtWidgets.QLabel("Escenario Seleccionado:")
        escenario_seleccionado_label.setStyleSheet("font-weight: bold;")
        escenario_seleccionado_label.setToolTip("El escenario actual para la simulación")
        escenario_seleccionado_layout.addWidget(escenario_seleccionado_label)
        
        self.selected_scenario_label = QtWidgets.QLabel("Ninguno")
        self.selected_scenario_label.setStyleSheet("color: #007ACC; font-weight: normal;")
        self.selected_scenario_label.setToolTip("Doble clic en un escenario para seleccionarlo")
        escenario_seleccionado_layout.addWidget(self.selected_scenario_label)
        escenario_seleccionado_layout.addStretch()
        
        top_layout.addWidget(escenario_seleccionado_panel, 0, 2, 1, 2)
        
        # Añadir panel superior al layout principal
        layout.addWidget(top_panel, current_row, 0, 1, 4)
        current_row += 1
        
        # Botón para agregar escenario - ocupa las 4 columnas (igual que Simulación)
        agregar_escenario_button = QtWidgets.QPushButton(" Agregar Escenario")
        agregar_escenario_button.setIcon(self.iconos["add"])  # Usar icono SVG moderno
        agregar_escenario_button.clicked.connect(self.agregar_escenario_popup)
        agregar_escenario_button.setToolTip("Crear un nuevo escenario de simulación")
        self.aplicar_estilo_boton_primario(agregar_escenario_button)  # Estilo Mercado Libre
        # Sobrescribir altura después del estilo (el padding del estilo causa altura extra)
        agregar_escenario_button.setStyleSheet(agregar_escenario_button.styleSheet() + "QPushButton { max-height: 40px; padding: 6px 24px; }")
        agregar_escenario_button.setFixedHeight(40)  # Misma altura que Agregar Evento (40px)
        self.agregar_animacion_hover_boton(agregar_escenario_button)  # Animación hover
        layout.addWidget(agregar_escenario_button, current_row, 0, 1, 4)
        layout.setRowStretch(current_row, 0)  # Sin stretch para este botón
        current_row += 1
        
        # Panel central - tabla de escenarios (Card moderna)
        table_panel = QtWidgets.QGroupBox("📋 Escenarios Disponibles")
        self.aplicar_estilo_card_moderno(table_panel)
        self.agregar_animacion_card_hover(table_panel)  # Animación hover en card
        table_layout = QtWidgets.QVBoxLayout(table_panel)
        
        # Contenedor con stack para tabla y empty state
        self.scenarios_stack = QtWidgets.QStackedWidget()
        
        self.scenarios_table = QtWidgets.QTableWidget(0, 2)
        self.scenarios_table.setHorizontalHeaderLabels(["Nombre del Escenario", "Descripción"])
        self.scenarios_table.horizontalHeader().setStretchLastSection(True)
        self.scenarios_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.scenarios_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.scenarios_table.setToolTip("Lista de escenarios disponibles. Doble clic para seleccionar.")
        self.scenarios_table.setAlternatingRowColors(False)  # Desactivar alternancia (se usará hover)
        self.scenarios_table.verticalHeader().setVisible(False)  # Ocultar cabecera vertical
        self.scenarios_table.setMinimumHeight(200)  # Altura mínima para mostrar varios elementos
        self.scenarios_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)  # Deshabilitar edición directa
        self.scenarios_table.setMouseTracking(True)  # Habilitar tracking para hover
        self.aplicar_estilo_tabla_moderno(self.scenarios_table)  # Aplicar estilo Mercado Libre
        
        # Empty state para escenarios
        self.scenarios_empty_state = self.crear_empty_state(
            self.scenarios_stack,
            "No hay escenarios configurados",
            "Crea escenarios para agrupar y comparar diferentes conjuntos de eventos de riesgo",
            "➕ Crear Primer Escenario",
            self.agregar_escenario_popup,
            icono="🎯"
        )
        
        # Añadir ambos al stack
        self.scenarios_stack.addWidget(self.scenarios_empty_state)  # índice 0
        self.scenarios_stack.addWidget(self.scenarios_table)  # índice 1
        
        # Mostrar empty state inicialmente si no hay escenarios
        if len(self.scenarios) == 0:
            self.scenarios_stack.setCurrentIndex(0)
        else:
            self.scenarios_stack.setCurrentIndex(1)
        
        table_layout.addWidget(self.scenarios_stack)
        
        # Conectar la señal de doble clic para seleccionar escenario
        self.scenarios_table.cellDoubleClicked.connect(self.select_scenario)
        
        # Conectar señal de selección para habilitar/deshabilitar botones
        self.scenarios_table.itemSelectionChanged.connect(self.actualizar_estado_botones_escenarios)
        
        # Añadir panel de tabla al layout principal
        layout.addWidget(table_panel, current_row, 0, 1, 4)
        layout.setRowStretch(current_row, 10)  # Dar mayor peso a la fila de la tabla
        current_row += 1
        
        # Panel inferior - botones de acción (mismo layout 2x2 que Simulación)
        bottom_panel = QtWidgets.QWidget()
        bottom_layout = QtWidgets.QGridLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 2, 0, 2)  # Mismo margen que Simulación
        
        # Fila 1 - Botones de acción (2 columnas como Simulación)
        self.editar_escenario_button = QtWidgets.QPushButton("Editar Escenario")
        self.editar_escenario_button.setIcon(self.iconos_oscuros.get("edit", self.iconos["edit"]))  # Usar icono oscuro
        self.editar_escenario_button.clicked.connect(self.editar_escenario_popup)
        self.editar_escenario_button.setFixedHeight(36)  # Altura FIJA para consistencia con Simulación
        self.editar_escenario_button.setToolTip("Modificar el escenario seleccionado")
        self.aplicar_estilo_boton_secundario(self.editar_escenario_button)  # Estilo Mercado Libre
        self.agregar_animacion_hover_boton(self.editar_escenario_button)  # Animación hover
        bottom_layout.addWidget(self.editar_escenario_button, 0, 0)
        
        self.duplicar_escenario_button = QtWidgets.QPushButton("Duplicar Escenario(s)")
        self.duplicar_escenario_button.setIcon(self.iconos_oscuros.get("copy", self.iconos["copy"]))  # Usar icono oscuro
        self.duplicar_escenario_button.clicked.connect(self.duplicar_escenario)
        self.duplicar_escenario_button.setFixedHeight(36)
        self.duplicar_escenario_button.setToolTip("Crear una copia del escenario seleccionado")
        self.aplicar_estilo_boton_secundario(self.duplicar_escenario_button)
        self.agregar_animacion_hover_boton(self.duplicar_escenario_button)
        bottom_layout.addWidget(self.duplicar_escenario_button, 0, 1)
        
        # Fila 2 - Eliminar y Ejecutar (2 columnas como Simulación)
        self.eliminar_escenario_button = QtWidgets.QPushButton("Eliminar Escenario(s)")
        self.eliminar_escenario_button.setIcon(self.iconos_oscuros.get("delete", self.iconos["delete"]))  # Usar icono oscuro
        self.eliminar_escenario_button.clicked.connect(self.eliminar_escenario)
        self.eliminar_escenario_button.setFixedHeight(36)  # Altura FIJA para consistencia con Simulación
        self.eliminar_escenario_button.setToolTip("Eliminar el escenario seleccionado")
        self.aplicar_estilo_boton_secundario(self.eliminar_escenario_button)  # Estilo secundario (igual que Editar/Duplicar)
        self.agregar_animacion_hover_boton(self.eliminar_escenario_button)  # Animación hover
        bottom_layout.addWidget(self.eliminar_escenario_button, 1, 0)
        
        simular_button = QtWidgets.QPushButton("Ejecutar Simulación")
        simular_button.setIcon(self.iconos["play"])  # Usar icono SVG moderno
        simular_button.clicked.connect(self.ejecutar_simulacion_escenario)
        simular_button.setFixedHeight(36)  # Altura FIJA para consistencia con Simulación
        simular_button.setToolTip("Ejecutar la simulación con el escenario seleccionado")
        self.aplicar_estilo_boton_exitoso(simular_button)  # Estilo Mercado Libre
        self.agregar_animacion_hover_boton(simular_button)  # Animación hover
        bottom_layout.addWidget(simular_button, 1, 1)
        
        # Añadir panel inferior al layout principal
        layout.addWidget(bottom_panel, current_row, 0, 1, 4)
        layout.setRowStretch(current_row, 0)  # Sin stretch para que no se expandan los botones
        
        # Estado inicial: botones deshabilitados (no hay selección)
        self.actualizar_estado_botones_escenarios()
        
        # La conexión doble clic ya fue configurada en la línea 3658
        # Evitamos la duplicación de la señal que causaba dos confirmaciones

    def ejecutar_simulacion_desde_escenarios(self):
        # Redirigir al método que hace el swap temporal de eventos
        self.ejecutar_simulacion_escenario()
    
    def actualizar_estado_botones_escenarios(self):
        """Actualiza el estado habilitado/deshabilitado de los botones según la selección en la tabla."""
        hay_seleccion = len(self.scenarios_table.selectedItems()) > 0
        
        # Editar solo se habilita con exactamente una fila seleccionada
        filas_seleccionadas = set(item.row() for item in self.scenarios_table.selectedItems())
        una_seleccion = len(filas_seleccionadas) == 1
        
        self.editar_escenario_button.setEnabled(una_seleccion)
        self.duplicar_escenario_button.setEnabled(una_seleccion)
        self.eliminar_escenario_button.setEnabled(hay_seleccion)

    def actualizar_num_simulaciones_escenarios(self, text):
        if self.num_simulaciones_var_escenarios.text() != text:
            self.num_simulaciones_var_escenarios.setText(text)

    def actualizar_num_simulaciones_simulacion(self, text):
        if self.num_simulaciones_var.text() != text:
            self.num_simulaciones_var.setText(text)

    def agregar_escenario_popup(self):
        """Método para abrir el diálogo de agregar escenario nuevo."""
        # Verificamos si existe el método editar_escenario_popup
        if hasattr(self, 'editar_escenario_popup'):
            self.editar_escenario_popup(new=True)
        else:
            # Si no existe, usamos el método original
            self.editar_scenario_popup(new=True)
        
    def agregar_scenario_popup(self):
        """Método original para agregar escenarios."""
        self.editar_scenario_popup(new=True)

    def editar_escenario_popup(self, new=False, row=None):
        """Alias para mantener consistencia en la nomenclatura española"""
        return self.editar_scenario_popup(new, row)
    
    def editar_scenario_popup(self, new=False, row=None):
        if not new:
            if row is None:
                selected_items = self.scenarios_table.selectedItems()
                if not selected_items:
                    QtWidgets.QMessageBox.warning(self, "Advertencia", "Seleccione un escenario para editar.")
                    return
                row = selected_items[0].row()
            scenario = self.scenarios[row]
        else:
            scenario = None

        # Crear diálogo
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Agregar Escenario" if new else "Editar Escenario")
        dialog.resize(900, 550)  # Tamaño inicial amplio
        dialog.setMaximumHeight(int(QtWidgets.QApplication.primaryScreen().availableGeometry().height() * 0.9))
        
        # Layout principal con scroll
        main_dialog_layout = QtWidgets.QVBoxLayout(dialog)
        main_dialog_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area_scenario = QtWidgets.QScrollArea()
        scroll_area_scenario.setWidgetResizable(True)
        scroll_area_scenario.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area_scenario.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        scroll_content_scenario = QtWidgets.QWidget()
        dialog_layout = QtWidgets.QVBoxLayout(scroll_content_scenario)
        dialog_layout.setContentsMargins(20, 20, 20, 20)
        dialog_layout.setSpacing(12)

        # Nombre del Escenario
        nombre_layout = QtWidgets.QHBoxLayout()
        nombre_label = QtWidgets.QLabel("Nombre:")
        nombre_label.setFixedWidth(80)
        nombre_var = QtWidgets.QLineEdit(scenario.nombre if scenario else "")
        nombre_layout.addWidget(nombre_label)
        nombre_layout.addWidget(nombre_var)
        dialog_layout.addLayout(nombre_layout)

        # Descripción del Escenario
        descripcion_layout = QtWidgets.QHBoxLayout()
        descripcion_label = QtWidgets.QLabel("Descripción:")
        descripcion_label.setFixedWidth(80)
        descripcion_var = QtWidgets.QLineEdit(scenario.descripcion if scenario else "")
        descripcion_layout.addWidget(descripcion_label)
        descripcion_layout.addWidget(descripcion_var)
        dialog_layout.addLayout(descripcion_layout)

        # Label informativo
        info_label = QtWidgets.QLabel("📋 Eventos del escenario (click en ✓/✗ para activar/desactivar):")
        dialog_layout.addWidget(info_label)

        # Tabla para mostrar eventos
        eventos_table = QtWidgets.QTableWidget()
        eventos_table.setColumnCount(3)
        eventos_table.setHorizontalHeaderLabels(["", "Evento de Riesgo", "Fact."])
        eventos_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        eventos_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        eventos_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        eventos_table.setColumnWidth(0, 40)
        eventos_table.setColumnWidth(2, 50)
        eventos_table.setMinimumHeight(280)
        eventos_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        eventos_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        eventos_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        eventos_table.verticalHeader().setVisible(False)

        # Obtener la lista de eventos
        self.eventos_scenario = copy.deepcopy(scenario.eventos_riesgo) if scenario else copy.deepcopy(self.eventos_riesgo)

        # Función para toggle del estado activo al hacer click
        def toggle_evento_activo(row):
            if 0 <= row < len(self.eventos_scenario):
                self.eventos_scenario[row]['activo'] = not self.eventos_scenario[row].get('activo', True)
                actualizar_tabla_eventos_escenario()
                eventos_table.selectRow(row)

        # Función para actualizar la tabla de eventos del escenario
        def actualizar_tabla_eventos_escenario():
            eventos_table.setRowCount(0)
            for idx, evento in enumerate(self.eventos_scenario):
                eventos_table.insertRow(idx)
                activo = evento.get('activo', True)
                
                # Columna 0: Solo icono ✓ o ✗
                estado_item = QtWidgets.QTableWidgetItem("✓" if activo else "✗")
                estado_item.setTextAlignment(QtCore.Qt.AlignCenter)
                font = estado_item.font()
                font.setPointSize(14)
                font.setBold(True)
                estado_item.setFont(font)
                estado_item.setForeground(QtGui.QColor("#28a745") if activo else QtGui.QColor("#dc3545"))
                estado_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                estado_item.setToolTip("Activo - Click para desactivar" if activo else "Inactivo - Click para activar")
                eventos_table.setItem(idx, 0, estado_item)
                
                # Columna 1: Nombre del evento
                nombre_item = QtWidgets.QTableWidgetItem(evento['nombre'])
                nombre_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                nombre_item.setToolTip("Doble click para editar parámetros y factores")
                if not activo:
                    nombre_item.setForeground(QtGui.QColor("#999999"))
                    font = nombre_item.font()
                    font.setItalic(True)
                    nombre_item.setFont(font)
                eventos_table.setItem(idx, 1, nombre_item)
                
                # Columna 2: Factores
                factores = evento.get('factores_ajuste', [])
                num_factores = len(factores)
                num_activos_f = len([f for f in factores if f.get('activo', True)])
                if num_factores > 0:
                    factores_text = f"{num_activos_f}/{num_factores}"
                    factores_item = QtWidgets.QTableWidgetItem(factores_text)
                    factores_item.setForeground(QtGui.QColor("#0066cc"))
                else:
                    factores_item = QtWidgets.QTableWidgetItem("—")
                    factores_item.setForeground(QtGui.QColor("#999999"))
                factores_item.setTextAlignment(QtCore.Qt.AlignCenter)
                factores_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                eventos_table.setItem(idx, 2, factores_item)
        
        # Click en columna Estado para toggle
        def on_eventos_table_clicked(row, col):
            if col == 0:  # Click en columna Estado
                toggle_evento_activo(row)
        
        eventos_table.cellClicked.connect(on_eventos_table_clicked)

        # Llenar la tabla inicial
        actualizar_tabla_eventos_escenario()

        dialog_layout.addWidget(eventos_table)

        # Seleccionar primera fila por defecto (si existe), para que el botón funcione sin clic previo
        try:
            if eventos_table.rowCount() > 0:
                eventos_table.selectRow(0)
        except Exception:
            pass

        # Botón explícito para abrir el editor de parámetros del evento seleccionado
        botones_edicion_layout = QtWidgets.QHBoxLayout()
        botones_edicion_layout.addStretch(1)
        editar_evento_btn = QtWidgets.QPushButton("Editar parámetros del evento seleccionado")
        botones_edicion_layout.addWidget(editar_evento_btn)
        dialog_layout.addLayout(botones_edicion_layout)

        def abrir_editor_evento():
            fila = eventos_table.currentRow()
            if fila < 0 or fila >= len(self.eventos_scenario):
                QtWidgets.QMessageBox.warning(dialog, "Advertencia", "Seleccione un evento en la tabla para editar.")
                return
            editar_parametros_evento_safe(fila, 0)
            # Actualizar tabla después de editar (para reflejar cambios en factores)
            actualizar_tabla_eventos_escenario()

        editar_evento_btn.clicked.connect(abrir_editor_evento)

        # (Eliminado) No manipular la tabla principal de escenarios desde este diálogo

        # Función para editar parámetros del evento
        def editar_parametros_evento(row, column):
            evento = self.eventos_scenario[row]
            _s = lambda v, d='': str(v) if v is not None else d
            # Crear diálogo para editar parámetros del evento
            evento_dialog = QtWidgets.QDialog(dialog)
            evento_dialog.setWindowTitle(f"Editar Parámetros del Evento '{evento['nombre']}'")
            evento_dialog.resize(700, 750)  # Tamaño amplio para ver todo
            evento_dialog.setMinimumSize(600, 600)
            evento_dialog.setMaximumHeight(int(QtWidgets.QApplication.primaryScreen().availableGeometry().height() * 0.9))
            
            # Layout principal con scroll
            main_evento_layout = QtWidgets.QVBoxLayout(evento_dialog)
            main_evento_layout.setContentsMargins(0, 0, 0, 0)
            
            scroll_area_evento = QtWidgets.QScrollArea()
            scroll_area_evento.setWidgetResizable(True)
            scroll_area_evento.setFrameShape(QtWidgets.QFrame.NoFrame)
            scroll_area_evento.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            
            scroll_content_evento = QtWidgets.QWidget()
            evento_layout = QtWidgets.QVBoxLayout(scroll_content_evento)
            evento_layout.setContentsMargins(15, 15, 15, 15)

            # Sección para la Frecuencia
            freq_group = QtWidgets.QGroupBox("Parámetros de Frecuencia")
            freq_layout = QtWidgets.QFormLayout(freq_group)

            if evento['freq_opcion'] == 1:  # Poisson
                tasa_var = QtWidgets.QLineEdit(_s(evento.get('tasa')))
                freq_layout.addRow("Tasa Media (λ):", tasa_var)
            elif evento['freq_opcion'] == 2:  # Binomial
                n_var = QtWidgets.QLineEdit(_s(evento.get('num_eventos')))
                p_var = QtWidgets.QLineEdit(_s(evento.get('prob_exito')))
                freq_layout.addRow("Número de Eventos (n):", n_var)
                freq_layout.addRow("Probabilidad de Éxito (p):", p_var)
            elif evento['freq_opcion'] == 3:  # Bernoulli
                p_var = QtWidgets.QLineEdit(_s(evento.get('prob_exito')))
                freq_layout.addRow("Probabilidad de Éxito (p):", p_var)
            elif evento['freq_opcion'] == 4:  # Poisson-Gamma
                pg_minimo_var = QtWidgets.QLineEdit(_s(evento.get('pg_minimo')))
                pg_mas_probable_var = QtWidgets.QLineEdit(_s(evento.get('pg_mas_probable')))
                pg_maximo_var = QtWidgets.QLineEdit(_s(evento.get('pg_maximo')))
                pg_confianza_var = QtWidgets.QLineEdit(_s(evento.get('pg_confianza'), '80'))
                
                freq_layout.addRow("Valor mínimo de ocurrencia:", pg_minimo_var)
                freq_layout.addRow("Valor más probable de ocurrencia:", pg_mas_probable_var)
                freq_layout.addRow("Valor máximo de ocurrencia:", pg_maximo_var)
                freq_layout.addRow("Confianza asociada al rango (%):", pg_confianza_var)
            elif evento['freq_opcion'] == 5:  # Beta
                beta_minimo_var = QtWidgets.QLineEdit(_s(evento.get('beta_minimo')))
                beta_mas_probable_var = QtWidgets.QLineEdit(_s(evento.get('beta_mas_probable')))
                beta_maximo_var = QtWidgets.QLineEdit(_s(evento.get('beta_maximo')))
                beta_confianza_var = QtWidgets.QLineEdit(_s(evento.get('beta_confianza'), '80'))
                
                freq_layout.addRow("Probabilidad mínima razonable (%):", beta_minimo_var)
                freq_layout.addRow("Probabilidad más probable (%):", beta_mas_probable_var)
                freq_layout.addRow("Probabilidad máxima razonable (%):", beta_maximo_var)
                freq_layout.addRow("Confianza asociada al rango (%):", beta_confianza_var)

            # --- Límite superior de frecuencia (opcional, solo para distribuciones con conteo > 1) ---
            freq_limite_esc_var = QtWidgets.QLineEdit(
                str(evento.get('freq_limite_superior', '')) if evento.get('freq_limite_superior') is not None else ""
            )
            freq_limite_esc_var.setPlaceholderText("Sin límite")
            freq_limite_esc_var.setToolTip("Máximo número de ocurrencias posibles por año. Dejar vacío = sin límite.")
            if evento['freq_opcion'] in (1, 2, 4):  # Poisson, Binomial, Poisson-Gamma
                freq_layout.addRow("Máximo ocurrencias/año:", freq_limite_esc_var)

            evento_layout.addWidget(freq_group)

            # Sección para la Severidad
            sev_group = QtWidgets.QGroupBox("Parámetros de Severidad")
            sev_layout = QtWidgets.QFormLayout(sev_group)

            sev_min_val_init = evento.get('sev_minimo')
            sev_max_val_init = evento.get('sev_maximo')
            sev_min_var = QtWidgets.QLineEdit("" if sev_min_val_init is None else str(sev_min_val_init))
            sev_max_var = QtWidgets.QLineEdit("" if sev_max_val_init is None else str(sev_max_val_init))

            sev_layout.addRow("Valor Mínimo:", sev_min_var)
            if evento['sev_opcion'] != 5:  # Si no es Uniforme
                sev_mas_probable_init = evento.get('sev_mas_probable')
                sev_mas_probable_var = QtWidgets.QLineEdit("" if sev_mas_probable_init is None else str(sev_mas_probable_init))
                sev_layout.addRow("Valor Más Probable:", sev_mas_probable_var)
            else:
                sev_mas_probable_var = None
            sev_layout.addRow("Valor Máximo:", sev_max_var)

            # --- Método de Entrada y Parámetros Directos para Severidad (Normal, LogNormal, Pareto/GPD) ---
            sev_input_method_label = QtWidgets.QLabel("Método de Entrada de Parámetros:")
            sev_input_method_combo = NoScrollComboBox()
            sev_input_method_combo.addItems(["Mínimo / Más Probable / Máximo", "Parámetros Directos"])

            # Estado inicial desde el evento
            sev_op = evento['sev_opcion']
            sev_input_method_index = 1 if evento.get('sev_input_method') == 'direct' else 0
            sev_input_method_combo.setCurrentIndex(sev_input_method_index)

            # Grupo para parámetros directos (contenedor con stack de páginas)
            sev_direct_group = QtWidgets.QGroupBox("Parámetros Directos de Severidad")
            sev_direct_layout = QtWidgets.QVBoxLayout(sev_direct_group)

            # Widgets para Normal (1)
            sev_norm_mean_var = QtWidgets.QLineEdit()
            sev_norm_std_var = QtWidgets.QLineEdit()

            # Widgets para LogNormal (2)
            sev_ln_param_mode_combo = NoScrollComboBox()
            sev_ln_param_mode_combo.addItems(["s/scale (SciPy)", "mean/std", "mu/sigma (ln X)"])
            sev_ln_s_var = QtWidgets.QLineEdit()
            sev_ln_scale_var = QtWidgets.QLineEdit()
            sev_ln_mean_var = QtWidgets.QLineEdit()
            sev_ln_std_var = QtWidgets.QLineEdit()
            sev_ln_mu_var = QtWidgets.QLineEdit()
            sev_ln_sigma_var = QtWidgets.QLineEdit()
            sev_ln_loc_var = QtWidgets.QLineEdit("0")
            # Stacked para modos de LogNormal
            sev_ln_stack = QtWidgets.QStackedWidget()
            sev_ln_stack.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
            sev_ln_stack.setMinimumHeight(120)
            # Modo 0: s/scale
            ln_mode0_widget = QtWidgets.QWidget()
            ln_mode0_layout = QtWidgets.QFormLayout(ln_mode0_widget)
            ln_mode0_layout.addRow("Shape (s/sigma):", sev_ln_s_var)
            ln_mode0_layout.addRow("Scale (exp(mu)):", sev_ln_scale_var)
            sev_ln_stack.addWidget(ln_mode0_widget)
            # Modo 1: mean/std
            ln_mode1_widget = QtWidgets.QWidget()
            ln_mode1_layout = QtWidgets.QFormLayout(ln_mode1_widget)
            ln_mode1_layout.addRow("Media (mean):", sev_ln_mean_var)
            ln_mode1_layout.addRow("Desviación (std):", sev_ln_std_var)
            sev_ln_stack.addWidget(ln_mode1_widget)
            # Modo 2: mu/sigma
            ln_mode2_widget = QtWidgets.QWidget()
            ln_mode2_layout = QtWidgets.QFormLayout(ln_mode2_widget)
            ln_mode2_layout.addRow("mu (ln X):", sev_ln_mu_var)
            ln_mode2_layout.addRow("sigma (ln X):", sev_ln_sigma_var)
            sev_ln_stack.addWidget(ln_mode2_widget)
            sev_ln_param_mode_combo.currentIndexChanged.connect(sev_ln_stack.setCurrentIndex)
            # Asegurar que el stack muestre la página correspondiente al inicio
            try:
                sev_ln_stack.setCurrentIndex(sev_ln_param_mode_combo.currentIndex())
            except Exception:
                pass

            # Widgets para GPD/Pareto (4)
            sev_gpd_c_var = QtWidgets.QLineEdit()
            sev_gpd_scale_var = QtWidgets.QLineEdit()
            sev_gpd_loc_var = QtWidgets.QLineEdit()

            # --- Ajustes visuales mínimos: asegurar altura suficiente sin cambiar el tema ---
            def _style_num(le: QtWidgets.QLineEdit):
                le.setMinimumHeight(28)
                le.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

            for le in [
                sev_norm_mean_var, sev_norm_std_var,
                sev_ln_s_var, sev_ln_scale_var, sev_ln_mean_var, sev_ln_std_var, sev_ln_mu_var, sev_ln_sigma_var, sev_ln_loc_var,
                sev_gpd_c_var, sev_gpd_scale_var, sev_gpd_loc_var
            ]:
                _style_num(le)

            # Precarga de valores si existe configuración directa previa
            if evento.get('sev_input_method') == 'direct' and isinstance(evento.get('sev_params_direct'), dict):
                pd = evento['sev_params_direct']
                if sev_op == 1:
                    sev_norm_mean_var.setText(_s(pd.get('mean', pd.get('mu'))))
                    sev_norm_std_var.setText(_s(pd.get('std', pd.get('sigma'))))
                elif sev_op == 2:
                    if 'mean' in pd and 'std' in pd:
                        sev_ln_param_mode_combo.setCurrentIndex(1)
                    elif 'mu' in pd and 'sigma' in pd:
                        sev_ln_param_mode_combo.setCurrentIndex(2)
                    else:
                        sev_ln_param_mode_combo.setCurrentIndex(0)
                    sev_ln_s_var.setText(_s(pd.get('s')))
                    sev_ln_scale_var.setText(_s(pd.get('scale')))
                    sev_ln_mean_var.setText(_s(pd.get('mean')))
                    sev_ln_std_var.setText(_s(pd.get('std')))
                    sev_ln_mu_var.setText(_s(pd.get('mu')))
                    sev_ln_sigma_var.setText(_s(pd.get('sigma')))
                    sev_ln_loc_var.setText(_s(pd.get('loc'), '0'))
                elif sev_op == 4:
                    sev_gpd_c_var.setText(_s(pd.get('c')))
                    sev_gpd_scale_var.setText(_s(pd.get('scale')))
                    sev_gpd_loc_var.setText(_s(pd.get('loc')))

            # --- Páginas del stack para direct params ---
            sev_direct_stack = QtWidgets.QStackedWidget()
            # Página Normal
            page_norm = QtWidgets.QWidget()
            page_norm_form = QtWidgets.QFormLayout(page_norm)
            page_norm_form.addRow("Media (mean):", sev_norm_mean_var)
            page_norm_form.addRow("Desviación (std):", sev_norm_std_var)
            sev_direct_stack.addWidget(page_norm)
            # Página LogNormal
            page_ln = QtWidgets.QWidget()
            page_ln_v = QtWidgets.QVBoxLayout(page_ln)
            page_ln_v.setContentsMargins(0, 0, 0, 0)
            page_ln_form_top = QtWidgets.QFormLayout()
            page_ln_form_top.setContentsMargins(0, 0, 0, 0)
            page_ln_form_top.addRow("Tipo de parametrización:", sev_ln_param_mode_combo)
            page_ln_v.addLayout(page_ln_form_top)
            page_ln_v.addWidget(sev_ln_stack)
            page_ln_form_bottom = QtWidgets.QFormLayout()
            page_ln_form_bottom.setContentsMargins(0, 0, 0, 0)
            page_ln_form_bottom.addRow("Location (loc, opcional):", sev_ln_loc_var)
            page_ln_v.addLayout(page_ln_form_bottom)
            sev_direct_stack.addWidget(page_ln)
            # Página GPD
            page_gpd = QtWidgets.QWidget()
            page_gpd_form = QtWidgets.QFormLayout(page_gpd)
            page_gpd_form.addRow("Shape (c/xi):", sev_gpd_c_var)
            page_gpd_form.addRow("Scale (beta):", sev_gpd_scale_var)
            page_gpd_form.addRow("Location (loc/umbral):", sev_gpd_loc_var)
            sev_direct_stack.addWidget(page_gpd)

            sev_direct_layout.addWidget(sev_direct_stack)
            # Asegurar que el grupo directo se expanda correctamente
            sev_direct_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

            def update_direct_stack_page():
                if sev_op == 1:
                    sev_direct_stack.setCurrentIndex(0)
                elif sev_op == 2:
                    sev_direct_stack.setCurrentIndex(1)
                elif sev_op == 4:
                    sev_direct_stack.setCurrentIndex(2)

            def toggle_sev_input_method():
                is_direct = (sev_input_method_combo.currentIndex() == 1)
                supports_direct = sev_op in (1, 2, 4)
                sev_input_method_label.setVisible(supports_direct)
                sev_input_method_combo.setVisible(supports_direct)
                sev_direct_group.setVisible(supports_direct and is_direct)
                # Ocultar Min/Mode/Max si direct
                sev_min_var.setVisible(not is_direct)
                if sev_mas_probable_var is not None:
                    sev_mas_probable_var.setVisible(not is_direct)
                sev_max_var.setVisible(not is_direct)
                # Asegurar que el contenido directo muestre la página adecuada al mostrarlo
                if supports_direct and is_direct:
                    update_direct_stack_page()
                    try:
                        sev_ln_stack.setCurrentIndex(sev_ln_param_mode_combo.currentIndex())
                    except Exception:
                        pass
                    try:
                        sev_direct_group.updateGeometry()
                        evento_dialog.adjustSize()
                    except Exception:
                        pass

            sev_input_method_combo.currentIndexChanged.connect(toggle_sev_input_method)
            # Añadir al layout de severidad
            sev_layout.addRow(sev_input_method_label, sev_input_method_combo)
            sev_layout.addRow(sev_direct_group)
            # Estado inicial
            update_direct_stack_page()
            toggle_sev_input_method()
            try:
                evento_dialog.adjustSize()
            except Exception:
                pass

            # --- Límite superior de severidad (opcional) ---
            sev_limite_esc_var = QtWidgets.QLineEdit(
                str(evento.get('sev_limite_superior', '')) if evento.get('sev_limite_superior') is not None else ""
            )
            sev_limite_esc_var.setPlaceholderText("Sin límite")
            sev_limite_esc_var.setToolTip("Máximo impacto posible por ocurrencia individual. Dejar vacío = sin límite.")
            sev_layout.addRow("Límite superior ($):", sev_limite_esc_var)

            evento_layout.addWidget(sev_group)

            # ====================================================================
            # SECCIÓN: ESCALAMIENTO DE SEVERIDAD POR FRECUENCIA (ESCENARIO)
            # ====================================================================
            sev_freq_config_esc, _on_freq_dist_changed_esc = _crear_seccion_escalamiento_ui(evento_layout, evento)
            # Inicializar estado según distribución del evento (fija en escenario)
            _on_freq_dist_changed_esc(evento.get('freq_opcion', 1))

            # ====================================================================
            # SECCIÓN DE FACTORES/CONTROLES DE RIESGO (NUEVA)
            # ====================================================================
            factores_group = QtWidgets.QGroupBox("Factores de Riesgo / Controles")
            factores_layout = QtWidgets.QVBoxLayout(factores_group)
            
            # Cargar factores existentes del evento (copia para edición)
            factores_escenario = copy.deepcopy(evento.get('factores_ajuste', []))
            
            # Normalizar factores (backward compatibility)
            for i, f in enumerate(factores_escenario):
                factores_escenario[i] = normalizar_factor_global(f)
            
            # Info label
            factores_info = QtWidgets.QLabel("Click en ✓/✗ para activar/desactivar. Doble click para editar.")
            factores_info.setStyleSheet("color: #666; font-size: 11px;")
            factores_layout.addWidget(factores_info)
            
            # Tabla de factores - 3 columnas simples
            factores_table = QtWidgets.QTableWidget()
            factores_table.setColumnCount(3)
            factores_table.setHorizontalHeaderLabels(["", "Factor / Control", "Configuración"])
            factores_table.horizontalHeader().setStretchLastSection(True)
            factores_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
            factores_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
            factores_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
            factores_table.setColumnWidth(0, 35)
            factores_table.setMinimumHeight(120)
            factores_table.setMaximumHeight(200)
            factores_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            factores_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            factores_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            factores_table.verticalHeader().setVisible(False)
            factores_layout.addWidget(factores_table)
            
            # Botones de acción
            factores_btn_layout = QtWidgets.QHBoxLayout()
            btn_agregar_factor = QtWidgets.QPushButton("➕ Agregar")
            btn_agregar_factor.setFixedHeight(28)
            btn_eliminar_factor = QtWidgets.QPushButton("🗑 Eliminar seleccionado")
            btn_eliminar_factor.setFixedHeight(28)
            btn_eliminar_factor.setStyleSheet("QPushButton { color: #dc3545; }")
            factores_btn_layout.addWidget(btn_agregar_factor)
            factores_btn_layout.addWidget(btn_eliminar_factor)
            factores_btn_layout.addStretch()
            factores_layout.addLayout(factores_btn_layout)
            
            # Toggle estado activo de factor
            def toggle_factor_activo(row):
                if 0 <= row < len(factores_escenario):
                    factores_escenario[row]['activo'] = not factores_escenario[row].get('activo', True)
                    actualizar_tabla_factores_escenario()
            
            # Función para actualizar la tabla de factores
            def actualizar_tabla_factores_escenario():
                factores_table.setRowCount(0)
                for idx, factor in enumerate(factores_escenario):
                    factores_table.insertRow(idx)
                    activo = factor.get('activo', True)
                    
                    # Columna 0: Solo icono ✓ o ✗
                    estado_item = QtWidgets.QTableWidgetItem("✓" if activo else "✗")
                    estado_item.setTextAlignment(QtCore.Qt.AlignCenter)
                    font = estado_item.font()
                    font.setPointSize(12)
                    font.setBold(True)
                    estado_item.setFont(font)
                    estado_item.setForeground(QtGui.QColor("#28a745") if activo else QtGui.QColor("#dc3545"))
                    estado_item.setToolTip("Click para cambiar estado")
                    factores_table.setItem(idx, 0, estado_item)
                    
                    # Columna 1: Nombre
                    item_nombre = QtWidgets.QTableWidgetItem(factor.get('nombre', ''))
                    if not activo:
                        item_nombre.setForeground(QtGui.QColor("#999999"))
                        font = item_nombre.font()
                        font.setItalic(True)
                        item_nombre.setFont(font)
                    factores_table.setItem(idx, 1, item_nombre)
                    
                    # Columna 2: Tipo y Configuración
                    tipo_modelo = factor.get('tipo_modelo', 'estatico')
                    if tipo_modelo == 'estocastico':
                        conf = factor.get('confiabilidad', 0)
                        freq_e = factor.get('reduccion_efectiva', 0)
                        freq_f = factor.get('reduccion_fallo', 0)
                        conf_text = f"Estocástico: {conf}% conf → {freq_e}%/{freq_f}%"
                    else:
                        parts = []
                        if factor.get('afecta_frecuencia', True):
                            val = -factor.get('impacto_porcentual', 0)
                            parts.append(f"Freq:{val:+d}%")
                        if factor.get('afecta_severidad', False):
                            tipo_sev = factor.get('tipo_severidad', 'porcentual')
                            if tipo_sev == 'seguro':
                                # Modelo de seguro - con validación de tipos
                                try:
                                    tipo_ded = factor.get('seguro_tipo_deducible', 'agregado')
                                    ded = float(factor.get('seguro_deducible', 0) or 0)
                                    cob = float(factor.get('seguro_cobertura_pct', 100) or 100)
                                    lim = float(factor.get('seguro_limite', 0) or 0)
                                    lim_ocurr = float(factor.get('seguro_limite_ocurrencia', 0) or 0)
                                    ded_str = f"${ded:,.0f}" if ded > 0 else "$0"
                                    if tipo_ded == 'por_ocurrencia':
                                        tipo_str = "p/ocurr"
                                        lim_str = f"${lim_ocurr:,.0f}/ocurr" if lim_ocurr > 0 else "∞/ocurr"
                                        if lim > 0:
                                            lim_str += f" ${lim:,.0f}/año"
                                    else:
                                        tipo_str = "agreg"
                                        lim_str = f"${lim:,.0f}" if lim > 0 else "∞"
                                    parts.append(f"🛡️ {tipo_str} Ded:{ded_str} Cob:{cob:.0f}% Lím:{lim_str}")
                                except (ValueError, TypeError):
                                    parts.append("🛡️ Seguro (config pendiente)")
                            else:
                                val = -factor.get('impacto_severidad_pct', 0)
                                parts.append(f"Sev:{val:+d}%")
                        conf_text = "Estático: " + (" ".join(parts) if parts else "0%")
                    
                    item_config = QtWidgets.QTableWidgetItem(conf_text)
                    item_config.setForeground(QtGui.QColor("#0066cc") if tipo_modelo == 'estocastico' else QtGui.QColor("#666666"))
                    if not activo:
                        item_config.setForeground(QtGui.QColor("#999999"))
                    factores_table.setItem(idx, 2, item_config)
            
            # Click en columna Estado para toggle
            def on_factores_table_clicked(row, col):
                if col == 0:
                    toggle_factor_activo(row)
            
            def eliminar_factor_escenario(row):
                if 0 <= row < len(factores_escenario):
                    del factores_escenario[row]
                    actualizar_tabla_factores_escenario()
            
            def agregar_factor_escenario():
                """Diálogo para agregar nuevo factor al evento del escenario"""
                factor_dialog = QtWidgets.QDialog(evento_dialog)
                factor_dialog.setWindowTitle("Agregar Control/Factor de Riesgo")
                factor_dialog.resize(500, 450)  # Tamaño inicial compacto
                factor_dialog.setMinimumSize(450, 350)
                factor_dialog.setMaximumHeight(int(QtWidgets.QApplication.primaryScreen().availableGeometry().height() * 0.9))
                
                # Layout principal con scroll
                main_factor_layout = QtWidgets.QVBoxLayout(factor_dialog)
                main_factor_layout.setContentsMargins(0, 0, 0, 0)
                
                scroll_area_factor = QtWidgets.QScrollArea()
                scroll_area_factor.setWidgetResizable(True)
                scroll_area_factor.setFrameShape(QtWidgets.QFrame.NoFrame)
                scroll_area_factor.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
                
                scroll_content_factor = QtWidgets.QWidget()
                factor_layout = QtWidgets.QVBoxLayout(scroll_content_factor)
                factor_layout.setContentsMargins(15, 15, 15, 15)
                
                # Nombre
                nombre_layout_f = QtWidgets.QFormLayout()
                nombre_factor_var = QtWidgets.QLineEdit()
                nombre_factor_var.setPlaceholderText("Ej: Firewall, Backup, etc.")
                nombre_layout_f.addRow("Nombre:", nombre_factor_var)
                factor_layout.addLayout(nombre_layout_f)
                
                # Tipo de modelo
                factor_layout.addWidget(QtWidgets.QLabel("<b>Tipo de modelo:</b>"))
                tipo_grupo = QtWidgets.QButtonGroup(factor_dialog)
                tipo_estatico_radio = QtWidgets.QRadioButton("Estático (reducción fija)")
                tipo_estocastico_radio = QtWidgets.QRadioButton("Estocástico (confiabilidad variable)")
                tipo_estatico_radio.setChecked(True)
                tipo_grupo.addButton(tipo_estatico_radio)
                tipo_grupo.addButton(tipo_estocastico_radio)
                factor_layout.addWidget(tipo_estatico_radio)
                factor_layout.addWidget(tipo_estocastico_radio)
                
                # Frame Estático
                estatico_frame = QtWidgets.QGroupBox("Configuración Estática")
                estatico_form = QtWidgets.QFormLayout(estatico_frame)
                
                afecta_freq_check = QtWidgets.QCheckBox("Afecta frecuencia")
                afecta_freq_check.setChecked(True)
                estatico_form.addRow(afecta_freq_check)
                impacto_freq_spin = NoScrollSpinBox()
                impacto_freq_spin.setRange(-200, 99)
                impacto_freq_spin.setValue(30)
                impacto_freq_spin.setSuffix("%")
                estatico_form.addRow("   Reducción frecuencia:", impacto_freq_spin)
                afecta_freq_check.toggled.connect(impacto_freq_spin.setEnabled)
                
                afecta_sev_check = QtWidgets.QCheckBox("Afecta severidad")
                afecta_sev_check.setChecked(False)
                estatico_form.addRow(afecta_sev_check)
                
                # Contenedor para opciones de severidad
                sev_container_esc = QtWidgets.QWidget()
                sev_container_layout_esc = QtWidgets.QVBoxLayout(sev_container_esc)
                sev_container_layout_esc.setContentsMargins(20, 0, 0, 0)
                sev_container_esc.setEnabled(False)
                
                # Radio buttons para tipo de severidad
                tipo_sev_grupo_esc = QtWidgets.QButtonGroup(factor_dialog)
                tipo_sev_porcentual_esc = QtWidgets.QRadioButton("Reducción porcentual")
                tipo_sev_seguro_esc = QtWidgets.QRadioButton("Seguro/Transferencia")
                tipo_sev_porcentual_esc.setChecked(True)
                tipo_sev_grupo_esc.addButton(tipo_sev_porcentual_esc)
                tipo_sev_grupo_esc.addButton(tipo_sev_seguro_esc)
                
                tipo_sev_layout_esc = QtWidgets.QHBoxLayout()
                tipo_sev_layout_esc.addWidget(tipo_sev_porcentual_esc)
                tipo_sev_layout_esc.addWidget(tipo_sev_seguro_esc)
                tipo_sev_layout_esc.addStretch()
                sev_container_layout_esc.addLayout(tipo_sev_layout_esc)
                
                # Frame porcentual
                porcentual_frame_esc = QtWidgets.QWidget()
                porcentual_layout_esc = QtWidgets.QFormLayout(porcentual_frame_esc)
                porcentual_layout_esc.setContentsMargins(0, 5, 0, 0)
                impacto_sev_spin = NoScrollSpinBox()
                impacto_sev_spin.setRange(-200, 99)
                impacto_sev_spin.setValue(25)
                impacto_sev_spin.setSuffix("%")
                porcentual_layout_esc.addRow("Reducción (%):", impacto_sev_spin)
                sev_container_layout_esc.addWidget(porcentual_frame_esc)
                
                # Frame seguro
                seguro_frame_esc = QtWidgets.QWidget()
                seguro_layout_esc = QtWidgets.QFormLayout(seguro_frame_esc)
                seguro_layout_esc.setContentsMargins(0, 5, 0, 0)
                
                # Tipo de deducible (por ocurrencia vs agregado)
                tipo_ded_group_esc = QtWidgets.QButtonGroup(seguro_frame_esc)
                tipo_ded_layout_esc = QtWidgets.QHBoxLayout()
                tipo_ded_ocurrencia_esc = QtWidgets.QRadioButton("Por ocurrencia")
                tipo_ded_ocurrencia_esc.setToolTip("El deducible se aplica a cada siniestro individual")
                tipo_ded_agregado_esc = QtWidgets.QRadioButton("Agregado anual")
                tipo_ded_agregado_esc.setToolTip("El deducible se aplica a la pérdida total del año")
                tipo_ded_agregado_esc.setChecked(True)
                tipo_ded_group_esc.addButton(tipo_ded_ocurrencia_esc)
                tipo_ded_group_esc.addButton(tipo_ded_agregado_esc)
                tipo_ded_layout_esc.addWidget(tipo_ded_ocurrencia_esc)
                tipo_ded_layout_esc.addWidget(tipo_ded_agregado_esc)
                tipo_ded_layout_esc.addStretch()
                seguro_layout_esc.addRow("Tipo deducible:", tipo_ded_layout_esc)
                
                seguro_ded_spin_esc = NoScrollSpinBox()
                seguro_ded_spin_esc.setRange(0, 999999999)
                seguro_ded_spin_esc.setValue(50000)
                seguro_ded_spin_esc.setPrefix("$ ")
                seguro_layout_esc.addRow("Deducible:", seguro_ded_spin_esc)
                
                seguro_cob_spin_esc = NoScrollSpinBox()
                seguro_cob_spin_esc.setRange(1, 100)
                seguro_cob_spin_esc.setValue(80)
                seguro_cob_spin_esc.setSuffix("%")
                seguro_layout_esc.addRow("Cobertura (%):", seguro_cob_spin_esc)
                
                # Límite por ocurrencia (nuevo)
                seguro_lim_ocurr_spin_esc = NoScrollSpinBox()
                seguro_lim_ocurr_spin_esc.setRange(0, 999999999)
                seguro_lim_ocurr_spin_esc.setValue(0)
                seguro_lim_ocurr_spin_esc.setPrefix("$ ")
                seguro_lim_ocurr_spin_esc.setToolTip("Máximo que paga el seguro por siniestro (0 = sin límite por ocurrencia)")
                seguro_layout_esc.addRow("Límite por siniestro:", seguro_lim_ocurr_spin_esc)
                
                seguro_lim_spin_esc = NoScrollSpinBox()
                seguro_lim_spin_esc.setRange(0, 999999999)
                seguro_lim_spin_esc.setValue(1000000)
                seguro_lim_spin_esc.setPrefix("$ ")
                seguro_lim_spin_esc.setToolTip("Máximo agregado anual que paga el seguro (0 = sin límite)")
                seguro_layout_esc.addRow("Límite agregado:", seguro_lim_spin_esc)
                
                seguro_help_esc = QtWidgets.QLabel(
                    "💡 <b>Por ocurrencia:</b> Deducible/límite por siniestro.<br>"
                    "<b>Agregado:</b> Deducible/límite al total anual."
                )
                seguro_help_esc.setWordWrap(True)
                seguro_help_esc.setStyleSheet("color: #666; font-size: 9pt; padding: 3px;")
                seguro_layout_esc.addRow(seguro_help_esc)
                
                seguro_frame_esc.setVisible(False)
                sev_container_layout_esc.addWidget(seguro_frame_esc)
                
                def toggle_tipo_sev_esc():
                    porcentual_frame_esc.setVisible(tipo_sev_porcentual_esc.isChecked())
                    seguro_frame_esc.setVisible(tipo_sev_seguro_esc.isChecked())
                
                tipo_sev_porcentual_esc.toggled.connect(toggle_tipo_sev_esc)
                estatico_form.addRow(sev_container_esc)
                afecta_sev_check.toggled.connect(sev_container_esc.setEnabled)
                
                factor_layout.addWidget(estatico_frame)
                
                # Frame Estocástico
                estocastico_frame = QtWidgets.QGroupBox("Configuración Estocástica")
                estocastico_form = QtWidgets.QFormLayout(estocastico_frame)
                
                confiabilidad_spin = NoScrollSpinBox()
                confiabilidad_spin.setRange(0, 100)
                confiabilidad_spin.setValue(70)
                confiabilidad_spin.setSuffix("%")
                estocastico_form.addRow("Confiabilidad:", confiabilidad_spin)
                
                estocastico_form.addRow(QtWidgets.QLabel("<b>Si funciona:</b>"))
                red_efe_freq = NoScrollSpinBox()
                red_efe_freq.setRange(-100, 99)
                red_efe_freq.setValue(80)
                red_efe_freq.setSuffix("%")
                estocastico_form.addRow("   Red. frecuencia:", red_efe_freq)
                red_efe_sev = NoScrollSpinBox()
                red_efe_sev.setRange(-100, 99)
                red_efe_sev.setValue(50)
                red_efe_sev.setSuffix("%")
                estocastico_form.addRow("   Red. severidad:", red_efe_sev)
                
                estocastico_form.addRow(QtWidgets.QLabel("<b>Si falla:</b>"))
                red_fal_freq = NoScrollSpinBox()
                red_fal_freq.setRange(-100, 99)
                red_fal_freq.setValue(10)
                red_fal_freq.setSuffix("%")
                estocastico_form.addRow("   Red. frecuencia:", red_fal_freq)
                red_fal_sev = NoScrollSpinBox()
                red_fal_sev.setRange(-100, 99)
                red_fal_sev.setValue(5)
                red_fal_sev.setSuffix("%")
                estocastico_form.addRow("   Red. severidad:", red_fal_sev)
                
                factor_layout.addWidget(estocastico_frame)
                estocastico_frame.setVisible(False)
                
                # Agregar stretch para compactar elementos arriba
                factor_layout.addStretch(1)
                
                def toggle_tipo_frames():
                    estatico_frame.setVisible(tipo_estatico_radio.isChecked())
                    estocastico_frame.setVisible(tipo_estocastico_radio.isChecked())
                    factor_dialog.adjustSize()
                
                tipo_estatico_radio.toggled.connect(toggle_tipo_frames)
                
                # Conectar scroll area con contenido
                scroll_area_factor.setWidget(scroll_content_factor)
                main_factor_layout.addWidget(scroll_area_factor)
                
                # Botones (fuera del scroll para que siempre sean visibles)
                buttons_f = QtWidgets.QDialogButtonBox(
                    QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
                )
                def validar_y_aceptar_factor():
                    nombre = nombre_factor_var.text().strip()
                    if not nombre:
                        QtWidgets.QMessageBox.warning(factor_dialog, "Advertencia", "El nombre no puede estar vacío.")
                        return
                    if tipo_estatico_radio.isChecked():
                        if not afecta_freq_check.isChecked() and not afecta_sev_check.isChecked():
                            QtWidgets.QMessageBox.warning(factor_dialog, "Advertencia", 
                                "Debe seleccionar al menos frecuencia o severidad.")
                            return
                    factor_dialog.accept()

                buttons_f.accepted.connect(validar_y_aceptar_factor)
                buttons_f.rejected.connect(factor_dialog.reject)
                main_factor_layout.addWidget(buttons_f)
                
                if factor_dialog.exec_() == QtWidgets.QDialog.Accepted:
                    nombre = nombre_factor_var.text().strip()
                    
                    if tipo_estatico_radio.isChecked():
                        
                        # Determinar tipo de severidad
                        es_seguro_esc = afecta_sev_check.isChecked() and tipo_sev_seguro_esc.isChecked()
                        
                        nuevo_factor = {
                            'nombre': nombre,
                            'tipo_modelo': 'estatico',
                            'afecta_frecuencia': afecta_freq_check.isChecked(),
                            'impacto_porcentual': -impacto_freq_spin.value() if afecta_freq_check.isChecked() else 0,
                            'afecta_severidad': afecta_sev_check.isChecked(),
                            'tipo_severidad': 'seguro' if es_seguro_esc else 'porcentual',
                            'impacto_severidad_pct': -impacto_sev_spin.value() if (afecta_sev_check.isChecked() and not es_seguro_esc) else 0,
                            'activo': True,
                            'confiabilidad': 100,
                            'reduccion_efectiva': impacto_freq_spin.value() if afecta_freq_check.isChecked() else 0,
                            'reduccion_fallo': 0,
                            'reduccion_severidad_efectiva': impacto_sev_spin.value() if (afecta_sev_check.isChecked() and not es_seguro_esc) else 0,
                            'reduccion_severidad_fallo': 0,
                            # Campos de seguro
                            'seguro_deducible': seguro_ded_spin_esc.value() if es_seguro_esc else 0,
                            'seguro_cobertura_pct': seguro_cob_spin_esc.value() if es_seguro_esc else 100,
                            'seguro_limite': seguro_lim_spin_esc.value() if es_seguro_esc else 0,
                            'seguro_tipo_deducible': 'por_ocurrencia' if (es_seguro_esc and tipo_ded_ocurrencia_esc.isChecked()) else 'agregado',
                            'seguro_limite_ocurrencia': seguro_lim_ocurr_spin_esc.value() if es_seguro_esc else 0
                        }
                    else:
                        nuevo_factor = {
                            'nombre': nombre,
                            'tipo_modelo': 'estocastico',
                            'confiabilidad': confiabilidad_spin.value(),
                            'reduccion_efectiva': red_efe_freq.value(),
                            'reduccion_fallo': red_fal_freq.value(),
                            'reduccion_severidad_efectiva': red_efe_sev.value(),
                            'reduccion_severidad_fallo': red_fal_sev.value(),
                            'activo': True,
                            'impacto_porcentual': -red_efe_freq.value(),
                            'afecta_frecuencia': True,
                            'afecta_severidad': (red_efe_sev.value() != 0 or red_fal_sev.value() != 0),
                            'impacto_severidad_pct': 0
                        }
                    
                    factores_escenario.append(nuevo_factor)
                    actualizar_tabla_factores_escenario()
            
            def editar_factor_escenario(row):
                """Diálogo para editar un factor existente"""
                if row < 0 or row >= len(factores_escenario):
                    return
                
                factor_actual = factores_escenario[row]
                
                factor_dialog = QtWidgets.QDialog(evento_dialog)
                factor_dialog.setWindowTitle("Editar Control/Factor de Riesgo")
                factor_dialog.resize(500, 450)  # Tamaño inicial compacto
                factor_dialog.setMinimumSize(450, 350)
                factor_dialog.setMaximumHeight(int(QtWidgets.QApplication.primaryScreen().availableGeometry().height() * 0.9))
                
                # Layout principal con scroll
                main_factor_edit_layout = QtWidgets.QVBoxLayout(factor_dialog)
                main_factor_edit_layout.setContentsMargins(0, 0, 0, 0)
                
                scroll_area_factor_edit = QtWidgets.QScrollArea()
                scroll_area_factor_edit.setWidgetResizable(True)
                scroll_area_factor_edit.setFrameShape(QtWidgets.QFrame.NoFrame)
                scroll_area_factor_edit.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
                
                scroll_content_factor_edit = QtWidgets.QWidget()
                factor_layout = QtWidgets.QVBoxLayout(scroll_content_factor_edit)
                factor_layout.setContentsMargins(15, 15, 15, 15)
                
                # Nombre
                nombre_layout_f = QtWidgets.QFormLayout()
                nombre_factor_var = QtWidgets.QLineEdit()
                nombre_factor_var.setText(factor_actual.get('nombre', ''))
                nombre_layout_f.addRow("Nombre:", nombre_factor_var)
                factor_layout.addLayout(nombre_layout_f)
                
                # Tipo de modelo
                factor_layout.addWidget(QtWidgets.QLabel("<b>Tipo de modelo:</b>"))
                tipo_grupo = QtWidgets.QButtonGroup(factor_dialog)
                tipo_estatico_radio = QtWidgets.QRadioButton("Estático (reducción fija)")
                tipo_estocastico_radio = QtWidgets.QRadioButton("Estocástico (confiabilidad variable)")
                
                tipo_actual = factor_actual.get('tipo_modelo', 'estatico')
                if tipo_actual == 'estocastico':
                    tipo_estocastico_radio.setChecked(True)
                else:
                    tipo_estatico_radio.setChecked(True)
                
                tipo_grupo.addButton(tipo_estatico_radio)
                tipo_grupo.addButton(tipo_estocastico_radio)
                factor_layout.addWidget(tipo_estatico_radio)
                factor_layout.addWidget(tipo_estocastico_radio)
                
                # Frame Estático
                estatico_frame = QtWidgets.QGroupBox("Configuración Estática")
                estatico_form = QtWidgets.QFormLayout(estatico_frame)
                
                afecta_freq_default = factor_actual.get('afecta_frecuencia', factor_actual.get('impacto_porcentual', 0) != 0)
                afecta_freq_check = QtWidgets.QCheckBox("Afecta frecuencia")
                afecta_freq_check.setChecked(afecta_freq_default)
                estatico_form.addRow(afecta_freq_check)
                impacto_freq_spin = NoScrollSpinBox()
                impacto_freq_spin.setRange(-200, 99)
                impacto_freq_spin.setValue(-factor_actual.get('impacto_porcentual', -30))
                impacto_freq_spin.setSuffix("%")
                impacto_freq_spin.setEnabled(afecta_freq_default)
                estatico_form.addRow("   Reducción frecuencia:", impacto_freq_spin)
                afecta_freq_check.toggled.connect(impacto_freq_spin.setEnabled)
                
                afecta_sev_check = QtWidgets.QCheckBox("Afecta severidad")
                afecta_sev_check.setChecked(factor_actual.get('afecta_severidad', False))
                estatico_form.addRow(afecta_sev_check)
                
                # Contenedor para opciones de severidad
                sev_container_edit_esc = QtWidgets.QWidget()
                sev_container_layout_edit_esc = QtWidgets.QVBoxLayout(sev_container_edit_esc)
                sev_container_layout_edit_esc.setContentsMargins(20, 0, 0, 0)
                sev_container_edit_esc.setEnabled(factor_actual.get('afecta_severidad', False))
                
                # Radio buttons para tipo de severidad
                tipo_sev_grupo_edit_esc = QtWidgets.QButtonGroup(factor_dialog)
                tipo_sev_porcentual_edit_esc = QtWidgets.QRadioButton("Reducción porcentual")
                tipo_sev_seguro_edit_esc = QtWidgets.QRadioButton("Seguro/Transferencia")
                
                # Pre-seleccionar según tipo actual
                tipo_sev_actual_esc = factor_actual.get('tipo_severidad', 'porcentual')
                if tipo_sev_actual_esc == 'seguro':
                    tipo_sev_seguro_edit_esc.setChecked(True)
                else:
                    tipo_sev_porcentual_edit_esc.setChecked(True)
                
                tipo_sev_grupo_edit_esc.addButton(tipo_sev_porcentual_edit_esc)
                tipo_sev_grupo_edit_esc.addButton(tipo_sev_seguro_edit_esc)
                
                tipo_sev_layout_edit_esc = QtWidgets.QHBoxLayout()
                tipo_sev_layout_edit_esc.addWidget(tipo_sev_porcentual_edit_esc)
                tipo_sev_layout_edit_esc.addWidget(tipo_sev_seguro_edit_esc)
                tipo_sev_layout_edit_esc.addStretch()
                sev_container_layout_edit_esc.addLayout(tipo_sev_layout_edit_esc)
                
                # Frame porcentual
                porcentual_frame_edit_esc = QtWidgets.QWidget()
                porcentual_layout_edit_esc = QtWidgets.QFormLayout(porcentual_frame_edit_esc)
                porcentual_layout_edit_esc.setContentsMargins(0, 5, 0, 0)
                impacto_sev_spin = NoScrollSpinBox()
                impacto_sev_spin.setRange(-200, 99)
                impacto_sev_spin.setValue(-factor_actual.get('impacto_severidad_pct', -25))
                impacto_sev_spin.setSuffix("%")
                porcentual_layout_edit_esc.addRow("Reducción (%):", impacto_sev_spin)
                sev_container_layout_edit_esc.addWidget(porcentual_frame_edit_esc)
                
                # Frame seguro
                seguro_frame_edit_esc = QtWidgets.QWidget()
                seguro_layout_edit_esc = QtWidgets.QFormLayout(seguro_frame_edit_esc)
                seguro_layout_edit_esc.setContentsMargins(0, 5, 0, 0)
                
                # Tipo de deducible (por ocurrencia vs agregado)
                tipo_ded_group_edit_esc = QtWidgets.QButtonGroup(seguro_frame_edit_esc)
                tipo_ded_layout_edit_esc = QtWidgets.QHBoxLayout()
                tipo_ded_ocurrencia_edit_esc = QtWidgets.QRadioButton("Por ocurrencia")
                tipo_ded_ocurrencia_edit_esc.setToolTip("El deducible se aplica a cada siniestro individual")
                tipo_ded_agregado_edit_esc = QtWidgets.QRadioButton("Agregado anual")
                tipo_ded_agregado_edit_esc.setToolTip("El deducible se aplica a la pérdida total del año")
                # Pre-seleccionar según valor actual
                tipo_ded_actual_esc = factor_actual.get('seguro_tipo_deducible', 'agregado')
                if tipo_ded_actual_esc == 'por_ocurrencia':
                    tipo_ded_ocurrencia_edit_esc.setChecked(True)
                else:
                    tipo_ded_agregado_edit_esc.setChecked(True)
                tipo_ded_group_edit_esc.addButton(tipo_ded_ocurrencia_edit_esc)
                tipo_ded_group_edit_esc.addButton(tipo_ded_agregado_edit_esc)
                tipo_ded_layout_edit_esc.addWidget(tipo_ded_ocurrencia_edit_esc)
                tipo_ded_layout_edit_esc.addWidget(tipo_ded_agregado_edit_esc)
                tipo_ded_layout_edit_esc.addStretch()
                seguro_layout_edit_esc.addRow("Tipo deducible:", tipo_ded_layout_edit_esc)
                
                seguro_ded_spin_edit_esc = NoScrollSpinBox()
                seguro_ded_spin_edit_esc.setRange(0, 999999999)
                seguro_ded_spin_edit_esc.setValue(factor_actual.get('seguro_deducible', 50000))
                seguro_ded_spin_edit_esc.setPrefix("$ ")
                seguro_layout_edit_esc.addRow("Deducible:", seguro_ded_spin_edit_esc)
                
                seguro_cob_spin_edit_esc = NoScrollSpinBox()
                seguro_cob_spin_edit_esc.setRange(1, 100)
                seguro_cob_spin_edit_esc.setValue(factor_actual.get('seguro_cobertura_pct', 80))
                seguro_cob_spin_edit_esc.setSuffix("%")
                seguro_layout_edit_esc.addRow("Cobertura (%):", seguro_cob_spin_edit_esc)
                
                # Límite por ocurrencia (nuevo)
                seguro_lim_ocurr_spin_edit_esc = NoScrollSpinBox()
                seguro_lim_ocurr_spin_edit_esc.setRange(0, 999999999)
                seguro_lim_ocurr_spin_edit_esc.setValue(factor_actual.get('seguro_limite_ocurrencia', 0))
                seguro_lim_ocurr_spin_edit_esc.setPrefix("$ ")
                seguro_lim_ocurr_spin_edit_esc.setToolTip("Máximo que paga el seguro por siniestro (0 = sin límite por ocurrencia)")
                seguro_layout_edit_esc.addRow("Límite por siniestro:", seguro_lim_ocurr_spin_edit_esc)
                
                seguro_lim_spin_edit_esc = NoScrollSpinBox()
                seguro_lim_spin_edit_esc.setRange(0, 999999999)
                seguro_lim_spin_edit_esc.setValue(factor_actual.get('seguro_limite', 1000000))
                seguro_lim_spin_edit_esc.setPrefix("$ ")
                seguro_lim_spin_edit_esc.setToolTip("Máximo agregado anual que paga el seguro (0 = sin límite)")
                seguro_layout_edit_esc.addRow("Límite agregado:", seguro_lim_spin_edit_esc)
                
                seguro_help_edit_esc = QtWidgets.QLabel(
                    "💡 <b>Por ocurrencia:</b> Deducible/límite por siniestro.<br>"
                    "<b>Agregado:</b> Deducible/límite al total anual."
                )
                seguro_help_edit_esc.setWordWrap(True)
                seguro_help_edit_esc.setStyleSheet("color: #666; font-size: 9pt; padding: 3px;")
                seguro_layout_edit_esc.addRow(seguro_help_edit_esc)
                
                # Visibilidad inicial
                porcentual_frame_edit_esc.setVisible(tipo_sev_actual_esc != 'seguro')
                seguro_frame_edit_esc.setVisible(tipo_sev_actual_esc == 'seguro')
                sev_container_layout_edit_esc.addWidget(seguro_frame_edit_esc)
                
                def toggle_tipo_sev_edit_esc():
                    porcentual_frame_edit_esc.setVisible(tipo_sev_porcentual_edit_esc.isChecked())
                    seguro_frame_edit_esc.setVisible(tipo_sev_seguro_edit_esc.isChecked())
                
                tipo_sev_porcentual_edit_esc.toggled.connect(toggle_tipo_sev_edit_esc)
                estatico_form.addRow(sev_container_edit_esc)
                afecta_sev_check.toggled.connect(sev_container_edit_esc.setEnabled)
                
                factor_layout.addWidget(estatico_frame)
                
                # Frame Estocástico
                estocastico_frame = QtWidgets.QGroupBox("Configuración Estocástica")
                estocastico_form = QtWidgets.QFormLayout(estocastico_frame)
                
                confiabilidad_spin = NoScrollSpinBox()
                confiabilidad_spin.setRange(0, 100)
                confiabilidad_spin.setValue(factor_actual.get('confiabilidad', 70))
                confiabilidad_spin.setSuffix("%")
                estocastico_form.addRow("Confiabilidad:", confiabilidad_spin)
                
                estocastico_form.addRow(QtWidgets.QLabel("<b>Si funciona:</b>"))
                red_efe_freq = NoScrollSpinBox()
                red_efe_freq.setRange(-100, 99)
                red_efe_freq.setValue(factor_actual.get('reduccion_efectiva', 80))
                red_efe_freq.setSuffix("%")
                estocastico_form.addRow("   Red. frecuencia:", red_efe_freq)
                red_efe_sev = NoScrollSpinBox()
                red_efe_sev.setRange(-100, 99)
                red_efe_sev.setValue(factor_actual.get('reduccion_severidad_efectiva', 50))
                red_efe_sev.setSuffix("%")
                estocastico_form.addRow("   Red. severidad:", red_efe_sev)
                
                estocastico_form.addRow(QtWidgets.QLabel("<b>Si falla:</b>"))
                red_fal_freq = NoScrollSpinBox()
                red_fal_freq.setRange(-100, 99)
                red_fal_freq.setValue(factor_actual.get('reduccion_fallo', 10))
                red_fal_freq.setSuffix("%")
                estocastico_form.addRow("   Red. frecuencia:", red_fal_freq)
                red_fal_sev = NoScrollSpinBox()
                red_fal_sev.setRange(-100, 99)
                red_fal_sev.setValue(factor_actual.get('reduccion_severidad_fallo', 5))
                red_fal_sev.setSuffix("%")
                estocastico_form.addRow("   Red. severidad:", red_fal_sev)
                
                factor_layout.addWidget(estocastico_frame)
                
                # Agregar stretch para compactar elementos arriba
                factor_layout.addStretch(1)
                
                def toggle_tipo_frames():
                    estatico_frame.setVisible(tipo_estatico_radio.isChecked())
                    estocastico_frame.setVisible(tipo_estocastico_radio.isChecked())
                    factor_dialog.adjustSize()
                
                tipo_estatico_radio.toggled.connect(toggle_tipo_frames)
                toggle_tipo_frames()
                
                # Conectar scroll area con contenido
                scroll_area_factor_edit.setWidget(scroll_content_factor_edit)
                main_factor_edit_layout.addWidget(scroll_area_factor_edit)
                
                # Botones (fuera del scroll para que siempre sean visibles)
                buttons_f = QtWidgets.QDialogButtonBox(
                    QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
                )
                def validar_y_aceptar_edicion_factor():
                    nombre = nombre_factor_var.text().strip()
                    if not nombre:
                        QtWidgets.QMessageBox.warning(factor_dialog, "Advertencia", "El nombre no puede estar vacío.")
                        return
                    if tipo_estatico_radio.isChecked():
                        if not afecta_freq_check.isChecked() and not afecta_sev_check.isChecked():
                            QtWidgets.QMessageBox.warning(factor_dialog, "Advertencia", 
                                "Debe seleccionar al menos frecuencia o severidad.")
                            return
                    factor_dialog.accept()

                buttons_f.accepted.connect(validar_y_aceptar_edicion_factor)
                buttons_f.rejected.connect(factor_dialog.reject)
                main_factor_edit_layout.addWidget(buttons_f)
                
                if factor_dialog.exec_() == QtWidgets.QDialog.Accepted:
                    nombre = nombre_factor_var.text().strip()
                    
                    # Preservar estado activo
                    activo_actual = factor_actual.get('activo', True)
                    
                    if tipo_estatico_radio.isChecked():
                        
                        # Determinar tipo de severidad
                        es_seguro_edit_esc = afecta_sev_check.isChecked() and tipo_sev_seguro_edit_esc.isChecked()
                        
                        factores_escenario[row] = {
                            'nombre': nombre,
                            'tipo_modelo': 'estatico',
                            'afecta_frecuencia': afecta_freq_check.isChecked(),
                            'impacto_porcentual': -impacto_freq_spin.value() if afecta_freq_check.isChecked() else 0,
                            'afecta_severidad': afecta_sev_check.isChecked(),
                            'tipo_severidad': 'seguro' if es_seguro_edit_esc else 'porcentual',
                            'impacto_severidad_pct': -impacto_sev_spin.value() if (afecta_sev_check.isChecked() and not es_seguro_edit_esc) else 0,
                            'activo': activo_actual,
                            'confiabilidad': 100,
                            'reduccion_efectiva': impacto_freq_spin.value() if afecta_freq_check.isChecked() else 0,
                            'reduccion_fallo': 0,
                            'reduccion_severidad_efectiva': impacto_sev_spin.value() if (afecta_sev_check.isChecked() and not es_seguro_edit_esc) else 0,
                            'reduccion_severidad_fallo': 0,
                            # Campos de seguro
                            'seguro_deducible': seguro_ded_spin_edit_esc.value() if es_seguro_edit_esc else 0,
                            'seguro_cobertura_pct': seguro_cob_spin_edit_esc.value() if es_seguro_edit_esc else 100,
                            'seguro_limite': seguro_lim_spin_edit_esc.value() if es_seguro_edit_esc else 0,
                            'seguro_tipo_deducible': 'por_ocurrencia' if (es_seguro_edit_esc and tipo_ded_ocurrencia_edit_esc.isChecked()) else 'agregado',
                            'seguro_limite_ocurrencia': seguro_lim_ocurr_spin_edit_esc.value() if es_seguro_edit_esc else 0
                        }
                    else:
                        factores_escenario[row] = {
                            'nombre': nombre,
                            'tipo_modelo': 'estocastico',
                            'confiabilidad': confiabilidad_spin.value(),
                            'reduccion_efectiva': red_efe_freq.value(),
                            'reduccion_fallo': red_fal_freq.value(),
                            'reduccion_severidad_efectiva': red_efe_sev.value(),
                            'reduccion_severidad_fallo': red_fal_sev.value(),
                            'activo': activo_actual,
                            'impacto_porcentual': -red_efe_freq.value(),
                            'afecta_frecuencia': True,
                            'afecta_severidad': (red_efe_sev.value() != 0 or red_fal_sev.value() != 0),
                            'impacto_severidad_pct': 0
                        }
                    
                    actualizar_tabla_factores_escenario()
            
            # Función para eliminar factor seleccionado
            def eliminar_factor_seleccionado():
                row = factores_table.currentRow()
                if row >= 0:
                    eliminar_factor_escenario(row)
                else:
                    QtWidgets.QMessageBox.information(evento_dialog, "Info", "Seleccione un factor para eliminar.")
            
            # Conectar eventos
            btn_agregar_factor.clicked.connect(agregar_factor_escenario)
            btn_eliminar_factor.clicked.connect(eliminar_factor_seleccionado)
            factores_table.cellClicked.connect(on_factores_table_clicked)
            factores_table.cellDoubleClicked.connect(
                lambda row, col: editar_factor_escenario(row) if col != 0 else None
            )
            
            # Llenar tabla inicial
            actualizar_tabla_factores_escenario()
            
            evento_layout.addWidget(factores_group)
            # ====================================================================
            # FIN SECCIÓN DE FACTORES/CONTROLES
            # ====================================================================

            # Conectar scroll area con contenido
            scroll_area_evento.setWidget(scroll_content_evento)
            main_evento_layout.addWidget(scroll_area_evento)

            # Botones (fuera del scroll para que siempre sean visibles)
            evento_buttons = QtWidgets.QDialogButtonBox()
            evento_buttons.setStandardButtons(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
            # Ajustar tamaño de botones
            save_btn = evento_buttons.button(QtWidgets.QDialogButtonBox.Save)
            save_btn.setFixedHeight(35)
            cancel_btn = evento_buttons.button(QtWidgets.QDialogButtonBox.Cancel)
            cancel_btn.setFixedHeight(35)
            main_evento_layout.addWidget(evento_buttons)

            evento_buttons.accepted.connect(lambda: guardar_cambios())
            evento_buttons.rejected.connect(evento_dialog.reject)

            def guardar_cambios():
                try:
                    # Acumular cambios en dict temporal para no mutar evento hasta que todo valide
                    cambios = {}

                    # Validar y preparar parámetros de frecuencia
                    if evento['freq_opcion'] == 1:  # Poisson
                        if not tasa_var.text().strip():
                            raise ValueError("La tasa media (λ) no puede estar vacía.")
                        tasa = float(tasa_var.text())
                        if tasa <= 0:
                            raise ValueError("La tasa media (λ) debe ser mayor que cero.")
                        cambios['tasa'] = tasa
                    elif evento['freq_opcion'] == 2:  # Binomial
                        if not n_var.text().strip():
                            raise ValueError("El número de eventos (n) no puede estar vacío.")
                        if not p_var.text().strip():
                            raise ValueError("La probabilidad de éxito (p) no puede estar vacía.")
                        n = int(n_var.text())
                        p = float(p_var.text())
                        if n <= 0:
                            raise ValueError("El número de eventos (n) debe ser mayor que cero.")
                        if not 0 <= p <= 1:
                            raise ValueError("La probabilidad de éxito (p) debe estar entre 0 y 1.")
                        cambios['num_eventos'] = n
                        cambios['prob_exito'] = p
                    elif evento['freq_opcion'] == 3:  # Bernoulli
                        if not p_var.text().strip():
                            raise ValueError("La probabilidad de éxito (p) no puede estar vacía.")
                        p = float(p_var.text())
                        if not 0 <= p <= 1:
                            raise ValueError("La probabilidad de éxito (p) debe estar entre 0 y 1.")
                        cambios['prob_exito'] = p
                    elif evento['freq_opcion'] == 4:  # Poisson-Gamma
                        # Verificar campos vacíos
                        if not pg_minimo_var.text().strip():
                            raise ValueError("El valor mínimo de ocurrencia no puede estar vacío.")
                        if not pg_mas_probable_var.text().strip():
                            raise ValueError("El valor más probable de ocurrencia no puede estar vacío.")
                        if not pg_maximo_var.text().strip():
                            raise ValueError("El valor máximo de ocurrencia no puede estar vacío.")
                        if not pg_confianza_var.text().strip():
                            raise ValueError("La confianza asociada al rango no puede estar vacía.")
                        # Obtener los valores de min/mode/max para Poisson-Gamma
                        pg_minimo = float(pg_minimo_var.text())
                        pg_mas_probable = float(pg_mas_probable_var.text())
                        pg_maximo = float(pg_maximo_var.text())
                        pg_confianza = float(pg_confianza_var.text()) / 100  # Convertir de porcentaje a proporción
                        
                        # Validaciones
                        if pg_minimo <= 0:
                            raise ValueError("El valor mínimo para Poisson-Gamma debe ser mayor que cero.")
                        if not (pg_minimo < pg_mas_probable < pg_maximo):
                            raise ValueError("Debe cumplirse: mínimo < más probable < máximo para Poisson-Gamma")
                        if not (0 < pg_confianza < 1):
                            raise ValueError("La confianza debe estar entre 0 y 100%")
                        
                        # Calcular alpha y beta para Poisson-Gamma
                        alpha, beta = obtener_parametros_gamma_para_poisson(pg_minimo, pg_mas_probable, pg_maximo, pg_confianza)
                        
                        cambios['pg_minimo'] = pg_minimo
                        cambios['pg_mas_probable'] = pg_mas_probable
                        cambios['pg_maximo'] = pg_maximo
                        cambios['pg_confianza'] = pg_confianza * 100  # Guardar como porcentaje
                        cambios['pg_alpha'] = alpha
                        cambios['pg_beta'] = beta
                        
                    elif evento['freq_opcion'] == 5:  # Beta
                        # Verificar campos vacíos
                        if not beta_minimo_var.text().strip():
                            raise ValueError("La probabilidad mínima no puede estar vacía.")
                        if not beta_mas_probable_var.text().strip():
                            raise ValueError("La probabilidad más probable no puede estar vacía.")
                        if not beta_maximo_var.text().strip():
                            raise ValueError("La probabilidad máxima no puede estar vacía.")
                        if not beta_confianza_var.text().strip():
                            raise ValueError("La confianza asociada al rango no puede estar vacía.")
                        # Obtener los valores de min/mode/max para Beta
                        beta_minimo = float(beta_minimo_var.text()) / 100  # Convertir de porcentaje a proporción
                        beta_mas_probable = float(beta_mas_probable_var.text()) / 100
                        beta_maximo = float(beta_maximo_var.text()) / 100
                        beta_confianza = float(beta_confianza_var.text()) / 100
                        
                        # Validaciones
                        if not (0 <= beta_minimo < beta_mas_probable < beta_maximo <= 1):
                            raise ValueError("Debe cumplirse: 0 ≤ mínimo < más probable < máximo ≤ 1 para Beta")
                        if not (0 < beta_confianza < 1):
                            raise ValueError("La confianza debe estar entre 0 y 100%")
                        
                        # Calcular alpha y beta para la distribución Beta
                        alpha, beta = obtener_parametros_beta_frecuencia(beta_minimo, beta_mas_probable, beta_maximo, beta_confianza)
                        
                        cambios['beta_minimo'] = beta_minimo * 100  # Guardar como porcentaje
                        cambios['beta_mas_probable'] = beta_mas_probable * 100
                        cambios['beta_maximo'] = beta_maximo * 100
                        cambios['beta_confianza'] = beta_confianza * 100
                        cambios['beta_alpha'] = alpha
                        cambios['beta_beta'] = beta

                    # Helper para leer de cambios con fallback a evento
                    def _get(key, default=None):
                        return cambios.get(key, evento.get(key, default))

                    # Generar distribución de frecuencia con los valores validados
                    cambios['dist_frecuencia'] = generar_distribucion_frecuencia(
                        evento['freq_opcion'],
                        tasa=_get('tasa'),
                        num_eventos_posibles=_get('num_eventos'),
                        probabilidad_exito=_get('prob_exito'),
                        poisson_gamma_params=(_get('pg_alpha'), _get('pg_beta')) if evento['freq_opcion'] == 4 else None,
                        beta_params=(_get('beta_alpha'), _get('beta_beta')) if evento['freq_opcion'] == 5 else None
                    )

                    # Validar y preparar parámetros de severidad
                    is_direct_sev_method = (sev_input_method_combo.currentIndex() == 1)
                    if not is_direct_sev_method:
                        txt_min = (sev_min_var.text() or "").strip()
                        txt_max = (sev_max_var.text() or "").strip()
                        if not txt_min:
                            raise ValueError("El valor mínimo de severidad no puede estar vacío.")
                        if not txt_max:
                            raise ValueError("El valor máximo de severidad no puede estar vacío.")
                        sev_minimo = float(txt_min)
                        sev_maximo = float(txt_max)
                        if evento['sev_opcion'] != 5:  # Si no es Uniforme
                            txt_mode = (sev_mas_probable_var.text() or "").strip()
                            if not txt_mode:
                                raise ValueError("El valor más probable de severidad no puede estar vacío.")
                            sev_mas_probable = float(txt_mode)
                        else:
                            sev_mas_probable = None

                        cambios['sev_minimo'] = sev_minimo
                        cambios['sev_mas_probable'] = sev_mas_probable
                        cambios['sev_maximo'] = sev_maximo

                    # Persistir método y parámetros directos de severidad si corresponde
                    if 'sev_opcion' in evento and evento['sev_opcion'] in (1, 2, 4) and sev_input_method_combo.currentIndex() == 1:
                        cambios['sev_input_method'] = 'direct'
                        params_direct = {}
                        if evento['sev_opcion'] == 1:
                            # Normal: mean/std
                            if not sev_norm_mean_var.text().strip():
                                raise ValueError("'mean' no puede estar vacío para Normal.")
                            if not sev_norm_std_var.text().strip():
                                raise ValueError("'std' no puede estar vacío para Normal.")
                            try:
                                mean = float(sev_norm_mean_var.text())
                                std = float(sev_norm_std_var.text())
                            except (ValueError, TypeError):
                                raise ValueError("'mean' y 'std' deben ser numéricos para Normal.")
                            if std <= 0:
                                raise ValueError("Desviación estándar (std) debe ser > 0 para Normal.")
                            params_direct = {'mean': mean, 'std': std}
                        elif evento['sev_opcion'] == 2:
                            # LogNormal: tres modos
                            mode = sev_ln_param_mode_combo.currentIndex()
                            try:
                                loc = float(sev_ln_loc_var.text() if sev_ln_loc_var.text() else '0')
                            except (ValueError, TypeError):
                                raise ValueError("loc debe ser numérico para LogNormal.")
                            if mode == 0:
                                if not sev_ln_s_var.text().strip():
                                    raise ValueError("'s' no puede estar vacío para LogNormal.")
                                if not sev_ln_scale_var.text().strip():
                                    raise ValueError("'scale' no puede estar vacío para LogNormal.")
                                try:
                                    s = float(sev_ln_s_var.text())
                                    scale = float(sev_ln_scale_var.text())
                                except (ValueError, TypeError):
                                    raise ValueError("'s' y 'scale' deben ser numéricos para LogNormal.")
                                if s <= 0:
                                    raise ValueError("Shape (s) debe ser > 0 para LogNormal.")
                                if scale <= 0:
                                    raise ValueError("Scale debe ser > 0 para LogNormal.")
                                params_direct = {'s': s, 'scale': scale, 'loc': loc}
                            elif mode == 1:
                                if not sev_ln_mean_var.text().strip():
                                    raise ValueError("'mean' no puede estar vacío para LogNormal.")
                                if not sev_ln_std_var.text().strip():
                                    raise ValueError("'std' no puede estar vacío para LogNormal.")
                                try:
                                    mean = float(sev_ln_mean_var.text())
                                    std = float(sev_ln_std_var.text())
                                except (ValueError, TypeError):
                                    raise ValueError("'mean' y 'std' deben ser numéricos para LogNormal.")
                                if mean <= 0:
                                    raise ValueError("mean debe ser > 0 para LogNormal.")
                                if std <= 0:
                                    raise ValueError("std debe ser > 0 para LogNormal.")
                                params_direct = {'mean': mean, 'std': std, 'loc': loc}
                            else:
                                if not sev_ln_mu_var.text().strip():
                                    raise ValueError("'mu' no puede estar vacío para LogNormal.")
                                if not sev_ln_sigma_var.text().strip():
                                    raise ValueError("'sigma' no puede estar vacío para LogNormal.")
                                try:
                                    mu = float(sev_ln_mu_var.text())
                                    sigma = float(sev_ln_sigma_var.text())
                                except (ValueError, TypeError):
                                    raise ValueError("'mu' y 'sigma' deben ser numéricos para LogNormal.")
                                if sigma <= 0:
                                    raise ValueError("sigma debe ser > 0 para LogNormal.")
                                params_direct = {'mu': mu, 'sigma': sigma, 'loc': loc}
                        elif evento['sev_opcion'] == 4:
                            # GPD: c, scale, loc
                            if not sev_gpd_c_var.text().strip():
                                raise ValueError("'c' (shape) no puede estar vacío para GPD.")
                            if not sev_gpd_scale_var.text().strip():
                                raise ValueError("'scale' no puede estar vacío para GPD.")
                            if not sev_gpd_loc_var.text().strip():
                                raise ValueError("'loc' no puede estar vacío para GPD.")
                            try:
                                c = float(sev_gpd_c_var.text())
                                scale = float(sev_gpd_scale_var.text())
                                loc = float(sev_gpd_loc_var.text())
                            except (ValueError, TypeError):
                                raise ValueError("Los parámetros de GPD deben ser numéricos.")
                            if scale <= 0:
                                raise ValueError("Scale (beta) debe ser positivo para GPD.")
                            params_direct = {'c': c, 'scale': scale, 'loc': loc}
                        cambios['sev_params_direct'] = params_direct
                    else:
                        cambios['sev_input_method'] = 'min_mode_max'
                        cambios['sev_params_direct'] = {}

                    # Generar distribución de severidad con los valores validados
                    cambios['dist_severidad'] = generar_distribucion_severidad(
                        evento['sev_opcion'],
                        _get('sev_minimo'),
                        _get('sev_mas_probable'),
                        _get('sev_maximo'),
                        input_method=_get('sev_input_method', 'min_mode_max'),
                        params_direct=_get('sev_params_direct')
                    )

                    # Preparar factores/controles editados
                    cambios['factores_ajuste'] = copy.deepcopy(factores_escenario)

                    # Preparar configuración de escalamiento severidad-frecuencia
                    if sev_freq_config_esc and isinstance(sev_freq_config_esc, dict):
                        for key, value in sev_freq_config_esc.items():
                            if key.startswith('sev_freq_'):
                                cambios[key] = value

                    # Validar límites superiores opcionales
                    sev_lim_text = sev_limite_esc_var.text().strip()
                    if sev_lim_text:
                        try:
                            val = float(sev_lim_text)
                        except (ValueError, TypeError):
                            raise ValueError("El límite superior de severidad debe ser un número válido.")
                        if val <= 0:
                            raise ValueError("El límite superior de severidad debe ser mayor que cero.")
                        cambios['sev_limite_superior'] = val
                    else:
                        cambios['sev_limite_superior'] = None
                    
                    freq_lim_text = freq_limite_esc_var.text().strip()
                    if freq_lim_text:
                        try:
                            val = int(float(freq_lim_text))
                        except (ValueError, TypeError):
                            raise ValueError("El máximo de ocurrencias por año debe ser un número válido.")
                        if val <= 0:
                            raise ValueError("El máximo de ocurrencias por año debe ser mayor que cero.")
                        cambios['freq_limite_superior'] = val
                    else:
                        cambios['freq_limite_superior'] = None

                    # Todas las validaciones pasaron: aplicar cambios al evento
                    evento.update(cambios)
                    evento_dialog.accept()
                except ValueError as ve:
                    QtWidgets.QMessageBox.critical(evento_dialog, "Error", str(ve))
                except Exception as e:
                    QtWidgets.QMessageBox.critical(evento_dialog, "Error", f"No se pudo guardar los cambios: {e}")

            evento_dialog.exec_()

        # Wrapper para capturar errores al abrir el editor y mostrarlos al usuario
        def editar_parametros_evento_safe(row, column):
            try:
                editar_parametros_evento(row, column)
            except Exception as e:
                try:
                    import traceback; traceback.print_exc()
                except Exception:
                    pass
                QtWidgets.QMessageBox.critical(dialog, "Error", f"No se pudo abrir el editor de parámetros:\n{e}")

        # Conectar doble clic en la tabla para editar parámetros específicos
        def on_evento_double_click(row, column):
            editar_parametros_evento_safe(row, column)
            # Actualizar tabla después de editar (para reflejar cambios en factores)
            actualizar_tabla_eventos_escenario()
        
        eventos_table.cellDoubleClicked.connect(on_evento_double_click)

        # Conectar scroll area con contenido
        scroll_area_scenario.setWidget(scroll_content_scenario)
        main_dialog_layout.addWidget(scroll_area_scenario)

        # Botones del diálogo principal para guardar o cancelar el escenario (fuera del scroll)
        buttons = QtWidgets.QDialogButtonBox()
        buttons.setStandardButtons(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        # Asegurar que los botones estén en español neutro y ajustar tamaño
        guardar_btn = buttons.button(QtWidgets.QDialogButtonBox.Save)
        guardar_btn.setText("Guardar")
        guardar_btn.setFixedHeight(35)
        cancelar_btn = buttons.button(QtWidgets.QDialogButtonBox.Cancel)
        cancelar_btn.setText("Cancelar")
        cancelar_btn.setFixedHeight(35)
        main_dialog_layout.addWidget(buttons)

        buttons.accepted.connect(lambda: self.guardar_scenario(dialog, new, row, nombre_var, descripcion_var))
        buttons.rejected.connect(dialog.reject)

        # Mostrar el diálogo
        dialog.exec_()

    def guardar_scenario(self, dialog, new, row, nombre_var, descripcion_var):
        try:
            nombre_scenario = nombre_var.text().strip()
            descripcion_scenario = descripcion_var.text().strip()

            if not nombre_scenario:
                raise ValueError("El nombre del escenario no puede estar vacío.")

            # Crear instancia del escenario
            old = self.scenarios[row] if (not new and 0 <= row < len(self.scenarios)) else None
            scenario = Scenario(nombre_scenario, descripcion_scenario)
            # Guardar una copia profunda de los eventos editados para evitar aliasing
            scenario.eventos_riesgo = copy.deepcopy(self.eventos_scenario)

            # Guardar o actualizar el escenario
            if new:
                self.scenarios.append(scenario)
                row_position = self.scenarios_table.rowCount()
                self.scenarios_table.insertRow(row_position)
                nombre_item = QtWidgets.QTableWidgetItem(nombre_scenario)
                nombre_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                desc_item = QtWidgets.QTableWidgetItem(descripcion_scenario)
                desc_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                self.scenarios_table.setItem(row_position, 0, nombre_item)
                self.scenarios_table.setItem(row_position, 1, desc_item)
                self.actualizar_vista_escenarios()  # Actualizar vista
            else:
                self.scenarios[row] = scenario
                nombre_item = QtWidgets.QTableWidgetItem(nombre_scenario)
                nombre_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                desc_item = QtWidgets.QTableWidgetItem(descripcion_scenario)
                desc_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                self.scenarios_table.setItem(row, 0, nombre_item)
                self.scenarios_table.setItem(row, 1, desc_item)
                # Mantener referencia coherente si este escenario estaba seleccionado
                if old is not None and self.current_scenario is old:
                    self.current_scenario = scenario
                    try:
                        self.selected_scenario_label.setText(self.current_scenario.nombre)
                    except Exception:
                        pass

            dialog.accept()

        except ValueError as ve:
            QtWidgets.QMessageBox.critical(self, "Error", str(ve))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo guardar el escenario: {e}")

    def eliminar_escenario(self):
        """Alias para eliminar_scenario para mantener consistencia en la nomenclatura."""
        return self.eliminar_scenario()
    
    def duplicar_escenario(self):
        """Alias para duplicar_scenario para mantener consistencia en la nomenclatura."""
        return self.duplicar_scenario()
        
    def eliminar_scenario(self):
        selected_items = self.scenarios_table.selectionModel().selectedRows()
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "Advertencia", "Seleccione al menos un escenario para eliminar.")
            return

        # Confirmar eliminación múltiple
        respuesta = QtWidgets.QMessageBox.question(
            self,
            "Eliminar Escenario(s)",
            f"¿Estás seguro de que deseas eliminar {len(selected_items)} escenario(s)?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if respuesta == QtWidgets.QMessageBox.Yes:
            # Ordenar los índices de fila en orden descendente para evitar problemas al eliminar filas
            rows = sorted([index.row() for index in selected_items], reverse=True)
            for row in rows:
                scenario_to_delete = self.scenarios[row]
                # Si el escenario a eliminar es el escenario seleccionado, deseleccionarlo
                if self.current_scenario == scenario_to_delete:
                    self.current_scenario = None
                    self.selected_scenario_label.setText("Ninguno")
                del self.scenarios[row]
                self.scenarios_table.removeRow(row)
            self.actualizar_vista_escenarios()  # Actualizar vista
            self.statusBar().showMessage("Escenario(s) eliminado(s) exitosamente", 3000)

    def duplicar_scenario(self):
        selected_items = self.scenarios_table.selectionModel().selectedRows()
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "Advertencia", "Seleccione un escenario para duplicar.")
            return
        if len(selected_items) > 1:
            QtWidgets.QMessageBox.warning(self, "Advertencia", "Seleccione solo un escenario para duplicar.")
            return
        row = selected_items[0].row()
        scenario_original = self.scenarios[row]

        # Crear una copia profunda del escenario
        import copy
        escenario_nuevo = copy.deepcopy(scenario_original)

        # Modificar el nombre y descripción del nuevo escenario
        escenario_nuevo.nombre = escenario_nuevo.nombre + " (Copia)"
        if escenario_nuevo.descripcion:
            escenario_nuevo.descripcion = escenario_nuevo.descripcion + " (Duplicado)"
        else:
            escenario_nuevo.descripcion = "Duplicado del escenario original"

        # Generar nuevos IDs para los eventos dentro del escenario duplicado
        id_original_a_nuevo = {}
        for evento in escenario_nuevo.eventos_riesgo:
            nuevo_id = str(uuid.uuid4())
            id_original_a_nuevo[evento['id']] = nuevo_id
            evento['id'] = nuevo_id

        # Actualizar las dependencias de los eventos duplicados
        for evento in escenario_nuevo.eventos_riesgo:
            # Manejar la nueva estructura de vínculos
            if 'vinculos' in evento:
                vinculos_actualizados = []
                for vinculo in evento.get('vinculos', []):
                    padre_id = vinculo['id_padre']
                    tipo = vinculo['tipo']
                    prob = vinculo.get('probabilidad', 100)
                    fsev = vinculo.get('factor_severidad', 1.0)
                    umbral = vinculo.get('umbral_severidad', 0)
                    # Si el evento padre fue duplicado, usamos el nuevo ID
                    if padre_id in id_original_a_nuevo:
                        vinculos_actualizados.append({
                            'id_padre': id_original_a_nuevo[padre_id],
                            'tipo': tipo,
                            'probabilidad': prob,
                            'factor_severidad': fsev,
                            'umbral_severidad': umbral
                        })
                    else:
                        # Si no, mantenemos el ID original
                        vinculos_actualizados.append({
                            'id_padre': padre_id,
                            'tipo': tipo,
                            'probabilidad': prob,
                            'factor_severidad': fsev,
                            'umbral_severidad': umbral
                        })
                evento['vinculos'] = vinculos_actualizados

            # Compatibilidad con formato antiguo
            elif 'eventos_padres' in evento:
                eventos_padres_originales = evento.get('eventos_padres', [])
                eventos_padres_actualizados = []
                for padre_id in eventos_padres_originales:
                    # Si el evento padre fue duplicado, usamos el nuevo ID
                    if padre_id in id_original_a_nuevo:
                        eventos_padres_actualizados.append(id_original_a_nuevo[padre_id])
                    else:
                        # Si no, mantenemos el ID original
                        eventos_padres_actualizados.append(padre_id)
                evento['eventos_padres'] = eventos_padres_actualizados

        # Verificar si el escenario duplicado introduce ciclos
        if self.tiene_ciclo(escenario_nuevo.eventos_riesgo):
            QtWidgets.QMessageBox.critical(self, "Error", "La duplicación de este escenario genera una dependencia cíclica.")
            return

        # Agregar el escenario duplicado a la lista y a la tabla
        self.scenarios.append(escenario_nuevo)
        row_position = self.scenarios_table.rowCount()
        self.scenarios_table.insertRow(row_position)
        nombre_item = QtWidgets.QTableWidgetItem(escenario_nuevo.nombre)
        nombre_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        desc_item = QtWidgets.QTableWidgetItem(escenario_nuevo.descripcion)
        desc_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        self.scenarios_table.setItem(row_position, 0, nombre_item)
        self.scenarios_table.setItem(row_position, 1, desc_item)
        self.actualizar_vista_escenarios()  # Actualizar vista

        self.statusBar().showMessage("Escenario duplicado exitosamente", 3000)
        
    def select_scenario(self, row, column):
        """Selecciona o deselecciona un escenario para utilizar en la simulación.
        Si el escenario clickeado ya está seleccionado, lo deselecciona (toggle).
        """
        if 0 <= row < len(self.scenarios):
            scenario_clicked = self.scenarios[row]
            
            # Bloquear actualizaciones de la ventana para evitar desajuste de márgenes
            self.setUpdatesEnabled(False)
            
            # Toggle: si el escenario clickeado ya es el activo, deseleccionarlo
            if self.current_scenario == scenario_clicked:
                self.current_scenario = None
                self.selected_scenario_label.setText("Ninguno")
                self.actualizar_vista_escenarios()
                self.statusBar().showMessage("Escenario deseleccionado", 3000)
            else:
                self.current_scenario = scenario_clicked
                self.selected_scenario_label.setText(self.current_scenario.nombre)
                self.actualizar_vista_escenarios()  # Resaltar escenario activo
                self.statusBar().showMessage(f"Escenario '{self.current_scenario.nombre}' seleccionado", 3000)
            
            # Restaurar actualizaciones de la ventana
            self.setUpdatesEnabled(True)
        else:
            QtWidgets.QMessageBox.warning(self, "Advertencia", "No se pudo seleccionar el escenario.")
    
    def seleccionar_scenario(self, row, column):
        """Método antiguo para seleccionar escenario (mantener por compatibilidad)."""
        # Redirigir al nuevo método para garantizar consistencia
        self.select_scenario(row, column)
        
    def ejecutar_simulacion_escenario(self):
        """Ejecuta la simulación con el escenario seleccionado.
        
        Sustituye temporalmente self.eventos_riesgo con los eventos del escenario,
        ejecuta la simulación y luego restaura los eventos originales.
        """
        if self.current_scenario is None:
            QtWidgets.QMessageBox.warning(self, "Advertencia", "Seleccione un escenario para simular.")
            return
        
        # Actualizar el número de simulaciones con el valor ingresado en la pestaña "Escenarios"
        self.num_simulaciones_var.setText(self.num_simulaciones_var_escenarios.text())
        
        # Sustituir temporalmente los eventos con los del escenario
        eventos_originales = self.eventos_riesgo
        try:
            self.eventos_riesgo = self.current_scenario.eventos_riesgo
            self.ejecutar_simulacion()
        finally:
            # Restaurar siempre los eventos originales de la pestaña Simulación
            self.eventos_riesgo = eventos_originales

    def generar_figuras(self, perdidas_totales, frecuencias_totales, perdidas_por_evento, frecuencias_por_evento, eventos_riesgo):
        """Genera las figuras de los gráficos para el reporte PDF."""
        figuras = []

        sns.set(style="whitegrid")

        # Gráfico 1: Distribución de pérdidas agregadas
        fig1 = Figure()
        ax1 = fig1.add_subplot(111)
        sns.histplot(perdidas_totales, bins=50, kde=True, color='#1f77b4', edgecolor='black', ax=ax1)
        media = np.mean(perdidas_totales)
        var_90 = np.percentile(perdidas_totales, 90)
        ax1.axvline(x=media, color='red', linestyle='-', linewidth=2, label=f'Media: {currency_format(media)}')
        ax1.axvline(x=var_90, color='green', linestyle='--', linewidth=2, label=f'P90: {currency_format(var_90)}')
        ax1.set_title('Distribución de Pérdidas Agregadas')
        ax1.set_xlabel('Pérdida Total')
        ax1.set_ylabel('Frecuencia')
        ax1.legend(fontsize=8)
        ax1.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
        figuras.append(fig1)

        # Gráfico 2: Distribución de pérdidas agregadas (sin ceros)
        perdidas_totales_sin_cero = perdidas_totales[perdidas_totales != 0]
        if len(perdidas_totales_sin_cero) > 0:
            fig2 = Figure()
            ax2 = fig2.add_subplot(111)
            sns.histplot(perdidas_totales_sin_cero, bins=50, kde=True, color='#1f77b4', edgecolor='black', ax=ax2)
            media_sin_cero = np.mean(perdidas_totales_sin_cero)
            var_90_sin_cero = np.percentile(perdidas_totales_sin_cero, 90)
            ax2.axvline(x=media_sin_cero, color='red', linestyle='-', linewidth=2, label=f'Media: {currency_format(media_sin_cero)}')
            ax2.axvline(x=var_90_sin_cero, color='green', linestyle='--', linewidth=2, label=f'P90: {currency_format(var_90_sin_cero)}')
            ax2.set_title('Distribución de Pérdidas Agregadas (Sin eventos en cero)')
            ax2.set_xlabel('Pérdida Total')
            ax2.set_ylabel('Frecuencia')
            ax2.legend(fontsize=8)
            ax2.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
            figuras.append(fig2)

        # Gráfico 3: Curva de Excedencia
        fig3 = Figure()
        ax3 = fig3.add_subplot(111)
        sorted_losses = np.sort(perdidas_totales)
        exceedance_prob = 1.0 - np.arange(1, len(sorted_losses) + 1) / len(sorted_losses)
        ax3.plot(sorted_losses, exceedance_prob, color='#ff7f0e', linewidth=2)
        ax3.set_title('Curva de Excedencia de Pérdidas Agregadas')
        ax3.set_xlabel('Pérdida Total')
        ax3.set_ylabel('Probabilidad de Excedencia')
        ax3.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
        ax3.yaxis.set_major_formatter(FuncFormatter(percentage_formatter))
        figuras.append(fig3)


        # Gráfico 4: Histograma de Frecuencia de Eventos
        if frecuencias_totales.max() > 0:
            fig4 = Figure()
            canvas4 = FigureCanvas(fig4)
            ax4 = fig4.add_subplot(111)
            bins = range(0, int(frecuencias_totales.max()) + 2)
            sns.histplot(frecuencias_totales, bins=bins, color='#1f77b4', edgecolor='black', ax=ax4)
            ax4.set_title('Histograma de Frecuencia de Eventos')
            ax4.set_xlabel('Número de Eventos')
            ax4.set_ylabel('Frecuencia')
            figuras.append(fig4)

        # Gráfico 5: Dispersión Frecuencia vs. Pérdidas
        if np.std(frecuencias_totales) > 0 and np.std(perdidas_totales) > 0:
            fig5 = Figure()
            canvas5 = FigureCanvas(fig5)
            ax5 = fig5.add_subplot(111)
            ax5.scatter(frecuencias_totales, perdidas_totales, alpha=0.5)
            ax5.set_title('Dispersión de Frecuencia vs. Pérdida Total')
            ax5.set_xlabel('Frecuencia Total de Eventos')
            ax5.set_ylabel('Pérdida Total')
            ax5.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
            figuras.append(fig5)

        # Gráfico 6: Comparación de Pérdidas por Evento de Riesgo
        fig6 = Figure()
        canvas6 = FigureCanvas(fig6)
        ax6 = fig6.add_subplot(111)
        datos_plot = False
        for idx, perdidas_evento in enumerate(perdidas_por_evento):
            nombre_evento = eventos_riesgo[idx]['nombre']
            if np.std(perdidas_evento) > 0:
                sns.kdeplot(perdidas_evento, label=nombre_evento, ax=ax6, bw_method='silverman')
                datos_plot = True
        if datos_plot:
            ax6.set_title('Comparación entre Eventos de Riesgo')
            ax6.set_xlabel('Pérdida')
            ax6.set_ylabel('Densidad')
            ax6.legend(fontsize=8)
            ax6.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
        figuras.append(fig6)

        # Gráfico 7: Gráfico de Tornado - Contribución de Eventos de Riesgo
        contribuciones = []
        nombres_eventos = []
        for idx, perdidas_evento in enumerate(perdidas_por_evento):
            contribucion = np.mean(perdidas_evento)
            contribuciones.append(contribucion)
            nombre_evento = eventos_riesgo[idx]['nombre']
            nombres_eventos.append(nombre_evento)

        if any(c > 0 for c in contribuciones):
            fig7 = Figure()
            canvas7 = FigureCanvas(fig7)
            ax7 = fig7.add_subplot(111)
            tornado_df = pd.DataFrame({
                'Evento de Riesgo': nombres_eventos,
                'Contribución Promedio': contribuciones
            })
            tornado_df = tornado_df[tornado_df['Contribución Promedio'] > 0]
            tornado_df.sort_values('Contribución Promedio', inplace=True, ascending=True)
            ax7.barh(tornado_df['Evento de Riesgo'], tornado_df['Contribución Promedio'], color='#1f77b4', edgecolor='black')
            ax7.set_title('Gráfico de Tornado - Contribución de Eventos de Riesgo')
            ax7.set_xlabel('Contribución Promedio a la Pérdida Media Total')
            ax7.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
            figuras.append(fig7)

        # Gráfico 8: Box Plots por Evento de Riesgo
        fig8 = Figure()
        ax8 = fig8.add_subplot(111)
        datos_perdidas = [perdidas_evento for perdidas_evento in perdidas_por_evento]
        nombres_eventos = [evento['nombre'] for evento in eventos_riesgo]

        # Crear el box plot
        ax8.boxplot(datos_perdidas, labels=nombres_eventos, vert=True, patch_artist=True)
        ax8.set_title('Distribución de Pérdidas por Evento de Riesgo')
        ax8.set_xlabel('Evento de Riesgo')
        ax8.set_ylabel('Pérdida')
        ax8.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
        ax8.set_xticklabels(nombres_eventos, rotation=45, ha='right')
        fig8.tight_layout()
        figuras.append(fig8)

        # Cálculo de perdidas_cola
        percentil_80 = np.percentile(perdidas_totales, 80)
        perdidas_cola = perdidas_totales[perdidas_totales >= percentil_80]

        # Gráfico 9: Cola de Pérdidas (Tail Risk)
        fig10 = Figure()
        ax10 = fig10.add_subplot(111)
        sns.histplot(perdidas_cola, bins=30, kde=True, color='#1f77b4', edgecolor='black', ax=ax10)
        ax10.set_title('Cola de Pérdidas (Percentil 80 al 100)')
        ax10.set_xlabel('Pérdida Total')
        ax10.set_ylabel('Frecuencia')
        ax10.xaxis.set_major_formatter(FuncFormatter(currency_formatter))

        # Añadir líneas verticales para percentiles clave
        percentiles_cola = np.percentile(perdidas_totales, [90, 95, 99])
        colores_percentiles = ['green', 'orange', 'red']
        labels_percentiles = ['P90', 'P95', 'P99']
        for p, color, label in zip(percentiles_cola, colores_percentiles, labels_percentiles):
            ax10.axvline(x=p, color=color, linestyle='--', linewidth=2, label=f'{label}: {currency_format(p)}')

        ax10.legend()
        fig10.tight_layout()
        figuras.append(fig10)

        return figuras

    def graficar_resultados(self, perdidas_totales, frecuencias_totales, perdidas_por_evento, frecuencias_por_evento, eventos_riesgo):
        """Genera y muestra los gráficos en la pestaña de Resultados."""
        # Mostrar cursor de espera durante el armado de gráficos
        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass
        # Limpiar las pestañas de gráficos anteriores
        self.graficos_tab_widget.clear()
        # Reset referencias para integración de tolerancia con gráficos
        try:
            self.ax_distrib_tol_line = None
            self.ax_exceed_tol_line = None
            self.cb_tol_line_distrib = None
            self.cb_tol_line_exceed = None
            self.canvas_distrib = None
            self.canvas_exceed = None
        except Exception:
            pass

        sns.set(style="whitegrid")

        # Ajuste de bins usando la regla de Freedman-Diaconis con manejo de valores extremos
        try:
            # Primero reemplazamos cualquier valor infinito o NaN
            perdidas_sanitizadas = np.copy(perdidas_totales)
            perdidas_sanitizadas = np.nan_to_num(perdidas_sanitizadas, nan=0, posinf=np.nanmax(perdidas_sanitizadas[np.isfinite(perdidas_sanitizadas)]) if np.any(np.isfinite(perdidas_sanitizadas)) else 1e6, neginf=0)
            
            # Calculamos el IQR de forma segura
            iqr_valor = stats.iqr(perdidas_sanitizadas)
            if iqr_valor == 0 or not np.isfinite(iqr_valor):
                # Si el IQR es cero o no es finito, usar un valor predeterminado
                bin_width = (np.max(perdidas_sanitizadas) - np.min(perdidas_sanitizadas)) / 50
                if bin_width <= 0 or not np.isfinite(bin_width):
                    bin_width = 1.0  # Valor seguro si todo lo demás falla
            else:
                # Cálculo normal con protección contra división por cero
                bin_width = 2 * iqr_valor / max(1.0, (len(perdidas_sanitizadas) ** (1/3)))
            
            # Calculamos el rango de forma segura
            rango = np.max(perdidas_sanitizadas) - np.min(perdidas_sanitizadas)
            if rango <= 0 or not np.isfinite(rango):
                bins = 50  # Valor predeterminado seguro
            else:
                # Limitamos el número de bins a un rango razonable
                bins = min(100, max(10, int(rango / max(bin_width, 1e-10))))
        except Exception as e:
            print(f"Error al calcular bins: {e}")
            bins = 50  # Valor predeterminado en caso de error

        # Gráfico 1: Distribución de pérdidas agregadas
        fig1 = Figure(figsize=(8, 5))
        canvas1 = InteractiveFigureCanvas(fig1)
        ax1 = fig1.add_subplot(111)
        
        # Histograma con estilo MercadoLibre
        sns.histplot(perdidas_totales, bins=bins, kde=True, 
                     color=MELI_AZUL, edgecolor='white', 
                     linewidth=0.5, alpha=0.85, ax=ax1)
        
        # Cálculo de estadísticas clave
        media = np.mean(perdidas_totales)
        mediana = np.median(perdidas_totales)
        var_90 = np.percentile(perdidas_totales, 90)
        var_99 = np.percentile(perdidas_totales, 99)
        
        # Líneas de referencia con colores y estilos MercadoLibre, incluyendo etiquetas para la leyenda
        ax1.axvline(x=media, color=MELI_ROJO, linestyle='-', linewidth=1.5, alpha=0.7, 
                  label=f'Media: {currency_format(media)}')
        ax1.axvline(x=mediana, color=MELI_AZUL_CORP, linestyle='--', linewidth=1.3, alpha=0.7,
                  label=f'Mediana: {currency_format(mediana)}')
        ax1.axvline(x=var_90, color=MELI_VERDE, linestyle='-.', linewidth=1.3, alpha=0.7,
                  label=f'P90: {currency_format(var_90)}')
        ax1.axvline(x=var_99, color=MELI_AMARILLO, linestyle=':', linewidth=1.5, alpha=0.8,
                  label=f'P99: {currency_format(var_99)}')
        
        # Añadir leyenda en una posición que no obstruya el gráfico
        ax1.legend(loc='upper right', fontsize=8, framealpha=0.9, bbox_to_anchor=(0.99, 0.99))
        
        # Resumen estadístico compact0, claro y bien posicionado
        #stats_text = (
        #    f"Media: {currency_format(media)}\n"
        #    f"Mediana: {currency_format(mediana)}\n"
        #    f"P90: {currency_format(var_90)}\n"
        #    f"P99: {currency_format(var_99)}"
        #)
        #ax1.text(0.95, 0.95, stats_text, transform=ax1.transAxes,
        #        fontsize=8, va='top', ha='right', linespacing=1.3,
        #        bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.9, 
        #                 edgecolor='#EEEEEE'))
        
        # Títulos y etiquetas
        ax1.set_title('Impacto Económico Anual Esperado')
        ax1.set_xlabel('Pérdida Total')
        ax1.set_ylabel('Frecuencia')
        
        # Formateo de ejes
        ax1.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
        ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{int(x):,}'.replace(",", ".")))
        
        # Aplicar estilo MercadoLibre global
        aplicar_estilo_meli(ax1)
        
        # Configurar datos para tooltips interactivos
        # Crear una función de formato para los tooltips
        def formatter_distribucion(x, y):
            percentil = np.searchsorted(np.sort(perdidas_totales), x)
            percentil = min(100, max(0, int(percentil / len(perdidas_totales) * 100)))
            return f"Pérdida: {currency_format(x)}\nPercentil: ~{percentil}%\nFrecuencia: {int(y)}"
        
        # Extraer datos del histograma para tooltips
        for collection in ax1.collections:
            if hasattr(collection, 'get_paths') and len(collection.get_paths()) > 0:
                for path in collection.get_paths():
                    v = path.vertices
                    if len(v) > 1:
                        x_points = [(v[i][0] + v[i+1][0])/2 for i in range(len(v)-1)]
                        y_points = [(v[i][1] + v[i+1][1])/2 for i in range(len(v)-1)]
                        canvas1.add_tooltip_data(ax1, x_points, y_points, formatter=formatter_distribucion)
        
        # Configurar tooltip para las líneas de referencia
        canvas1.add_tooltip_data(ax1, [media, mediana, var_90, var_99], 
                             [0, 0, 0, 0],
                             labels=[f'Media: {currency_format(media)}', 
                                    f'Mediana: {currency_format(mediana)}',
                                    f'P90: {currency_format(var_90)}',
                                    f'P99: {currency_format(var_99)}'])
        
        tab1 = QtWidgets.QWidget()
        layout1 = QtWidgets.QVBoxLayout(tab1)
        # Controles para mostrar/ocultar línea de tolerancia en Distribución
        distrib_ctrls = QtWidgets.QWidget()
        distrib_ctrls_layout = QtWidgets.QHBoxLayout(distrib_ctrls)
        distrib_ctrls_layout.setContentsMargins(0, 0, 0, 0)
        self.cb_tol_line_distrib = QtWidgets.QCheckBox("Mostrar límite de tolerancia")
        try:
            self.cb_tol_line_distrib.setChecked(False)
        except Exception:
            pass
        self.cb_tol_line_distrib.toggled.connect(self.actualizar_linea_tolerancia_graficos)
        distrib_ctrls_layout.addWidget(self.cb_tol_line_distrib)
        distrib_ctrls_layout.addStretch()
        layout1.addWidget(distrib_ctrls)
        layout1.addWidget(canvas1)
        # Dibujar línea de tolerancia inicial en Distribución
        try:
            T = float(self.tolerancia_ex_spin.value()) if hasattr(self, 'tolerancia_ex_spin') else float(np.percentile(perdidas_totales, 90))
        except Exception:
            T = float(np.percentile(perdidas_totales, 90))
        try:
            self.ax_distrib_tol_line = ax1.axvline(x=T, color=MELI_ROJO, linestyle='-', linewidth=1.8, alpha=0.85)
            # Crear etiqueta "Tolerancia" con pequeño offset para evitar solapes
            try:
                x_left, x_right = ax1.get_xlim()
                x_range = max(1e-9, x_right - x_left)
                dx = 0.01 * x_range
                y_bottom, y_top = ax1.get_ylim()
                y_pos = y_bottom + 0.9 * (y_top - y_bottom)
                self.ax_distrib_tol_label = ax1.text(T + dx, y_pos, "Tolerancia", rotation=90,
                                                     fontsize=8, color=MELI_ROJO,
                                                     va='center', ha='left',
                                                     bbox=dict(facecolor='white', alpha=0.9, edgecolor=None))
            except Exception:
                self.ax_distrib_tol_label = None
            visible = self.cb_tol_line_distrib.isChecked()
            self.ax_distrib_tol_line.set_visible(visible)
            if getattr(self, 'ax_distrib_tol_label', None) is not None:
                self.ax_distrib_tol_label.set_visible(visible)
        except Exception:
            self.ax_distrib_tol_line = None
        self.canvas_distrib = canvas1
        self.graficos_tab_widget.addTab(tab1, "Distribución")
        try:
            curr = self.progress_bar.value()
            self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
        except Exception:
            pass

        # Gráfico 2: Distribución de pérdidas agregadas (sin ceros)
        perdidas_totales_sin_cero = perdidas_totales[perdidas_totales != 0]
        # Cálculo del porcentaje de casos no cero
        porcentaje_no_cero = (len(perdidas_totales_sin_cero) / len(perdidas_totales)) * 100
        if len(perdidas_totales_sin_cero) > 0:
            fig2 = Figure(figsize=(8, 5))
            canvas2 = InteractiveFigureCanvas(fig2)
            ax2 = fig2.add_subplot(111)
            
            # Usar un tono más claro del azul para diferenciar del primer gráfico
            sns.histplot(perdidas_totales_sin_cero, bins=bins, kde=True, 
                         color=MELI_AZUL, edgecolor='white', 
                         linewidth=0.5, alpha=0.85, ax=ax2)
            
            # Calcular estadísticas
            media_sin_cero = np.mean(perdidas_totales_sin_cero)
            mediana_sin_cero = np.median(perdidas_totales_sin_cero)
            var_90_sin_cero = np.percentile(perdidas_totales_sin_cero, 90)
            var_99_sin_cero = np.percentile(perdidas_totales_sin_cero, 99)
            
            # Líneas de referencia con etiquetas para la leyenda
            ax2.axvline(x=media_sin_cero, color=MELI_ROJO, linestyle='-', linewidth=1.5, alpha=0.7,
                      label=f'Media: {currency_format(media_sin_cero)}')
            ax2.axvline(x=mediana_sin_cero, color=MELI_AZUL_CORP, linestyle='--', linewidth=1.3, alpha=0.7,
                      label=f'Mediana: {currency_format(mediana_sin_cero)}')
            ax2.axvline(x=var_90_sin_cero, color=MELI_VERDE, linestyle='-.', linewidth=1.3, alpha=0.7,
                      label=f'P90: {currency_format(var_90_sin_cero)}')
            ax2.axvline(x=var_99_sin_cero, color=MELI_AMARILLO, linestyle=':', linewidth=1.5, alpha=0.8,
                      label=f'P99: {currency_format(var_99_sin_cero)}')
            
            # Añadir leyenda
            ax2.legend(loc='upper right', fontsize=8, framealpha=0.9)
            
            # Sincronizar ejes X con el primer histograma para mejor comparación
            try:
                ax2.set_xlim(ax1.get_xlim())
            except:
                pass
            
            # Información estadística
            #stats_text = (
            #    f"Media: {currency_format(media_sin_cero)}\n"
            #    f"Mediana: {currency_format(mediana_sin_cero)}\n"
            #    f"P90: {currency_format(var_90_sin_cero)}"
            #)
            
            #ax2.text(0.95, 0.95, stats_text, transform=ax2.transAxes,
            #        fontsize=8, va='top', ha='right', linespacing=1.3,
            #        bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.9, 
            #                 edgecolor='#EEEEEE'))
            
            # Información sobre porcentaje de simulaciones con pérdidas
            ax2.text(0.05, 0.95, f"{porcentaje_no_cero:.1f}% simulaciones con pérdidas", 
                    transform=ax2.transAxes, ha='left', fontsize=8, va='top',
                    color=MELI_AZUL_CORP, 
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#DDDDDD", alpha=0.8))
            
            ax2.set_title('Impacto Económico (Excluyendo Casos con Cero-Pérdida)')
            ax2.set_xlabel('Pérdida Total')
            ax2.set_ylabel('Frecuencia')
            
            # Formateo de ejes
            ax2.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
            
            # Aplicar estilo MercadoLibre global
            aplicar_estilo_meli(ax2)
            
            # Configurar datos para tooltips interactivos
            # Crear una función de formato para los tooltips
            def formatter_distribucion_sin_ceros(x, y):
                percentil = np.searchsorted(np.sort(perdidas_totales_sin_cero), x)
                percentil = min(100, max(0, int(percentil / len(perdidas_totales_sin_cero) * 100)))
                return f"Pérdida: {currency_format(x)}\nPercentil: ~{percentil}%\nFrecuencia: {int(y)}"
            
            # Extraer datos del histograma para tooltips
            for collection in ax2.collections:
                if hasattr(collection, 'get_paths') and len(collection.get_paths()) > 0:
                    for path in collection.get_paths():
                        v = path.vertices
                        if len(v) > 1:
                            x_points = [(v[i][0] + v[i+1][0])/2 for i in range(len(v)-1)]
                            y_points = [(v[i][1] + v[i+1][1])/2 for i in range(len(v)-1)]
                            canvas2.add_tooltip_data(ax2, x_points, y_points, formatter=formatter_distribucion_sin_ceros)
            
            # Configurar tooltip para las líneas de referencia
            canvas2.add_tooltip_data(ax2, [media_sin_cero, mediana_sin_cero, var_90_sin_cero, var_99_sin_cero], 
                                 [0, 0, 0, 0],
                                 labels=[f'Media: {currency_format(media_sin_cero)}', 
                                        f'Mediana: {currency_format(mediana_sin_cero)}',
                                        f'P90: {currency_format(var_90_sin_cero)}',
                                        f'P99: {currency_format(var_99_sin_cero)}'])
            
            tab2 = QtWidgets.QWidget()
            layout2 = QtWidgets.QVBoxLayout(tab2)
            # Controles para mostrar/ocultar línea de tolerancia en Distribución sin ceros
            distrib2_ctrls = QtWidgets.QWidget()
            distrib2_ctrls_layout = QtWidgets.QHBoxLayout(distrib2_ctrls)
            distrib2_ctrls_layout.setContentsMargins(0, 0, 0, 0)
            self.cb_tol_line_distrib_sin_cero = QtWidgets.QCheckBox("Mostrar límite de tolerancia")
            try:
                self.cb_tol_line_distrib_sin_cero.setChecked(False)
            except Exception:
                pass
            self.cb_tol_line_distrib_sin_cero.toggled.connect(self.actualizar_linea_tolerancia_graficos)
            distrib2_ctrls_layout.addWidget(self.cb_tol_line_distrib_sin_cero)
            distrib2_ctrls_layout.addStretch()
            layout2.addWidget(distrib2_ctrls)
            layout2.addWidget(canvas2)
            # Dibujar línea de tolerancia inicial (vertical) en x=T con etiqueta
            try:
                T2 = float(self.tolerancia_ex_spin.value()) if hasattr(self, 'tolerancia_ex_spin') else float(np.percentile(perdidas_totales_sin_cero, 90))
            except Exception:
                T2 = float(np.percentile(perdidas_totales_sin_cero, 90))
            try:
                self.ax_distrib_sin_cero_tol_line = ax2.axvline(x=T2, color=MELI_ROJO, linestyle='-', linewidth=1.8, alpha=0.85)
                # Etiqueta "Tolerancia" con offset para evitar solapes
                try:
                    x_left2, x_right2 = ax2.get_xlim()
                    x_range2 = max(1e-9, x_right2 - x_left2)
                    dx2 = 0.01 * x_range2
                    y_bottom2, y_top2 = ax2.get_ylim()
                    y_pos2 = y_bottom2 + 0.9 * (y_top2 - y_bottom2)
                    self.ax_distrib_sin_cero_tol_label = ax2.text(T2 + dx2, y_pos2, "Tolerancia", rotation=90,
                                                                   fontsize=8, color=MELI_ROJO,
                                                                   va='center', ha='left',
                                                                   bbox=dict(facecolor='white', alpha=0.9, edgecolor=None))
                except Exception:
                    self.ax_distrib_sin_cero_tol_label = None
                visible2 = self.cb_tol_line_distrib_sin_cero.isChecked()
                self.ax_distrib_sin_cero_tol_line.set_visible(visible2)
                if getattr(self, 'ax_distrib_sin_cero_tol_label', None) is not None:
                    self.ax_distrib_sin_cero_tol_label.set_visible(visible2)
            except Exception:
                self.ax_distrib_sin_cero_tol_line = None
            self.canvas_distrib_sin_cero = canvas2
            self.graficos_tab_widget.addTab(tab2, "Sin Ceros")
            try:
                curr = self.progress_bar.value()
                self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
            except Exception:
                pass

        # Gráfico 3: Curva de Excedencia (con Probabilidad de Excedencia en eje X)
        fig3 = Figure(figsize=(8, 5.5))
        canvas3 = InteractiveFigureCanvas(fig3)
        ax3 = fig3.add_subplot(111)
        
        # Usar probabilidad de excedencia (100 - percentil) en lugar de percentil
        # Esto hace que el gráfico sea más intuitivo: "X% de probabilidad de exceder este valor"
        percentiles = np.arange(1, 100)  # Evitar 0 para escala log
        prob_excedencia = 100 - percentiles  # Convertir a probabilidad de excedencia

        # Calcular las pérdidas correspondientes a cada percentil
        loss_values = np.percentile(perdidas_totales, percentiles)

        # Trazar probabilidad de excedencia en eje X contra pérdidas en eje Y
        ax3.plot(prob_excedencia, loss_values, color=MELI_AZUL, linewidth=2)

        # Cálculo de percentiles clave
        p50 = np.percentile(perdidas_totales, 50)
        p75 = np.percentile(perdidas_totales, 75)
        p90 = np.percentile(perdidas_totales, 90)
        p95 = np.percentile(perdidas_totales, 95)
        p99 = np.percentile(perdidas_totales, 99)

        # Percentiles clave y sus probabilidades de excedencia
        # (percentil, prob_excedencia, valor, etiqueta)
        percentiles_clave = [
            (50, 50, p50, "50% prob. de exceder"),
            (90, 10, p90, "10% prob. de exceder"),
            (99, 1, p99, "1% prob. de exceder")
        ]
        colores = [MELI_AZUL_CORP, MELI_VERDE, MELI_ROJO]
        
        # Líneas horizontales sutiles para los percentiles principales
        for (perc, prob_exc, valor, etiq), color in zip(percentiles_clave, colores):
            ax3.axhline(y=valor, color=color, linestyle='--', linewidth=1.2, alpha=0.5)

        # Puntos para marcar los percentiles en la curva
        for (perc, prob_exc, valor, etiq), color in zip(percentiles_clave, colores):
            ax3.scatter(prob_exc, valor, color=color, s=50, zorder=5, edgecolor='white', linewidth=1)

        # Definir ubicaciones inteligentes para evitar superposición de etiquetas
        # Ahora en términos de probabilidad de excedencia
        etiquetas_pos = {
            50: {'x': 55, 'y': 1.08},   # 50% prob excedencia (P50)
            10: {'x': 15, 'y': 1.05},   # 10% prob excedencia (P90)
            1: {'x': 5, 'y': 1.08}      # 1% prob excedencia (P99)
        }
        
        # Añadir etiquetas con formato más intuitivo
        for (perc, prob_exc, valor, etiq), color in zip(percentiles_clave, colores):
            posicion = etiquetas_pos[prob_exc]
            ax3.text(posicion['x'], valor * posicion['y'], 
                    f'{prob_exc}%: {currency_format(valor)}', 
                    color=color, fontsize=8, fontweight='bold',
                    bbox=dict(facecolor='white', alpha=0.9, edgecolor=None, 
                            boxstyle='round,pad=0.3'))
        
        # Título y etiquetas actualizadas
        ax3.set_title('Curva de Excedencia')
        ax3.set_xlabel('Probabilidad de Exceder (%)')
        ax3.set_ylabel('Pérdida Total')
        
        # Invertir eje X para que vaya de mayor a menor probabilidad (más intuitivo)
        ax3.invert_xaxis()
        
        # Marcas en el eje X con valores de probabilidad relevantes
        ax3.set_xticks([99, 90, 75, 50, 25, 10, 5, 1])
        ax3.set_xticklabels(['99%', '90%', '75%', '50%', '25%', '10%', '5%', '1%'])
        
        # Formateo de ejes
        ax3.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
        
        # Aplicar estilo MercadoLibre global
        aplicar_estilo_meli(ax3)
        
        # Guardar referencia al eje para toggle de escala log
        self.ax_exceed = ax3
        self.fig_exceed = fig3
        
        # Configurar datos para tooltips interactivos
        def formatter_excedencia(x, y):
            # x es probabilidad de excedencia, y es el valor de pérdida
            return f"Prob. de exceder: {x:.1f}%\nPérdida: {currency_format(y)}"
        
        # Configurar tooltips para la curva de excedencia
        canvas3.add_tooltip_data(ax3, prob_excedencia, loss_values, formatter=formatter_excedencia)
        
        # Añadir tooltips para puntos específicos
        prob_exc_key = [50, 10, 5, 1]  # Probabilidades de excedencia
        loss_values_key = [p50, p90, p95, p99]
        
        canvas3.add_tooltip_data(ax3, prob_exc_key, loss_values_key,
                              labels=[f'{p}% prob. exceder: {currency_format(v)}' for p, v in zip(prob_exc_key, loss_values_key)])
        
        # Pestaña Curva de Excedencia con controles
        tab3 = QtWidgets.QWidget()
        layout3 = QtWidgets.QVBoxLayout(tab3)
        exceed_ctrls = QtWidgets.QWidget()
        exceed_ctrls_layout = QtWidgets.QHBoxLayout(exceed_ctrls)
        exceed_ctrls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Checkbox para mostrar límite de tolerancia
        self.cb_tol_line_exceed = QtWidgets.QCheckBox("Mostrar límite de tolerancia")
        self.cb_tol_line_exceed.setChecked(False)
        self.cb_tol_line_exceed.toggled.connect(self.actualizar_linea_tolerancia_graficos)
        exceed_ctrls_layout.addWidget(self.cb_tol_line_exceed)
        
        # Separador visual
        exceed_ctrls_layout.addSpacing(20)
        
        # Checkbox para escala logarítmica en Y
        self.cb_log_scale_exceed = QtWidgets.QCheckBox("Escala logarítmica (Y)")
        self.cb_log_scale_exceed.setChecked(False)
        self.cb_log_scale_exceed.toggled.connect(self.toggle_escala_log_excedencia)
        exceed_ctrls_layout.addWidget(self.cb_log_scale_exceed)
        
        exceed_ctrls_layout.addStretch()
        layout3.addWidget(exceed_ctrls)
        layout3.addWidget(canvas3)
        
        # Dibujar línea horizontal inicial en y=T
        try:
            T = float(self.tolerancia_ex_spin.value()) if hasattr(self, 'tolerancia_ex_spin') else float(np.percentile(perdidas_totales, 90))
        except Exception:
            T = float(np.percentile(perdidas_totales, 90))
        try:
            self.ax_exceed_tol_line = ax3.axhline(y=T, color=MELI_ROJO, linestyle='--', linewidth=1.8, alpha=0.85)
            # Etiqueta "Tolerancia" cerca del borde izquierdo (ahora que el eje está invertido)
            try:
                x_left, x_right = ax3.get_xlim()
                x_pos = x_left - 0.02 * abs(x_right - x_left)
                self.ax_exceed_tol_label = ax3.text(x_pos, T, "Tolerancia",
                                                    fontsize=8, color=MELI_ROJO,
                                                    va='bottom', ha='left',
                                                    bbox=dict(facecolor='white', alpha=0.9, edgecolor=None))
            except Exception:
                self.ax_exceed_tol_label = None
            visible = self.cb_tol_line_exceed.isChecked()
            self.ax_exceed_tol_line.set_visible(visible)
            if getattr(self, 'ax_exceed_tol_label', None) is not None:
                self.ax_exceed_tol_label.set_visible(visible)
        except Exception:
            self.ax_exceed_tol_line = None
            self.ax_exceed_tol_label = None
        self.canvas_exceed = canvas3
        self.graficos_tab_widget.addTab(tab3, "Excedencia")
        try:
            curr = self.progress_bar.value()
            self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
        except Exception:
            pass

        # Gráfico: Box Plot de Pérdida Agregada
        fig_boxplot = Figure(figsize=(8, 6))
        canvas_boxplot = InteractiveFigureCanvas(fig_boxplot)
        ax_boxplot = fig_boxplot.add_subplot(111)

        # Crear el box plot con diseño mejorado
        box = ax_boxplot.boxplot([perdidas_totales], labels=['Pérdida Agregada'],
                                patch_artist=True, showfliers=True,
                                whiskerprops={'color':'black', 'linestyle':'-'},
                                medianprops={'color':'red', 'linewidth':2},
                                flierprops={'marker':'o', 'markerfacecolor':'red', 'markersize':3})

        # Personalizar colores
        for patch in box['boxes']:
            patch.set_facecolor('#4c72b0')
            patch.set_alpha(0.7)

        # Cálculo de percentiles adicionales importantes para análisis de riesgo
        mean_val = np.mean(perdidas_totales)
        median_val = np.median(perdidas_totales)
        p25 = np.percentile(perdidas_totales, 25)
        p75 = np.percentile(perdidas_totales, 75)
        p90 = np.percentile(perdidas_totales, 90)
        p95 = np.percentile(perdidas_totales, 95)
        p99 = np.percentile(perdidas_totales, 99)

        # Añadir líneas para los percentiles adicionales
        ax_boxplot.axhline(y=p90, color='green', linestyle='--', linewidth=1.5, alpha=0.7, label='P90')
        ax_boxplot.axhline(y=p95, color='purple', linestyle='--', linewidth=1.5, alpha=0.7, label='P95')
        ax_boxplot.axhline(y=p99, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='P99')

        # Añadir etiquetas con estadísticas clave - Formato mejorado con colores
        stats_text = f"Media: {currency_format(mean_val)}\n"
        stats_text += f"Mediana: {currency_format(median_val)}\n"
        stats_text += f"Q1: {currency_format(p25)}\n"
        stats_text += f"Q3: {currency_format(p75)}"

        # Colocar etiquetas de texto para percentiles de cola en posiciones estratégicas
        ax_boxplot.text(1.15, median_val, stats_text, va='center', ha='left',
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=3))
        ax_boxplot.text(1.15, p90, f'P90: {currency_format(p90)}', color='green', va='center', ha='left',
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
        ax_boxplot.text(1.15, p95, f'P95: {currency_format(p95)}', color='purple', va='center', ha='left',
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
        ax_boxplot.text(1.15, p99, f'P99: {currency_format(p99)}', color='red', va='center', ha='left',
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

        # Añadir leyenda
        ax_boxplot.legend(loc='upper right')

        ax_boxplot.set_title('Distribución de Pérdida Agregada - Análisis de Percentiles')
        ax_boxplot.set_ylabel('Pérdida')
        ax_boxplot.grid(axis='y', linestyle='--', alpha=0.3)  # Rejilla sutil para mejor lectura
        ax_boxplot.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
        fig_boxplot.tight_layout()
        
        # Configurar tooltips para el boxplot
        # Datos principales del boxplot: [min, q1, mediana, q3, max]
        boxplot_data = [perdidas_totales.min(), p25, median_val, p75, perdidas_totales.max()]
        boxplot_labels = [
            f'Mínimo: {currency_format(perdidas_totales.min())}',
            f'Q1 (P25): {currency_format(p25)}',
            f'Mediana (P50): {currency_format(median_val)}',
            f'Q3 (P75): {currency_format(p75)}',
            f'Máximo: {currency_format(perdidas_totales.max())}'
        ]
        
        # Añadir tooltips para los componentes básicos del boxplot
        # Usar puntos fantasma para posicionar los tooltips
        positions = [1] * len(boxplot_data)  # Todos en la posición 1 en el eje x
        canvas_boxplot.add_tooltip_data(ax_boxplot, positions, boxplot_data, labels=boxplot_labels)
        
        # Añadir tooltips para los percentiles adicionales
        percentiles_adicionales = [p90, p95, p99]
        percentiles_nombres = ['P90', 'P95', 'P99']
        percentiles_colores = ['green', 'purple', 'red']
        
        for valor, nombre, color in zip(percentiles_adicionales, percentiles_nombres, percentiles_colores):
            canvas_boxplot.add_tooltip_data(ax_boxplot, [1], [valor], 
                                       labels=[f'{nombre}: {currency_format(valor)}'],
                                       highlight_colors=color)

        tab4 = QtWidgets.QWidget()
        layout_boxplot = QtWidgets.QVBoxLayout(tab4)
        layout_boxplot.addWidget(canvas_boxplot)
        self.graficos_tab_widget.addTab(tab4, "Box Plot")
        try:
            curr = self.progress_bar.value()
            self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
        except Exception:
            pass

        # --- GRÁFICO VIOLIN COMENTADO (Información redundante con Box Plot) ---
        # # Gráfico: Violin Plot para Pérdida Agregada
        # fig_violin = Figure(figsize=(8, 6))
        # canvas_violin = InteractiveFigureCanvas(fig_violin)
        # ax_violin = fig_violin.add_subplot(111)
        #
        # # Preparar datos en formato adecuado para violinplot
        # violin_data = [perdidas_totales]
        #
        # # Crear violin plot con mejor diseño visual
        # parts = ax_violin.violinplot(violin_data, showmedians=True, showextrema=True)
        #
        # # Personalizar el violin plot
        # for pc in parts['bodies']:
        #     pc.set_facecolor('#4c72b0')
        #     pc.set_alpha(0.7)
        #     pc.set_edgecolor('black')
        #     pc.set_linewidth(1)
        #
        # # Calcular percentiles clave
        # percentiles = [10, 25, 50, 75, 90, 95, 99]
        # percentiles_val = np.percentile(perdidas_totales, percentiles)
        # percentiles_colors = ['#e6e6e6', '#c2c2c2', 'green', 'blue', 'orange', 'purple', 'red']
        # percentiles_styles = ['-', '-', '--', '--', '--', '--', '--']
        # percentiles_widths = [0.7, 0.7, 1.0, 1.0, 1.5, 1.5, 2.0]
        #
        # # Añadir líneas horizontales para los percentiles con mejor formato
        # for i, p in enumerate(percentiles):
        #     ax_violin.axhline(y=percentiles_val[i], 
        #                   color=percentiles_colors[i], 
        #                   linestyle=percentiles_styles[i], 
        #                   alpha=0.8, 
        #                   linewidth=percentiles_widths[i],
        #                   label=f"P{p}" if p >= 50 else None)  # Solo mostrar en leyenda los más importantes
        #
        # # Añadir etiquetas de texto para percentiles clave directamente en el gráfico
        # ax_violin.text(1.25, percentiles_val[2], f"P50: {currency_format(percentiles_val[2])}", 
        #               va='center', ha='left', fontsize=9, color='green',
        #               bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
        # ax_violin.text(1.25, percentiles_val[4], f"P90: {currency_format(percentiles_val[4])}", 
        #               va='center', ha='left', fontsize=9, color='orange',
        #               bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
        # ax_violin.text(1.25, percentiles_val[5], f"P95: {currency_format(percentiles_val[5])}", 
        #               va='center', ha='left', fontsize=9, color='purple',
        #               bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
        # ax_violin.text(1.25, percentiles_val[6], f"P99: {currency_format(percentiles_val[6])}", 
        #               va='center', ha='left', fontsize=9, color='red',
        #               bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
        #
        # ax_violin.set_title('Distribución Detallada de Pérdida Agregada - Análisis de Percentiles')
        # ax_violin.set_ylabel('Pérdida')
        # ax_violin.set_xticks([1])
        # ax_violin.set_xticklabels(['Pérdida Agregada'])
        # ax_violin.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
        # ax_violin.grid(axis='y', linestyle='--', alpha=0.3)  # Rejilla sutil para mejor lectura
        # ax_violin.legend(loc='upper right')
        # fig_violin.tight_layout()
        # 
        # # Configurar tooltips para el violin plot
        # # Para cada percentil clave, crear un tooltip
        # for i, p in enumerate(percentiles):
        #     if p >= 50:  # Solo mostrar tooltips para los percentiles más importantes
        #         canvas_violin.add_tooltip_data(
        #             ax_violin, 
        #             [1], 
        #             [percentiles_val[i]], 
        #             labels=[f'P{p}: {currency_format(percentiles_val[i])}'],
        #             highlight_color=percentiles_colors[i]
        #         )
        # 
        # # Añadir tooltips para las líneas de cada percentil
        # def formatter_violin(x, y):
        #     # Buscar el percentil aproximado para este valor y
        #     idx = np.searchsorted(np.sort(perdidas_totales), y)
        #     percentil_aprox = min(100, max(0, int(idx / len(perdidas_totales) * 100)))
        #     return f"Valor: {currency_format(y)}\nPercentil Aprox: {percentil_aprox}%"
        # 
        # # Añadir datos para tooltips en varios puntos a lo largo del violin plot
        # # Crear puntos fantasma distribuidos en el eje Y para mejor cobertura
        # y_points = np.linspace(perdidas_totales.min(), perdidas_totales.max(), 20)
        # x_points = [1] * len(y_points)
        # canvas_violin.add_tooltip_data(ax_violin, x_points, y_points, formatter=formatter_violin)
        #
        # tab5 = QtWidgets.QWidget()
        # layout_violin = QtWidgets.QVBoxLayout(tab5)
        # layout_violin.addWidget(canvas_violin)
        # self.graficos_tab_widget.addTab(tab5, "Violin")
        # try:
        #     curr = self.progress_bar.value()
        #     self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
        # except Exception:
        #     pass
        # --- FIN GRÁFICO VIOLIN COMENTADO ---

        # --- GRÁFICO COMPAR COMENTADO (Split Violin) ---
        # # Gráfico: Split Violin para comparar distribución completa vs cola
        # fig_split = Figure()
        # canvas_split = InteractiveFigureCanvas(fig_split)
        # ax_split = fig_split.add_subplot(111)
        #
        # # Obtener la cola de distribución (últimos 20%)
        # percentil_80 = np.percentile(perdidas_totales, 80)
        # perdidas_cola = perdidas_totales[perdidas_totales >= percentil_80]
        #
        # # Preparar datos para el split violin
        # split_data = [perdidas_totales, perdidas_cola]
        # positions = [1, 2]
        # labels = ['Distribución Completa', 'Cola (P80-P100)']
        #
        # # Crear violin split
        # parts = ax_split.violinplot(split_data, positions, showmedians=True, showextrema=True)
        #
        # # Personalizar colores
        # for i, pc in enumerate(parts['bodies']):
        #     if i == 0:
        #         pc.set_facecolor('#4c72b0')
        #     else:
        #         pc.set_facecolor('#de425b')
        #     pc.set_alpha(0.7)
        #     pc.set_edgecolor('black')
        #
        # # Añadir textos con estadísticas
        # for i, data in enumerate(split_data):
        #     mean_val = np.mean(data)
        #     median_val = np.median(data)
        #     stats_text = f"Media: {currency_format(mean_val)}\n"
        #     stats_text += f"Mediana: {currency_format(median_val)}"
        #     ax_split.text(positions[i] + 0.3, median_val, stats_text, va='center', ha='left', fontsize=8)
        #
        # ax_split.set_title('Comparativa de Distribución Completa vs Cola')
        # ax_split.set_ylabel('Pérdida')
        # ax_split.set_xticks(positions)
        # ax_split.set_xticklabels(labels)
        # ax_split.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
        # fig_split.tight_layout()
        # 
        # # Configurar tooltips para el split violin plot
        # # Crear funciones de formateo para los tooltips
        # def formatter_split_completa(x, y):
        #     idx = np.searchsorted(np.sort(perdidas_totales), y)
        #     percentil = min(100, max(0, int(idx / len(perdidas_totales) * 100)))
        #     return f"Distribución Completa\nValor: {currency_format(y)}\nPercentil: ~{percentil}%"
        #     
        # def formatter_split_cola(x, y):
        #     idx = np.searchsorted(np.sort(perdidas_cola), y)
        #     percentil = min(100, max(0, int(idx / len(perdidas_cola) * 100)))
        #     percentil_global = 80 + percentil * 0.2  # Ajustar al rango P80-P100
        #     return f"Cola (P80-P100)\nValor: {currency_format(y)}\nPercentil global: ~{percentil_global:.1f}%"
        # 
        # # Añadir puntos para tooltips en la distribución completa
        # y_points1 = np.linspace(perdidas_totales.min(), perdidas_totales.max(), 15)
        # x_points1 = [positions[0]] * len(y_points1)  # Posición del primer violin
        # canvas_split.add_tooltip_data(ax_split, x_points1, y_points1, formatter=formatter_split_completa)
        # 
        # # Añadir puntos para tooltips en la distribución de cola
        # y_points2 = np.linspace(perdidas_cola.min(), perdidas_cola.max(), 15)
        # x_points2 = [positions[1]] * len(y_points2)  # Posición del segundo violin
        # canvas_split.add_tooltip_data(ax_split, x_points2, y_points2, formatter=formatter_split_cola)
        # 
        # # Añadir tooltips para los estadísticos
        # for i, data in enumerate(split_data):
        #     mean_val = np.mean(data)
        #     median_val = np.median(data)
        #     p90 = np.percentile(data, 90)
        #     label = f"Media: {currency_format(mean_val)}\nMediana: {currency_format(median_val)}"
        #     if i == 1:  # Para la cola, mostrar también P90 dentro de la cola
        #         label += f"\nP90 de cola: {currency_format(p90)}"
        #     canvas_split.add_tooltip_data(ax_split, [positions[i]], [median_val], labels=[label])
        #
        # tab6 = QtWidgets.QWidget()
        # layout_split = QtWidgets.QVBoxLayout(tab6)
        # layout_split.addWidget(canvas_split)
        # self.graficos_tab_widget.addTab(tab6, "Compar")
        # try:
        #     curr = self.progress_bar.value()
        #     self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
        # except Exception:
        #     pass
        # --- FIN GRÁFICO COMPAR COMENTADO ---

        # Gráfico 4: Histograma de Frecuencia de Eventos
        if frecuencias_totales.max() > 0:
            fig4 = Figure(figsize=(8, 5))
            canvas4 = InteractiveFigureCanvas(fig4)
            ax4 = fig4.add_subplot(111)

            # Contar la frecuencia de cada número de eventos
            frecuencia_counts = np.bincount(frecuencias_totales.astype(int))
            x_values = np.arange(len(frecuencia_counts))

            # Usar la misma paleta de colores del gráfico de distribución (azul como base)
            ax4.bar(x_values, frecuencia_counts, 
                   color=MELI_AZUL, edgecolor='white',
                   alpha=0.8, width=0.7)
            
            # Destacar la moda (valor más frecuente) con un color distinto
            idx_max = np.argmax(frecuencia_counts)
            ax4.bar([idx_max], [frecuencia_counts[idx_max]], 
                   color=MELI_ROJO, edgecolor='white',
                   alpha=1.0, width=0.7, zorder=10,
                   label=f'Moda: {int(x_values[idx_max])} eventos')
            
            # Marcar la media con una línea vertical
            media_freq = np.mean(frecuencias_totales)
            ax4.axvline(x=media_freq, color=MELI_VERDE, linestyle='--', linewidth=1.5, alpha=0.7,
                       label=f'Media: {media_freq:.2f}')
            
            # Añadir información sobre la moda
            moda_freq = x_values[idx_max]
            moda_count = frecuencia_counts[idx_max]
            moda_pct = (moda_count / np.sum(frecuencia_counts)) * 100
            
            # Información estadística concisa
            stats_text = f"{moda_pct:.1f}% de simulaciones con {int(moda_freq)} eventos"
            
            # Posicionar el texto en la parte superior izquierda
            ax4.text(0.03, 0.97, stats_text, transform=ax4.transAxes,
                    fontsize=8, va='top', ha='left',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
                  
            # Colocar la leyenda en una posición que no se superponga con ningún elemento
            ax4.legend(loc='upper right', fontsize=8, framealpha=0.9, 
                     bbox_to_anchor=(0.99, 0.90))

            # Ajustar las etiquetas del eje X según la cantidad de valores
            max_freq = len(frecuencia_counts)

            if max_freq <= 15:
                ax4.set_xticks(range(max_freq))
            elif max_freq <= 30:
                ax4.set_xticks(range(0, max_freq, 2))
            else:
                # Para cantidades muy grandes, mostrar marcas cada 5 o según densidad
                step = max(1, max_freq // 10)
                ax4.set_xticks(range(0, max_freq, step))

            # Título y etiquetas
            ax4.set_title('Distribución de Frecuencia de Eventos')
            ax4.set_xlabel('Número de Eventos por Año')
            ax4.set_ylabel('Frecuencia')
            
            # Añadir leyenda
            ax4.legend(loc='upper right', fontsize=8, framealpha=0.9)
            
            # Aplicar estilo MercadoLibre
            aplicar_estilo_meli(ax4)

            # Asegurar que el layout tenga buen espacio
            fig4.tight_layout()
            
            # Configurar tooltips para el histograma de frecuencia
            def formatter_frecuencia(x, y):
                # x es el número de eventos, y es la frecuencia (cantidad de simulaciones)
                porcentaje = (y / len(frecuencias_totales)) * 100
                return f"Eventos: {int(x)}\nSimulaciones: {int(y)}\nPorcentaje: {porcentaje:.2f}%"
            
            # Añadir tooltips para cada barra del histograma
            canvas4.add_tooltip_data(ax4, x_values, frecuencia_counts, formatter=formatter_frecuencia)
            
            # Añadir tooltip especial para la moda (valor más frecuente)
            moda_tooltip = f"Moda: {int(x_values[idx_max])} eventos\nSimulaciones: {frecuencia_counts[idx_max]}\nPorcentaje: {(frecuencia_counts[idx_max]/len(frecuencias_totales))*100:.2f}%"
            canvas4.add_tooltip_data(ax4, [idx_max], [frecuencia_counts[idx_max]], labels=[moda_tooltip], highlight_color=MELI_ROJO)
            
            # Añadir tooltip para la media
            media_tooltip = f"Media: {media_freq:.2f} eventos"
            canvas4.add_tooltip_data(ax4, [media_freq], [0], labels=[media_tooltip], highlight_color=MELI_VERDE)

            tab7 = QtWidgets.QWidget()
            layout4 = QtWidgets.QVBoxLayout(tab7)
            layout4.addWidget(canvas4)
            self.graficos_tab_widget.addTab(tab7, "Frecuencia")
            try:
                curr = self.progress_bar.value()
                self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
            except Exception:
                pass

        # --- GRÁFICO BOX x EVT (PRIMERO) COMENTADO (Duplicado con Perd x Evt) ---
        # # Gráfico 8: Box Plot por Evento de Riesgo
        # fig8 = Figure(figsize=(10, 6))
        # canvas8 = InteractiveFigureCanvas(fig8)
        # ax8 = fig8.add_subplot(111)
        # 
        # # Inicializar datos para el boxplot por evento
        # datos_perdidas = [perdidas_evento for perdidas_evento in perdidas_por_evento]
        # nombres_eventos = [evento['nombre'] for evento in eventos_riesgo]
        # 
        # # Crear box plot para cada evento de riesgo
        # sns.boxplot(data=datos_perdidas, ax=ax8, palette='Blues', width=0.6, showfliers=False)
        # 
        # # Añadir puntos para los percentiles 90 y 95
        # for i, evento_data in enumerate(datos_perdidas):
        #     if len(evento_data) > 0:
        #         p90 = np.percentile(evento_data, 90)
        #         p95 = np.percentile(evento_data, 95)
        #         ax8.scatter([i], [p90], color=MELI_VERDE, marker='D', s=30, zorder=10, label='P90' if i == 0 else '')
        #         ax8.scatter([i], [p95], color=MELI_VERDE, marker='*', s=40, zorder=10, label='P95' if i == 0 else '')
        #         
        #         # Añadir punto para la media
        #         mean_val = np.mean(evento_data)
        #         ax8.scatter([i], [mean_val], color=MELI_AMARILLO, marker='o', s=30, zorder=10, label='Media' if i == 0 else '')
        # 
        # # Configurar etiquetas y leyenda
        # ax8.set_title('Box Plot por Evento de Riesgo')
        # ax8.set_xlabel('Evento de Riesgo')
        # ax8.set_ylabel('Pérdida')
        # ax8.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
        # aplicar_estilo_meli(ax8)
        # fig8.tight_layout()
        # 
        # # Configurar tooltips para el box plot por evento de riesgo
        # # Para cada box plot, añadir tooltips con la información estadística
        # for i, (evento_data, nombre_evento) in enumerate(zip(datos_perdidas, nombres_eventos)):
        #     if len(evento_data) > 0:
        #         # Calcular estadísticos clave para los tooltips
        #         min_val = np.min(evento_data)
        #         p25 = np.percentile(evento_data, 25)
        #         median_val = np.median(evento_data)
        #         p75 = np.percentile(evento_data, 75)
        #         max_val = np.max(evento_data)
        #         mean_val = np.mean(evento_data)
        #         p90 = np.percentile(evento_data, 90)
        #         p95 = np.percentile(evento_data, 95)
        #         
        #         # Crear las etiquetas para los tooltips
        #         labels = [
        #             f"{nombre_evento}\nMínimo: {currency_format(min_val)}",
        #             f"{nombre_evento}\nQ1 (P25): {currency_format(p25)}",
        #             f"{nombre_evento}\nMediana: {currency_format(median_val)}",
        #             f"{nombre_evento}\nQ3 (P75): {currency_format(p75)}",
        #             f"{nombre_evento}\nMáximo: {currency_format(max_val)}"
        #         ]
        #         
        #         # Datos para los tooltips: el eje X es la posición del box plot (1-indexed)
        #         x_pos = i + 1
        #         y_values = [min_val, p25, median_val, p75, max_val]
        #         x_values = [x_pos] * len(y_values)
        #         
        #         # Añadir los tooltips principales del boxplot
        #         canvas8.add_tooltip_data(ax8, x_values, y_values, labels=labels)
        #         
        #         # Añadir tooltips para percentiles especiales (90, 95)
        #         canvas8.add_tooltip_data(ax8, [x_pos, x_pos], [p90, p95],
        #                              labels=[f"{nombre_evento}\nP90: {currency_format(p90)}", 
        #                                      f"{nombre_evento}\nP95: {currency_format(p95)}"],
        #                              highlight_color=MELI_VERDE)
        #         
        #         # Añadir tooltip para la media
        #         canvas8.add_tooltip_data(ax8, [x_pos], [mean_val],
        #                              labels=[f"{nombre_evento}\nMedia: {currency_format(mean_val)}"],
        #                              highlight_color=MELI_AMARILLO)
        # 
        # tab11 = QtWidgets.QWidget()
        # layout8 = QtWidgets.QVBoxLayout(tab11)
        # layout8.addWidget(canvas8)
        # self.graficos_tab_widget.addTab(tab11, "Box x Evt")
        # try:
        #     curr = self.progress_bar.value()
        #     self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
        # except Exception:
        #     pass
        # --- FIN GRÁFICO BOX x EVT (PRIMERO) COMENTADO ---

        # Gráfico 5: Dispersión Frecuencia vs. Pérdidas
        if np.std(frecuencias_totales) > 0 and np.std(perdidas_totales) > 0:
            fig5 = Figure()
            canvas5 = InteractiveFigureCanvas(fig5)
            ax5 = fig5.add_subplot(111)
            sns.scatterplot(x=frecuencias_totales + np.random.uniform(-0.2, 0.2, size=frecuencias_totales.size),
                            y=perdidas_totales,
                            alpha=0.5, s=20, ax=ax5, hue=frecuencias_totales, palette='viridis', legend=False)
            sns.regplot(x=frecuencias_totales, y=perdidas_totales, scatter=False, ax=ax5, color='red', line_kws={'linewidth':1})
            ax5.set_title('Dispersión de Frecuencia vs. Pérdida Total')
            ax5.set_xlabel('Frecuencia Total de Eventos')
            ax5.set_ylabel('Pérdida Total')
            ax5.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
            
            # Configurar tooltips para el gráfico de dispersión
            def formatter_dispersion(x, y):
                return f"Eventos: {int(x)}\nPérdida: {currency_format(y)}"
            
            # Añadir tooltip para cada punto de datos (frecuencia, pérdida)
            # Usamos los datos originales, no los jittered que se muestran visualmente
            canvas5.add_tooltip_data(ax5, frecuencias_totales, perdidas_totales, formatter=formatter_dispersion)
            
            # Añadir tooltip para la línea de regresión
            # Calcular algunos puntos a lo largo de la línea de regresión para mostrar tooltips
            x_min, x_max = min(frecuencias_totales), max(frecuencias_totales)
            x_points = np.linspace(x_min, x_max, 5)
            
            # Calcular los valores y correspondientes usando regresión lineal
            z = np.polyfit(frecuencias_totales, perdidas_totales, 1)
            p = np.poly1d(z)
            y_points = p(x_points)
            
            # Tooltip para la línea de tendencia
            def formatter_tendencia(x, y):
                pendiente = z[0]
                intercepto = z[1]
                return f"Línea de tendencia\nPendiente: {currency_format(pendiente)} / evento\nValor proyectado: {currency_format(y)}"
                
            canvas5.add_tooltip_data(ax5, x_points, y_points, 
                               formatter=formatter_tendencia, 
                               highlight_color='red')

            tab8 = QtWidgets.QWidget()
            layout5 = QtWidgets.QVBoxLayout(tab8)
            layout5.addWidget(canvas5)
            self.graficos_tab_widget.addTab(tab8, "Dispersión")
            try:
                curr = self.progress_bar.value()
                self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
            except Exception:
                pass


        # Gráfico 6: Comparación de Pérdidas por Evento de Riesgo
        fig6 = Figure()
        canvas6 = InteractiveFigureCanvas(fig6)
        ax6 = fig6.add_subplot(111)
        datos_plot = False
        for idx, perdidas_evento in enumerate(perdidas_por_evento):
            nombre_evento = eventos_riesgo[idx]['nombre']
            if np.std(perdidas_evento) > 0:
                sns.kdeplot(perdidas_evento, label=nombre_evento, ax=ax6, bw_method='silverman')
                datos_plot = True
        if datos_plot:
            ax6.set_title('Comparación entre Eventos de Riesgo')
            ax6.set_xlabel('Pérdida')
            ax6.set_ylabel('Densidad')
            ax6.legend(fontsize=8)
            ax6.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
            
            # Configurar tooltips para las distribuciones de pérdida por evento
            # Para cada distribución, agregar tooltips en varios puntos clave
            for idx, perdidas_evento in enumerate(perdidas_por_evento):
                nombre_evento = eventos_riesgo[idx]['nombre']
                if np.std(perdidas_evento) > 0:
                    # Calcular los principales estadísticos
                    p25 = np.percentile(perdidas_evento, 25)
                    p50 = np.percentile(perdidas_evento, 50)
                    p75 = np.percentile(perdidas_evento, 75)
                    p90 = np.percentile(perdidas_evento, 90)
                    p95 = np.percentile(perdidas_evento, 95)
                    mean_val = np.mean(perdidas_evento)
                    
                    # Crear puntos donde mostrar tooltips (25, 50, 75, 90, 95 percentiles)
                    tooltip_points = [p25, p50, p75, p90, p95]
                    
                    # Obtener la densidad de KDE para cada valor (usando la curva que ya existe)
                    try:
                        x_vals = np.linspace(min(perdidas_evento), max(perdidas_evento), 1000)
                        kde = stats.gaussian_kde(perdidas_evento, bw_method='silverman')
                        y_vals = kde(x_vals)
                        
                        # Interpolar para obtener las alturas KDE en los puntos de interés
                        y_points = np.interp(tooltip_points, x_vals, y_vals)
                        
                        # Crear los tooltips para los percentiles
                        for i, (x, y, p) in enumerate(zip(tooltip_points, y_points, [25, 50, 75, 90, 95])):
                            label = f"{nombre_evento}\nP{p}: {currency_format(x)}"
                            canvas6.add_tooltip_data(ax6, [x], [y], labels=[label])
                        
                        # Tooltip especial para la media
                        y_mean = np.interp(mean_val, x_vals, y_vals)
                        label_mean = f"{nombre_evento}\nMedia: {currency_format(mean_val)}"
                        canvas6.add_tooltip_data(ax6, [mean_val], [y_mean], labels=[label_mean])
                    except Exception:
                        pass
            tab9 = QtWidgets.QWidget()
            layout6 = QtWidgets.QVBoxLayout(tab9)
            layout6.addWidget(canvas6)
            self.graficos_tab_widget.addTab(tab9, "Dist. por Evento")
            try:
                curr = self.progress_bar.value()
                self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
                QtWidgets.QApplication.processEvents()
            except Exception:
                pass

            # Gráfico 7: Gráfico de Tornado - Contribución de Eventos de Riesgo
            contribuciones = []
            nombres_eventos = []
            for idx, perdidas_evento in enumerate(perdidas_por_evento):
                contribucion = np.mean(perdidas_evento)
                contribuciones.append(contribucion)
                nombre_evento = eventos_riesgo[idx]['nombre']
                nombres_eventos.append(nombre_evento)

            if any(c > 0 for c in contribuciones):
                fig7 = Figure(figsize=(9, 6))  # Tamño optimizado para mejor visualización
                canvas7 = InteractiveFigureCanvas(fig7)
                ax7 = fig7.add_subplot(111)
                tornado_df = pd.DataFrame({
                    'Evento de Riesgo': nombres_eventos,
                    'Contribución Promedio': contribuciones
                })
                tornado_df = tornado_df[tornado_df['Contribución Promedio'] > 0]
                tornado_df['Porcentaje'] = (tornado_df['Contribución Promedio'] / tornado_df['Contribución Promedio'].sum()) * 100
                
                # Ordenar para el gráfico de tornado (ascendente para barras horizontales)
                tornado_df.sort_values('Contribución Promedio', inplace=True, ascending=True)
                
                # Limitar a los 10 eventos más significativos si hay demasiados
                if len(tornado_df) > 10:
                    top_eventos = tornado_df.tail(10).copy()
                    otros_eventos = tornado_df.head(len(tornado_df)-10)
                    suma_otros = {
                        'Evento de Riesgo': f'Otros eventos ({len(otros_eventos)})',
                        'Contribución Promedio': otros_eventos['Contribución Promedio'].sum(),
                        'Porcentaje': otros_eventos['Porcentaje'].sum()
                    }
                    tornado_df = pd.concat([pd.DataFrame([suma_otros]), top_eventos])
                    tornado_df.reset_index(drop=True, inplace=True)
                
                # Crear degradado de colores desde amarillo (MercadoLibre) hasta azul
                num_eventos = len(tornado_df)
                colores_eventos = []
                
                for i in range(num_eventos):
                    if i == num_eventos - 1:  # El evento más importante
                        colores_eventos.append(MELI_AMARILLO)  # Amarillo MercadoLibre para evento principal
                    elif i == num_eventos - 2:  # Segundo evento más importante
                        colores_eventos.append(MELI_AZUL_CORP)  # Azul corporativo
                    elif i == 0 and 'Otros eventos' in tornado_df.iloc[0]['Evento de Riesgo']:
                        colores_eventos.append('#CCCCCC')  # Gris para los eventos agrupados
                    else:
                        # Mezcla entre azul y amarillo MELI con una proporción adecuada
                        ratio = i / (num_eventos - 1)
                        colores_eventos.append(f'#{blend_colors(MELI_AZUL, MELI_AMARILLO, ratio)}')
                
                # Crear las barras horizontales con colores personalizados MercadoLibre
                bars = ax7.barh(tornado_df['Evento de Riesgo'], 
                              tornado_df['Contribución Promedio'], 
                              color=colores_eventos, 
                              edgecolor='white', 
                              alpha=0.85,
                              height=0.65)  # Altura para mejor visualización
                
                # Añadir etiquetas con valor y porcentaje
                for i, (bar, valor, porcentaje, nombre) in enumerate(zip(bars, 
                                                        tornado_df['Contribución Promedio'],
                                                        tornado_df['Porcentaje'],
                                                        tornado_df['Evento de Riesgo'])):
                    width = bar.get_width()
                    label_x_pos = width * 1.01
                    
                    # Optimización de etiquetas para evitar sobrecargar el gráfico
                    if porcentaje >= 1.0:  # Solo mostrar porcentaje si es significativo
                        label_text = f"{currency_format(valor)} ({porcentaje:.1f}%)"
                    else:
                        label_text = f"{currency_format(valor)}"
                    
                    # Etiqueta con fondo blanco para mejor legibilidad
                    ax7.text(label_x_pos, 
                           bar.get_y() + bar.get_height()/2, 
                           label_text, 
                           va='center',
                           fontsize=8,
                           fontweight='bold' if i >= num_eventos - 3 else 'normal', 
                           bbox=dict(facecolor='white', alpha=0.9, edgecolor=None))
                
                # Añadir línea vertical para la media con estilo MELI
                mean_contrib = tornado_df['Contribución Promedio'].mean()
                ax7.axvline(x=mean_contrib, color=MELI_ROJO, linestyle='--', alpha=0.7, 
                          label=f'Media: {currency_format(mean_contrib)}')
                
                # Resumen de contribuciones para referencia rápida
                total_contrib = tornado_df['Contribución Promedio'].sum()
                top3_contrib = tornado_df.nlargest(3, 'Contribución Promedio')['Contribución Promedio'].sum()
                top3_pct = (top3_contrib / total_contrib) * 100
                
                # Añadir texto resumen en esquina superior izquierda
                resumen_text = f"Total: {currency_format(total_contrib)}\nTop 3: {top3_pct:.0f}%"
                ax7.text(0.02, 0.97, resumen_text, transform=ax7.transAxes, 
                        fontsize=8, va='top', ha='left',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
                
                # Título y etiquetas mejoradas
                ax7.set_title('Contribución por Evento de Riesgo')
                ax7.set_xlabel('Contribución a la Pérdida Media ($)')
                ax7.set_ylabel('Evento de Riesgo')
                
                # Formatear el eje X para moneda
                ax7.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
                
                # Aplicar estilo MercadoLibre global
                aplicar_estilo_meli(ax7, tipo='barh')
                
                # Añadir grid horizontal sutil
                ax7.grid(axis='x', linestyle='--', alpha=0.3)
                
                # Añadir leyenda con estilo depurado
                ax7.legend(loc='lower right', fontsize=8, framealpha=0.9)
                
                # Asegurar que haya suficiente espacio para las etiquetas
                fig7.tight_layout()
                
                # Configurar tooltips para el gráfico de tornado
                # Para cada barra del tornado, crear un tooltip con información detallada
                for i, (bar, evento, contribucion, porcentaje) in enumerate(zip(bars, 
                                                             tornado_df['Evento de Riesgo'],
                                                             tornado_df['Contribución Promedio'],
                                                             tornado_df['Porcentaje'])):
                    y_pos = bar.get_y() + bar.get_height() / 2
                    tooltip_label = f"{evento}\nContribución: {currency_format(contribucion)}\nPorcentaje: {porcentaje:.2f}%"
                    
                    # Determinar el color del tooltip según la posición/importancia en el gráfico
                    if i == num_eventos - 1:  # El evento más importante
                        color = MELI_AMARILLO
                    elif i == num_eventos - 2:  # Segundo evento más importante
                        color = MELI_AZUL_CORP
                    elif i == 0 and 'Otros eventos' in evento:
                        color = '#CCCCCC'
                    else:
                        color = None  # Usar el color por defecto
                    
                    canvas7.add_tooltip_data(ax7, [contribucion], [y_pos], 
                                         labels=[tooltip_label],
                                         highlight_color=color)
                
                # Añadir tooltip para la línea de la media
                media_tooltip = f"Contribución media: {currency_format(mean_contrib)}"
                # Encontrar un punto y adecuado para mostrar el tooltip de la media
                # Usamos la altura media del gráfico
                y_mid = len(tornado_df) / 2
                canvas7.add_tooltip_data(ax7, [mean_contrib], [y_mid], 
                                     labels=[media_tooltip], 
                                     highlight_color=MELI_ROJO)
                
                # Guardar referencias para actualización dinámica
                self.fig_contribucion = fig7
                self.canvas_contribucion = canvas7
                self.ax_contribucion = ax7
                
                tab10 = QtWidgets.QWidget()
                layout7 = QtWidgets.QVBoxLayout(tab10)
                
                # Panel de controles superiores con selector de percentil
                contrib_ctrls = QtWidgets.QWidget()
                contrib_ctrls_layout = QtWidgets.QHBoxLayout(contrib_ctrls)
                contrib_ctrls_layout.setContentsMargins(0, 0, 0, 0)
                
                lbl_percentil = QtWidgets.QLabel("Contribución al:")
                lbl_percentil.setStyleSheet("font-weight: bold;")
                self.combo_percentil_contrib = QtWidgets.QComboBox()
                self.combo_percentil_contrib.addItems([
                    "Media", "P75", "P80", "P90", "P95", "P99"
                ])
                self.combo_percentil_contrib.setToolTip(
                    "Seleccione el percentil para ver qué eventos contribuyen más\n"
                    "cuando la pérdida total está en ese nivel.\n"
                    "Ej: P90 muestra contribución en escenarios de cola severos."
                )
                self.combo_percentil_contrib.currentIndexChanged.connect(self.actualizar_grafico_contribucion)
                
                contrib_ctrls_layout.addWidget(lbl_percentil)
                contrib_ctrls_layout.addWidget(self.combo_percentil_contrib)
                contrib_ctrls_layout.addStretch()
                
                layout7.addWidget(contrib_ctrls)
                layout7.addWidget(canvas7)
                self.graficos_tab_widget.addTab(tab10, "Contribución")
                try:
                    curr = self.progress_bar.value()
                    self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
                    QtWidgets.QApplication.processEvents()
                except Exception:
                    pass

        # Gráfico 8: Box Plots por Evento de Riesgo
        fig8 = Figure(figsize=(9, 6))  # Tamaño optimizado para buena visualización
        canvas8 = InteractiveFigureCanvas(fig8)
        ax8 = fig8.add_subplot(111)
        # Preparar datos para boxplots por evento
        datos_perdidas = [perdidas_evento for perdidas_evento in perdidas_por_evento]
        nombres_eventos = [evento['nombre'] for evento in eventos_riesgo]
        
        # Configuración personalizada para los boxplots
        box_props = dict(linestyle='-', linewidth=1.2, color=MELI_AZUL_CORP)
        whisker_props = dict(linestyle='-', linewidth=1, color=MELI_AZUL_CORP)
        cap_props = dict(linestyle='-', linewidth=1, color=MELI_AZUL_CORP)
        median_props = dict(linestyle='-', linewidth=1.5, color=MELI_ROJO)
        flier_props = dict(marker='o', markerfacecolor=MELI_AMARILLO, markersize=4, alpha=0.7,
                          linestyle='none', markeredgecolor=MELI_AZUL)

        # Crear el box plot con estilo MercadoLibre
        box = ax8.boxplot(datos_perdidas, 
                       labels=nombres_eventos, 
                       vert=True, 
                       patch_artist=True, 
                       showfliers=False,  # Sin outliers para claridad
                       boxprops=box_props,
                       whiskerprops=whisker_props,
                       capprops=cap_props,
                       medianprops=median_props)
                       
        # Personalizar el color de cada caja con un gradiente de azul a amarillo
        for i, patch in enumerate(box['boxes']):
            # Degradado de color desde azul hasta amarillo
            ratio = i / max(1, len(datos_perdidas) - 1)
            color_hex = f'#{blend_colors(MELI_AZUL, MELI_AMARILLO, ratio)}'
            patch.set_facecolor(color_hex)
            patch.set_alpha(0.7)

        # Añadir una guía de interpretación
        interpretacion_text = "Caja: Q1-Q3\nLínea Roja: Mediana\nBigotes: Mín/Máx (sin outliers)"
        ax8.text(0.02, 0.97, interpretacion_text, transform=ax8.transAxes,
                fontsize=8, va='top', ha='left',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))

        # Título y etiquetas
        ax8.set_title('Distribución de Pérdidas por Evento de Riesgo')
        ax8.set_xlabel('Evento de Riesgo')
        ax8.set_ylabel('Pérdida')
        
        # Formateo de ejes
        ax8.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
        
        # Ajustar etiquetas del eje X para mejor legibilidad
        plt.setp(ax8.get_xticklabels(), rotation=45, ha='right', rotation_mode='anchor')
        
        # Si hay muchos eventos, limitar las etiquetas visibles
        if len(nombres_eventos) > 10:
            for i, tick in enumerate(ax8.xaxis.get_major_ticks()):
                if i % 2 != 0 and i < len(nombres_eventos) - 1:
                    tick.label1.set_visible(False)  # Matplotlib 3.9+ usa label1
        
        # Aplicar estilo MercadoLibre
        aplicar_estilo_meli(ax8)
        
        # Asegurar espacio para etiquetas rotadas
        fig8.tight_layout()
        
        # Configurar tooltips para el box plot por evento de riesgo
        # Para cada box plot, añadir tooltips con la información estadística
        for i, (evento_data, nombre_evento) in enumerate(zip(datos_perdidas, nombres_eventos)):
            if len(evento_data) > 0:
                # Calcular estadísticos clave para los tooltips
                min_val = np.min(evento_data)
                p25 = np.percentile(evento_data, 25)
                median_val = np.median(evento_data)
                p75 = np.percentile(evento_data, 75)
                max_val = np.max(evento_data)
                mean_val = np.mean(evento_data)
                p90 = np.percentile(evento_data, 90)
                p95 = np.percentile(evento_data, 95)
                
                # Crear las etiquetas para los tooltips
                labels = [
                    f"{nombre_evento}\nMínimo: {currency_format(min_val)}",
                    f"{nombre_evento}\nQ1 (P25): {currency_format(p25)}",
                    f"{nombre_evento}\nMediana: {currency_format(median_val)}",
                    f"{nombre_evento}\nQ3 (P75): {currency_format(p75)}",
                    f"{nombre_evento}\nMáximo: {currency_format(max_val)}"
                ]
                
                # Datos para los tooltips: el eje X es la posición del box plot (1-indexed)
                x_pos = i + 1
                y_values = [min_val, p25, median_val, p75, max_val]
                x_values = [x_pos] * len(y_values)
                
                # Añadir los tooltips principales del boxplot
                canvas8.add_tooltip_data(ax8, x_values, y_values, labels=labels)
                
                # Añadir tooltips para percentiles especiales (90, 95)
                canvas8.add_tooltip_data(ax8, [x_pos, x_pos], [p90, p95],
                                     labels=[f"{nombre_evento}\nP90: {currency_format(p90)}", 
                                             f"{nombre_evento}\nP95: {currency_format(p95)}"],
                                     highlight_color=MELI_VERDE)
                
                # Añadir tooltip para la media
                canvas8.add_tooltip_data(ax8, [x_pos], [mean_val],
                                     labels=[f"{nombre_evento}\nMedia: {currency_format(mean_val)}"],
                                     highlight_color=MELI_AMARILLO)

        tab11 = QtWidgets.QWidget()
        layout8 = QtWidgets.QVBoxLayout(tab11)
        layout8.addWidget(canvas8)
        self.graficos_tab_widget.addTab(tab11, "Perd por Evento")
        try:
            curr = self.progress_bar.value()
            self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
        except Exception:
            pass

        # Cálculo de perdidas_cola
        percentil_80 = np.percentile(perdidas_totales, 80)
        perdidas_cola = perdidas_totales[perdidas_totales >= percentil_80]

        # Gráfico 9: Cola de Pérdidas (Tail Risk)
        fig10 = Figure(figsize=(8, 5))
        canvas10 = InteractiveFigureCanvas(fig10)
        ax10 = fig10.add_subplot(111)
        
        # Usar color rojo de MELI para resaltar el riesgo de la cola
        sns.histplot(perdidas_cola, bins=30, kde=True, 
                    color=MELI_ROJO, edgecolor='white', linewidth=0.5,
                    alpha=0.75, ax=ax10)
        
        # Calcular estadísticas de la cola
        media_cola = np.mean(perdidas_cola)
        mediana_cola = np.median(perdidas_cola)
        p95_cola = np.percentile(perdidas_cola, 95)
        p99_cola = np.percentile(perdidas_cola, 99)
        
        # Percentiles clave para toda la distribución
        percentiles_cola = np.percentile(perdidas_totales, [90, 95, 99])
        colores_percentiles = [MELI_AZUL_CORP, MELI_VERDE, MELI_ROJO]
        labels_percentiles = ['P90', 'P95', 'P99']
        
        # Añadir líneas de referencia con estilo MELI
        for p, color, label in zip(percentiles_cola, colores_percentiles, labels_percentiles):
            ax10.axvline(x=p, color=color, linestyle='--', linewidth=1.5, alpha=0.8)
        
        # Estadísticas de la cola como texto
        stats_text = f"Mediana: {currency_format(mediana_cola)}\nMedia: {currency_format(media_cola)}"
        ax10.text(0.97, 0.97, stats_text, transform=ax10.transAxes,
                fontsize=8, va='top', ha='right',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
        
        # Información sobre los percentiles
        percentil_text = (
            f"P90: {currency_format(percentiles_cola[0])}\n"
            f"P95: {currency_format(percentiles_cola[1])}\n"
            f"P99: {currency_format(percentiles_cola[2])}"
        )
        ax10.text(0.03, 0.97, percentil_text, transform=ax10.transAxes,
                fontsize=8, va='top', ha='left', color=MELI_GRIS_SECUNDARIO,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
        
        # Mejorar títulos y etiquetas
        ax10.set_title('Cola de Pérdidas (Percentil 80-100)')
        ax10.set_xlabel('Pérdida Total')
        ax10.set_ylabel('Frecuencia')
        
        # Formatear ejes
        ax10.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
        ax10.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:,}'.format(int(y)).replace(",", ".")))
        
        # Aplicar estilo MercadoLibre
        aplicar_estilo_meli(ax10)
        fig10.tight_layout()
        
        # Añadir tooltips para la cola de pérdidas
        # Obtener los datos del histograma para posicionar tooltips en las barras
        n_bins = 30  # Mismo número de bins usado en el histplot
        hist, bin_edges = np.histogram(perdidas_cola, bins=n_bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # Crear puntos para tooltips en barras significativas
        for i, (count, x_pos) in enumerate(zip(hist, bin_centers)):
            if count > 0:
                # Para cada barra del histograma, mostrar el rango y la frecuencia
                lower_bound = bin_edges[i]
                upper_bound = bin_edges[i+1]
                porcentaje = (count / len(perdidas_cola)) * 100
                
                tooltip_text = (
                    f"Rango: {currency_format(lower_bound)} - {currency_format(upper_bound)}\n"
                    f"Frecuencia: {count:,}\n"
                    f"Porcentaje: {porcentaje:.2f}%"
                ).replace(",", ".")
                
                # Añadir tooltip para esta barra
                canvas10.add_tooltip_data(ax10, [x_pos], [count/2],  # Posición en el medio de la barra
                                      labels=[tooltip_text])
        
        # Añadir tooltips para los percentiles clave
        try:
            kde_cola = gaussian_kde(perdidas_cola)
        except Exception:
            kde_cola = None
        for p, color, label in zip(percentiles_cola, colores_percentiles, labels_percentiles):
            # Estimar la altura del punto para el tooltip
            if kde_cola is not None:
                altura_kde = kde_cola(p)[0] * len(perdidas_cola) * (bin_edges[-1] - bin_edges[0]) / n_bins
            else:
                altura_kde = 0
            
            # Añadir tooltip para este percentil
            percentile_text = f"{label}: {currency_format(p)}\n"
            
            # Interpretar el percentil
            if label == 'P90':
                percentile_text += "90% de las simulaciones están por debajo de este valor"
            elif label == 'P95':
                percentile_text += "Valor de pérdida con 5% de probabilidad de excedencia"
            elif label == 'P99':
                percentile_text += "Escenario extremo (1% de probabilidad)"
                
            canvas10.add_tooltip_data(ax10, [p], [altura_kde], 
                                  labels=[percentile_text],
                                  highlight_color=color)
        
        # Añadir tooltips para estadísticas clave
        canvas10.add_tooltip_data(ax10, [media_cola], [len(perdidas_cola)/n_bins/2],
                              labels=[f"Media de la cola: {currency_format(media_cola)}"],
                              highlight_color=MELI_AMARILLO)
        
        canvas10.add_tooltip_data(ax10, [mediana_cola], [len(perdidas_cola)/n_bins/3],
                              labels=[f"Mediana de la cola: {currency_format(mediana_cola)}"],
                              highlight_color=MELI_AZUL_CORP)
        
        tab12 = QtWidgets.QWidget()
        layout10 = QtWidgets.QVBoxLayout(tab12)
        layout10.addWidget(canvas10)
        self.graficos_tab_widget.addTab(tab12, "Tail Risk")
        try:
            curr = self.progress_bar.value()
            self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
        except Exception:
            pass

# --- INICIO: Nuevo Gráfico - Mapa de Riesgos Mejorado (Jerarquía Visual y Cuadrantes) ---
        try:
            if len(eventos_riesgo) > 0 and len(perdidas_por_evento) == len(eventos_riesgo) and len(frecuencias_por_evento) == len(eventos_riesgo):

                # 1. Preparar datos para el gráfico con cálculos mejorados
                data_riesgos = []
                for idx, evento in enumerate(eventos_riesgo):
                    nombre = evento['nombre']
                    # Usar una copia para evitar modificar los arrays originales
                    perdidas_evt = np.array(perdidas_por_evento[idx])
                    frecuencias_evt = np.array(frecuencias_por_evento[idx])

                    # Cálculos de impacto
                    impacto_medio = np.mean(perdidas_evt) if len(perdidas_evt) > 0 else 0
                    impacto_p90 = np.percentile(perdidas_evt, 90) if len(perdidas_evt) > 0 else 0

                    # Cálculo de Frecuencia MODO (Valor más frecuente)
                    if len(frecuencias_evt) > 0:
                        mode_result = stats.mode(frecuencias_evt, keepdims=True)
                        frecuencia_modo = float(mode_result.mode[0]) if mode_result.mode.size > 0 else 0
                        # Añadir también frecuencia media para comparación
                        frecuencia_media = np.mean(frecuencias_evt) 
                    else:
                        frecuencia_modo = 0
                        frecuencia_media = 0

                    # Actualizar Importancia usando P90 * Frecuencia MODO para mejor representación del riesgo
                    # Esto da más peso a los escenarios severos pero probables
                    importancia = (impacto_p90 * frecuencia_modo) + 1e-9  # Epsilon para evitar tamaño cero

                    data_riesgos.append({
                        'Nombre': nombre,
                        'ImpactoMedio': impacto_medio,
                        'ImpactoP90': impacto_p90,
                        'FrecuenciaModo': frecuencia_modo,
                        'FrecuenciaMedia': frecuencia_media,
                        'Importancia': importancia
                    })

                # 2. Crear DataFrame
                df_riesgos = pd.DataFrame(data_riesgos)

                # Asegurarnos de que no haya valores negativos o cero donde no deben
                df_riesgos['Importancia'] = df_riesgos['Importancia'].clip(lower=1e-9)
                df_riesgos['ImpactoP90'] = df_riesgos['ImpactoP90'].clip(lower=0)
                df_riesgos['ImpactoMedio'] = df_riesgos['ImpactoMedio'].clip(lower=0)
                df_riesgos['FrecuenciaModo'] = df_riesgos['FrecuenciaModo'].clip(lower=0)

                # 3. Generar Gráfico Scatterplot Mejorado
                fig_mapa = Figure(figsize=(11, 8))  # Tamaño aumentado para mejor visualización
                canvas_mapa = InteractiveFigureCanvas(fig_mapa)
                
                # Usar gridspec para definir la estructura del gráfico con mejor control
                gs = fig_mapa.add_gridspec(1, 20, wspace=0.5)  # 20 columnas para control fino
                ax_mapa = fig_mapa.add_subplot(gs[0, :16])     # Gráfico principal: 16/20 del ancho
                cax = fig_mapa.add_subplot(gs[0, 17:19])       # Barra de color: 2/20 del ancho

                # Crear el scatterplot con visualización mejorada
                scatter = sns.scatterplot(
                    data=df_riesgos,
                    x='ImpactoMedio',
                    y='FrecuenciaModo',
                    size='Importancia',
                    hue='ImpactoP90',
                    palette='RdYlGn_r',     # Paleta Verde(bajo)->Rojo(alto)
                    sizes=(50, 1500),       # Rango de tamaño
                    alpha=0.75,             # Transparencia
                    legend=False,           # Quitar leyendas automáticas
                    ax=ax_mapa
                )
                
                # Agregar tooltips interactivos para el mapa de riesgos
                for i, row in df_riesgos.iterrows():
                    tooltip_text = (
                        f"Evento: {row['Nombre']}\n"
                        f"Impacto Medio: {currency_format(row['ImpactoMedio'])}\n"
                        f"Impacto P90: {currency_format(row['ImpactoP90'])}\n"
                        f"Frecuencia Modo: {row['FrecuenciaModo']:.0f}\n"
                        f"Frecuencia Media: {row['FrecuenciaMedia']:.2f}\n"
                        f"Importancia: {row['Importancia']:.0f}"
                    )
                    
                    # Determinar color del tooltip según la importancia del riesgo
                    # Los eventos más importantes reciben colores destacados
                    highlight_color = None
                    if row['Importancia'] == df_riesgos['Importancia'].max():
                        highlight_color = MELI_ROJO
                    elif row['Importancia'] >= df_riesgos['Importancia'].quantile(0.75):
                        highlight_color = MELI_AMARILLO
                    
                    canvas_mapa.add_tooltip_data(
                        ax_mapa, 
                        [row['ImpactoMedio']], 
                        [row['FrecuenciaModo']],
                        labels=[tooltip_text],
                        highlight_color=highlight_color
                    )

                # 4. Mejorar la visualización con cuadrantes de riesgo
                if not df_riesgos.empty:
                    # Usar percentiles de los datos para los umbrales de cuadrantes
                    umbral_x = df_riesgos['ImpactoMedio'].median() * 1.2  # Ajustado hacia arriba
                    umbral_y = df_riesgos['FrecuenciaModo'].median() * 1.2
                    
                    # Asegurar que los umbrales no sean cero
                    umbral_x = max(umbral_x, df_riesgos['ImpactoMedio'].max() * 0.3)
                    umbral_y = max(umbral_y, df_riesgos['FrecuenciaModo'].max() * 0.3)
                    
                    # Calcular límites máximos para posicionar etiquetas
                    max_x = df_riesgos['ImpactoMedio'].max() * 1.1
                    max_y = df_riesgos['FrecuenciaModo'].max() * 1.1
                    
                    # Líneas de cuadrantes con estilo mejorado
                    ax_mapa.axvline(x=umbral_x, color='gray', linestyle='--', alpha=0.5)
                    ax_mapa.axhline(y=umbral_y, color='gray', linestyle='--', alpha=0.5)
                    
                    # Etiquetar cuadrantes con más claridad
                    ax_mapa.text(max_x * 0.2, max_y * 0.9, "IMPACTO BAJO\nFRECUENCIA ALTA", 
                             ha='center', fontsize=8, alpha=0.7, color='darkblue',
                             bbox=dict(facecolor='white', alpha=0.4, edgecolor='none'))
                    ax_mapa.text(max_x * 0.8, max_y * 0.9, "IMPACTO ALTO\nFRECUENCIA ALTA", 
                             ha='center', fontsize=8, alpha=0.7, color='darkred',
                             bbox=dict(facecolor='white', alpha=0.4, edgecolor='none'))
                    ax_mapa.text(max_x * 0.2, max_y * 0.1, "IMPACTO BAJO\nFRECUENCIA BAJA", 
                             ha='center', fontsize=8, alpha=0.7, color='darkgreen',
                             bbox=dict(facecolor='white', alpha=0.4, edgecolor='none'))
                    ax_mapa.text(max_x * 0.8, max_y * 0.1, "IMPACTO ALTO\nFRECUENCIA BAJA", 
                             ha='center', fontsize=8, alpha=0.7, color='darkorange',
                             bbox=dict(facecolor='white', alpha=0.4, edgecolor='none'))

                # 5. Personalizar Gráfico Principal con mejor jerarquía visual
                ax_mapa.set_title('Mapa de Riesgos: Análisis Jerárquico de Impacto y Frecuencia', fontsize=14)
                ax_mapa.set_xlabel('Impacto Económico Promedio', fontsize=11)
                ax_mapa.set_ylabel('Frecuencia Anual Más Probable (Modo)', fontsize=11)
                ax_mapa.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
                ax_mapa.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{int(y)}'))
                
                # Ajustar límites y rejilla para mejor visualización
                min_x = df_riesgos['ImpactoMedio'].min() if not df_riesgos.empty else 0
                min_y = df_riesgos['FrecuenciaModo'].min() if not df_riesgos.empty else 0
                ax_mapa.set_xlim(left=max(0, min_x * 0.9))
                ax_mapa.set_ylim(bottom=max(0, min_y * 0.9))
                ax_mapa.grid(True, linestyle='--', alpha=0.4)  # Rejilla más sutil

                # 6. Añadir anotaciones con Nombre y P90 (manteniendo formato actual)
                n_top_riesgos = 7  # Anotar los N más importantes por tamaño
                if not df_riesgos.empty:
                    df_riesgos_sorted = df_riesgos.nlargest(min(n_top_riesgos, len(df_riesgos)), 'Importancia')

                    for i, row in df_riesgos_sorted.iterrows():
                        # Mantener formato actual de etiqueta con nombre y P90
                        label_texto = f"{row['Nombre']}\nP90: {currency_format(row['ImpactoP90'])}"
                        
                        # Mejorar la apariencia de las etiquetas con flechas para evitar solapamientos
                        ax_mapa.annotate(
                            label_texto,
                            xy=(row['ImpactoMedio'], row['FrecuenciaModo']),  # Posición del punto
                            xytext=(15, 0),  # Offset desde el punto
                            textcoords="offset points",
                            fontsize=8,
                            ha='left', va='center',
                            bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.85, ec='grey', lw=0.5),
                            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.2', color='grey', alpha=0.7)
                        )

                # 7. Crear Barra de Color para Leyenda de P90 (hue)
                if not df_riesgos.empty:
                    norm = plt.Normalize(df_riesgos['ImpactoP90'].min(), df_riesgos['ImpactoP90'].max())
                    cmap = plt.get_cmap("RdYlGn_r")  # Colormap: Verde(bajo)->Rojo(alto)
            else:
                frecuencia_modo = 0
                frecuencia_media = 0

            # Actualizar Importancia usando P90 * Frecuencia MODO para mejor representación del riesgo
            # Esto da más peso a los escenarios severos pero probables
            importancia = (impacto_p90 * frecuencia_modo) + 1e-9  # Epsilon para evitar tamaño cero
        except ImportError:
            # Manejo específico si falta SciPy
            print("Error: Se requiere SciPy para calcular el modo. Instala SciPy: pip install scipy")
            # Mostrar mensaje al usuario en la GUI
            QtWidgets.QMessageBox.warning(self, "Dependencia Faltante",
                                          "Se requiere la librería SciPy para usar la frecuencia modo en el Mapa de Riesgos.\n"
                                          "Por favor, instálala (ej: pip install scipy) y reinicia la aplicación.\n"
                                          "El gráfico no se generará en esta sesión.")
        except Exception as e:
            # Capturar otros errores
            print(f"Error al generar el Mapa de Riesgos Mejorado: {e}")
            error_message_mapa = traceback.format_exc()
            print(error_message_mapa)

# --- FIN: Nuevo Gráfico - Mapa de Riesgos Mejorado ---

        # Gráfico de Velocímetro/Gauge de Riesgo con umbrales fijos
        from matplotlib.patches import Wedge, FancyArrow, Circle, FancyBboxPatch
        import math
        
        fig_term = Figure(figsize=(10, 6))
        canvas_term = InteractiveFigureCanvas(fig_term)
        ax_term = fig_term.add_subplot(111)

        # Definir umbrales de riesgo FIJOS
        umbral_bajo = 3_000_000        # Bajo: menos de 3 millones
        umbral_moderado = 32_000_000   # Moderado: entre 3 y 32 millones
        umbral_alto = 110_000_000      # Alto: entre 32 y 110 millones
        # Crítico: más de 110 millones

        # Calcular estadísticas de la distribución para contextualizar
        perdida_media = np.mean(perdidas_totales)
        perdida_mediana = np.median(perdidas_totales)
        p90 = np.percentile(perdidas_totales, 90)
        p99 = np.percentile(perdidas_totales, 99)

        # Definir un máximo para la escala (usar máximo entre p99 y 120% del umbral crítico)
        max_escala = max(p99, umbral_alto * 1.2)

        # Colores para las zonas del velocímetro
        colores = ['#4CAF50', '#FFC107', '#FF9800', '#F44336']  # Verde, amarillo, naranja, rojo
        etiquetas = ['BAJO', 'MODERADO', 'ALTO', 'CRÍTICO']
        
        # Configuración del velocímetro
        centro = (0, 0)
        radio_ext = 1.0
        radio_int = 0.6
        angulo_inicio = 180  # Grados (izquierda)
        angulo_fin = 0       # Grados (derecha)
        
        # Calcular ángulos para cada zona basándose en los umbrales
        def valor_a_angulo(valor):
            """Convierte un valor de pérdida a un ángulo en el velocímetro"""
            proporcion = min(valor / max_escala, 1.0)
            return angulo_inicio - proporcion * (angulo_inicio - angulo_fin)
        
        # Definir los límites de ángulo para cada zona
        angulos_zona = [
            (angulo_inicio, valor_a_angulo(umbral_bajo)),      # Bajo
            (valor_a_angulo(umbral_bajo), valor_a_angulo(umbral_moderado)),   # Moderado
            (valor_a_angulo(umbral_moderado), valor_a_angulo(umbral_alto)),   # Alto
            (valor_a_angulo(umbral_alto), angulo_fin)          # Crítico
        ]
        
        # Dibujar las zonas del velocímetro como arcos
        for i, ((ang_inicio, ang_fin), color, etiqueta) in enumerate(zip(angulos_zona, colores, etiquetas)):
            # Crear el arco exterior
            wedge = Wedge(
                centro, radio_ext, ang_fin, ang_inicio,
                width=radio_ext - radio_int,
                facecolor=color, edgecolor='white', linewidth=2, alpha=0.85
            )
            ax_term.add_patch(wedge)
            
            # Añadir etiqueta de la zona en el centro del arco
            angulo_medio = (ang_inicio + ang_fin) / 2
            radio_texto = (radio_ext + radio_int) / 2
            x_texto = radio_texto * math.cos(math.radians(angulo_medio))
            y_texto = radio_texto * math.sin(math.radians(angulo_medio))
            
            # Calcular probabilidad de esta zona
            if i == 0:
                prob = len(perdidas_totales[perdidas_totales < umbral_bajo]) / len(perdidas_totales) * 100
            elif i == 1:
                prob = len(perdidas_totales[(perdidas_totales >= umbral_bajo) & (perdidas_totales < umbral_moderado)]) / len(perdidas_totales) * 100
            elif i == 2:
                prob = len(perdidas_totales[(perdidas_totales >= umbral_moderado) & (perdidas_totales < umbral_alto)]) / len(perdidas_totales) * 100
            else:
                prob = len(perdidas_totales[perdidas_totales >= umbral_alto]) / len(perdidas_totales) * 100
            
            ax_term.text(x_texto, y_texto, f'{etiqueta}\n({prob:.1f}%)',
                        ha='center', va='center', fontsize=9, fontweight='bold',
                        color='white' if i >= 2 else 'black')
        
        # Añadir marcas de umbral en el borde exterior
        for umbral, etiqueta_umbral in [(0, '$0'), (umbral_bajo, currency_format(umbral_bajo)), 
                                         (umbral_moderado, currency_format(umbral_moderado)),
                                         (umbral_alto, currency_format(umbral_alto)),
                                         (max_escala, currency_format(max_escala))]:
            angulo = valor_a_angulo(umbral)
            # Marca pequeña
            x1 = radio_ext * math.cos(math.radians(angulo))
            y1 = radio_ext * math.sin(math.radians(angulo))
            x2 = (radio_ext + 0.08) * math.cos(math.radians(angulo))
            y2 = (radio_ext + 0.08) * math.sin(math.radians(angulo))
            ax_term.plot([x1, x2], [y1, y2], 'k-', linewidth=2)
            
            # Etiqueta del valor
            x_label = (radio_ext + 0.18) * math.cos(math.radians(angulo))
            y_label = (radio_ext + 0.18) * math.sin(math.radians(angulo))
            ax_term.text(x_label, y_label, etiqueta_umbral, ha='center', va='center', fontsize=7)
        
        # Dibujar la aguja principal (pérdida media)
        angulo_media = valor_a_angulo(perdida_media)
        longitud_aguja = radio_int - 0.05
        x_aguja = longitud_aguja * math.cos(math.radians(angulo_media))
        y_aguja = longitud_aguja * math.sin(math.radians(angulo_media))
        
        # Aguja como línea gruesa
        ax_term.annotate('', xy=(x_aguja, y_aguja), xytext=centro,
                        arrowprops=dict(arrowstyle='->', color=MELI_AZUL, lw=4))
        
        # Centro de la aguja (círculo)
        circulo_centro = Circle(centro, 0.08, facecolor=MELI_AZUL, edgecolor='white', linewidth=2, zorder=10)
        ax_term.add_patch(circulo_centro)
        
        # Marcadores adicionales para P90 y P99 como líneas en el arco
        for valor, color_marca, nombre in [(p90, '#9C27B0', 'P90'), (p99, '#E91E63', 'P99')]:
            angulo_marca = valor_a_angulo(valor)
            # Línea de marca
            x1 = radio_int * math.cos(math.radians(angulo_marca))
            y1 = radio_int * math.sin(math.radians(angulo_marca))
            x2 = radio_ext * math.cos(math.radians(angulo_marca))
            y2 = radio_ext * math.sin(math.radians(angulo_marca))
            ax_term.plot([x1, x2], [y1, y2], color=color_marca, linewidth=3, zorder=5)
            
            # Etiqueta
            x_label = (radio_ext + 0.12) * math.cos(math.radians(angulo_marca))
            y_label = (radio_ext + 0.12) * math.sin(math.radians(angulo_marca))
            ax_term.text(x_label, y_label, nombre, ha='center', va='center', 
                        fontsize=8, fontweight='bold', color=color_marca)

        # Determinar categoría de riesgo actual
        if perdida_media < umbral_bajo:
            categoria_actual = "BAJO"
            color_categoria = colores[0]
        elif perdida_media < umbral_moderado:
            categoria_actual = "MODERADO"
            color_categoria = colores[1]
        elif perdida_media < umbral_alto:
            categoria_actual = "ALTO"
            color_categoria = colores[2]
        else:
            categoria_actual = "CRÍTICO"
            color_categoria = colores[3]

        # Panel central con información
        ax_term.text(0, -0.25, f'NIVEL DE RIESGO', ha='center', va='center',
                    fontsize=10, fontweight='bold', color='gray')
        ax_term.text(0, -0.42, categoria_actual, ha='center', va='center',
                    fontsize=16, fontweight='bold', color=color_categoria,
                    bbox=dict(facecolor='white', edgecolor=color_categoria, 
                             boxstyle='round,pad=0.3', linewidth=2))
        
        # Valor de la media debajo
        ax_term.text(0, -0.62, f'Media: {currency_format(perdida_media)}', ha='center', va='center',
                    fontsize=11, fontweight='bold', color=MELI_AZUL)

        # Configurar el gráfico
        ax_term.set_xlim(-1.3, 1.3)
        ax_term.set_ylim(-0.9, 1.4)
        ax_term.set_aspect('equal')
        ax_term.axis('off')
        ax_term.set_title('Velocímetro de Riesgo', fontsize=14, fontweight='bold', pad=10)
        
        # Ajustar márgenes
        fig_term.tight_layout()

        # Integrar en la interfaz
        tab_term = QtWidgets.QWidget()
        layout_term = QtWidgets.QVBoxLayout(tab_term)
        layout_term.addWidget(canvas_term)
        self.graficos_tab_widget.addTab(tab_term, "Termómetro")
        try:
            curr = self.progress_bar.value()
            self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
        except Exception:
            pass
        
        # Gráfico de Semáforo de Impacto con Umbrales Fijos
        fig_semaforo = Figure(figsize=(10, 5))  # Tamaño mejorado para visualización
        canvas_semaforo = InteractiveFigureCanvas(fig_semaforo)
        ax_semaforo = fig_semaforo.add_subplot(111)
        
        # Usar los mismos umbrales fijos que en el termómetro de riesgo
        umbral_bajo = 3_000_000        # Bajo: menos de 3 millones
        umbral_moderado = 32_000_000   # Moderado: entre 3 y 32 millones
        umbral_alto = 110_000_000      # Alto: entre 32 y 110 millones
        # Crítico: más de 110 millones
        
        # Calcular los percentiles P90 y P99 para referencia
        p90 = np.percentile(perdidas_totales, 90)
        p99 = np.percentile(perdidas_totales, 99)
        
        # Definir rangos con los umbrales fijos
        rangos = [
            (0, umbral_bajo, "Bajo"),
            (umbral_bajo, umbral_moderado, "Moderado"),
            (umbral_moderado, umbral_alto, "Alto"),
            (umbral_alto, np.max(perdidas_totales), "Crítico")
        ]
        
        # Calcular probabilidad para cada rango con visualización mejorada
        probabilidades = []
        etiquetas_detalladas = []
        
        for min_val, max_val, etiqueta in rangos:
            # Calcular el porcentaje de simulaciones en este rango
            mask = (perdidas_totales >= min_val) & (perdidas_totales < max_val)
            prob = len(perdidas_totales[mask]) / len(perdidas_totales)
            probabilidades.append(prob * 100)  # Convertir a porcentaje
            
            # Crear etiquetas detalladas con rango monetario
            if etiqueta == "Bajo":
                detalle = f"Menos de {currency_format(umbral_bajo)}"
            elif etiqueta == "Crítico":
                detalle = f"Más de {currency_format(umbral_alto)}"
            else:
                detalle = f"{currency_format(min_val)} - {currency_format(max_val)}"
                
            etiquetas_detalladas.append(f"{etiqueta}\n{detalle}")
        
        # Colores consistentes con el termómetro de riesgo
        colores_semaforo = ['#90EE90', '#FFFF66', '#FFA500', '#DC143C']  # Verde, amarillo, naranja, rojo

        # Crear gráfico de barras con etiquetas mejoradas
        bars = ax_semaforo.barh(etiquetas_detalladas, probabilidades, color=colores_semaforo, edgecolor='black', alpha=0.8, height=0.6)

        # Agregar etiquetas de porcentaje dentro de las barras con mejor formato
        for bar, porcentaje in zip(bars, probabilidades):
            width = bar.get_width()
            if width >= 5:  # Reducido para mostrar más etiquetas
                ax_semaforo.text(width / 2, bar.get_y() + bar.get_height() / 2,
                              f"{porcentaje:.1f}%",
                              ha='center', va='center', fontweight='bold',
                              bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
            else:
                # Para barras muy pequeñas, colocar la etiqueta a la derecha
                ax_semaforo.text(width + 1, bar.get_y() + bar.get_height() / 2,
                              f"{porcentaje:.1f}%",
                              ha='left', va='center', fontsize=8)

        # No incluir las referencias de P90 y P99

        # Personalizar gráfico con mejor estilo
        ax_semaforo.set_xlabel('Probabilidad (%)', fontsize=11)
        ax_semaforo.set_title('Probabilidad por Nivel de Impacto', fontsize=14)
        ax_semaforo.set_xlim(0, max(110, max(probabilidades) * 1.2))  # Dar espacio para etiquetas
        ax_semaforo.grid(axis='x', linestyle='--', alpha=0.4)  # Rejilla más sutil
        
        # Resaltar el nivel donde cae la pérdida media
        nivel_actual = ""
        for i, (min_val, max_val, etiqueta) in enumerate(rangos):
            if min_val <= perdida_media < max_val:
                nivel_actual = etiqueta
                # Resaltar la barra correspondiente
                bars[i].set_alpha(1.0)  # Mayor opacidad
                bars[i].set_edgecolor('blue')  # Borde azul
                bars[i].set_linewidth(2)  # Borde más grueso
                # Añadir texto destacando que es el nivel actual
                ax_semaforo.text(
                    probabilidades[i] + 2, i,
                    f"Nivel Actual: {nivel_actual}",
                    va='center', ha='left', fontsize=10,
                    fontweight='bold', color='blue',
                    bbox=dict(facecolor='white', alpha=0.9, edgecolor='blue', boxstyle='round,pad=0.3')
                )

        # No incluir leyenda explicativa
        
        fig_semaforo.tight_layout()  # Ajustar layout sin espacio adicional para leyenda

        tab14 = QtWidgets.QWidget()
        layout_semaforo = QtWidgets.QVBoxLayout(tab14)
        layout_semaforo.addWidget(canvas_semaforo)
        self.graficos_tab_widget.addTab(tab14, "Semáforo")
        try:
            curr = self.progress_bar.value()
            self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
        except Exception:
            pass

        # Gráfico "¿Qué pasaría si...?" - Comparativa de escenarios (formato horizontal)
        fig_escenarios = Figure(figsize=(10, 5))
        canvas_escenarios = InteractiveFigureCanvas(fig_escenarios)
        ax_escenarios = fig_escenarios.add_subplot(111)

        # Obtener pérdidas para diferentes percentiles (ordenados de menor a mayor impacto)
        escenarios = [
            ("Típico (Media)", np.mean(perdidas_totales), "50% prob.", '#4CAF50'),
            ("Adverso (P90)", np.percentile(perdidas_totales, 90), "10% prob.", '#FFC107'),
            ("Muy Adverso (P95)", np.percentile(perdidas_totales, 95), "5% prob.", '#FF9800'),
            ("Extremo (P99)", np.percentile(perdidas_totales, 99), "1% prob.", '#F44336')
        ]

        # Extraer datos
        nombres = [e[0] for e in escenarios]
        valores = [e[1] for e in escenarios]
        probabilidades = [e[2] for e in escenarios]
        colores_barras = [e[3] for e in escenarios]

        # Posiciones de las barras (Extremo arriba, Típico abajo)
        y_pos = np.arange(len(escenarios))

        # Crear gráfico de barras horizontales
        bars = ax_escenarios.barh(y_pos, valores, color=colores_barras, height=0.6, 
                                   edgecolor='white', linewidth=1.5)

        # Añadir etiquetas de valor al final de cada barra
        max_valor = max(valores)
        for bar, prob in zip(bars, probabilidades):
            width = bar.get_width()
            # Valor de la pérdida
            ax_escenarios.text(width + max_valor * 0.02, bar.get_y() + bar.get_height()/2,
                              f'{currency_format(width)}',
                              ha='left', va='center', fontsize=11, fontweight='bold')
            # Probabilidad de excedencia
            ax_escenarios.text(width + max_valor * 0.02, bar.get_y() + bar.get_height()/2 - 0.18,
                              f'({prob})',
                              ha='left', va='top', fontsize=9, color='gray')

        # Configurar eje Y con nombres de escenarios
        ax_escenarios.set_yticks(y_pos)
        ax_escenarios.set_yticklabels(nombres, fontsize=11)

        # Personalizar gráfico
        ax_escenarios.set_xlabel('Impacto Económico Potencial', fontsize=11)
        ax_escenarios.set_title('¿Qué impacto habría si se materializara el riesgo?', 
                               fontsize=14, fontweight='bold', pad=15)
        ax_escenarios.set_xlim(0, max_valor * 1.35)  # Espacio para etiquetas
        ax_escenarios.set_ylim(-0.8, len(escenarios) - 0.4)  # Espacio para etiqueta de tolerancia
        ax_escenarios.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
        
        # Estilo limpio
        ax_escenarios.spines['top'].set_visible(False)
        ax_escenarios.spines['right'].set_visible(False)
        ax_escenarios.spines['left'].set_visible(False)
        ax_escenarios.tick_params(left=False)
        ax_escenarios.grid(axis='x', linestyle='--', alpha=0.3)

        # Crear línea de tolerancia (inicialmente oculta, se muestra con checkbox)
        try:
            T = float(self.tolerancia_ex_spin.value()) if hasattr(self, 'tolerancia_ex_spin') else float(np.percentile(perdidas_totales, 90))
        except Exception:
            T = float(np.percentile(perdidas_totales, 90))
        
        self.ax_escenarios_tol_line = ax_escenarios.axvline(x=T, color='#E91E63', linestyle='--', 
                                                            linewidth=2.5, alpha=0.9, zorder=5)
        self.ax_escenarios_tol_label = ax_escenarios.text(T, -0.6, 
                                                          f'Tolerancia\n{currency_format(T)}',
                                                          ha='center', va='top', color='#E91E63', 
                                                          fontweight='bold', fontsize=9,
                                                          bbox=dict(facecolor='white', alpha=0.9, 
                                                                   edgecolor='#E91E63', boxstyle='round,pad=0.3'))
        # Inicialmente oculto
        self.ax_escenarios_tol_line.set_visible(False)
        self.ax_escenarios_tol_label.set_visible(False)
        
        # Guardar referencias para actualización
        self.ax_escenarios = ax_escenarios
        self.canvas_escenarios = canvas_escenarios

        fig_escenarios.tight_layout()

        # Pestaña con checkbox para tolerancia
        tab15 = QtWidgets.QWidget()
        layout_escenarios = QtWidgets.QVBoxLayout(tab15)
        
        # Controles superiores
        escenarios_ctrls = QtWidgets.QWidget()
        escenarios_ctrls_layout = QtWidgets.QHBoxLayout(escenarios_ctrls)
        escenarios_ctrls_layout.setContentsMargins(0, 0, 0, 0)
        
        self.cb_tol_line_escenarios = QtWidgets.QCheckBox("Mostrar límite de tolerancia")
        self.cb_tol_line_escenarios.setChecked(False)
        self.cb_tol_line_escenarios.toggled.connect(self.actualizar_linea_tolerancia_graficos)
        escenarios_ctrls_layout.addWidget(self.cb_tol_line_escenarios)
        escenarios_ctrls_layout.addStretch()
        
        layout_escenarios.addWidget(escenarios_ctrls)
        layout_escenarios.addWidget(canvas_escenarios)
        self.graficos_tab_widget.addTab(tab15, "Escenarios")
        try:
            curr = self.progress_bar.value()
            self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
        except Exception:
            pass

        # Gráfico de Traducción del Riesgo a Términos de Negocio
        # fig_traduccion = Figure(figsize=(9, 6))
        # canvas_traduccion = FigureCanvas(fig_traduccion)
        # ax_traduccion = fig_traduccion.add_subplot(111)

        # Definir equivalencias de negocio (ajustar según la organización)
        # media_perdidas = np.mean(perdidas_totales)
        # p99_perdidas = np.percentile(perdidas_totales, 99)

        # Crear datos para el gráfico - ajusta estos valores según tu contexto
        # impacto_unidades = {
        #    "% del Presupuesto Anual": [media_perdidas / 1000000 * 100, p99_perdidas / 1000000 * 100],
        #    "Meses de Ingresos": [media_perdidas / 100000, p99_perdidas / 100000],
        #    "GMV Anual": [media_perdidas / 50000, p99_perdidas / 50000],
        #    "EBITDA": [media_perdidas / 200000, p99_perdidas / 200000],
        #    "Días de operación\ndetenida": [media_perdidas / 30000, p99_perdidas / 30000]
        #}

        # Preparar datos para el gráfico
        # categorias = list(impacto_unidades.keys())
        # impacto_media = [val[0] for val in impacto_unidades.values()]
        # impacto_extremo = [val[1] for val in impacto_unidades.values()]

        # Posición de las barras
        # x = np.arange(len(categorias))
        # ancho = 0.35

        # Crear barras para casos medio y extremo
        # rects1 = ax_traduccion.barh(x - ancho/2, impacto_media, ancho, color='#5DADE2', label='Caso promedio')
        # rects2 = ax_traduccion.barh(x + ancho/2, impacto_extremo, ancho, color='#EC7063', label='Caso extremo (P99)')

        # Añadir etiquetas y título
        # ax_traduccion.set_title('El Impacto del Riesgo en Términos de Negocio', fontsize=14)
        # ax_traduccion.set_xlabel('Magnitud del Impacto')
        # ax_traduccion.set_yticks(x)
        # ax_traduccion.set_yticklabels(categorias)
        # ax_traduccion.legend(loc='upper right')

        # Añadir valores dentro o al final de las barras
        # for i, rect in enumerate(rects1):
        #    width = rect.get_width()
        #    ax_traduccion.text(max(width + 0.5, 1), rect.get_y() + rect.get_height()/2.,
        #                    f'{width:.1f}', ha='left', va='center')

        # for i, rect in enumerate(rects2):
        #    width = rect.get_width()
        #    ax_traduccion.text(max(width + 0.5, 1), rect.get_y() + rect.get_height()/2.,
        #                    f'{width:.1f}', ha='left', va='center')

        # Añadir explicación
        # explicacion = """
        # Este gráfico traduce el impacto del riesgo a términos que son relevantes para el negocio.
        # Compara el caso promedio (azul) con un escenario extremo que ocurriría aproximadamente una vez cada 100 eventos (rojo).

        # Nota: Estos valores son aproximaciones basadas en los parámetros actuales de la organización.
        # """
        # fig_traduccion.text(0.5, 0.01, explicacion, ha='center', va='bottom', fontsize=9,
        #                  bbox=dict(facecolor='white', edgecolor='gray', boxstyle='round', alpha=0.9))

        # fig_traduccion.tight_layout(rect=[0, 0.1, 0.95, 0.95])  # Ajustar para texto explicativo

        # tab16 = QtWidgets.QWidget()
        # layout_traduccion = QtWidgets.QVBoxLayout(tab16)
        # layout_traduccion.addWidget(canvas_traduccion)
        # self.graficos_tab_widget.addTab(tab16, "Impacto en Negocio")

        # Gráfico de Calendario de Riesgo - Formato Línea de Tiempo (4 niveles)
        fig_calendario = Figure(figsize=(12, 5))
        canvas_calendario = InteractiveFigureCanvas(fig_calendario)
        ax_calendario = fig_calendario.add_subplot(111)

        # Calcular frecuencia promedio de eventos
        eventos_por_año = np.mean(frecuencias_totales)

        # Usar los mismos 4 umbrales que en otros gráficos (Termómetro, Semáforo)
        umbral_bajo = 3_000_000
        umbral_moderado = 32_000_000
        umbral_alto = 110_000_000

        # 4 niveles consistentes con otros gráficos
        niveles = [
            (umbral_bajo, "BAJO", '#4CAF50'),
            (umbral_moderado, "MODERADO", '#FFC107'),
            (umbral_alto, "ALTO", '#FF9800'),
            (max(umbral_alto * 1.5, np.percentile(perdidas_totales, 99.5)), "CRÍTICO", '#F44336')
        ]

        # Calcular período de retorno y probabilidad para cada nivel
        datos_calendario = []
        for umbral, nombre, color in niveles:
            prob_exceder = len(perdidas_totales[perdidas_totales > umbral]) / len(perdidas_totales)
            prob_anual = prob_exceder * 100  # Probabilidad anual en %
            
            if prob_exceder > 0 and eventos_por_año > 0:
                periodo_retorno = 1 / (prob_exceder * eventos_por_año)
            else:
                periodo_retorno = float('inf')
            
            datos_calendario.append({
                'umbral': umbral,
                'nombre': nombre,
                'color': color,
                'prob_anual': prob_anual,
                'periodo': periodo_retorno
            })

        # Crear línea de tiempo horizontal
        # Marcas de tiempo en el eje X (escala logarítmica)
        marcas_tiempo = [1/12, 1/4, 1/2, 1, 2, 5, 10, 25, 50, 100]  # años
        etiquetas_marcas = ['1 mes', '3 meses', '6 meses', '1 año', '2 años', 
                           '5 años', '10 años', '25 años', '50 años', '100 años']

        # Dibujar línea base del timeline
        ax_calendario.axhline(y=0, color='#333333', linewidth=3, zorder=1)
        
        # Dibujar marcas de tiempo en la línea
        for marca in marcas_tiempo:
            ax_calendario.plot(marca, 0, '|', color='#666666', markersize=15, zorder=2)

        # Posiciones verticales para los 4 niveles (alternando arriba/abajo)
        y_positions = [1.5, -1.5, 1.5, -1.5]
        
        # Dibujar cada nivel como un punto en la línea de tiempo
        for i, datos in enumerate(datos_calendario):
            periodo = min(datos['periodo'], 100)  # Limitar a 100 años para visualización
            y_pos = y_positions[i]
            
            # Punto grande en la línea de tiempo
            ax_calendario.scatter(periodo, 0, s=200, c=datos['color'], 
                                 edgecolors='white', linewidths=2, zorder=5)
            
            # Línea conectora vertical
            ax_calendario.plot([periodo, periodo], [0, y_pos * 0.7], 
                              color=datos['color'], linewidth=2, linestyle='--', alpha=0.7)
            
            # Cuadro de información
            # Formato del período
            if datos['periodo'] < 1/12:
                texto_periodo = f"{datos['periodo']*365:.0f} días"
            elif datos['periodo'] < 1:
                texto_periodo = f"{datos['periodo']*12:.0f} meses"
            elif datos['periodo'] < 100:
                texto_periodo = f"{datos['periodo']:.1f} años"
            else:
                texto_periodo = ">100 años"
            
            # Texto con período Y probabilidad anual
            info_text = f"{datos['nombre']}\n{currency_format(datos['umbral'])}\n\nCada {texto_periodo}\n({datos['prob_anual']:.1f}% anual)"
            
            # Cuadro de texto
            bbox_props = dict(boxstyle='round,pad=0.5', facecolor=datos['color'], 
                             alpha=0.15, edgecolor=datos['color'], linewidth=2)
            ax_calendario.text(periodo, y_pos, info_text,
                              ha='center', va='center' if y_pos > 0 else 'center',
                              fontsize=9, fontweight='bold',
                              bbox=bbox_props)

        # Configurar eje X (logarítmico)
        ax_calendario.set_xscale('log')
        ax_calendario.set_xlim(0.05, 150)
        ax_calendario.set_xticks(marcas_tiempo)
        ax_calendario.set_xticklabels(etiquetas_marcas, fontsize=9)
        
        # Configurar eje Y
        ax_calendario.set_ylim(-3, 3)
        ax_calendario.set_yticks([])
        
        # Estilo limpio
        ax_calendario.spines['left'].set_visible(False)
        ax_calendario.spines['right'].set_visible(False)
        ax_calendario.spines['top'].set_visible(False)
        ax_calendario.spines['bottom'].set_visible(False)
        
        # Título
        ax_calendario.set_title('Línea de Tiempo de Riesgo: ¿Cada cuánto ocurre cada nivel de impacto?', 
                               fontsize=14, fontweight='bold', pad=15)
        
        # Etiqueta del eje X
        ax_calendario.set_xlabel('Período de Retorno (escala logarítmica)', fontsize=10)
        
        # Leyenda en la parte inferior
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=d['color'], edgecolor=d['color'], 
                                label=f"{d['nombre']}: >{currency_format(d['umbral'])}") 
                          for d in datos_calendario]
        ax_calendario.legend(handles=legend_elements, loc='upper center', 
                            bbox_to_anchor=(0.5, -0.12), ncol=4, fontsize=9)

        fig_calendario.tight_layout(rect=[0, 0.08, 1, 0.95])

        tab17 = QtWidgets.QWidget()
        layout_calendario = QtWidgets.QVBoxLayout(tab17)
        layout_calendario.addWidget(canvas_calendario)
        self.graficos_tab_widget.addTab(tab17, "Calendario")
        try:
            curr = self.progress_bar.value()
            self.actualizar_progreso_post(min(curr + 1, 93), "Agregando gráficos…")
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass

        # --- REORDENAR PESTAÑAS DE GRÁFICOS ---
        # Orden deseado:
        # 1. Distribución, 2. Excedencia, 3. Contribución, 4. Termómetro, 5. Semáforo
        # 6. Frecuencia, 7. Tail Risk, 8. Perd por Evento, 9. Dist. por Evento
        # 10. Escenarios, 11. Sin Ceros, 12. Calendario, 13. Box Plot, 14. Dispersión
        try:
            orden_deseado = [
                "Distribución",
                "Excedencia",
                "Contribución",
                "Termómetro",
                "Semáforo",
                "Frecuencia",
                "Tail Risk",
                "Perd por Evento",
                "Dist. por Evento",
                "Escenarios",
                "Sin Ceros",
                "Calendario",
                "Box Plot",
                "Dispersión"
            ]
            
            # Obtener todas las pestañas actuales y sus índices
            tab_widget = self.graficos_tab_widget
            tabs_actuales = {}
            for i in range(tab_widget.count()):
                nombre = tab_widget.tabText(i)
                widget = tab_widget.widget(i)
                tabs_actuales[nombre] = widget
            
            # Remover todas las pestañas (pero no eliminar los widgets)
            while tab_widget.count() > 0:
                tab_widget.removeTab(0)
            
            # Agregar las pestañas en el orden deseado
            for nombre in orden_deseado:
                if nombre in tabs_actuales:
                    tab_widget.addTab(tabs_actuales[nombre], nombre)
            
            # Agregar cualquier pestaña que no esté en el orden deseado al final
            for nombre, widget in tabs_actuales.items():
                if nombre not in orden_deseado:
                    tab_widget.addTab(widget, nombre)
                    
            print(f"[DEBUG] Pestañas reordenadas: {[tab_widget.tabText(i) for i in range(tab_widget.count())]}")
        except Exception as e:
            print(f"[DEBUG] Error al reordenar pestañas: {e}")
        # --- FIN REORDENAR PESTAÑAS ---

        # --- CÓDIGO SHAP REMOVIDO COMPLETAMENTE ---
        # El análisis SHAP ha sido eliminado para reducir el tamaño del ejecutable
        # y evitar falsos positivos de antivirus.
        print("Análisis SHAP deshabilitado en esta versión.")

        # Restaurar el cursor de espera al finalizar siempre
        try:
            # Qt mantiene una pila de cursores; aseguramos vaciarla por completo
            while QtWidgets.QApplication.overrideCursor() is not None:
                QtWidgets.QApplication.restoreOverrideCursor()
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass


    def exportar_a_pdf(self):
        """Exporta los resultados de la simulación a un archivo PDF profesional.
        Usa la clase ResultReport para generar un PDF con tablas y gráficos.
        """
        # Verificar si hay resultados para exportar
        if not hasattr(self, 'resultados_simulacion'):
            QtWidgets.QMessageBox.warning(self, "Advertencia",
                                          "No hay resultados de simulación para exportar. Por favor, ejecute una simulación primero.")
            return

        # Solicitar la ruta donde guardar el PDF
        pdf_filename = self.solicitar_ruta_guardado_pdf()
        if not pdf_filename:
            return  # Usuario canceló la selección de archivo

        # Obtener los datos de simulación
        perdidas_totales = self.resultados_simulacion.get('perdidas_totales')
        frecuencias_totales = self.resultados_simulacion.get('frecuencias_totales')
        perdidas_por_evento = self.resultados_simulacion.get('perdidas_por_evento')
        frecuencias_por_evento = self.resultados_simulacion.get('frecuencias_por_evento')
        eventos_riesgo = self.resultados_simulacion.get('eventos_riesgo')

        if not all([perdidas_totales is not None, frecuencias_totales is not None,
                  perdidas_por_evento is not None, frecuencias_por_evento is not None,
                  eventos_riesgo is not None]):
            QtWidgets.QMessageBox.warning(self, "Advertencia",
                                        "Los datos de la simulación están incompletos. Por favor, ejecute la simulación nuevamente.")
            return
            
        # === Utilizar ResultReport para generar un PDF profesional ===
        try:
            # Primer asegurarnos que se han generado todos los gráficos en la GUI
            # Si no hay pestañas en el widget de gráficos, generarlos primero
            if self.graficos_tab_widget.count() == 0:
                self.graficar_resultados(
                    perdidas_totales, 
                    frecuencias_totales, 
                    perdidas_por_evento, 
                    frecuencias_por_evento, 
                    eventos_riesgo
                )
            
            # Ahora recopilamos todos los gráficos de las pestañas
            todas_figuras = []
            # Para cada pestaña en el widget de gráficos
            for i in range(self.graficos_tab_widget.count()):
                # Obtener el widget de la pestaña
                tab = self.graficos_tab_widget.widget(i)
                # Obtener el título de la pestaña
                tab_title = self.graficos_tab_widget.tabText(i)
                
                # Buscar un FigureCanvas dentro de la pestaña (puede estar dentro de varios layouts)
                canvas = None
                for child in tab.findChildren(FigureCanvas):
                    canvas = child
                    break  # Tomamos el primer canvas que encontremos
                
                if canvas:
                    # Obtener la figura del canvas y guardarla
                    fig = canvas.figure
                    # Añadir título a la figura para identificarla en el PDF
                    if not hasattr(fig, '_suptitle') or not fig._suptitle:
                        fig.suptitle(tab_title)
                    todas_figuras.append(fig)
            
            # Asegurarnos de que al menos tenemos un gráfico básico
            if not todas_figuras:
                # Generar gráficos básicos con ReportReport
                report = ResultReport(
                    perdidas_totales,
                    frecuencias_totales,
                    perdidas_por_evento,
                    frecuencias_por_evento,
                    eventos_riesgo
                )
                todas_figuras = report.build_figures()
            
            # Crear instancia de ResultReport con los datos de la simulación y los gráficos recopilados
            report = ResultReport(
                perdidas_totales,
                frecuencias_totales,
                perdidas_por_evento,
                frecuencias_por_evento,
                eventos_riesgo
            )
            
            # Generar el PDF con todos los gráficos
            report.create_pdf_with_figures(pdf_filename, todas_figuras)
            
            # Informar al usuario
            self.statusBar().showMessage("Reporte PDF guardado exitosamente", 4000)
        except Exception as e:
            # Capturar cualquier error durante la generación del PDF
            error_trace = traceback.format_exc()
            print(f"Error al generar PDF con ResultReport: {error_trace}")
            QtWidgets.QMessageBox.critical(
                self, "Error al generar PDF",
                f"Ocurrió un error al generar el PDF con el nuevo formato:\n{str(e)}\n\nPor favor, contacte al soporte técnico."
            )

    def generar_texto_resultados(self, perdidas_totales, frecuencias_totales, perdidas_por_evento, frecuencias_por_evento, eventos_riesgo):
        """Calcula estadísticas y genera texto de resultados."""
        texto_resultados = ""

        # Calculamos estadísticas para pérdidas agregadas
        percentiles_valores = [10, 20, 30, 40, 50, 60, 70, 75, 80, 85, 90, 92, 95, 99, 99.99]
        percentiles = np.percentile(perdidas_totales, percentiles_valores)
        media = np.mean(perdidas_totales)
        desviacion_estandar = np.std(perdidas_totales)

        # Estadísticas de frecuencias agregadas
        min_freq_total = int(frecuencias_totales.min())
        max_freq_total = int(frecuencias_totales.max())
        mode_freq_total = int(stats.mode(frecuencias_totales, keepdims=True).mode[0]) if len(frecuencias_totales) > 0 else 0

        # Creamos DataFrame de percentiles para pérdidas agregadas
        percentiles_df = pd.DataFrame({
            'Percentil (%)': percentiles_valores,
            'Valor de Pérdida': percentiles
        })

        # Formateamos los valores de pérdida sin decimales
        percentiles_df['Valor de Pérdida'] = percentiles_df['Valor de Pérdida'].round(0).astype(int)
        percentiles_df['Valor de Pérdida'] = percentiles_df['Valor de Pérdida'].apply(currency_format)

        # Formateamos los percentiles (%), dejando decimales donde corresponda
        percentiles_df['Percentil (%)'] = percentiles_df['Percentil (%)'].apply(
            lambda x: ('{:.2f}'.format(x).replace('.', ',')) if x != int(x) else ('{:.0f}'.format(x)))

        # Obtener resumen ejecutivo
        var_90 = np.percentile(perdidas_totales, 90)
        opvar_99 = np.percentile(perdidas_totales, 99)
        opvar = perdidas_totales[perdidas_totales >= opvar_99].mean()
        texto_resultados += obtener_resumen_ejecutivo_texto(media, desviacion_estandar, var_90, opvar_99, opvar,
                                                            min_freq_total, mode_freq_total, max_freq_total)

        # Obtener tabla de percentiles
        texto_resultados += obtener_tabla_percentiles_texto(percentiles_df, "Percentiles de Pérdida Agregada")

        # Agregamos cálculo y muestra de estadísticas para cada evento de riesgo
        for idx, (perdidas_evento, frecuencias_evento) in enumerate(zip(perdidas_por_evento, frecuencias_por_evento)):
            nombre_evento = eventos_riesgo[idx]['nombre']
            media_evento = np.mean(perdidas_evento)
            desviacion_evento = np.std(perdidas_evento)
            percentiles_evento = np.percentile(perdidas_evento, percentiles_valores)
            min_freq = int(frecuencias_evento.min())
            max_freq = int(frecuencias_evento.max())
            mode_freq = int(stats.mode(frecuencias_evento, keepdims=True).mode[0]) if len(frecuencias_evento) > 0 else 0
            percentiles_evento_df = pd.DataFrame({
                'Percentil (%)': percentiles_valores,
                'Valor de Pérdida': percentiles_evento
            })
            percentiles_evento_df['Valor de Pérdida'] = percentiles_evento_df['Valor de Pérdida'].round(0).astype(int)
            percentiles_evento_df['Valor de Pérdida'] = percentiles_evento_df['Valor de Pérdida'].apply(currency_format)
            percentiles_evento_df['Percentil (%)'] = percentiles_evento_df['Percentil (%)'].apply(
                lambda x: ('{:.2f}'.format(x).replace('.', ',')) if x != int(x) else ('{:.0f}'.format(x)))

            texto_resultados += f"\nEstadísticas para el Evento de Riesgo: {nombre_evento}\n"
            texto_resultados += f"Media de Impacto: {currency_format(round(media_evento))}\n"
            texto_resultados += f"Desviación Estándar: {currency_format(round(desviacion_evento))}\n"
            texto_resultados += f"Número mínimo de eventos materializados: {min_freq}\n"
            texto_resultados += f"Número más probable de eventos materializados: {mode_freq}\n"
            texto_resultados += f"Número máximo de eventos materializados: {max_freq}\n"
            texto_resultados += "Percentiles de Pérdida:\n"
            texto_resultados += tabulate(percentiles_evento_df, headers='keys', tablefmt='fancy_grid', showindex=False)
            texto_resultados += "\n"

        return texto_resultados

    def guardar_configuracion(self):
        if not self.eventos_riesgo and not self.scenarios:
            QtWidgets.QMessageBox.warning(self, "Advertencia", "No hay datos para guardar.")
            return
        options = QtWidgets.QFileDialog.Options()
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Guardar Simulación", "",
                                                            "JSON Files (*.json);;All Files (*)", options=options)
        if filepath:
            try:
                try:
                    num_sim_guardar = int(self.num_simulaciones_var.text())
                except (ValueError, TypeError):
                    num_sim_guardar = 10000
                configuracion = {
                    'num_simulaciones': num_sim_guardar,
                    'eventos_riesgo': [],
                    'scenarios': [],
                    'current_scenario_name': getattr(getattr(self, 'current_scenario', None), 'nombre', None)
                }
                # Guardar eventos de riesgo
                for evento in self.eventos_riesgo:
                    evento_data = copy.deepcopy(evento)  # Deep copy para preservar listas anidadas como factores_ajuste
                    # Removemos objetos no serializables
                    if 'dist_severidad' in evento_data: # Comprobar si existe antes de borrar
                        del evento_data['dist_severidad']
                    if 'dist_frecuencia' in evento_data: # Comprobar si existe antes de borrar
                        del evento_data['dist_frecuencia']
                    
                    # Remover flags temporales de simulación (no deben guardarse)
                    if '_usa_estocastico' in evento_data:
                        del evento_data['_usa_estocastico']
                    if '_factores_vector' in evento_data:
                        del evento_data['_factores_vector']
                    # NUEVOS: flags de severidad
                    if '_factores_severidad_vector' in evento_data:
                        del evento_data['_factores_severidad_vector']
                    if '_factor_severidad_estatico' in evento_data:
                        del evento_data['_factor_severidad_estatico']
                    if '_seguros_aplicables' in evento_data:
                        del evento_data['_seguros_aplicables']
                    if '_factor_severidad_vinculos' in evento_data:
                        del evento_data['_factor_severidad_vinculos']
                    
                    # DEBUG: Verificar que factores_ajuste se está guardando
                    if 'factores_ajuste' in evento_data and evento_data['factores_ajuste']:
                        print(f"[DEBUG GUARDAR JSON] Guardando evento '{evento_data.get('nombre')}' con {len(evento_data['factores_ajuste'])} factores")
                    
                    configuracion['eventos_riesgo'].append(evento_data)

                # Guardar escenarios
                for scenario in self.scenarios:
                    escenario_data = {
                        'nombre': scenario.nombre,
                        'descripcion': scenario.descripcion,
                        'eventos_riesgo': []
                    }
                    for evento in scenario.eventos_riesgo:
                        evento_data = copy.deepcopy(evento)  # Deep copy para preservar listas anidadas
                        # Remover objetos no serializables si existen
                        if 'dist_severidad' in evento_data:
                            del evento_data['dist_severidad']
                        if 'dist_frecuencia' in evento_data:
                            del evento_data['dist_frecuencia']
                        
                        # Remover flags temporales de simulación (no deben guardarse)
                        if '_usa_estocastico' in evento_data:
                            del evento_data['_usa_estocastico']
                        if '_factores_vector' in evento_data:
                            del evento_data['_factores_vector']
                        # NUEVOS: flags de severidad
                        if '_factores_severidad_vector' in evento_data:
                            del evento_data['_factores_severidad_vector']
                        if '_factor_severidad_estatico' in evento_data:
                            del evento_data['_factor_severidad_estatico']
                        if '_seguros_aplicables' in evento_data:
                            del evento_data['_seguros_aplicables']
                        if '_factor_severidad_vinculos' in evento_data:
                            del evento_data['_factor_severidad_vinculos']
                        
                        escenario_data['eventos_riesgo'].append(evento_data)
                    configuracion['scenarios'].append(escenario_data)

                # Guardar resultados de simulación si existen
                try:
                    res = getattr(self, 'resultados_simulacion', None)
                    if res:
                        # Obtener nombres de eventos en el mismo orden que los resultados
                        eventos_para_nombres = res.get('eventos_riesgo', self.eventos_riesgo)
                        event_names = []
                        try:
                            event_names = [ev.get('nombre', '') for ev in eventos_para_nombres]
                        except Exception:
                            event_names = []

                        # Serializar arrays numpy a listas
                        pt = res.get('perdidas_totales')
                        ft = res.get('frecuencias_totales')
                        ppe = res.get('perdidas_por_evento') or []
                        fpe = res.get('frecuencias_por_evento') or []

                        results_payload = {
                            'perdidas_totales': (pt.tolist() if hasattr(pt, 'tolist') else (list(pt) if pt is not None else [])),
                            'frecuencias_totales': (ft.tolist() if hasattr(ft, 'tolist') else (list(ft) if ft is not None else [])),
                            'perdidas_por_evento': [(arr.tolist() if hasattr(arr, 'tolist') else list(arr)) for arr in ppe],
                            'frecuencias_por_evento': [(arr.tolist() if hasattr(arr, 'tolist') else list(arr)) for arr in fpe],
                            'event_names': event_names,
                            'num_simulaciones': int(len(pt)) if pt is not None else 0
                        }
                        configuracion['simulation_results'] = results_payload
                except Exception:
                    # Si falla la serialización de resultados, continuar sin bloquear el guardado de configuración
                    pass
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(configuracion, f, ensure_ascii=False, indent=4)
                self.statusBar().showMessage("La Simulación ha sido guardada exitosamente", 5000)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo guardar la Simulación: {e}")

    def cargar_configuracion(self):
        options = QtWidgets.QFileDialog.Options()
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Cargar Simulación", "",
                                                            "JSON Files (*.json);;All Files (*)", options=options)
        if filepath:
            # Agregar confirmación al usuario
            respuesta = QtWidgets.QMessageBox.question(
                self,
                "Cargar Simulación",
                "Al cargar una simulación, se eliminarán los escenarios y resultados actuales. ¿Desea continuar?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if respuesta != QtWidgets.QMessageBox.Yes:
                return
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    configuracion = json.load(f)

                # === INICIO DE TRANSACCIÓN: Procesar en variables temporales ===
                # Si hay algún error durante el procesamiento, los datos originales quedan intactos
                
                eventos_riesgo_temp = []
                scenarios_temp = []
                num_simulaciones_temp = configuracion.get('num_simulaciones', 10000)
                
                # Diccionario para mapear IDs antiguos a nuevos (para evitar conflictos)
                id_mapeo = {}
                
                # Lista para acumular eventos que no se pudieron cargar
                eventos_con_error = []

                # Cargar eventos de riesgo de la simulación principal a lista temporal
                for evento_data in configuracion.get('eventos_riesgo', []):
                    sev_opcion = evento_data['sev_opcion']
                    sev_input_method = evento_data.get('sev_input_method', 'min_mode_max') # Lee o usa default
                    sev_params_direct = evento_data.get('sev_params_direct', {}) # Lee o usa default
                    sev_minimo = evento_data['sev_minimo']
                    sev_mas_probable = evento_data['sev_mas_probable']
                    sev_maximo = evento_data['sev_maximo']

                    try:
                         dist_sev = generar_distribucion_severidad(
                            sev_opcion,
                            sev_minimo,
                            sev_mas_probable,
                            sev_maximo,
                            input_method=sev_input_method,
                            params_direct=sev_params_direct
                        )
                    except Exception as e:
                          # Acumular error para reportar al usuario (con traducción)
                          nombre_evento = evento_data.get('nombre', 'N/A')
                          error_traducido = traducir_error(e)
                          eventos_con_error.append(f"• {nombre_evento}: {error_traducido}")
                          continue # Saltar al siguiente evento si hay error

                    freq_opcion = evento_data['freq_opcion']
                    tasa = evento_data.get('tasa', None)
                    num_eventos = evento_data.get('num_eventos', None)
                    prob_exito = evento_data.get('prob_exito', None)
                    if tasa is not None:
                        tasa = float(tasa)
                    if num_eventos is not None:
                        num_eventos = int(num_eventos)
                    if prob_exito is not None:
                        prob_exito = float(prob_exito)
                    if 'eventos_padres' in evento_data and 'vinculos' not in evento_data:
                        vinculos = []
                        tipo = evento_data.get('tipo_dependencia', 'AND')
                        for padre_id in evento_data['eventos_padres']:
                            vinculos.append({'id_padre': padre_id, 'tipo': tipo, 'probabilidad': 100, 'factor_severidad': 1.0, 'umbral_severidad': 0})
                        evento_data['vinculos'] = vinculos

                    pg_params = None
                    beta_params = None
                    if freq_opcion == 4:
                        alpha = evento_data.get('pg_alpha', evento_data.get('poisson_gamma_alpha'))
                        beta = evento_data.get('pg_beta', evento_data.get('poisson_gamma_beta'))
                        if alpha is None or beta is None:
                            try:
                                pg_min = evento_data.get('pg_minimo')
                                pg_mode = evento_data.get('pg_mas_probable')
                                pg_max = evento_data.get('pg_maximo')
                                pg_conf_pct = evento_data.get('pg_confianza')
                                if None not in (pg_min, pg_mode, pg_max, pg_conf_pct):
                                    alpha, beta = obtener_parametros_gamma_para_poisson(float(pg_min), float(pg_mode), float(pg_max), float(pg_conf_pct) / 100.0)
                            except Exception:
                                alpha, beta = None, None
                        if alpha is not None and beta is not None:
                            pg_params = (float(alpha), float(beta))
                    elif freq_opcion == 5:
                        alpha = evento_data.get('beta_alpha')
                        beta = evento_data.get('beta_beta')
                        if alpha is not None and beta is not None:
                            beta_params = (float(alpha), float(beta))

                    dist_freq = generar_distribucion_frecuencia(
                        freq_opcion,
                        tasa=tasa,
                        num_eventos_posibles=num_eventos,
                        probabilidad_exito=prob_exito,
                        poisson_gamma_params=pg_params,
                        beta_params=beta_params
                    )
                    evento_data['dist_severidad'] = dist_sev
                    evento_data['dist_frecuencia'] = dist_freq
                    
                    # Normalizar factores_ajuste para backward compatibility
                    if 'factores_ajuste' in evento_data and evento_data['factores_ajuste']:
                        evento_data['factores_ajuste'] = [normalizar_factor_global(f) for f in evento_data['factores_ajuste']]
                        print(f"[DEBUG CARGAR JSON] Evento '{evento_data.get('nombre')}' tiene {len(evento_data['factores_ajuste'])} factores (normalizados)")
                    else:
                        print(f"[DEBUG CARGAR JSON] Evento '{evento_data.get('nombre')}' NO tiene factores_ajuste")

                    # Crear un nuevo ID para el evento y mapearlo
                    antiguo_id = evento_data['id']
                    nuevo_id = str(uuid.uuid4())
                    id_mapeo[antiguo_id] = nuevo_id
                    evento_data['id'] = nuevo_id

                    # Actualizar 'eventos_padres' con los nuevos IDs en caso de que existan en la simulación principal
                    eventos_padres_actualizados = []
                    for padre_id in evento_data.get('eventos_padres', []):
                        eventos_padres_actualizados.append(id_mapeo.get(padre_id, padre_id))
                    evento_data['eventos_padres'] = eventos_padres_actualizados

                    # Asegurar que tenga el campo 'activo' (backward compatibility con archivos antiguos)
                    if 'activo' not in evento_data:
                        evento_data['activo'] = True

                    # Agregar a lista temporal (NO modificar self.eventos_riesgo todavía)
                    eventos_riesgo_temp.append(evento_data)

                # Actualizar IDs en los vínculos después de procesar todos los eventos
                for evento_data in eventos_riesgo_temp:
                    if 'vinculos' in evento_data:
                        vinculos_actualizados = []
                        for vinculo in evento_data['vinculos']:
                            id_padre_antiguo = vinculo['id_padre']
                            id_padre_nuevo = id_mapeo.get(id_padre_antiguo, id_padre_antiguo)  # Usar ID antiguo si no hay mapeo
                            prob = max(1, min(100, int(vinculo.get('probabilidad', 100))))
                            fsev = max(0.10, min(5.0, float(vinculo.get('factor_severidad', 1.0))))
                            umbral = max(0, int(vinculo.get('umbral_severidad', 0)))
                            vinculos_actualizados.append({'id_padre': id_padre_nuevo, 'tipo': vinculo['tipo'], 'probabilidad': prob, 'factor_severidad': fsev, 'umbral_severidad': umbral})
                        evento_data['vinculos'] = vinculos_actualizados

                # Cargar escenarios
                for escenario_data in configuracion.get('scenarios', []):
                    scenario = Scenario(escenario_data['nombre'], escenario_data.get('descripcion', ''))
                    scenario.eventos_riesgo = []

                    # Nuevo diccionario de IDs para los eventos del escenario
                    id_mapeo_scenario = {}

                    for evento_data in escenario_data['eventos_riesgo']:
                        sev_opcion = evento_data['sev_opcion']
                        sev_minimo = evento_data['sev_minimo']
                        sev_mas_probable = evento_data['sev_mas_probable']
                        sev_maximo = evento_data['sev_maximo']
                        try:
                            dist_sev_esc = generar_distribucion_severidad(
                                evento_data['sev_opcion'],
                                evento_data.get('sev_minimo'),
                                evento_data.get('sev_mas_probable'),
                                evento_data.get('sev_maximo'),
                                input_method=evento_data.get('sev_input_method', 'min_mode_max'),
                                params_direct=evento_data.get('sev_params_direct', {})
                            )
                        except Exception as e:
                            # Acumular error para reportar al usuario (con traducción)
                            nombre_evento = evento_data.get('nombre', 'N/A')
                            nombre_escenario = escenario_data['nombre']
                            error_traducido = traducir_error(e)
                            eventos_con_error.append(f"• {nombre_evento} (Escenario: {nombre_escenario}): {error_traducido}")
                            continue  # Omitir evento con distribución de severidad inválida

                        freq_opcion = evento_data['freq_opcion']
                        tasa = evento_data.get('tasa', None)
                        num_eventos = evento_data.get('num_eventos', None)
                        prob_exito = evento_data.get('prob_exito', None)
                        if tasa is not None:
                            tasa = float(tasa)
                        if num_eventos is not None:
                            num_eventos = int(num_eventos)
                        if prob_exito is not None:
                            prob_exito = float(prob_exito)
                        if 'eventos_padres' in evento_data and 'vinculos' not in evento_data:
                            vinculos = []
                            tipo = evento_data.get('tipo_dependencia', 'AND')
                            for padre_id in evento_data['eventos_padres']:
                                vinculos.append({'id_padre': padre_id, 'tipo': tipo, 'probabilidad': 100, 'factor_severidad': 1.0, 'umbral_severidad': 0})
                            evento_data['vinculos'] = vinculos

                        # Reconstruir distribución de frecuencia para eventos del escenario
                        pg_params = None
                        beta_params = None
                        if freq_opcion == 4:
                            alpha = evento_data.get('pg_alpha', evento_data.get('poisson_gamma_alpha'))
                            beta = evento_data.get('pg_beta', evento_data.get('poisson_gamma_beta'))
                            if alpha is None or beta is None:
                                try:
                                    pg_min = evento_data.get('pg_minimo')
                                    pg_mode = evento_data.get('pg_mas_probable')
                                    pg_max = evento_data.get('pg_maximo')
                                    pg_conf_pct = evento_data.get('pg_confianza')
                                    if None not in (pg_min, pg_mode, pg_max, pg_conf_pct):
                                        alpha, beta = obtener_parametros_gamma_para_poisson(float(pg_min), float(pg_mode), float(pg_max), float(pg_conf_pct) / 100.0)
                                except Exception:
                                    alpha, beta = None, None
                            if alpha is not None and beta is not None:
                                pg_params = (float(alpha), float(beta))
                        elif freq_opcion == 5:
                            alpha = evento_data.get('beta_alpha')
                            beta = evento_data.get('beta_beta')
                            if alpha is not None and beta is not None:
                                beta_params = (float(alpha), float(beta))

                        dist_freq = generar_distribucion_frecuencia(
                            freq_opcion,
                            tasa=tasa,
                            num_eventos_posibles=num_eventos,
                            probabilidad_exito=prob_exito,
                            poisson_gamma_params=pg_params,
                            beta_params=beta_params
                        )
                        evento_data['dist_severidad'] = dist_sev_esc
                        evento_data['dist_frecuencia'] = dist_freq

                        # Normalizar factores_ajuste para backward compatibility
                        if 'factores_ajuste' in evento_data and evento_data['factores_ajuste']:
                            evento_data['factores_ajuste'] = [normalizar_factor_global(f) for f in evento_data['factores_ajuste']]

                        # Crear un nuevo ID para el evento y mapearlo
                        antiguo_id = evento_data['id']
                        nuevo_id = str(uuid.uuid4())
                        id_mapeo_scenario[antiguo_id] = nuevo_id
                        evento_data['id'] = nuevo_id

                        # Actualizar 'eventos_padres' con los nuevos IDs dentro del escenario
                        eventos_padres_actualizados = []
                        for padre_id in evento_data.get('eventos_padres', []):
                            if padre_id in id_mapeo_scenario:
                                eventos_padres_actualizados.append(id_mapeo_scenario[padre_id])
                            else:
                                # Si el evento padre está en la simulación principal
                                eventos_padres_actualizados.append(id_mapeo.get(padre_id, padre_id))
                        evento_data['eventos_padres'] = eventos_padres_actualizados

                        # Asegurar que tenga el campo 'activo' (backward compatibility)
                        if 'activo' not in evento_data:
                            evento_data['activo'] = True

                        scenario.eventos_riesgo.append(evento_data)

                    # Agregar a lista temporal (NO modificar self.scenarios todavía)
                    scenarios_temp.append(scenario)

                    for evento_data in scenario.eventos_riesgo:
                        if 'vinculos' in evento_data:
                            vinculos_actualizados = []
                            for vinculo in evento_data['vinculos']:
                                id_padre_antiguo = vinculo['id_padre']
                                # Primero buscar en el mapeo del escenario, luego en el mapeo general
                                if id_padre_antiguo in id_mapeo_scenario:
                                    id_padre_nuevo = id_mapeo_scenario[id_padre_antiguo]
                                else:
                                    id_padre_nuevo = id_mapeo.get(id_padre_antiguo, id_padre_antiguo)
                                prob = max(1, min(100, int(vinculo.get('probabilidad', 100))))
                                fsev = max(0.10, min(5.0, float(vinculo.get('factor_severidad', 1.0))))
                                umbral = max(0, int(vinculo.get('umbral_severidad', 0)))
                                vinculos_actualizados.append({'id_padre': id_padre_nuevo, 'tipo': vinculo['tipo'], 'probabilidad': prob, 'factor_severidad': fsev, 'umbral_severidad': umbral})
                            evento_data['vinculos'] = vinculos_actualizados

                # === COMMIT DE TRANSACCIÓN: Todo procesado exitosamente, ahora actualizar la UI ===
                # Limpiar escenarios y resultados actuales
                self.scenarios.clear()
                self.scenarios_table.setRowCount(0)
                self.current_scenario = None
                self.selected_scenario_label.setText("Ninguno")

                # Limpiar resultados de simulación
                self.resultados_text_edit.clear()
                self.graficos_tab_widget.clear()

                # Limpiar eventos de riesgo
                self.eventos_riesgo.clear()
                self.eventos_table.setRowCount(0)

                # Aplicar la nueva configuración
                self.num_simulaciones_var.setText(str(num_simulaciones_temp))
                
                # Aplicar eventos de riesgo
                self.eventos_riesgo = eventos_riesgo_temp
                for evento_data in self.eventos_riesgo:
                    row_position = self.eventos_table.rowCount()
                    self.eventos_table.insertRow(row_position)
                    # Columna 0: checkbox
                    activo = evento_data.get('activo', True)
                    self.eventos_table.setCellWidget(row_position, 0, self.crear_checkbox_activo(row_position, activo=activo))
                    # Columna 1: nombre
                    self.eventos_table.setItem(row_position, 1, self.crear_table_item_con_wrap(evento_data['nombre']))
                    # Aplicar estilo según estado
                    self.aplicar_estilo_fila_evento(row_position)
                
                self.actualizar_vista_eventos()  # Actualizar vista
                
                # Aplicar escenarios
                self.scenarios = scenarios_temp
                for scenario in self.scenarios:
                    row_position = self.scenarios_table.rowCount()
                    self.scenarios_table.insertRow(row_position)
                    nombre_item = QtWidgets.QTableWidgetItem(scenario.nombre)
                    nombre_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    desc_item = QtWidgets.QTableWidgetItem(scenario.descripcion)
                    desc_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                    self.scenarios_table.setItem(row_position, 0, nombre_item)
                    self.scenarios_table.setItem(row_position, 1, desc_item)
                
                self.actualizar_vista_escenarios()  # Actualizar vista

                # Restaurar el escenario seleccionado actual, si existe
                current_scenario_name = configuracion.get('current_scenario_name')
                if current_scenario_name:
                    for scenario in self.scenarios:
                        if scenario.nombre == current_scenario_name:
                            self.current_scenario = scenario
                            self.selected_scenario_label.setText(scenario.nombre)
                            break

                # Intentar restaurar resultados de simulación guardados
                try:
                    sr = configuracion.get('simulation_results')
                    if sr:
                        # Reconstruir arrays numpy
                        pt = np.array(sr.get('perdidas_totales', []), dtype=float)
                        ft = np.array(sr.get('frecuencias_totales', []), dtype=np.int32)
                        ppe_list = [np.array(arr, dtype=float) for arr in sr.get('perdidas_por_evento', [])]
                        fpe_list = [np.array(arr, dtype=np.int32) for arr in sr.get('frecuencias_por_evento', [])]
                        saved_names = sr.get('event_names', [])

                        # Buscar lista de eventos que coincida por nombres (principal o algún escenario)
                        eventos_candidatos = []
                        # Candidato principal
                        try:
                            main_names = [ev['nombre'] for ev in self.eventos_riesgo]
                            if saved_names and saved_names == main_names:
                                eventos_candidatos = self.eventos_riesgo
                        except Exception:
                            pass
                        # Si no coincide con principal, probar escenarios
                        if not eventos_candidatos and saved_names:
                            for scen in self.scenarios:
                                try:
                                    scen_names = [ev['nombre'] for ev in scen.eventos_riesgo]
                                    if saved_names == scen_names:
                                        eventos_candidatos = scen.eventos_riesgo
                                        break
                                except Exception:
                                    continue

                        # Validar dimensiones
                        if eventos_candidatos and len(ppe_list) == len(eventos_candidatos) == len(fpe_list):
                            # Almacenar y reconstruir la UI utilizando la misma ruta que al finalizar simulación
                            self.simulacion_completada(pt, ft, ppe_list, fpe_list, eventos_candidatos)
                            self.statusBar().showMessage("La Simulación y sus resultados han sido cargados exitosamente", 6000)
                        else:
                            # No coincide o faltan datos; omitir restauración de resultados
                            self.statusBar().showMessage("Configuración cargada. Los resultados guardados no coinciden con los eventos actuales y no se restauraron.", 7000)
                except Exception:
                    # Cualquier error al restaurar resultados no debe impedir cargar la configuración
                    pass

                # Reportar eventos que no se pudieron cargar
                if eventos_con_error:
                    cantidad_errores = len(eventos_con_error)
                    mensaje_errores = f"Se cargó la configuración, pero {cantidad_errores} evento(s) no pudieron ser restaurado(s):\n\n"
                    
                    # Mostrar máximo 10 errores para no sobrecargar el diálogo
                    errores_a_mostrar = eventos_con_error[:10]
                    mensaje_errores += "\n".join(errores_a_mostrar)
                    
                    if cantidad_errores > 10:
                        mensaje_errores += f"\n\n... y {cantidad_errores - 10} error(es) adicional(es)."
                    
                    mensaje_errores += "\n\nEstos eventos fueron omitidos. Verifique la configuración del archivo."
                    
                    QtWidgets.QMessageBox.warning(self, "Eventos No Cargados", mensaje_errores)
                    self.statusBar().showMessage(f"Configuración cargada con {cantidad_errores} advertencia(s)", 5000)
                else:
                    self.statusBar().showMessage("La Simulación ha sido cargada exitosamente", 5000)
                
                # Refrescar layout si la ventana está maximizada (fix bug de alineación)
                self._refrescar_ventana_maximizada()
            except Exception as e:
                error_message = traceback.format_exc()
                QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo cargar la Simulación: {e}\n{error_message}")

# Función principal
def main():
    # Compensar escala alta de Windows para evitar UI gigante
    # Con escala > 125%, usamos QT_SCALE_FACTOR para reducir el tamaño de la UI
    if _SYSTEM_SCALE > 1.25:
        # Calcular factor de compensación inverso
        # Ej: 150% Windows → queremos que Qt escale solo ~1.0x
        compensation = 1.0 / _SYSTEM_SCALE
        os.environ['QT_SCALE_FACTOR'] = str(round(compensation, 2))
        print(f"QT_SCALE_FACTOR ajustado a: {compensation:.2f}")
    
    # Habilitar High DPI Scaling ANTES de crear QApplication
    # Esto permite que la UI se vea correctamente en pantallas 4K y con escalado de Windows
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    
    app = QtWidgets.QApplication(sys.argv)
    window = RiskLabApp()
    window.show()
    sys.exit(app.exec_())

# Clase ResultReport para unificar reportes en PDF y gráficos
class ResultReport:
    """
    Clase que consolida la generación de estadísticas, gráficos y reportes PDF
    usando un formato profesional con ReportLab platypus.
    """
    def __init__(self, perdidas_totales, frecuencias_totales, perdidas_por_evento, frecuencias_por_evento, eventos_riesgo):
        """
        Inicializa el reporte con los datos de simulación.
        
        Args:
            perdidas_totales: Array numpy con pérdidas totales simuladas
            frecuencias_totales: Array numpy con frecuencias totales simuladas
            perdidas_por_evento: Lista de arrays con pérdidas por evento
            frecuencias_por_evento: Lista de arrays con frecuencias por evento
            eventos_riesgo: Lista de diccionarios con información de eventos
        """
        self.perdidas_totales = perdidas_totales
        self.frecuencias_totales = frecuencias_totales
        self.perdidas_por_evento = perdidas_por_evento
        self.frecuencias_por_evento = frecuencias_por_evento
        self.eventos_riesgo = eventos_riesgo
        self._stats_cache = None  # Cache para estadísticas calculadas
    
    def stats(self):
        """
        Calcula y devuelve estadísticas descriptivas de la simulación.
        Utiliza caché para evitar recalcular si ya fue calculado.
        
        Returns:
            Dict con DataFrames y valores estadísticos
        """
        if self._stats_cache is not None:
            return self._stats_cache
        
        # Calcular estadísticas básicas de pérdidas agregadas
        stats_dict = {}
        
        # Estadísticas agregadas
        stats_dict['mean'] = float(np.mean(self.perdidas_totales))
        stats_dict['median'] = float(np.median(self.perdidas_totales))
        stats_dict['std_dev'] = float(np.std(self.perdidas_totales))
        stats_dict['min'] = float(np.min(self.perdidas_totales))
        stats_dict['max'] = float(np.max(self.perdidas_totales))
        
        # Percentiles de pérdidas agregadas
        percentiles = [50, 75, 80, 85, 90, 95, 99]
        percentile_values = np.percentile(self.perdidas_totales, percentiles)
        stats_dict['percentiles'] = {p: float(val) for p, val in zip(percentiles, percentile_values)}
        
        # OpVaR: Pérdida esperada más allá del P99
        opvar_99 = stats_dict['percentiles'][99]
        perdidas_extremas = self.perdidas_totales[self.perdidas_totales >= opvar_99]
        stats_dict['opvar'] = float(np.mean(perdidas_extremas)) if len(perdidas_extremas) > 0 else opvar_99
        
        # Estadísticas de frecuencias agregadas
        stats_dict['freq_min'] = int(np.min(self.frecuencias_totales))
        stats_dict['freq_max'] = int(np.max(self.frecuencias_totales))
        stats_dict['freq_mean'] = float(np.mean(self.frecuencias_totales))
        # Moda de frecuencias
        try:
            mode_result = stats.mode(self.frecuencias_totales, keepdims=True)
            stats_dict['freq_mode'] = int(mode_result.mode[0])
        except Exception:
            stats_dict['freq_mode'] = int(np.median(self.frecuencias_totales))
        
        # Estadísticas por evento
        stats_dict['event_means'] = [float(np.mean(p_evt)) for p_evt in self.perdidas_por_evento]
        stats_dict['event_std'] = [float(np.std(p_evt)) for p_evt in self.perdidas_por_evento]
        stats_dict['event_contributions'] = [float(m / stats_dict['mean']) if stats_dict['mean'] > 0 else 0 
                                           for m in stats_dict['event_means']]
        
        # Estadísticas de frecuencia por evento
        stats_dict['event_freq_min'] = [int(np.min(f_evt)) for f_evt in self.frecuencias_por_evento]
        stats_dict['event_freq_max'] = [int(np.max(f_evt)) for f_evt in self.frecuencias_por_evento]
        stats_dict['event_freq_mode'] = []
        for f_evt in self.frecuencias_por_evento:
            try:
                mode_result = stats.mode(f_evt, keepdims=True)
                stats_dict['event_freq_mode'].append(int(mode_result.mode[0]))
            except Exception:
                stats_dict['event_freq_mode'].append(int(np.median(f_evt)))
        
        # Crear DataFrame con percentiles por evento
        percentiles_por_evento = {}
        for i, evento in enumerate(self.eventos_riesgo):
            nombre = evento['nombre']
            vals = np.percentile(self.perdidas_por_evento[i], percentiles)
            percentiles_por_evento[nombre] = vals
            
        # Crear DataFrame de percentiles para fácil visualización
        df_percentiles = pd.DataFrame(percentiles_por_evento, index=[f'P{p}' for p in percentiles])
        df_percentiles['Pérdida Total'] = percentile_values
        stats_dict['percentiles_df'] = df_percentiles
        
        self._stats_cache = stats_dict  # Guardar en caché
        return stats_dict
        
    def build_figures(self):
        """
        Genera figuras matplotlib para visualización o exportación a PDF.
        Implementa directamente la lógica de generación de gráficos.
        
        Returns:
            Lista de objetos Figure de matplotlib
        """
        figuras = []
        
        # Configurar estilo
        sns.set(style="whitegrid")
        
        # Gráfico 1: Distribución de pérdidas agregadas
        fig1 = Figure(figsize=(8, 5))
        ax1 = fig1.add_subplot(111)
        
        # Calcular bins óptimos usando regla de Freedman-Diaconis
        perdidas_sanitizadas = np.copy(self.perdidas_totales)
        perdidas_sanitizadas = np.nan_to_num(perdidas_sanitizadas, nan=0, 
                                           posinf=np.nanmax(perdidas_sanitizadas[np.isfinite(perdidas_sanitizadas)]), 
                                           neginf=0)
        try:
            iqr_valor = stats.iqr(perdidas_sanitizadas)
            if iqr_valor == 0 or not np.isfinite(iqr_valor):
                bins = 50
            else:
                bin_width = 2 * iqr_valor / max(1.0, (len(perdidas_sanitizadas) ** (1/3)))
                rango = np.max(perdidas_sanitizadas) - np.min(perdidas_sanitizadas)
                bins = min(100, max(10, int(rango / max(bin_width, 1e-10))))
        except Exception:
            bins = 50
            
        # Histograma
        sns.histplot(self.perdidas_totales, bins=bins, kde=True, color=MELI_AZUL, edgecolor='white', 
                    linewidth=0.5, alpha=0.85, ax=ax1)
        media = np.mean(self.perdidas_totales)
        var_90 = np.percentile(self.perdidas_totales, 90)
        ax1.axvline(x=media, color=MELI_ROJO, linestyle='-', linewidth=2, label=f'Media: {currency_format(media)}')
        ax1.axvline(x=var_90, color=MELI_VERDE, linestyle='--', linewidth=2, label=f'P90: {currency_format(var_90)}')
        ax1.set_title('Distribución de Pérdidas Agregadas')
        ax1.set_xlabel('Pérdida Total')
        ax1.set_ylabel('Frecuencia')
        ax1.legend(fontsize=8)
        ax1.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
        fig1.tight_layout()
        figuras.append(fig1)
        
        # Gráfico 2: Distribución de pérdidas agregadas sin ceros
        perdidas_sin_ceros = self.perdidas_totales[self.perdidas_totales > 0]
        if len(perdidas_sin_ceros) > 0:
            fig2 = Figure(figsize=(8, 5))
            ax2 = fig2.add_subplot(111)
            sns.histplot(perdidas_sin_ceros, bins=bins, kde=True, color=MELI_AZUL, edgecolor='white', 
                        linewidth=0.5, alpha=0.85, ax=ax2)
            media_sin_cero = np.mean(perdidas_sin_ceros)
            var_90_sin_cero = np.percentile(perdidas_sin_ceros, 90)
            ax2.axvline(x=media_sin_cero, color=MELI_ROJO, linestyle='-', linewidth=2, 
                        label=f'Media: {currency_format(media_sin_cero)}')
            ax2.axvline(x=var_90_sin_cero, color=MELI_VERDE, linestyle='--', linewidth=2, 
                         label=f'P90: {currency_format(var_90_sin_cero)}')
            ax2.set_title('Distribución de Pérdidas Agregadas (Excluyendo Ceros)')
            ax2.set_xlabel('Pérdida Total')
            ax2.set_ylabel('Frecuencia')
            ax2.legend(fontsize=8)
            ax2.xaxis.set_major_formatter(FuncFormatter(currency_formatter))
            fig2.tight_layout()
            figuras.append(fig2)
            
        # Gráfico 3: Gráfico de frecuencias
        fig3 = Figure(figsize=(8, 5))
        ax3 = fig3.add_subplot(111)
        sns.histplot(self.frecuencias_totales, bins=min(50, len(set(self.frecuencias_totales))), 
                    kde=False, color=MELI_AZUL, edgecolor='white', linewidth=0.5, ax=ax3)
        media_freq = np.mean(self.frecuencias_totales)
        ax3.axvline(x=media_freq, color=MELI_ROJO, linestyle='-', linewidth=2, 
                    label=f'Media: {media_freq:.2f}')
        ax3.set_title('Distribución de Frecuencias de Eventos')
        ax3.set_xlabel('Número Total de Eventos por Simulación')
        ax3.set_ylabel('Frecuencia')
        ax3.legend()
        fig3.tight_layout()
        figuras.append(fig3)
        
        # Añadir gráficos de dispersión para eventos principales
        for i, evento in enumerate(self.eventos_riesgo):
            if np.any(self.perdidas_por_evento[i] > 0):  # Solo graficar eventos con pérdidas
                fig = Figure(figsize=(8, 5))
                ax = fig.add_subplot(111)
                
                scatter = ax.scatter(self.frecuencias_por_evento[i], self.perdidas_por_evento[i], 
                                  alpha=0.5, edgecolor='none', color=MELI_AZUL)
                ax.set_title(f'Frecuencia vs Pérdida: {evento["nombre"]}')
                ax.set_xlabel('Frecuencia del Evento')
                ax.set_ylabel('Pérdida del Evento')
                ax.yaxis.set_major_formatter(FuncFormatter(currency_formatter))
                
                # Añadir línea de tendencia
                freq_non_zero = self.frecuencias_por_evento[i]
                loss_non_zero = self.perdidas_por_evento[i]
                if len(freq_non_zero) > 1 and np.any(freq_non_zero > 0) and np.any(loss_non_zero > 0):
                    try:
                        z = np.polyfit(freq_non_zero, loss_non_zero, 1)
                        p = np.poly1d(z)
                        x_range = np.linspace(np.min(freq_non_zero), np.max(freq_non_zero), 100)
                        ax.plot(x_range, p(x_range), color=MELI_ROJO, linestyle='--', 
                                label=f'Tendencia: {z[0]:.2f}x + {z[1]:.2f}')
                        ax.legend()
                    except Exception:
                        pass  # Si falla el ajuste, simplemente no mostrar línea de tendencia
                
                fig.tight_layout()
                figuras.append(fig)
        
        return figuras
    
    def create_pdf(self, filename):
        """
        Genera un reporte PDF profesional con ReportLab platypus.
        
        Args:
            filename: Ruta completa del archivo PDF a generar
        """
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer, PageBreak
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        import io
        from datetime import datetime
        
        # Obtener estadísticas y figuras
        stats_dict = self.stats()
        figuras = self.build_figures()
        
        # Llamamos al método interno con las figuras generadas
        self._create_pdf_internal(filename, stats_dict, figuras)
    
    def create_pdf_with_figures(self, filename, figuras_externas):
        """
        Genera un reporte PDF profesional con ReportLab platypus usando figuras proporcionadas externamente.
        
        Args:
            filename: Ruta completa del archivo PDF a generar
            figuras_externas: Lista de objetos Figure de matplotlib a incluir en el PDF
        """
        # Obtener estadísticas
        stats_dict = self.stats()
        
        # Llamamos al método interno con las figuras externas
        self._create_pdf_internal(filename, stats_dict, figuras_externas)
        
    def _create_pdf_internal(self, filename, stats_dict, figuras):
        """
        Método interno que maneja la generación real del PDF.
        
        Args:
            filename: Ruta completa del archivo PDF a generar
            stats_dict: Diccionario con estadísticas calculadas
            figuras: Lista de objetos Figure de matplotlib a incluir en el PDF
        """
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer, PageBreak, KeepInFrame
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        import io
        from datetime import datetime
        
        # Crear documento con márgenes adecuados
        doc = SimpleDocTemplate(filename, 
                               pagesize=A4,
                               leftMargin=2*cm, 
                               rightMargin=2*cm,
                               topMargin=2*cm, 
                               bottomMargin=2*cm)
        
        # Estilos y colores corporativos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'MeliTitle',
            parent=styles['Title'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            alignment=1,  # Centrado
            spaceAfter=12
        )
        
        heading_style = ParagraphStyle(
            'MeliHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=14,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor(MELI_AZUL_CORP)
        )
        
        # Lista de elementos a incluir en el PDF
        elements = []
        
        # Portada
        elements.append(Paragraph("<b>Risk Lab - Reporte de Simulación</b>", title_style))
        elements.append(Spacer(1, 12))
        
        # Fecha y hora del reporte
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        elements.append(Paragraph(f"Generado: {fecha}", styles["Normal"]))
        elements.append(Spacer(1, 24))
        
        # Resumen ejecutivo
        elements.append(Paragraph("Resumen Ejecutivo de Resultados", heading_style))
        
        # Tabla de resumen con estadísticas principales (todos los datos de la UI)
        data = [
            ["Métrica", "Valor"],
            ["Media de Pérdidas Agregadas", currency_format(stats_dict['mean'])],
            ["Desviación Estándar", currency_format(stats_dict['std_dev'])],
            ["VaR al 90%", currency_format(stats_dict['percentiles'][90])],
            ["OpVaR al 99%", currency_format(stats_dict['percentiles'][99])],
            ["Pérdida Esperada más allá del OpVaR 99%", currency_format(stats_dict['opvar'])],
            ["Máximo", currency_format(stats_dict['max'])],
        ]
        
        t = Table(data, colWidths=[doc.width*0.55, doc.width*0.25])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(MELI_AZUL_CORP)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 16))
        
        # Estadísticas de frecuencia de eventos
        elements.append(Paragraph("Frecuencia de Eventos Materializados", heading_style))
        
        data_freq = [
            ["Métrica", "Valor"],
            ["Número mínimo de eventos materializados", str(stats_dict['freq_min'])],
            ["Número más probable de eventos materializados", str(stats_dict['freq_mode'])],
            ["Número máximo de eventos materializados", str(stats_dict['freq_max'])],
        ]
        
        t_freq = Table(data_freq, colWidths=[doc.width*0.55, doc.width*0.25])
        t_freq.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(MELI_AZUL_CORP)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ]))
        elements.append(t_freq)
        elements.append(Spacer(1, 24))
        
        # Tabla de percentiles de pérdida agregada
        elements.append(Paragraph("Percentiles de Pérdida Agregada", heading_style))
        
        percentiles_list = [50, 75, 80, 85, 90, 95, 99]
        data_pct_agg = [["Percentil", "Valor"]]
        for p in percentiles_list:
            data_pct_agg.append([f"P{p}", currency_format(stats_dict['percentiles'][p])])
        
        t_pct_agg = Table(data_pct_agg, colWidths=[doc.width*0.3, doc.width*0.3])
        t_pct_agg.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(MELI_AZUL_CORP)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ]))
        elements.append(t_pct_agg)
        elements.append(PageBreak())
        
        # Sección de estadísticas por evento de riesgo
        elements.append(Paragraph("Estadísticas por Evento de Riesgo", heading_style))
        elements.append(Spacer(1, 8))
        
        # Crear estilo para subtítulos de eventos
        event_title_style = ParagraphStyle(
            'EventTitle',
            parent=styles['Heading3'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=12,
            spaceBefore=10,
            spaceAfter=4,
            textColor=colors.HexColor('#333333')
        )
        
        # Para cada evento, mostrar estadísticas completas
        for i, evento in enumerate(self.eventos_riesgo):
            nombre_evento = evento['nombre']
            # Truncar nombre si es muy largo para el título
            if len(nombre_evento) > 60:
                nombre_evento_display = nombre_evento[:57] + "..."
            else:
                nombre_evento_display = nombre_evento
            
            elements.append(Paragraph(f"<b>{i+1}. {nombre_evento_display}</b>", event_title_style))
            
            # Info de vínculos si existen
            vinculos_evt = evento.get('vinculos', [])
            if vinculos_evt:
                deps = []
                for v in vinculos_evt:
                    nombre_padre = "?"
                    for e in self.eventos_riesgo:
                        if e['id'] == v.get('id_padre'):
                            nombre_padre = e['nombre'][:25]
                            break
                    desc = f"{v.get('tipo', '?')} → {nombre_padre} ({v.get('probabilidad', 100)}%"
                    fsev = v.get('factor_severidad', 1.0)
                    umbral = v.get('umbral_severidad', 0)
                    if fsev != 1.0:
                        desc += f", sev:{fsev:.2f}x"
                    if umbral > 0:
                        desc += f", umbral:${umbral:,}"
                    desc += ")"
                    deps.append(desc)
                dep_text = " | ".join(deps)
                elements.append(Paragraph(f"<i>Vínculos: {dep_text}</i>", styles['Normal']))
                elements.append(Spacer(1, 3))
            
            # Tabla de estadísticas del evento
            event_data = [
                ["Métrica", "Valor"],
                ["Media de Impacto", currency_format(stats_dict['event_means'][i])],
                ["Desviación Estándar", currency_format(stats_dict['event_std'][i])],
                ["Eventos mínimos materializados", str(stats_dict['event_freq_min'][i])],
                ["Eventos más probables materializados", str(stats_dict['event_freq_mode'][i])],
                ["Eventos máximos materializados", str(stats_dict['event_freq_max'][i])],
            ]
            
            t_evt = Table(event_data, colWidths=[doc.width*0.45, doc.width*0.25])
            t_evt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5C9F35')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ]))
            elements.append(t_evt)
            elements.append(Spacer(1, 6))
        
        elements.append(PageBreak())
        
        # Tabla de percentiles por evento (formato mejorado: eventos en filas)
        elements.append(Paragraph("Percentiles de Pérdida por Evento", heading_style))
        elements.append(Spacer(1, 8))
        
        # Encabezado: Evento | P50 | P75 | P80 | P85 | P90 | P95 | P99
        percentiles_header = ["Evento"] + [f"P{p}" for p in percentiles_list]
        data_pct_evt = [percentiles_header]
        
        # Agregar fila por cada evento
        for i, evento in enumerate(self.eventos_riesgo):
            nombre = evento['nombre']
            # Truncar nombres largos para que quepan
            if len(nombre) > 25:
                nombre = nombre[:22] + "..."
            
            row = [nombre]
            vals = np.percentile(self.perdidas_por_evento[i], percentiles_list)
            for val in vals:
                row.append(currency_format(val))
            data_pct_evt.append(row)
        
        # Agregar fila de Pérdida Total
        row_total = ["Pérdida Total"]
        for p in percentiles_list:
            row_total.append(currency_format(stats_dict['percentiles'][p]))
        data_pct_evt.append(row_total)
        
        # Calcular anchos de columna dinámicamente
        num_cols = len(percentiles_header)
        col_width_evento = doc.width * 0.22
        col_width_pct = (doc.width - col_width_evento) / (num_cols - 1)
        col_widths_pct = [col_width_evento] + [col_width_pct] * (num_cols - 1)
        
        t_pct_evt = Table(data_pct_evt, colWidths=col_widths_pct)
        
        # Estilo de tabla con colores alternados
        table_style_pct = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(MELI_AZUL_CORP)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Última fila en negrita
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F4E8')),  # Fila total con fondo verde claro
        ]
        
        # Alternar colores en filas de datos
        for i in range(1, len(data_pct_evt) - 1, 2):
            table_style_pct.append(('BACKGROUND', (0, i), (-1, i), colors.whitesmoke))
        
        t_pct_evt.setStyle(TableStyle(table_style_pct))
        elements.append(t_pct_evt)
        elements.append(PageBreak())
        
        # Añadir gráficos
        elements.append(Paragraph("Gráficos de Análisis", heading_style))
        
        from reportlab.platypus import KeepInFrame
        
        # Convertir figuras a imágenes para el PDF con mejor ajuste de tamaño
        for idx, fig in enumerate(figuras, start=1):
            # Extraer el título del gráfico para usarlo como encabezado en el PDF
            titulo = f"Gráfico {idx}"
            
            # Obtener el título del gráfico original antes de modificarlo
            if hasattr(fig, '_suptitle') and fig._suptitle:
                titulo_original = fig._suptitle.get_text()
                if titulo_original and len(titulo_original.strip()) > 0:
                    titulo = titulo_original
            
            # También verificar títulos en los ejes
            for ax in fig.get_axes():
                if ax.get_title() and len(ax.get_title().strip()) > 0:
                    # Si no tenemos un título mejor, usar este
                    if titulo == f"Gráfico {idx}":
                        titulo = ax.get_title()
            
            # Crear una figura limpia sin títulos para la exportación
            # Guardamos referencias a los títulos originales
            suptitle_original = None
            if hasattr(fig, '_suptitle') and fig._suptitle:
                suptitle_original = fig._suptitle.get_text()
                fig._suptitle.set_text("")
            
            # Guardar los títulos originales de los ejes
            axis_titles = []
            for ax in fig.get_axes():
                axis_titles.append(ax.get_title())
                ax.set_title("")  # Eliminar título temporalmente
            
            # Guardar figura sin títulos en buffer de memoria
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            
            # Restaurar títulos originales
            if hasattr(fig, '_suptitle') and fig._suptitle and suptitle_original:
                fig._suptitle.set_text(suptitle_original)
            
            # Restaurar títulos de ejes
            for ax, title in zip(fig.get_axes(), axis_titles):
                ax.set_title(title)
            
            # Añadir el título como encabezado en el PDF
            elements.append(Paragraph(titulo, styles['Heading3']))
            elements.append(Spacer(1, 6))
            
            # Calcular dimensiones máximas seguras para la imagen (75% de ancho, 500 pt de alto)
            width = doc.width * 0.75
            height = 400
            
            # Añadir imagen al PDF con dimensiones controladas
            img = Image(img_buffer, width=width, height=height, kind='proportional')
            
            # Usar KeepInFrame para garantizar que la imagen se ajuste correctamente
            image_container = KeepInFrame(width, height, [img], mode='shrink')
            elements.append(image_container)
            elements.append(Spacer(1, 12))
            
            # Salto de página entre gráficos (excepto el último)
            if idx < len(figuras):
                elements.append(PageBreak())
                
        # Construir el documento
        doc.build(elements)


# Ejecutamos el programa principal
if __name__ == "__main__":
    main()

