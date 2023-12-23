# -*- mode: python ; coding: utf-8 -*-

from __version__ import __version__

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--arch")
parser.add_argument("--os", default="windows")
options = parser.parse_args()

block_cipher = None

_suffix = f"_{options.arch}" if options.arch else ""
_extension = ".exe" if options.os == "windows"
filename = f"tdmgr_{__version__}{_suffix}{_extension}"


a = Analysis(['tdmgr.py'],
             binaries=[],
             datas=[('GUI', 'GUI'), ('Util', 'Util')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
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
          console=False, icon='tdmgr.ico')
