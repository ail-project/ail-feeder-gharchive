import os
import re
import sys
import json
import gzip
import time
import shutil
import pathlib
import argparse
import datetime
import requests
import subprocess
import configparser
from uuid import uuid4
from pyail import PyAIL

pathProg = pathlib.Path(__file__).parent.absolute()

## Config
config = configparser.ConfigParser()
config.read('../etc/config.cfg')

if 'general' in config:
    uuid = config['general']['uuid']

if 'github' in config:
    api_token = config['github']['api_token']

if 'ail' in config:
    ail_url = config['ail']['url']
    ail_key = config['ail']['apikey']



## Function
def json_patch(element, i, j, cpPatch, json_api_repo, json_api):

    data = j["patch"]

    default_encoding = "UTF-8"

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

    source = "patch"
    source_uuid = uuid

    cpPatch += 1
    
    pyail.feed_json_item(data, meta_dict, source, source_uuid, default_encoding)
    
    return cpPatch
    

def json_commit(element, i, cpCommit, flagCommitDelete, flagRepoDelete, json_api_repo, json_api):

    data = element["payload"]["commits"][i]["message"]
    default_encoding = "UTF-8"

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
    
    source = "commit"
    source_uuid = uuid

    cpCommit += 1

    pyail.feed_json_item(data, meta_commit, source, source_uuid, default_encoding)
    
    return cpCommit


def subprocessCall(request):
    p = subprocess.Popen(request, stdout=subprocess.PIPE)
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

            print(f"\n\n[-] API rate limit exceeded, sleep for {diff}")
            time.sleep(diff.total_seconds() + 10)

            flagRecur = True

    return flagRepoDelete, flagCommitDelete, flagRecur


def json_process(element, i, cpPatch, cpCommit):
    flagRepoDelete = flagCommitDelete = flagRecur = flagCommit = False
    locRepoDelete = locCommitDelete = locRecur = False

    header = {'Authorization': f'token {api_token}'}

    try:
        response = requests.get(element["payload"]["commits"][i]["url"], headers=header)
    except requests.exceptions.ConnectionError:
        print("[-] Connection Error to GHArchive")
        exit(-1)
    json_api = json.loads(response.content)

    flagRepoDelete, flagCommitDelete, flagRecur = api_traitment(json_api, int(response.headers['X-RateLimit-Reset']))

    while flagRecur:
        flagCommit = True
        
        try:
            response = requests.get(element["payload"]["commits"][i]["url"], headers=header)
        except requests.exceptions.ConnectionError:
            print("[-] Connection Error to GHArchive")
            exit(-1)
        json_api = json.loads(response.content)

        flagRepoDelete, flagCommitDelete, flagRecur = api_traitment(json_api, int(response.headers['X-RateLimit-Reset']))

    ## Get repo owner
    json_api_repo = None
    if not flagRepoDelete:
        header = {'Authorization': f'token api_token'}
        
        try:
            response = requests.get(element["repo"]["url"], headers=header)
        except requests.exceptions.ConnectionError:
            print("[-] Connection Error to GHArchive")
            exit(-1)
        json_api_repo = json.loads(response.content)

        locRepoDelete, locCommitDelete, locRecur = api_traitment(json_api_repo, int(response.headers['X-RateLimit-Reset']))
        while flagRecur:
            try:
                response = requests.get(element["payload"]["commits"][i]["url"], headers=header)
            except requests.exceptions.ConnectionError:
                print("[-] Connection Error to GHArchive")
                exit(-1)
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


## Check if archive already exist
def check_archive_folder(pathArchive, archive):
    for file in os.listdir(pathArchive):
        if file == archive:
            pathSrc = os.path.join(pathArchive, file)
            pathDst = os.path.join(pathCurrentArchive, file)
            os.rename(pathSrc, pathDst)
            return True
    return False




## Arguments parsing
parser = argparse.ArgumentParser()
parser.add_argument("datetime", help="date of the GHArchive, YYYY-MM-DD-H, YYYY-MM-DD-{H..H}, YYYY-MM-{DD..DD}-{H..H}, YYYY-MM-{DD..DD}-H")
parser.add_argument("--nocache", help="disable cache", action="store_true")

parser.add_argument("-u", "--users", nargs="+", help="search username")
parser.add_argument("-fu", "--fileusers", help="file containing list of username")

parser.add_argument("-o", "--org", nargs="+", help="search organisation")
parser.add_argument("-fo", "--fileorg", help="file containing list of organisations")

parser.add_argument("-l", "--list", nargs="+", help="list of word to search. If no list is give, all commit message will be add")
parser.add_argument("-fl", "--filelist", help="file containing list of word for commit message")
args = parser.parse_args()

## Check for datetime parameter
x = re.match(r"[0-9]{4}\-[0-9]{2}\-\{?[0-9]{1,2}\.{0,2}[0-9]{0,2}\}?\-\{?[0-9]{1,2}\.{0,2}[0-9]{0,2}\}?", args.datetime)
if x == None:
    print("[-] Date Format Error")
    exit(-1)

pathArchive = os.path.join(pathProg, "archive")
if 'archive' in config:
    if config['archive']['pathArchive']:
        pathArchive = config['archive']['pathArchive']

pathCurrentArchive = os.path.join(pathArchive, "current")

## Ail
try:
    pyail = PyAIL(ail_url, ail_key, ssl=False)
except Exception as e:
    # print(e)
    print("\n\n[-] Error during creation of AIL instance")
    sys.exit(0)


if not os.path.isdir(pathArchive):
    os.mkdir(pathArchive)
if not os.path.isdir(pathCurrentArchive):
    os.mkdir(pathCurrentArchive)

if args.filelist:
    with open(args.filelist, "r") as read_file:
        list_leak = read_file.readlines()
if args.fileorg:
    with open(args.fileorg, "r") as read_file:
        list_org = read_file.readlines()
if args.fileusers:
    with open(args.fileusers, "r") as read_file:
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
                    url = f"https://data.gharchive.org/{currentDate[0]}0{i}-{range_list[0][2]}.json.gz"
                else:
                    url = f"https://data.gharchive.org/{currentDate[0]}{i}-{range_list[0][2]}.json.gz"

                if not check_archive_folder(pathArchive, url.split("/")[-1]):
                    request = ["wget", url, "-P", pathCurrentArchive]
                    subprocessCall(request)
        else:
            print("[-] Date Value Error for Days")
            exit(-1)
    
    ## YYYY-MM-DD-{HH..HH}
    if len(range_list) == 1:
        if int(range_list[0][0]) >= 0 and int(range_list[0][1]) < 24:
            for i in range(int(range_list[0][0]), int(range_list[0][1]) + 1):
                url = f"https://data.gharchive.org/{currentDate[0]}{i}.json.gz"

                if not check_archive_folder(pathArchive, url.split("/")[-1]):
                    request = ["wget", url, "-P", pathCurrentArchive]
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
                        url = f"https://data.gharchive.org/{currentDate[0]}0{i}-"
                    else:
                        url = f"https://data.gharchive.org/{currentDate[0]}{i}-"
                    url += f"{j}.json.gz"

                    if not check_archive_folder(pathArchive, url.split("/")[-1]):
                        request = ["wget", url, "-P", pathCurrentArchive]
                        subprocessCall(request)
        else:
            print("[-] Date Value Error for Days or Hours")
            exit(-1)
else:
    loc = args.datetime.split("-")
    if (int(loc[1]) > 0 and int(loc[1]) < 13) and (int(loc[2]) > 0 and int(loc[2]) < 32) and (int(loc[3]) >= 0 and int(loc[3]) < 24):
        url = f"https://data.gharchive.org/{args.datetime}.json.gz"

        if not check_archive_folder(pathArchive, url.split("/")[-1]):
            request = ["wget", url, "-P", pathCurrentArchive]
            subprocessCall(request)


for archive in os.listdir(pathCurrentArchive):
    currentArchive = os.path.join(pathCurrentArchive, archive)

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
                        cpPatch, cpCommit = json_process(element, i, cpPatch, cpCommit)
            else:
                cpPatch, cpCommit = json_process(element, i, cpPatch, cpCommit)
               
        print(f"\r[+] Commit JSON files: {cpCommit}, Patch JSON files: {cpPatch}", end="")
        
if args.nocache:
    shutil.rmtree(pathArchive)
else:
    for archive in os.listdir(pathCurrentArchive):
        fileSrc = os.path.join(pathCurrentArchive, archive)
        fileDst = os.path.join(pathArchive, archive)

        os.rename(fileSrc, fileDst)