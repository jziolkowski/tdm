# -*- mode: python ; coding: utf-8 -*-

import platform
import setuptools_scm
import sys

version = setuptools_scm.get_version(local_scheme='no-local-version')

arch = ""
extension = ""
exe_extra_kwargs = {}

if sys.platform == 'win32':
    os = "win"
    arch, _ = platform.architecture()
    exe_extra_kwargs = {"icon": 'tdmgr.ico'}

elif sys.platform == 'darwin':
    os = "mac"
    extension = ".app"
    _, _, arch = platform.mac_ver()
    exe_extra_kwargs = {"bundle_identifier": 'com.tasmota.tdmgr', "icon": 'tdmgr.icns'}

filename = f"tdmgr_{version}_{os}_{arch}{extension}"

block_cipher = None

a = Analysis(
    ['tdmgr/run.py'],
    binaries=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=filename,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    **exe_extra_kwargs,
)
