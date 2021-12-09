import os
import re
import sys
import json
import gzip
import time
import redis
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
config.read('../etc/ail-feeder-gharchive.cfg')

if 'general' in config:
    uuid = config['general']['uuid']

if 'github' in config:
    api_token = config['github']['api_token']
else:
    api_token = ""

if 'cache' in config:
    cache_expire = config['cache']['expire']
else:
    cache_expire = 86400

if 'ail' in config:
    ail_url = config['ail']['url']
    ail_key = config['ail']['apikey']

if 'redis' in config:
    r = redis.Redis(host=config['redis']['host'], port=config['redis']['port'], db=config['redis']['db'])
else:
    r = redis.Redis(host='localhost', port=6379, db=0)


## Function
def json_patch(element, i, j, cpPatch, json_api_repo, json_api, date, time_element):

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

    source = "gharchive:patch"
    source_uuid = uuid

    cpPatch += 1
    
    if not debug:
        pyail.feed_json_item(data, meta_dict, source, source_uuid, default_encoding)
    else:
        json_patch = {}
        json_patch["data"] = data
        json_patch["default-encoding"] = default_encoding
        json_patch["meta"] = meta_dict
        json_patch["source"] = source
        json_patch["source_uuid"] = source_uuid

        with open(os.path.join(pathProg, "debug.json"), "a") as write_debug:
            json.dump(json_patch, write_debug, indent=4)
    
    return cpPatch
    

def json_commit(element, i, cpCommit, flagCommitDelete, flagRepoDelete, json_api_repo, json_api, date, time_element):

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
    
    source = "gharchive:commit"
    source_uuid = uuid

    cpCommit += 1


    if not debug:
        pyail.feed_json_item(data, meta_commit, source, source_uuid, default_encoding)
    else:
        json_commit = {}
        json_commit["data"] = data
        json_commit["default-encoding"] = default_encoding
        json_commit["meta"] = meta_commit
        json_commit["source"] = source
        json_commit["source_uuid"] = source_uuid

        with open(os.path.join(pathProg, "debug.json"), "a") as write_debug:
            json.dump(json_commit, write_debug, indent=4)
    
    return cpCommit


def subprocessCall(request):
    p = subprocess.Popen(request, stdout=subprocess.PIPE)
    (output, err) = p.communicate()
    p_status = p.wait()

    return output


def api_process(json_api, time_to_wait):
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


def json_process(element, i, date, time_element, cpPatch, cpCommit):
    flagRepoDelete = flagCommitDelete = flagRecur = flagCommit = False
    locRepoDelete = locCommitDelete = locRecur = False

    header = {'Authorization': f'token {api_token}'}

    try:
        if api_token:
            response = requests.get(element["payload"]["commits"][i]["url"], headers=header)
        else:
            response = requests.get(element["payload"]["commits"][i]["url"])
    except requests.exceptions.ConnectionError:
        print("[-] Connection Error to GHArchive")
        exit(-1)
    json_api = json.loads(response.content)

    flagRepoDelete, flagCommitDelete, flagRecur = api_process(json_api, int(response.headers['X-RateLimit-Reset']))

    while flagRecur:
        flagCommit = True
        
        try:
            if api_token:
                response = requests.get(element["payload"]["commits"][i]["url"], headers=header)
            else:
                response = requests.get(element["payload"]["commits"][i]["url"])
        except requests.exceptions.ConnectionError:
            print("[-] Connection Error to GHArchive")
            exit(-1)
        json_api = json.loads(response.content)

        flagRepoDelete, flagCommitDelete, flagRecur = api_process(json_api, int(response.headers['X-RateLimit-Reset']))

    ## Get repo owner
    json_api_repo = None
    if not flagRepoDelete:
        header = {'Authorization': f'token {api_token}'}
        
        try:
            if api_token:
                response = requests.get(element["repo"]["url"], headers=header)
            else:
                response = requests.get(element["repo"]["url"])
        except requests.exceptions.ConnectionError:
            print("[-] Connection Error to GHArchive")
            exit(-1)
        json_api_repo = json.loads(response.content)

        locRepoDelete, locCommitDelete, locRecur = api_process(json_api_repo, int(response.headers['X-RateLimit-Reset']))
        while locRecur:
            try:
                if api_token:
                    response = requests.get(element["repo"]["url"], headers=header)
                else:
                    response = requests.get(element["repo"]["url"])
            except requests.exceptions.ConnectionError:
                print("[-] Connection Error to GHArchive")
                exit(-1)
            json_api = json.loads(response.content)

            locRepoDelete, locCommitDelete, locRecur = api_process(json_api_repo, int(response.headers['X-RateLimit-Reset']))

    ## Create Json file
    if not flagCommitDelete and not flagRepoDelete:
        for j in json_api["files"]:
            if "patch" in j:
                cpPatch = json_patch(element, i, j, cpPatch, json_api_repo, json_api, date, time_element)
    if not flagCommit:
        cpCommit = json_commit(element, i, cpCommit, flagCommitDelete, flagRepoDelete, json_api_repo, json_api, date, time_element)

    return cpPatch, cpCommit, response.headers['X-RateLimit-Remaining']


## Check if archive already exist
def check_archive_folder(pathArchive, pathCurrentArchive, archive):
    for file in os.listdir(pathCurrentArchive):
        if file == archive:
            return True
    for file in os.listdir(pathArchive):
        if file == archive:
            pathSrc = os.path.join(pathArchive, file)
            pathDst = os.path.join(pathCurrentArchive, file)
            os.rename(pathSrc, pathDst)
            return True
    return False




## Arguments parsing
parser = argparse.ArgumentParser()
parser.add_argument("-d", help="debug", action="store_true")
parser.add_argument("-v", help="verbose, more display", action="store_true")

parser.add_argument("-a", "--archiveName", help="date of the GHArchive to Download, YYYY-MM-DD-H, YYYY-MM-DD-{H..H}, YYYY-MM-{DD..DD}-{H..H}, YYYY-MM-{DD..DD}-H", required=True)
parser.add_argument("--nocache", help="disable store of archive", action="store_true")

parser.add_argument("-u", "--users", nargs="+", help="search username")
parser.add_argument("-fu", "--fileusers", help="file containing list of username")

parser.add_argument("-o", "--org", nargs="+", help="search organisation")
parser.add_argument("-fo", "--fileorg", help="file containing list of organisations")

parser.add_argument("-l", "--list", nargs="+", help="list of word to search. If no list is give, all commit message will be add")
parser.add_argument("-fl", "--filelist", help="file containing list of word for commit message")
args = parser.parse_args()

debug = args.d
verbose = args.v

## Check for archiveName parameter
x = re.match(r"[0-9]{4}\-[0-9]{2}\-\{?[0-9]{1,2}\.{0,2}[0-9]{0,2}\}?\-\{?[0-9]{1,2}\.{0,2}[0-9]{0,2}\}?", args.archiveName)
if x == None:
    print("[-] Date Format Error, expected format: YYYY-MM-DD-H, YYYY-MM-DD-{H..H}, YYYY-MM-{DD..DD}-{H..H}, YYYY-MM-{DD..DD}-H")
    exit(-1)

head, tail = os.path.split(pathProg)
pathArchive = os.path.join(head, "archive")

if 'archive' in config:
    if config['archive']['pathArchive']:
        pathArchive = config['archive']['pathArchive']

pathCurrentArchive = os.path.join(pathArchive, "current")

## Ail
if not debug:
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
else:
    # move last archive in case of precedente error
    for archive in os.listdir(pathCurrentArchive):
        fileSrc = os.path.join(pathCurrentArchive, archive)
        fileDst = os.path.join(pathArchive, archive)

        os.rename(fileSrc, fileDst)


## claim entry parameters
if args.users:
    list_users = args.users
if args.org:
    list_org = args.org
if args.list:
    list_leak = args.list

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
if "{" in args.archiveName:
    range_list = list()
    currentDate = args.archiveName.split("{")

    for element in currentDate:
        if "}" in element:
            range_list.append(re.findall(r"[0-9]+", element))

    ## YYYY-MM-{DD..DD}-H
    if re.search(r"{.*}$", str(args.archiveName)) == None:
        if int(range_list[0][0]) > 0 and int(range_list[0][1]) < 32:
            for i in range(int(range_list[0][0]), int(range_list[0][1]) + 1):
                if i < 10:
                    url = f"https://data.gharchive.org/{currentDate[0]}0{i}-{range_list[0][2]}.json.gz"
                else:
                    url = f"https://data.gharchive.org/{currentDate[0]}{i}-{range_list[0][2]}.json.gz"

                if not check_archive_folder(pathArchive, pathCurrentArchive, url.split("/")[-1]):
                    print("[+] Downloading...")
                    if verbose:
                        request = ["wget", url, "-P", pathCurrentArchive]
                    else:
                        request = ["wget", "-q", url, "-P", pathCurrentArchive]
                    subprocessCall(request)
                else:
                    print("[+] Archive already Download")
        else:
            print("[-] Date Value Error for Days")
            exit(-1)
    
    ## YYYY-MM-DD-{HH..HH}
    if len(range_list) == 1:
        if int(range_list[0][0]) >= 0 and int(range_list[0][1]) < 24:
            for i in range(int(range_list[0][0]), int(range_list[0][1]) + 1):
                url = f"https://data.gharchive.org/{currentDate[0]}{i}.json.gz"

                if not check_archive_folder(pathArchive, pathCurrentArchive, url.split("/")[-1]):
                    print("[+] Downloading...")
                    if verbose:
                        request = ["wget", url, "-P", pathCurrentArchive]
                    else:
                        request = ["wget", "-q", url, "-P", pathCurrentArchive]
                    subprocessCall(request)
                else:
                    print("[+] Archive already Download")
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

                    if not check_archive_folder(pathArchive, pathCurrentArchive, url.split("/")[-1]):
                        print("[+] Downloading...")
                        if verbose:
                            request = ["wget", url, "-P", pathCurrentArchive]
                        else:
                            request = ["wget", "-q", url, "-P", pathCurrentArchive]
                        subprocessCall(request)
                    else:
                        print("[+] Archive already Download")
        else:
            print("[-] Date Value Error for Days or Hours")
            exit(-1)
else:
    loc = args.archiveName.split("-")
    if (int(loc[1]) > 0 and int(loc[1]) < 13) and (int(loc[2]) > 0 and int(loc[2]) < 32) and (int(loc[3]) >= 0 and int(loc[3]) < 24):
        url = f"https://data.gharchive.org/{args.archiveName}.json.gz"

        if not check_archive_folder(pathArchive, pathCurrentArchive, url.split("/")[-1]):
            print("[+] Downloading...")
            if verbose:
                request = ["wget", url, "-P", pathCurrentArchive]
            else:
                request = ["wget", "-q", url, "-P", pathCurrentArchive]
            subprocessCall(request)
        else:
            print("[+] Archive already Download")



for archive in os.listdir(pathCurrentArchive):
    currentArchive = os.path.join(pathCurrentArchive, archive)

    ## Open json file
    print("[+] Unzip...")
    data = [json.loads(line) for line in gzip.open(currentArchive, 'r')]

    print("[+] Process...")
    ele_list = list()
    for element in data:
        if element["type"] == "PushEvent":
            flag = False
            if args.org or args.fileorg:
                if "org" in element:
                    for orgs in list_org:
                        if orgs.rstrip("\n") == element["org"]["login"]:
                            flag = True
                            break
            if args.users or args.fileusers:
                for i in range(0, len(element["payload"]["commits"])):
                    for users in list_users:
                        if users.rstrip("\n") == element["payload"]["commits"][i]["author"]["name"]:
                            flag = True
                            break
                    if flag:
                        break

            ## org or user match with entry
            if flag or (not args.org and not args.users and not args.fileorg and not args.fileusers):
                ## If cache is active, check in redis db to see if this event have already process
                if not r.exists("event:{}".format(element["id"])) or args.nocache:
                    if not args.nocache:
                        r.set("event:{}".format(element["id"]), element["id"])
                        r.expire("event:{}".format(element["id"]), cache_expire)
                    ele_list.append(element)
                elif verbose:
                    print(f"Already done for PushEvent {element['id']}")

    print("[+] Rule Creation")
    ## Rule creation
    cpCommit = 0
    cpPatch = 0
    headerRemain = ""

    if verbose:
        print("\t[+] Check commit message if word or list are give in entry")

    for element in ele_list:
        date = datetime.datetime.strptime(element["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
        time_element = datetime.datetime.strptime(element["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%H:%M:%S")

        uuid_parent = str(uuid4())

        ## Check each commit message for remaining elements
        for i in range(0,len(element["payload"]["commits"])):
            if args.filelist:
                for lines in list_leak:
                    if lines.rstrip("\n") in element["payload"]["commits"][i]["message"]:
                        cpPatch, cpCommit, headerRemain = json_process(element, i, date, time_element, cpPatch, cpCommit)
            ## If all pass words are in the commit message then do the process
            ## and condition apply with all word give in entry
            elif args.list:
                flagListWord = True
                for lines in list_leak:
                    if not lines.rstrip("\n") in element["payload"]["commits"][i]["message"]:
                        flagListWord = False
                        break
                if flagListWord:
                    cpPatch, cpCommit, headerRemain = json_process(element, i, date, time_element, cpPatch, cpCommit)
            else:
                cpPatch, cpCommit, headerRemain = json_process(element, i, date, time_element, cpPatch, cpCommit)
               
        print(f"\r\t[+] Commit JSON files: {cpCommit}, Patch JSON files: {cpPatch}, API call remaining: {headerRemain}", end="")
print()

if args.nocache:
    shutil.rmtree(pathArchive)
else:
    for archive in os.listdir(pathCurrentArchive):
        fileSrc = os.path.join(pathCurrentArchive, archive)
        fileDst = os.path.join(pathArchive, archive)

        os.rename(fileSrc, fileDst)