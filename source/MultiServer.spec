"""
PyInstaller spec file for MultiServer.py
"""
# pyling: disable=invalid-name
# pylint: disable=too-many-nested-blocks
# -*- mode: python -*-
import os
import sys

BLOCK_CIPHER = None
CONSOLE = True   #   <--- change this to True to enable command prompt when the app runs

if sys.platform.find("mac") or sys.platform.find("osx"):
  CONSOLE = False

BINARY_SLUG = "MultiServer"

def recurse_for_py_files(names_so_far):
    """
    Search recursively for python script files
    """
    returnvalue = []
    for name in os.listdir(os.path.join(*names_so_far)):
        if name != "__pycache__":
            subdir_name = os.path.join(*names_so_far, name)
            if os.path.isdir(subdir_name):
                new_name_list = names_so_far + [name]
                for filename in os.listdir(os.path.join(*new_name_list)):
                    base_file,file_extension = os.path.splitext(filename)
                    if file_extension == ".py":
                        new_name = ".".join(new_name_list+[base_file])
                        if new_name not in returnvalue:
                            returnvalue.append(new_name)
                returnvalue.extend(recurse_for_py_files(new_name_list))
    returnvalue.append("PIL._tkinter_finder") #Linux needs this
    return returnvalue

hiddenimports = []
binaries = []

a = Analysis([f"../{BINARY_SLUG}.py"],
             pathex=[],
             binaries=binaries,
             datas=[('../data/', 'data/')],
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=BLOCK_CIPHER,
             noarchive=False)

# https://stackoverflow.com/questions/17034434/how-to-remove-exclude-modules-and-files-from-pyinstaller
excluded_binaries = [
        'VCRUNTIME140.dll',
        'ucrtbase.dll',
        'msvcp140.dll',
        'mfc140u.dll']
a.binaries = TOC([x for x in a.binaries if x[0] not in excluded_binaries])

pyz = PYZ(
          a.pure,
          a.zipped_data,
          cipher=BLOCK_CIPHER
)
exe = EXE(
          pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name=BINARY_SLUG,
          debug=False,
          bootloader_ignore_signals=False,
          icon=os.path.join(os.getcwd(),"data","ER.ico"),
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=CONSOLE
)
