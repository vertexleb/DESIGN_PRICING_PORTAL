# PyInstaller spec: one-file, windowed, always elevated (UAC manifest).
# Build with:  pyinstaller --noconfirm --clean corex_boot.spec
a = Analysis(
    ["src/corex_boot/__main__.py"],
    pathex=["src"],
    datas=[
        ("src/corex_boot/scripts/*.ps1", "corex_boot/scripts"),
        ("src/corex_boot/gui/style.qss", "corex_boot/gui"),
        ("assets/corex_boot.ico", "."),
    ],
    excludes=["tkinter", "unittest", "pydoc", "pytest", "pycdlib"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CorexBoot",
    console=False,
    uac_admin=True,
    icon="assets/corex_boot.ico",
    version="version_info.txt",
    upx=False,
)
