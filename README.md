# AIL - feeder from GHArchive

This AIL feeder is a generic software to extract informations from [GHArchive](https://www.gharchive.org/), collect and feed AIL via AIL ReST API.



# Usage

~~~shell
dacru@dacru:~/git/ail-feeder-gharchive/bin$ python3 gharchive_feeder.py --help
usage: gharchive_feeder.py [-h] [--nocache] [-u USERS [USERS ...]]
                           [-fu FILEUSERS] [-o ORG [ORG ...]] [-fo FILEORG]
                           [-l LIST [LIST ...]] [-fl FILELIST]
                           datetime

positional arguments:
  datetime              date of the GHArchive, YYYY-MM-DD-H, YYYY-MM-
                        DD-{H..H}, YYYY-MM-{DD..DD}-{H..H}, YYYY-MM-{DD..DD}-H

optional arguments:
  -h, --help            show this help message and exit
  --nocache             disable store of archive
  -u USERS [USERS ...], --users USERS [USERS ...]
                        search username
  -fu FILEUSERS, --fileusers FILEUSERS
                        file containing list of username
  -o ORG [ORG ...], --org ORG [ORG ...]
                        search organisation
  -fo FILEORG, --fileorg FILEORG
                        file containing list of organisations
  -l LIST [LIST ...], --list LIST [LIST ...]
                        list of word to search. If no list is give, all commit
                        message will be add
  -fl FILELIST, --filelist FILELIST

~~~



# JSON output format to AIL

- `source` is the name of the AIL feeder module
- `source-uuid` is the UUID of the feeder (unique per feeder)
- `data` is commit message or path informations
- `meta` is the generic field where feeder can add the metadata collected



Using the AIL API, `data` will be compress in gzip format and encode with base64 procedure. Then a new field will created, `data-sha256` who will be the result of sha256 on data after treatment.





# (main) Requirements

- [PyAIL](https://github.com/ail-project/PyAIL)



## ail_feeder_gharchive

#### Commit part

`data` will contain commit message of a PushEvent

~~~json
{
    "data": "Bump to 0.0.4",
    "default-encoding": "UTF-8",
    "meta": {
        "id": "3304d136-ccef-4cee-9ec3-169022547eff",
        "github:id_event": "18249112571",
        "github:repo_id": "408646046",
        "github:repo_name": "edumoreira1506/cig-factories",
        "github:repo_node_id": "R_kgDOGFtxng",
        "github:repo_owner": "edumoreira1506",
        "github:repo_owner_id": "49662698",
        "github:repo_owner_node_id": "MDQ6VXNlcjQ5NjYyNjk4",
        "github:push_id": "8062525290",
        "github:commit_id": "bd6ea0f6acf85ce548d0e9a11629aa5d8a99de59",
        "github:commit_node_id": "C_kwDOGFtxntoAKGJkNmVhMGY2YWNmODVjZTU0OGQwZTlhMTE2MjlhYTVkOGE5OWRlNTk",
        "github:commit_url": "https://api.github.com/repos/edumoreira1506/cig-factories/commits/bd6ea0f6acf85ce548d0e9a11629aa5d8a99de59",
        "github:pusher_email": "00ceee5b1c012899ffa1231a9566ffe1440c25ee@eduardoem.com.br",
        "github:pusher": "Eduardo Moreira",
        "github:pusher_id": "49662698",
        "github:pusher_node_id": "MDQ6VXNlcjQ5NjYyNjk4",
        "github:datestamp": "2021-10-02",
        "github:timestamp": "00:00:01",
        "github:timezone": "UTC"
    },
    "source": "commit",
    "source-uuid": "80172ead-7023-496c-a4be-6ee280d8fbcf"
}
~~~



#### Patch part

`data` will contain patch informations of a commit

~~~json
{
    "data": "@@ -1,6 +1,6 @@\n {\n \t\"name\": \"@cig-platform/factories\",\n-\t\"version\": \"0.0.3\",\n+\t\"version\": \"0.0.4\",\n \t\"description\": \"\",\n \t\"main\": \"build/index.js\",\n \t\"types\": \"build/index.d.ts\",",
    "default-encoding": "UTF-8",
    "meta": {
        "github:id_event": "18249112571",
        "github:repo_id": "408646046",
        "github:repo_name": "edumoreira1506/cig-factories",
        "github:repo_node_id": "R_kgDOGFtxng",
        "github:repo_owner": "edumoreira1506",
        "github:repo_owner_id": "49662698",
        "github:repo_owner_node_id": "MDQ6VXNlcjQ5NjYyNjk4",
        "github:push_id": "8062525290",
        "github:commit_id": "bd6ea0f6acf85ce548d0e9a11629aa5d8a99de59",
        "github:commit_node_id": "C_kwDOGFtxntoAKGJkNmVhMGY2YWNmODVjZTU0OGQwZTlhMTE2MjlhYTVkOGE5OWRlNTk",
        "github:commit_url": "https://api.github.com/repos/edumoreira1506/cig-factories/commits/bd6ea0f6acf85ce548d0e9a11629aa5d8a99de59",
        "github:pusher_email": "00ceee5b1c012899ffa1231a9566ffe1440c25ee@eduardoem.com.br",
        "github:pusher": "Eduardo Moreira",
        "github:pusher_id": "49662698",
        "github:pusher_node_id": "MDQ6VXNlcjQ5NjYyNjk4",
        "github:datestamp": "2021-10-02",
        "github:timestamp": "00:00:01",
        "github:timezone": "UTC",
        "github:parent": "3304d136-ccef-4cee-9ec3-169022547eff"
    },
    "source": "patch",
    "source-uuid": "80172ead-7023-496c-a4be-6ee280d8fbcf"
}
~~~



















