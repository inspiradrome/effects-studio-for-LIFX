# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

datas = [
    ("effects_studio/static", "effects_studio/static"),
    ("LICENSE", "."),
    ("README.md", "."),
    ("CHANGELOG.md", "."),
    ("THIRD_PARTY_NOTICES.md", "."),
]
datas += copy_metadata("lifx-photons-core", recursive=True)

photons_packages = (
    "photons_app",
    "photons_control",
    "photons_core",
    "photons_messages",
    "photons_protocol",
    "photons_transport",
)

hiddenimports = []
for package in photons_packages:
    hiddenimports += collect_submodules(package)
    # Photons generates protocol classes by inspecting package source at runtime.
    if package != "photons_core":
        datas += collect_data_files(package, include_py_files=True)

for package in ("sanic", "tracerite"):
    datas += collect_data_files(package)

a = Analysis(
    ["run_studio.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="EffectsStudioForLIFX",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/lifx-effects-studio.ico",
    version="packaging/windows-version.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="EffectsStudioForLIFX",
)
