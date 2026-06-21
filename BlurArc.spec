# -*- mode: python ; coding: utf-8 -*-
"""
Blur Arc v0.5.3 - PyInstaller 打包配置
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)
SQLITE3_DLL = Path(sys.prefix) / 'Library' / 'bin' / 'sqlite3.dll'
PYTHON_DLL = Path(sys.prefix) / 'python313.dll'

import importlib.util, site
def _pkg_dir(name):
    spec = importlib.util.find_spec(name)
    if spec and spec.origin:
        return str(Path(spec.origin).parent)
    for sp in site.getsitepackages():
        p = Path(sp) / name
        if p.exists():
            return str(p)
    raise RuntimeError(f"Cannot find package: {name}")

block_cipher = None

datas = [
    (str(ROOT / 'frontend'), 'frontend'),
    (_pkg_dir('pillow_heif'), 'pillow_heif'),
]

ffmpeg_dir = ROOT / 'backend' / 'ffmpeg_binaries'
if ffmpeg_dir.exists():
    datas.append((str(ffmpeg_dir), 'backend/ffmpeg_binaries'))

hiddenimports = [
    'flask', 'flask_cors', 'werkzeug', 'werkzeug.serving', 'werkzeug.routing', 'werkzeug.exceptions',
    'jinja2', 'jinja2.ext', 'click',
    'sqlalchemy', 'sqlalchemy.dialects.sqlite', 'sqlalchemy.orm', 'sqlalchemy.ext.declarative',
    'PIL', 'PIL.Image', 'PIL.ExifTags', 'PIL.ImageOps',
    'pillow_heif',
    'dateutil', 'dateutil.parser',
    'tkinter', 'tkinter.filedialog',
    'email', 'email.mime', 'email.mime.text', 'html.parser',
    'webview', 'webview.platforms', 'webview.platforms.winforms',
    'qrcode',           # 手机上传二维码生成
    'threading',
    # 标准库（确保不被排除）
    'difflib', 'doctest', 'pdb', 'profile', 'pstats', 'cProfile',
    'ftplib', 'imaplib', 'smtplib', 'poplib', 'nntplib', 'telnetlib',
]

excludes = [
    'matplotlib', 'numpy', 'pandas', 'scipy',
    'IPython', 'notebook', 'jupyter',
    'test', 'unittest',
    'setuptools', 'pkg_resources', 'pip',
    'tkinter.test',
    'turtledemo', 'turtle', 'idlelib',
    '_pydev_bundle', 'pydevd',
]

ANACONDA_BASE = Path(sys.prefix) / 'Library' / 'bin'

PYTHON_DLL_TARGET = str(PYTHON_DLL.name)

a = Analysis(
    [str(ROOT / 'src' / 'BlurArc.py')],
    pathex=[str(ROOT)],
    binaries=[
        (str(SQLITE3_DLL), '.'),
        (str(ANACONDA_BASE / 'tk86t.dll'), '.'),
        (str(ANACONDA_BASE / 'tcl86t.dll'), '.'),
        (str(ANACONDA_BASE / 'ffi-7.dll'), '.'),
        (str(ANACONDA_BASE / 'ffi.dll'), '.'),
    ] if SQLITE3_DLL.exists() else [],
    datas=datas + [(str(PYTHON_DLL), '.')] if PYTHON_DLL.exists() else datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BlurArc',
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
    icon='docs/icon.ico',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=True,
        name='BlurArc.app',
        icon='docs/icon.icns',
        bundle_identifier='com.blurarc.app',
    )
else:
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=True,
        upx_exclude=[
            'vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll',
            'python3*.dll', 'webview2loader.dll', 'WebView2Loader.dll',
        ],
        name='BlurArc',
    )

import shutil
dist_dir = ROOT / 'dist' / 'BlurArc'
src_dll = dist_dir / '_internal' / 'python313.dll'
dst_dll = dist_dir / 'python313.dll'
if src_dll.exists():
    shutil.copy2(str(src_dll), str(dst_dll))
    print(f"Copied python313.dll to {dst_dll}")
