# pylint: disable=invalid-name
'''
List GitHub Actions versions used and latest versions
'''
import json
import os
import ssl
import urllib.request
import yaml
from json.decoder import JSONDecodeError

allACTIONS = {}
listACTIONS = []

VER_WIDTH = 10
NAME_WIDTH = 40
LINE_WIDTH = 1 + NAME_WIDTH + 5 + VER_WIDTH + 5 + VER_WIDTH + 1

def process_walk(key, node):
    '''
    Process walking through the array
    '''
    global allACTIONS
    global listACTIONS
    if key == "uses":
        action = node.split('@')
        version = ""
        if '@' in node:
            version = action[1]
        action = action[0]
        if action not in allACTIONS:
            allACTIONS[action] = {
                "versions": [],
                "latest": ""
            }
        allACTIONS[action]["versions"].append(version)
        allACTIONS[action]["versions"] = list(
            set(
                allACTIONS[action]["versions"]
            )
        )
        listACTIONS.append(node)


def walk(key, node):
    '''
    How to walk through the array
    '''
    if isinstance(node, dict):
        return {k: walk(k, v) for k, v in node.items()}
    elif isinstance(node, list):
        return [walk(key, x) for x in node]
    else:
        return process_walk(key, node)


for r, d, f in os.walk(os.path.join(".", ".github")):
    if "actions" in r or "workflows" in r:
        for filename in f:
            # if it's not a YAML or it's turned off, skip it
            if (".yml" not in filename and ".yaml" not in filename) or (".off" in filename):
                continue
            listACTIONS = []
            # print filename
            filename_line = "─" * (len(os.path.join(r, filename)) + 2)
            print(
                "┌" +
                filename_line +
                "┐"
            )
            print("| " + os.path.join(r, filename) + " |")
            # read the file
            with(open(os.path.join(r, filename), "r", encoding="utf-8")) as yamlFile:
                print(
                    "├" +
                    filename_line +
                    "┴" +
                    ("─" * (LINE_WIDTH - len(filename_line) + 1)) +
                    "┐"
                )
                yml = yaml.safe_load(yamlFile)
                walk("uses", yml)
                dictACTIONS = {}
                for k in sorted(list(set(listACTIONS))):
                    action = k.split('@')[0]
                    version = k.split('@')[1] if '@' in k else ""
                    latest = ""
                    # if it's not a location action, get the latest version number
                    if "./." not in action:
                        apiURL = f"https://api.github.com/repos/{action}/releases/latest"
                        if True:
                            apiReq = None
                            try:
                                apiReq = urllib.request.urlopen(
                                    apiURL,
                                    context=ssl._create_unverified_context()
                                )
                            except urllib.error.HTTPError as e:
                                if e.code != 403:
                                    print(e.code, apiURL)
                            if apiReq:
                                apiRes = {}
                                try:
                                    apiRes = json.loads(
                                        apiReq.read().decode("utf-8"))
                                except JSONDecodeError as e:
                                    raise ValueError("🔴API Request failed: " + apiURL)
                                if apiRes:
                                    latest = apiRes["tag_name"] if "tag_name" in apiRes else ""
                                    if latest != "":
                                        allACTIONS[action]["latest"] = latest
                    dictACTIONS[action] = version
                # print action name and version info
                for action, version in dictACTIONS.items():
                    print(
                        "| " + \
                        f"{action.ljust(NAME_WIDTH)}" + \
                        "\t" + \
                        f"{(version or 'N/A').ljust(VER_WIDTH)}" + \
                        "\t" + \
                        f"{(allACTIONS[action]['latest'] or 'N/A').ljust(VER_WIDTH)}" + \
                        " |"
                    )
                print(
                    "└" +
                    ("─" * (LINE_WIDTH + 2)) +
                    "┘"
                )
            print("")

# print outdated versions summary
first = True
outdated = False
for action, actionData in allACTIONS.items():
    if len(actionData["versions"]) > 0:
        if actionData["latest"] != "" and actionData["versions"][0] != actionData["latest"]:
            outdated = True
            if first:
                first = False
                filename_line = "─" * (len("| Outdated |"))
                print(
                    "┌" +
                    filename_line +
                    "┐"
                )
                print("| 🔴Outdated |")
                print(
                    "├" +
                    filename_line +
                    "┴" +
                    ("─" * (LINE_WIDTH - len(filename_line) + 1)) +
                    "┐"
                )
            print(
                "| " + \
                f"{action.ljust(40)}" + \
                "\t" + \
                f"{(','.join(actionData['versions']) or 'N/A').ljust(10)}" + \
                "\t" + \
                f"{actionData['latest'].ljust(10)}" + \
                " |"
            )
if outdated:
    print(
        "└" +
        ("─" * (LINE_WIDTH + 2)) +
        "┘"
    )
