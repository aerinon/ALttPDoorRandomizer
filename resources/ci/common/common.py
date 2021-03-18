import os   # for env vars
import stat # file statistics
import sys  # default system info
from my_path import get_py_path

global UBUNTU_VERSIONS
global DEFAULT_EVENT
global DEFAULT_REPO_SLUG
global FILENAME_CHECKS
global FILESIZE_CHECK
UBUNTU_VERSIONS = {
  "latest": "focal",
  "20.04": "focal",
  "18.04": "bionic",
  "16.04": "xenial"
}
DEFAULT_EVENT = "event"
DEFAULT_REPO_SLUG = "miketrethewey/ALttPDoorRandomizer"
FILENAME_CHECKS = [ "Gui", "DungeonRandomizer" ]
FILESIZE_CHECK = (6 * 1024 * 1024) # 6MB

# take number of bytes and convert to string with units measure
def convert_bytes(num):
	for x in ["bytes","KB","MB","GB","TB","PB"]:
		if num < 1024.0:
			return "%3.1f %s" % (num,x)
		num /= 1024.0

# get filesize of file at path
def file_size(file_path):
	if os.path.isfile(file_path):
		file_info = os.stat(file_path)
		return convert_bytes(file_info.st_size)

# prepare environment variables
def prepare_env():
  global DEFAULT_EVENT
  global DEFAULT_REPO_SLUG
  env = {}

	# get app version
  APP_VERSION = ""
  APP_VERSION_FILE = os.path.join(".","resources","app","meta","manifests","app_version.txt")
  if os.path.isfile(APP_VERSION_FILE):
    with open(APP_VERSION_FILE,"r") as f:
      APP_VERSION = f.readlines()[0].strip()
  # ci data
  env["CI_SYSTEM"] = os.getenv("CI_SYSTEM","")
  # py data
  (env["PYTHON_EXE_PATH"],env["PY_EXE_PATH"],env["PIP_EXE_PATH"]) = get_py_path()
  # git data
  env["BRANCH"] = os.getenv("TRAVIS_BRANCH","")
  env["GITHUB_ACTOR"] = os.getenv("GITHUB_ACTOR","MegaMan.EXE")
  env["GITHUB_SHA"] = os.getenv("GITHUB_SHA","")
  env["GITHUB_RUN_NUMBER"] = os.getenv("GITHUB_RUN_NUMBER","")
  env["GITHUB_SHA_SHORT"] = env["GITHUB_SHA"]
  # commit data
  env["COMMIT_ID"] = os.getenv("TRAVIS_COMMIT",os.getenv("GITHUB_SHA",""))
  env["COMMIT_COMPARE"] = os.getenv("TRAVIS_COMMIT_RANGE","")
  # event data
  env["EVENT_MESSAGE"] = os.getenv("TRAVIS_COMMIT_MESSAGE","")
  env["EVENT_LOG"] = os.getenv("GITHUB_EVENT_PATH","")
  env["EVENT_TYPE"] = os.getenv("TRAVIS_EVENT_TYPE",os.getenv("GITHUB_EVENT_NAME",DEFAULT_EVENT))
  # repo data
  env["REPO_SLUG"] = os.getenv("TRAVIS_REPO_SLUG",os.getenv("GITHUB_REPOSITORY",DEFAULT_REPO_SLUG))
  env["REPO_USERNAME"] = ""
  env["REPO_NAME"] = ""

  # repo slug
  if '/' in env["REPO_SLUG"]:
    tmp = env["REPO_SLUG"].split('/')
    env["REPO_USERNAME"] = tmp[0]
    env["REPO_NAME"] = tmp[1]

  if not env["GITHUB_SHA"] == "":
    env["GITHUB_SHA_SHORT"] = env["GITHUB_SHA"][:7]

  # ci data
  env["BUILD_NUMBER"] = os.getenv("TRAVIS_BUILD_NUMBER",env["GITHUB_RUN_NUMBER"])

  GITHUB_TAG = os.getenv("TRAVIS_TAG",os.getenv("GITHUB_TAG",""))
  OS_NAME = os.getenv("TRAVIS_OS_NAME",os.getenv("OS_NAME",sys.platform)).replace("macOS","osx")
  OS_DIST = os.getenv("TRAVIS_DIST","notset")
  OS_VERSION = ""

  if "win32" in OS_NAME or \
    "cygwin" in OS_NAME or \
    "msys" in OS_NAME:
    OS_NAME = "windows"
  elif "darwin" in OS_NAME:
    OS_NAME = "osx"
  elif "linux2" in OS_NAME:
    OS_NAME = "linux"

  if '-' in OS_NAME:
    OS_VERSION = OS_NAME[OS_NAME.find('-')+1:]
    OS_NAME = OS_NAME[:OS_NAME.find('-')]
    if OS_NAME == "linux" or OS_NAME == "ubuntu":
      if OS_VERSION in UBUNTU_VERSIONS:
        OS_VERSION = UBUNTU_VERSIONS[OS_VERSION]
      OS_DIST = OS_VERSION

  if OS_VERSION == "" and not OS_DIST == "" and not OS_DIST == "notset":
    OS_VERSION = OS_DIST

	# if no tag
  if GITHUB_TAG == "":
    # if we haven't appended the build number, do it
    if env["BUILD_NUMBER"] not in GITHUB_TAG:
      GITHUB_TAG = APP_VERSION
      # if the app version didn't have the build number, add it
      # set to <app_version>.<build_number>
      if env["BUILD_NUMBER"] not in GITHUB_TAG:
        GITHUB_TAG += '.' + env["BUILD_NUMBER"]

  env["GITHUB_TAG"] = GITHUB_TAG
  env["OS_NAME"] = OS_NAME
  env["OS_DIST"] = OS_DIST
  env["OS_VERSION"] = OS_VERSION

  return env

# build filename based on metadata
def prepare_filename(BUILD_FILENAME):
	env = prepare_env()

	DEST_FILENAME = ""

	# build the filename
	if not BUILD_FILENAME == "":
		os.chmod(BUILD_FILENAME,0o755)
		fileparts = os.path.splitext(BUILD_FILENAME)
		DEST_SLUG = fileparts[0]
		DEST_EXTENSION = fileparts[1]
		DEST_SLUG = DEST_SLUG + '-' + env["GITHUB_TAG"] + '-' + env["OS_NAME"]
		if not env["OS_DIST"] == "" and not env["OS_DIST"] == "notset":
			DEST_SLUG += '-' + env["OS_DIST"]
		DEST_FILENAME = DEST_SLUG + DEST_EXTENSION
	return DEST_FILENAME

# find a binary file if it's executable
#  failing that, assume it's over 6MB
def find_binary(listdir):
  global FILENAME_CHECKS
  global FILESIZE_CHECK

  BUILD_FILENAMES = []
  executable = stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH
  for filename in os.listdir(listdir):
    if os.path.isfile(filename):
      if os.path.splitext(filename)[1] != ".py":
        st = os.stat(filename)
        mode = st.st_mode
        big = st.st_size > FILESIZE_CHECK
        if (mode & executable) or big:
          for check in FILENAME_CHECKS:
            if check in filename:
              BUILD_FILENAMES.append(filename)
  return BUILD_FILENAMES

if __name__ == "__main__":
  env = prepare_env()
  print(env)
