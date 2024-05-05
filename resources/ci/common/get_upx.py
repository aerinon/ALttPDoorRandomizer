import common
import os			# for env vars
import sys    # for path
import urllib.request	# for downloads
from shutil import unpack_archive

# only do stuff if we don't have a UPX folder

if not os.path.isdir(os.path.join(".","upx")):
  # get env vars
  env = common.prepare_env()
  # set up download url
  UPX_VERSION = os.getenv("UPX_VERSION") or "3.96"
  UPX_SLUG = ""
  UPX_FILE = ""
  if "windows" in env["OS_NAME"]:
    UPX_SLUG = "upx-" + UPX_VERSION + "-win64"
    UPX_FILE = UPX_SLUG + ".zip"
  else:
    UPX_SLUG = "upx-" + UPX_VERSION + "-amd64_linux"
    UPX_FILE = UPX_SLUG + ".tar.xz"
  UPX_URL = "https://github.com/upx/upx/releases/download/v" + UPX_VERSION + '/' + UPX_FILE

  # if it's not macos
  if "osx" not in env["OS_NAME"]:
    print("Getting UPX: " + UPX_FILE)

    # download UPX
    with open(os.path.join(".",UPX_FILE),"wb") as upx:
	    UPX_REQ = urllib.request.Request(
		    UPX_URL,
  		  data=None
  	  )
	    UPX_REQ = urllib.request.urlopen(UPX_REQ)
	    UPX_DATA = UPX_REQ.read()
	    upx.write(UPX_DATA)

    # extract UPX
    unpack_archive(UPX_FILE,os.path.join("."))

    # move UPX
    os.rename(os.path.join(".",UPX_SLUG),os.path.join(".","upx"))
    os.remove(os.path.join(".",UPX_FILE))

print("UPX should " + ("not " if not os.path.isdir(os.path.join(".","upx")) else "") + "be available.")
