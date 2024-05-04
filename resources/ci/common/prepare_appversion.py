import common
import os               # for env vars
from shutil import copy	# file manipulation

env = common.prepare_env()

# set tag to app_version.txt
# if not env["GITHUB_TAG"] == "":
#   with open(os.path.join(".","resources","app","meta","manifests","app_version.txt"),"w+") as f:
# 	  _ = f.read()
# 	  f.seek(0)
# 	  f.write(env["GITHUB_TAG"])
# 	  f.truncate()

if not os.path.isdir(os.path.join("..","build")):
	os.mkdir(os.path.join("..","build"))
copy(
	os.path.join(".","resources","app","meta","manifests","app_version.txt"),
	os.path.join("..","build","app_version.txt")
)
