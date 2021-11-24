import os
import re
import json
import gzip
import time
import hashlib
import pathlib
import argparse
import datetime
import requests
import subprocess
import configparser
from uuid import uuid4

pathProg = pathlib.Path(__file__).parent.absolute()

config = configparser.ConfigParser()
config.read('../etc/config.cfg')

if 'general' in config:
    uuid = config['general']['uuid']

if 'github' in config:
    api_token = config['github']['api_token']


def json_patch(element, i, j, cpPatch, json_api_repo, json_api):
    json_patch = {}
    json_patch["data"] = j["patch"]
    json_patch["data-sha256"] = str(hashlib.sha256(json_patch["data"].encode()).hexdigest())

    json_patch["default-encoding"] = "UTF-8"

    meta_dict = dict()
    meta_dict["github:id_event"] = element["id"]

    meta_dict["github:repo_id"] = str(element["repo"]["id"])
    
    meta_dict["github:repo_name"] = element["repo"]["name"]

    if not json_api_repo == None:
        meta_dict["github:repo_node_id"] = json_api_repo["node_id"]
        meta_dict["github:repo_owner"] = json_api_repo["owner"]["login"]
        meta_dict["github:repo_owner_id"] = str(json_api_repo["owner"]["id"])
        meta_dict["github:repo_owner_node_id"] = json_api_repo["owner"]["node_id"]

    meta_dict["github:push_id"] = str(element["payload"]["push_id"])
    meta_dict["github:commit_id"] = element["payload"]["commits"][i]["sha"]
    meta_dict["github:commit_node_id"] = json_api["node_id"]
    meta_dict["github:commit_url"] = element["payload"]["commits"][i]["url"]

    meta_dict["github:pusher_email"] = element["payload"]["commits"][i]["author"]["email"]
    meta_dict["github:pusher"] = element["payload"]["commits"][i]["author"]["name"]

    try:
        meta_dict["github:pusher_id"] = str(json_api["committer"]["id"])
        meta_dict["github:pusher_node_id"] = json_api["committer"]["node_id"]
    except:
        pass

    if "org" in element:
        meta_dict["github:org_id"] = str(element["org"]["id"])
        meta_dict["github:org_name"] = element["org"]["login"]

    meta_dict["github:datestamp"] = date
    meta_dict["github:timestamp"] = time_element
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
    

def json_commit(element, i, cpCommit, flagCommitDelete, flagRepoDelete, json_api_repo, json_api):
    json_commit = {}

    json_commit["data"] = element["payload"]["commits"][i]["message"]
    json_commit["data-sha256"] = str(hashlib.sha256(json_commit["data"].encode()).hexdigest())
    json_commit["default-encoding"] = "UTF-8"

    meta_commit = dict()
    meta_commit["id"] = uuid_parent
    meta_commit["github:id_event"] = element["id"]

    meta_commit["github:repo_id"] = str(element["repo"]["id"])
    meta_commit["github:repo_name"] = element["repo"]["name"]

    if not json_api_repo == None:
        meta_commit["github:repo_node_id"] = json_api_repo["node_id"]
        meta_commit["github:repo_owner"] = json_api_repo["owner"]["login"]
        meta_commit["github:repo_owner_id"] = str(json_api_repo["owner"]["id"])
        meta_commit["github:repo_owner_node_id"] = json_api_repo["owner"]["node_id"]

    meta_commit["github:push_id"] = str(element["payload"]["push_id"])
    meta_commit["github:commit_id"] = element["payload"]["commits"][i]["sha"]
    if not "message" in json_api:
        meta_commit["github:commit_node_id"] = json_api["node_id"]
    meta_commit["github:commit_url"] = element["payload"]["commits"][i]["url"]

    meta_commit["github:pusher_email"] = element["payload"]["commits"][i]["author"]["email"]
    meta_commit["github:pusher"] = element["payload"]["commits"][i]["author"]["name"]
    if not "message" in json_api:
        try:
            meta_commit["github:pusher_id"] = str(json_api["committer"]["id"])
            meta_commit["github:pusher_node_id"] = json_api["committer"]["node_id"]
        except:
            pass

    if "org" in element:
        meta_commit["github:org_id"] = str(element["org"]["id"])
        meta_commit["github:org_name"] = element["org"]["login"]

    meta_commit["github:datestamp"] = date
    meta_commit["github:timestamp"] = time_element
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

def subprocessCall(request):
    p = subprocess.Popen(request, stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()

    return output

def api_traitment(json_api, time_to_wait):
    flagRepoDelete = flagCommitDelete = flagRecur = False

    if "message" in json_api:
        ## The Repository has been deleted
        if "Not Found" in json_api["message"]:
            flagRepoDelete = True
        ## The commit has been deleted
        if "No commit found" in json_api["message"]:
            flagCommitDelete = True
        if "Bad credentials" in json_api["message"]:
            print("[-] Bad credentials for API")
            exit(-1)
        if "API rate limit exceeded" in json_api["message"]:

            time_remain = datetime.datetime.fromtimestamp(time_to_wait).strftime('%Y-%m-%d %H:%M:%S')
            time_remain = datetime.datetime.strptime(time_remain, "%Y-%m-%d %H:%M:%S")
            diff = abs(time_remain - datetime.datetime.now())

            print("\n\n[-] API rate limit exceeded, sleep for %s" % (diff))
            time.sleep(diff.total_seconds() + 10)

            flagRecur = True

    return flagRepoDelete, flagCommitDelete, flagRecur


def traitement_json(element, i, cpPatch, cpCommit):
    flagRepoDelete = flagCommitDelete = flagRecur = flagCommit = False
    locRepoDelete = locCommitDelete = locRecur = False

    header = {'Authorization': 'token ' + api_token}
    response = requests.get(element["payload"]["commits"][i]["url"], headers=header)

    json_api = json.loads(response.content)

    flagRepoDelete, flagCommitDelete, flagRecur = api_traitment(json_api, int(response.headers['X-RateLimit-Reset']))

    while flagRecur:
        flagCommit = True

        response = requests.get(element["payload"]["commits"][i]["url"], headers=header)
        json_api = json.loads(response.content)

        flagRepoDelete, flagCommitDelete, flagRecur = api_traitment(json_api, int(response.headers['X-RateLimit-Reset']))

    ## Get repo owner
    json_api_repo = None
    if not flagRepoDelete:
        header = {'Authorization': 'token ' + api_token}
        response = requests.get(element["repo"]["url"], headers=header)

        json_api_repo = json.loads(response.content)

        locRepoDelete, locCommitDelete, locRecur = api_traitment(json_api_repo, int(response.headers['X-RateLimit-Reset']))
        while flagRecur:
            response = requests.get(element["payload"]["commits"][i]["url"], headers=header)
            json_api = json.loads(response.content)

            locRepoDelete, locCommitDelete, locRecur = api_traitment(json_api_repo, int(response.headers['X-RateLimit-Reset']))

    ## Create Json file
    if not flagCommitDelete and not flagRepoDelete:
        for j in json_api["files"]:
            if "patch" in j:
                cpPatch = json_patch(element, i, j, cpPatch, json_api_repo, json_api)
    if not flagCommit:
        cpCommit = json_commit(element, i, cpCommit, flagCommitDelete, flagRepoDelete, json_api_repo, json_api)

    return cpPatch, cpCommit

def check_archive_folder(pathArchive, archive):
    for file in os.listdir(pathArchive):
        if file == archive:
            return True
    return False




# arguments parsing

parser = argparse.ArgumentParser()
parser.add_argument("datetime", help="date of the GHArchive, YYYY-MM-DD-H, YYYY-MM-DD-{H..H}, YYYY-MM-{DD..DD}-{H..H}, YYYY-MM-{DD..DD}-H")
parser.add_argument("--nocache", help="disable cache", action="store_true")
parser.add_argument("-u", "--users", help="search username")
parser.add_argument("-o", "--org", help="search organisation")
parser.add_argument("-l", "--list", help="list of word to search. If no list is give, all commit message will be add")
args = parser.parse_args()


x = re.match(r"[0-9]{4}\-[0-9]{2}\-\{?[0-9]{1,2}\.{0,2}[0-9]{0,2}\}?\-\{?[0-9]{1,2}\.{0,2}[0-9]{0,2}\}?", args.datetime)
if x == None:
    print("[-] Date Format Error")
    exit(-1)


pathArchive = os.path.join(pathProg, "archive")
pathPatch = os.path.join(pathProg, "patch")
pathCommit = os.path.join(pathProg, "commit")
pathError = os.path.join(pathProg, "error.json")

if not os.path.isdir(pathArchive):
    os.mkdir(pathArchive)

if args.list:
    with open(args.list, "r") as read_file:
        list_leak = read_file.readlines()
if args.org:
    with open(args.org, "r") as read_file:
        list_org = read_file.readlines()
if args.users:
    with open(args.users, "r") as read_file:
        list_users = read_file.readlines()

## Download archive file
print("[+] Downloading...")
if "{" in args.datetime:
    range_list = list()
    currentDate = args.datetime.split("{")

    for element in currentDate:
        if "}" in element:
            range_list.append(re.findall(r"[0-9]+", element))

    ## YYYY-MM-{DD..DD}-H
    if re.search(r"{.*}$", str(args.datetime)) == None:
        if int(range_list[0][0]) > 0 and int(range_list[0][1]) < 32:
            for i in range(int(range_list[0][0]), int(range_list[0][1]) + 1):
                if i < 10:
                    url = "https://data.gharchive.org/%s0%s-%s.json.gz" % (currentDate[0], i, range_list[0][2])
                else:
                    url = "https://data.gharchive.org/%s%s-%s.json.gz" % (currentDate[0], i, range_list[0][2])

                if not check_archive_folder(pathArchive, url.split("/")[-1]):
                    request = "wget %s -P %s" % (url, pathArchive)
                    subprocessCall(request)
        else:
            print("[-] Date Value Error for Days")
            exit(-1)
    
    ## YYYY-MM-DD-{HH..HH}
    if len(range_list) == 1:
        if int(range_list[0][0]) >= 0 and int(range_list[0][1]) < 24:
            for i in range(int(range_list[0][0]), int(range_list[0][1]) + 1):
                url = "https://data.gharchive.org/%s%s.json.gz" % (currentDate[0], i)

                if not check_archive_folder(pathArchive, url.split("/")[-1]):
                    request = "wget %s -P %s" % (url, pathArchive)
                    subprocessCall(request)
        else:
            print("[-] Date Value Error for Hours")
            exit(-1)

    ## YYYY-MM-{DD..DD}-{H..H}
    elif len(range_list) == 2:
        if ( int(range_list[0][0]) > 0 and int(range_list[0][1]) < 32 ) and int(range_list[0][0]) >= 0 and int(range_list[0][1]) < 24:
            for i in range(int(range_list[0][0]), int(range_list[0][1]) + 1):
                for j in range(int(range_list[0][0]), int(range_list[0][1]) + 1):
                    if i < 10:
                        url = "https://data.gharchive.org/%s0%s-" % (currentDate[0], i)
                    else:
                        url = "https://data.gharchive.org/%s%s-" % (currentDate[0], i)
                    url += "%s.json.gz" % (j)

                    if not check_archive_folder(pathArchive, url.split("/")[-1]):
                        request = "wget %s -P %s" % (url, pathArchive)
                        subprocessCall(request)
        else:
            print("[-] Date Value Error for Days or Hours")
            exit(-1)
else:
    loc = args.datetime.split("-")
    if (int(loc[1]) > 0 and int(loc[1]) < 13) and (int(loc[2]) > 0 and int(loc[2]) < 32) and (int(loc[3]) >= 0 and int(loc[3]) < 24):
        url = "https://data.gharchive.org/%s.json.gz" % (args.datetime)

        if not check_archive_folder(pathArchive, url.split("/")[-1]):
            request = "wget -nv %s -P %s" % (url, pathArchive)
            subprocessCall(request)


for archive in os.listdir(pathArchive):
    currentArchive = os.path.join(pathArchive, archive)

    ## Open json file
    print("[+] Unizp...")
    data = [json.loads(line) for line in gzip.open(currentArchive, 'r')]

    print("[+] Traitment...")
    ele_list = list()

    for element in data:
        if element["type"] == "PushEvent":
            flag = False
            if args.org:
                if "org" in element:
                    for orgs in list_org:
                        if orgs.rstrip("\n") == element["org"]["login"]:
                            flag = True
                            break
            if args.users:
                for i in range(0, len(element["payload"]["commits"])):
                    for users in list_users:
                        if users.rstrip("\n") == element["payload"]["commits"][i]["author"]["name"]:
                            flag = True
                            break
                    if flag:
                        break

            ## org or user match with entry
            if flag or (not args.org and not args.users):
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
        time_element = datetime.datetime.strptime(element["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%H:%M:%S")

        uuid_parent = str(uuid4())

        for i in range(0,len(element["payload"]["commits"])):
            if args.list:
                for lines in list_leak:
                    if lines.rstrip("\n") in element["payload"]["commits"][i]["message"]:
                        cpPatch, cpCommit = traitement_json(element, i, cpPatch, cpCommit)
            else:
                cpPatch, cpCommit = traitement_json(element, i, cpPatch, cpCommit)
               
        print("\r[+] Commit JSON files: %s, Patch JSON files: %s" % (cpCommit, cpPatch), end="")
        