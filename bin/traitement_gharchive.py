import os
import json
import gzip
import hashlib
import pathlib
import argparse
import datetime
import requests
import configparser
from uuid import uuid4

pathProg = pathlib.Path(__file__).parent.absolute()

uuid = "80172ead-7023-496c-a4be-6ee280d8fbcf"

config = configparser.ConfigParser()
config.read('../etc/config.cfg')

def json_patch(element, i, j, cpPatch):
    json_patch = {}
    json_patch["data"] = j["patch"]
    json_patch["data-sha256"] = str(hashlib.sha256(json_patch["data"].encode()).hexdigest())

    json_patch["default-encoding"] = "UTF-8"

    meta_dict = dict()
    meta_dict["github:id_event"] = element["id"]

    meta_dict["github:repo_id"] = str(element["repo"]["id"])
    meta_dict["github:repo_name"] = element["repo"]["name"]
    meta_dict["github:repo_owner"] = element["actor"]["login"]
    meta_dict["github:repo_owner_id"] = str(element["actor"]["id"])

    meta_dict["github:push_id"] = str(element["payload"]["push_id"])
    meta_dict["github:commit_id"] = element["payload"]["commits"][i]["sha"]
    meta_dict["github:commit_url"] = element["payload"]["commits"][i]["url"]

    meta_dict["github:pusher_email"] = element["payload"]["commits"][i]["author"]["email"]
    meta_dict["github:pusher"] = element["payload"]["commits"][i]["author"]["name"]

    if "org" in element:
        meta_dict["github:org_id"] = str(element["org"]["id"])
        meta_dict["github:org_name"] = element["org"]["login"]
    else:
        meta_dict["github:org_id"] = ""
        meta_dict["github:org_name"] = ""

    meta_dict["github:datestamp"] = date
    meta_dict["github:timestamp"] = time
    meta_dict["github:timezone"] = "UTC"

    meta_dict["github:parent"] = uuid_parent

    json_patch["meta"] = meta_dict

    json_patch["source"] = "patch"
    json_patch["source-uuid"] = uuid

    cpPatch += 1

    pathPatchLoc = os.path.join(pathPatch, "patch")
    pathPatchLoc = "%s_%s.json" % (pathPatchLoc, cpPatch)

    with open(pathPatchLoc, "w") as write_file:
        json.dump(json_patch, write_file, indent=4)
    
    return cpPatch
    

def json_commit(element, i, cpCommit, flagCommitDelete, flagRepoDelete):
    json_commit = {}

    json_commit["data"] = element["payload"]["commits"][i]["message"]
    json_commit["data-sha256"] = str(hashlib.sha256(json_commit["data"].encode()).hexdigest())
    json_commit["default-encoding"] = "UTF-8"

    meta_commit = dict()
    meta_commit["id"] = uuid_parent
    meta_commit["github:id_event"] = element["id"]

    meta_commit["github:repo_id"] = str(element["repo"]["id"])
    meta_commit["github:repo_name"] = element["repo"]["name"]
    meta_commit["github:repo_owner"] = element["actor"]["login"]
    meta_commit["github:repo_owner_id"] = str(element["actor"]["id"])

    meta_commit["github:push_id"] = str(element["payload"]["push_id"])
    meta_commit["github:commit_id"] = element["payload"]["commits"][i]["sha"]
    meta_commit["github:commit_url"] = element["payload"]["commits"][i]["url"]

    meta_commit["github:pusher_email"] = element["payload"]["commits"][i]["author"]["email"]
    meta_commit["github:pusher"] = element["payload"]["commits"][i]["author"]["name"]

    if "org" in element:
        meta_commit["github:org_id"] = str(element["org"]["id"])
        meta_commit["github:org_name"] = element["org"]["login"]
    else:
        meta_commit["github:org_id"] = ""
        meta_commit["github:org_name"] = ""

    meta_commit["github:datestamp"] = date
    meta_commit["github:timestamp"] = time
    meta_commit["github:timezone"] = "UTC"

    if flagRepoDelete:
        meta_commit["github:delete_repo"] = True
    if flagCommitDelete:
        meta_commit["github:delete_commit"] = True
    

    json_commit["meta"] = meta_commit

    json_commit["source"] = "commit"
    json_commit["source-uuid"] = uuid

    cpCommit += 1

    pathCommitLoc = os.path.join(pathCommit, "commit")
    pathCommitLoc = "%s_%s.json" % (pathCommitLoc, cpCommit)

    with open(pathCommitLoc, "w") as write_file:
        json.dump(json_commit, write_file, indent=4)
    
    return cpCommit




def traitement_json(element, i, cpPatch, cpCommit):
    flagRepoDelete = False
    flagCommitDelete = False

    response = requests.get(element["payload"]["commits"][i]["url"])
    json_api = json.loads(response.text)

    if "message" in json_api:
        ## The Repository has been deleted
        if "Not Found" in json_api["message"]:
            flagRepoDelete = True
        ## The commit has been deleted
        if "No commit found" in json_api["message"]:
            flagCommitDelete = True
        if "API rate limit exceeded" in json_api["message"]:
            print("\n\n[-] API rate limit exceeded")
            exit(-1)
    else:
        for j in json_api["files"]:
            if "patch" in j:
                cpPatch = json_patch(element, i, j, cpPatch)
    
    cpCommit = json_commit(element, i, cpCommit, flagCommitDelete, flagRepoDelete)

    return cpPatch, cpCommit


# arguments parsing

parser = argparse.ArgumentParser()
parser.add_argument("datetime", help="date of the GHArchive, YYYY-MM-DD-H, YYYY-MM-DD-{H..H}, YYYY-MM-{DD..DD}-{H..H}")
parser.add_argument("--nocache", help="disable cache", action="store_true")
parser.add_argument("-u", "--users", help="search username", action="store_true")
parser.add_argument("-o", "--org", help="search organisation", action="store_true")
parser.add_argument("-l", "--list", help="list of word to search. If no list is give, all commit message will be add")
args = parser.parse_args()

url = "https://data.gharchive.org/%s.json.gz" % (args.datetime)
filename = url.split("/")[-1]
pathTemp = os.path.join(pathProg, filename)
pathPatch = os.path.join(pathProg, "patch")
pathCommit = os.path.join(pathProg, "commit")
pathError = os.path.join(pathProg, "error.json")

if args.list:
    with open(args.list, "r") as read_file:
        list_leak = read_file.readlines()

## Download archive file
print("[+] Downloading...")
r = requests.get(url)

if len(r.content) == 127:
    print("[-] Date Format Error")
    exit(-1)
    
if not os.path.isfile(pathTemp):
    with open(pathTemp, "wb") as f:
                   
        f.write(r.content)

## Open json file
print("[+] Unizp...")
data = [json.loads(line) for line in gzip.open(pathTemp, 'r')]
# with open(pathTemp, "r") as json_read:
    # data = json.load(json_read)


print("[+] Traitment...")
ele_list = list()

for element in data:
    if element["type"] == "PushEvent":
        flag = False
        if args.org or args.users:
            if "org" in element and args.org == element["org"]["login"]:
                # ele_list.append(element)
                # continue
                flag = True
            for i in range(0, len(element["payload"]["commits"])):
                if args.users == element["payload"]["commits"][i]["author"]["name"]:
                    flag = True
                    break

        ## org or user match with entry
        if flag or (not args.org and not args.users):
            """if args.list:
                flagList = False
                for i in range(0, len(element["payload"]["commits"])):
                    for lines in list_leak:
                        if lines.rstrip("\n") in element["payload"]["commits"][i]["message"]:
                            ele_list.append(element)
                            flagList = True
                            break
                    if flagList:
                        break
            ## There's no list-leak, so element is add without check commit message
            else:"""
            ele_list.append(element)

print("[+] Rule Creation")

if not os.path.isdir(pathCommit):
    os.mkdir(pathCommit)
if not os.path.isdir(pathPatch):
    os.mkdir(pathPatch)

## Rule creation
cpCommit = 0
cpPatch = 0
for element in ele_list:
    date = datetime.datetime.strptime(element["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
    time = datetime.datetime.strptime(element["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%H:%M:%S")

    uuid_parent = str(uuid4())

    for i in range(0,len(element["payload"]["commits"])):
        if args.list:
            for lines in list_leak:
                if lines.rstrip("\n") in element["payload"]["commits"][i]["message"]:
                    cpPatch, cpCommit = traitement_json(element, i, cpPatch, cpCommit)
        else:
            cpPatch, cpCommit = traitement_json(element, i, cpPatch, cpCommit)


                    
    print("\r[+] Commit JSON files: %s, Patch JSON files: %s" % (cpCommit, cpPatch), end="")
    # print("\r[+] Patch JSON files: %s" % (cpCommit), end="")

