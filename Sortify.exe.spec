# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('ui/styles.css', 'ui'), ('resources/icons/*.png', 'resources/icons'), ('data', 'data')]
binaries = []
hiddenimports = ['sqlite3', 'sqlite3.dbapi2', 'win32security', 'ntsecuritycon', 'sklearn.neighbors._partition_nodes', 'sklearn.utils._cython_blas', 'sklearn.neighbors._quad_tree', 'sklearn.tree._utils', 'spacy.kb', 'spacy.tokens', 'spacy.lang.en', 'en_core_web_sm', 'en_core_web_sm.load', 'spacy_legacy', 'spacy_legacy.architectures', 'PIL._tkinter_finder', 'numpy.random.common', 'numpy.random.bounded_integers', 'numpy.random.entropy', 'cymem', 'cymem.cymem', 'preshed', 'preshed.maps', 'blis', 'blis.py', 'thinc', 'thinc.api']
tmp_ret = collect_all('numpy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('thinc')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('spacy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('blis')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('cymem')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('preshed')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=['spacy_hook.py'],
    excludes=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'PySide2', 'PySide2.QtCore', 'PySide2.QtGui', 'PySide2.QtWidgets'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Sortify.exe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources\\icons\\app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Sortify.exe',
)
