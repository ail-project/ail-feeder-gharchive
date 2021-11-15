import os
import json

pathPatch = "B:\\git\\ail-feeder-gharchive\\bin\\patch"
pathCommit = "B:\\git\\ail-feeder-gharchive\\bin\\commit"

cpPatch = 0

for content in os.listdir(pathPatch):
    chemin = os.path.join(pathPatch, content)
    if os.path.isfile(chemin):
        cpPatch += 1
        with open(chemin, "r") as read_file:
            json_patch = json.load(read_file)

            flag = False

            for contentC in os.listdir(pathCommit):
                cheminC = os.path.join(pathCommit, contentC)
                if os.path.isfile(cheminC):
                    with open(cheminC, "r") as read_commit:
                        json_commit = json.load(read_commit)

                        if json_patch["meta"]["github:parent"] == json_commit["meta"]["id"]:
                            flag = True
                            break
                            
            if not flag:
                print("json name: %s\n" % (content))
                print(json_patch)
                exit(-1)
    print("\rpatch file: %s" % (cpPatch), end="")