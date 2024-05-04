import distutils.dir_util			# for copying trees
import os											# for env vars
import stat										# for file stats
import subprocess							# do stuff at the shell level
import common
from git_clean import git_clean
from shutil import copy, make_archive, move, rmtree	# file manipulation

env = common.prepare_env() # get env vars

dirs = [
  os.path.join("..", "artifact"), # temp dir for binary
  os.path.join("..", "build"),    # temp dir for other stuff
  os.path.join("..", "deploy")    # dir for archive
]
for dirname in dirs:
  if not os.path.isdir(dirname):
    os.makedirs(dirname)

# make dirs for each os
for dirname in ["linux","macos","windows"]:
  if not os.path.isdir(os.path.join("..","deploy",dirname)):
  	os.mkdir(os.path.join("..","deploy",dirname))

# sanity check permissions for working_dirs.json
dirpath = "."
for dirname in ["resources","user","meta","manifests"]:
	dirpath += os.path.join(dirpath,dirname)
	if os.path.isdir(dirpath):
		os.chmod(dirpath,0o755)

# nuke git files
for git in [ os.path.join(".", ".gitattrubutes"), os.path.join(".", ".gitignore") ]:
  if os.path.isfile(git):
    os.remove(git)

# nuke travis file if it exists
for travis in [ os.path.join(".", ".travis.yml"), os.path.join(".", ".travis.off") ]:
  if os.path.isfile(travis):
    os.remove(travis)

# nuke test suite if it exists
if os.path.isdir(os.path.join(".","tests")):
  distutils.dir_util.remove_tree(os.path.join(".","tests"))

BUILD_FILENAME = ""
ZIP_FILENAME = ""

# list executables
BUILD_FILENAME = common.find_binary(os.path.join("."))
if BUILD_FILENAME == "":
  BUILD_FILENAME = common.find_binary(os.path.join("..","artifact"))

if isinstance(BUILD_FILENAME,str):
  BUILD_FILENAME = list(BUILD_FILENAME)

BUILD_FILENAMES = BUILD_FILENAME

print(BUILD_FILENAMES)

if len(BUILD_FILENAMES) > 0:
  for BUILD_FILENAME in BUILD_FILENAMES:
    if not BUILD_FILENAME == "":
      if not "artifact" in BUILD_FILENAME:
        # move the binary to temp folder
        move(
          os.path.join(".",BUILD_FILENAME),
          os.path.join("..","artifact",BUILD_FILENAME)
        )

  # clean the git slate
  git_clean()

	# mv dirs from source code
  dirs = [
    os.path.join(".",".git"),
    os.path.join(".",".github"),
    os.path.join(".",".gitignore"),
    os.path.join(".","html"),
    os.path.join(".","resources","ci")
  ]
  for dirname in dirs:
    if os.path.isdir(dirname):
      move(
        dirname,
        os.path.join("..", "build", dirname)
      )

  for BUILD_FILENAME in BUILD_FILENAMES:
    if not "artifact" in BUILD_FILENAME:
      if os.path.isfile(os.path.join("..","artifact",BUILD_FILENAME)):
      	# move the binary back
      	move(
          os.path.join("..","artifact",BUILD_FILENAME),
      		os.path.join(".",BUILD_FILENAME)
      	)
      	# Make Linux/Mac binary executable
      	if "linux" in env["OS_NAME"] or "ubuntu" in env["OS_NAME"] or "mac" in env["OS_NAME"] or "osx" in env["OS_NAME"]:
      		os.chmod(os.path.join(".",BUILD_FILENAME),0o755)

	# .zip if windows
	# .tar.gz otherwise
  if len(BUILD_FILENAMES) > 1:
    ZIP_FILENAME = os.path.join("..","deploy",env["REPO_NAME"])
  else:
    ZIP_FILENAME = os.path.join("..","deploy",os.path.splitext(BUILD_FILENAME)[0])
  if env["OS_NAME"] == "windows":
    make_archive(ZIP_FILENAME,"zip")
    ZIP_FILENAME += ".zip"
  else:
    make_archive(ZIP_FILENAME,"gztar")
    ZIP_FILENAME += ".tar.gz"

	# mv dirs back
  for dir in dirs:
    if os.path.isdir(os.path.join("..","build",dir)):
      move(
        os.path.join("..","build",dir),
        os.path.join(".",dir)
      )

for BUILD_FILENAME in BUILD_FILENAMES:
  if not BUILD_FILENAME == "":
    print("Build Filename: " + BUILD_FILENAME)
    print("Build Filesize: " + common.file_size(BUILD_FILENAME))
  else:
    print("No Build to prepare: " + BUILD_FILENAME)

if not ZIP_FILENAME == "":
  print("Zip Filename:   " + ZIP_FILENAME)
  print("Zip Filesize:   " + common.file_size(ZIP_FILENAME))
else:
  print("No Zip to prepare: " + ZIP_FILENAME)

print("Git tag:        " + env["GITHUB_TAG"])

if (len(BUILD_FILENAMES) == 0) or (ZIP_FILENAME == ""):
  exit(1)
