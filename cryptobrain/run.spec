# -*- mode: python ; coding: utf-8 -*-

import os

# The root of the Django project (where this spec file is located)
PROJECT_ROOT = os.path.dirname(os.path.abspath(SPECPATH))

# --- Data files to bundle ---
# We need to include templates, static files, the database, and the .env file.
datas = [
    ('analyzer/templates', 'analyzer/templates'),
    ('staticfiles', 'staticfiles'),
    ('db.sqlite3', '.'),
    ('.env', '.'),  # Cambiado de '../.env' a '.env'
]

# --- Analysis Configuration ---
a = Analysis(
    ['run.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'analyzer.apps.AnalyzerConfig',
        'PIL',
        'jinja2',
        'colorama',
        'numpy',
    ],
    # This is the crucial part: we tell PyInstaller where to find our custom hooks.
    hookspath=['pyinstaller-hooks'],
    # The runtime hook will be executed when the app starts.
    runtime_hooks=['pyinstaller-hooks/rthook-django.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

# --- Executable Configuration ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    name='CryptoBrain',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True,  # Keep console=True to see startup errors
    icon=None,
)

# --- One-Dir Bundle Configuration ---
# This creates a directory with the EXE and all its dependencies,
# which is more reliable for complex apps like Django.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CryptoBrain',
)
