# -*- mode: python -*-

import json
import os
import sys
from json.decoder import JSONDecodeError
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
console = False  # <--- change this to True to enable command prompt when the app runs

if sys.platform.find("mac") or sys.platform.find("osx"):
    console = True

BINARY_SLUG = "MultiServer"


def recurse_for_py_files(names_so_far):
    # get py files
    returnvalue = []
    for name in os.listdir(os.path.join(*names_so_far)):
        # ignore __pycache__
        if name != "__pycache__":
            subdir_name = os.path.join(*names_so_far, name)
            if os.path.isdir(subdir_name):
                new_name_list = names_so_far + [name]
                for filename in os.listdir(os.path.join(*new_name_list)):
                    base_file, file_extension = os.path.splitext(filename)
                    # if it's a .py
                    if file_extension == ".py":
                        new_name = ".".join(new_name_list+[base_file])
                        if not new_name in returnvalue:
                            returnvalue.append(new_name)
                returnvalue.extend(recurse_for_py_files(new_name_list))
    return returnvalue


hiddenimports = recurse_for_py_files(["source"])
for hidden in (collect_submodules("pkg_resources")):
    hiddenimports.append(hidden)

a = Analysis(
    [f"../{BINARY_SLUG}.py"],
    pathex=[],
    binaries=[],
    datas=[('../data/', 'data/')],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

# https://stackoverflow.com/questions/17034434/how-to-remove-exclude-modules-and-files-from-pyinstaller
excluded_binaries = [
    'mfc140u.dll',
    'msvcp140.dll',
    'ucrtbase.dll',
    'VCRUNTIME140.dll'
]

# win is temperamental
with open(os.path.join(".","resources","app","meta","manifests","excluded_dlls.json")) as dllsManifest:
  dlls = []
  try:
    dlls = json.load(dllsManifest)
  except JSONDecodeError as e:
    raise ValueError("Windows DLLs manifest malformed!")
  for dll in dlls:
    for submod in ["core", "crt"]:
      for ver in ["1-1-0", "1-1-1", "1-2-0", "2-1-0"]:
        excluded_binaries.append(f"api-ms-win-{submod}-{dll}-l{ver}.dll")

a.binaries = TOC([x for x in a.binaries if x[0] not in excluded_binaries])

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
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
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=console
)
