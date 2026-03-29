# Risk_Lab_Beta_mac.spec
# -*- mode: python ; coding: utf-8 -*-
# Spec exclusivo para macOS — genera un .app bundle nativo
import sys
import os
from glob import glob

sys.setrecursionlimit(20000)

block_cipher = None

# Obtener todos los archivos SVG explícitamente
svg_files = [(svg, 'icons') for svg in glob('icons/*.svg')]

# Definir todos los archivos adicionales que necesita la aplicación
added_files = [
    ('styles/enhanced_theme.qss', 'styles'),
    ('styles/mercado_theme.qss', 'styles'),
    ('icons/button-icon-fix.qss', 'icons'),
    ('icons/button-fix.css', 'icons'),
    ('icons/icon-colors.css', 'icons'),
    ('icons/menu-styles.css', 'icons'),
    ('images/risk_lab_logo.png', 'images'),
]

# Agregar los archivos SVG explícitamente
added_files.extend(svg_files)

a = Analysis(
    ['Risk_Lab_Beta.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        # Módulos personalizados del proyecto
        'InteractiveFigureCanvas',
        'log_odds_utils',
        # Dependencias scipy
        'scipy.stats',
        'scipy.stats._stats',
        'scipy.special',
        'scipy.special._ufuncs_cxx',
        # Dependencias pandas
        'pandas',
        'pandas._libs.tslibs.timedeltas',
        # Dependencias matplotlib
        'matplotlib',
        'matplotlib.backends.backend_qt5agg',
        'seaborn',
        # Dependencias numpy
        'numpy',
        'numpy.random.common',
        'numpy.random.bounded_integers',
        'numpy.random.entropy',
        # Dependencias PyQt5
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtSvg',
        # Dependencias reportlab
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.lib',
        'reportlab.platypus',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Risk Lab Beta',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='images/risk_lab_logo.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Risk Lab Beta',
)

app = BUNDLE(
    coll,
    name='Risk Lab Beta.app',
    icon='images/risk_lab_logo.png',
    bundle_identifier='com.risklab.beta',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
    },
)
