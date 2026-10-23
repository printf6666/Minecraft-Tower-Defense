# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('D:/pytools/Library/bin/libexpat.dll', '.'), ('D:/pytools/Library/bin/libbz2.dll', '.'), ('D:/pytools/Library/bin/liblzma.dll', '.'), ('D:/pytools/Library/bin/libmpdec-4.dll', '.'), ('D:/pytools/Library/bin/ffi.dll', '.')],
    datas=[('bgm', 'bgm'), ('debuff', 'debuff'), ('enchantment', 'enchantment'), ('enemy', 'enemy'), ('sound', 'sound'), ('tower', 'tower'), ('Minecraft.ttf', '.'), ('seed.json', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'scipy', 'pandas', 'matplotlib', 'PIL', 'tkinter'],
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
    name='MCTD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
