# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\Kênh mới\\TC 196\\DTA 2.3.2\\src\\dta_autolive\\launcher\\main.py'],
    pathex=['D:\\Kênh mới\\TC 196\\DTA 2.3.2\\src'],
    binaries=[],
    datas=[],
    hiddenimports=['websockets', 'websockets.legacy', 'websockets.legacy.server', 'pydantic', 'pydantic_core', 'asyncio', 'json', 'cv2', 'numpy', 'PIL', 'ctypes', 'ctypes.wintypes', 'dta_autolive', 'dta_autolive.launcher', 'dta_autolive.launcher.backend_service', 'dta_autolive.infrastructure.websocket_server', 'dta_autolive.infrastructure.dta_softcam_engine', 'dta_autolive.infrastructure.dta_audio_driver', 'dta_autolive.infrastructure.product_pinner', 'dta_autolive.infrastructure.host_live_chat_responder', 'dta_autolive.infrastructure.satellite_seeding_manager', 'dta_autolive.infrastructure.tiktok_cart_scraper', 'dta_autolive.infrastructure.deepseek_engine', 'dta_autolive.infrastructure.dta_qwen_engine', 'dta_autolive.infrastructure.sadcaptcha_engine', 'dta_autolive.infrastructure.solver', 'dta_autolive.infrastructure.stream_recorder', 'dta_autolive.infrastructure.dta_driver_setup', 'dta_autolive.application.media_worker', 'dta_autolive.application.timeline_scheduler', 'dta_autolive.domain.models', 'dta_autolive.domain.state_machine'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'scipy', 'pandas', 'sympy', 'matplotlib', 'tkinter', 'IPython', 'notebook', 'paddle', 'tensorrt', 'pytest', 'unittest', 'tcl', 'tk'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='dta_backend',
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
    icon=['D:\\Kênh mới\\TC 196\\DTA 2.3.2\\assets\\logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='dta_backend',
)
