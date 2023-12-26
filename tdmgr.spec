# -*- mode: python ; coding: utf-8 -*-

from tdmgr.__version__ import __version__

import sys

_suffix = f"_x64" if sys.maxsize > 2**32 else ""
filename = f"tdmgr_{__version__}{_suffix}"

block_cipher = None

a = Analysis(['tdmgr/run.py'],
             binaries=[],
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
