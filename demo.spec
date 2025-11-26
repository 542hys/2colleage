# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['demo.py'],
    pathex=[],
    binaries=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
    datas=[
    ('./global_config.json', 'configs'),  # 源文件：当前目录下的 global_config.json → 打包到 configs 文件夹
    ('./utils/config_strings.json', 'utils'),
    ('./models/model_config.json', 'models'),  # 去掉末尾的多余引号 "
    ('./models/protocol_templates.json', 'models')  # 正确：源文件路径和目标文件夹均无误
    
]
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='demo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='demo',
)
