# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.building.api import PYZ, EXE
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_submodules

jinja_module = collect_submodules('jinja2')
click_module = collect_submodules('click')
alive_module = collect_submodules('alive_progress')
grapheme_module = collect_submodules('grapheme')
openai_module = collect_submodules('openai')
numpy_module = collect_submodules('numpy')
pyfiglet_module = collect_submodules('pyfiglet')


a = Analysis(
    ['cb_release_note.py'],
    pathex=[],
    binaries=[],
    datas=[('cb_release_config_schema.yaml','.'),
    ('cb_release_notes_config.yaml','.'),
    ('./templates/*','templates')],
    hiddenimports= jinja_module + click_module + alive_module + grapheme_module + openai_module + numpy_module + pyfiglet_module,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='cb-release-note',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
