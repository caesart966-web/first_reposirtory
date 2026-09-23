# -*- mode: python ; coding: utf-8 -*-
# Сборка настольной версии: pyinstaller odo-app/desktop/odo.spec  (запускать из корня репозитория)
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))       # корень репозитория
APP = os.path.join(ROOT, "odo-app")
ENGINE = os.path.join(ROOT, ".claude", "skills", "sro-odo")

datas = [
    (os.path.join(APP, "server", "templates"), os.path.join("server", "templates")),
    (os.path.join(APP, "server", "static"), os.path.join("server", "static")),
    (os.path.join(ENGINE, "scripts"), os.path.join("engine", "scripts")),
    (os.path.join(ENGINE, "schemas"), os.path.join("engine", "schemas")),
    (os.path.join(ENGINE, "cases"), os.path.join("engine", "cases")),
    (os.path.join(ENGINE, "references"), os.path.join("engine", "references")),
]
datas += collect_data_files("pymupdf")
hiddenimports = (collect_submodules("uvicorn") + collect_submodules("server") + collect_submodules("anthropic")
                 + ["multipart", "python_multipart", "jinja2", "jsonschema", "docx", "openpyxl", "pymupdf", "tkinter", "webview",
                    "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on"])

a = Analysis(
    [os.path.join(APP, "desktop", "launcher.py")],
    pathex=[APP],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "httpx2"],
    noarchive=False,
)
pyz = PYZ(a.pure)

# один файл
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="ODO-proverka", console=False, upx=False,
          icon=os.path.join(APP, "desktop", "odo.ico") if os.path.exists(os.path.join(APP, "desktop", "odo.ico")) else None)

# папка (быстрее запускается, меньше ложных тревог антивирусов)
exe_dir = EXE(pyz, a.scripts, [], exclude_binaries=True, name="ODO-proverka", console=False, upx=False,
              icon=os.path.join(APP, "desktop", "odo.ico") if os.path.exists(os.path.join(APP, "desktop", "odo.ico")) else None)
coll = COLLECT(exe_dir, a.binaries, a.datas, name="ODO-proverka-folder")
