# pylint: disable=invalid-name
# pylint: disable=subprocess-run-check
"""
Build MultiServer.py into MultiServer.exe
"""
import subprocess
import os
import shutil
import sys

# Spec file
SPEC_FILE = os.path.join(".", "source", "MultiServer.spec")

# Destination is current dir
DEST_DIRECTORY = '.'

# Check for UPX
if os.path.isdir("upx"):
    UPX_STRING = "--upx-dir=upx"
else:
    UPX_STRING = ""

if os.path.isdir("build") and not sys.platform.find("mac") and not sys.platform.find("osx"):
    shutil.rmtree("build")

# Run pyinstaller for MultiServer
subprocess.run(" ".join([f"pyinstaller {SPEC_FILE} ",
                                      UPX_STRING,
                                      "-y ",
                                      f"--distpath {DEST_DIRECTORY} ",
                                      ]),
                shell=True)
