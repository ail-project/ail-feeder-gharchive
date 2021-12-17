import re
import sys
import pattern
from langdetect import detect as langdetect

def find_vuln(commit_msg, pattern, verbose=False):
    """Find a potential vulnerability from a commit message thanks to a regex
    pattern.
    """
    m = pattern.search(commit_msg)
    if m:
        if verbose:
            print("Match found: {}".format(m.group(0)), file=sys.stderr)
            print(commit_msg, file=sys.stderr)
            print("---", file=sys.stderr)
        ret = {}
        ret["commit"] = commit_msg
        ret["match"] = m.groups()
        return ret
    else:
        return None


def summary(
    commit,
    pattern,
    element,
    vuln_match=None,
    commit_state="under-review"
):
    potential_vulnerabilities = {}
    
    cve, cve_found = extract_cve(commit["message"])

    potential_vulnerabilities[commit["sha"]] = {}
    potential_vulnerabilities[commit["sha"]]["repo_name"] = element["repo"]["name"]
    potential_vulnerabilities[commit["sha"]]["message"] = commit["message"]
    potential_vulnerabilities[commit["sha"]]["language"] = langdetect(commit["message"])
    potential_vulnerabilities[commit["sha"]]["commit-id"] = commit["sha"]
    potential_vulnerabilities[commit["sha"]]["author"] = commit["author"]["name"]
    potential_vulnerabilities[commit["sha"]]["author-email"] = commit["author"]["email"]
    potential_vulnerabilities[commit["sha"]]["authored_date"] = element["created_at"]
    potential_vulnerabilities[commit["sha"]]["branches"] = element["payload"]["ref"]
    potential_vulnerabilities[commit["sha"]]["pattern-selected"] = pattern.pattern
    potential_vulnerabilities[commit["sha"]]["pattern-matches"] = vuln_match
    potential_vulnerabilities[commit["sha"]]["origin-github-api"] = commit["url"]
    if cve:
        potential_vulnerabilities[commit["sha"]]["cve"] = cve
        potential_vulnerabilities[commit["sha"]]["state"] = "cve-assigned"
    else:
        potential_vulnerabilities[commit["sha"]]["state"] = commit_state

    return potential_vulnerabilities, cve_found


def extract_cve(commit):
    cve_found = set()
    cve_find = re.compile(r"CVE-[1-2]\d{1,4}-\d{1,7}", re.IGNORECASE)
    m = cve_find.findall(commit)
    if m:
        for v in m:
            cve_found.add(v)
        return m, cve_found
    else:
        return None, set()




def find(commit, element):
    # Initialization of the variables for the results
    found = 0
    all_potential_vulnerabilities = {}
    all_cve_found = set()

    # Initialization of the patterns
    patterns = pattern.get_patterns()
    vulnpatterns = patterns["en"]["medium"]["vuln"]
    cryptopatterns = patterns["en"]["medium"]["crypto"]
    cpatterns = patterns["en"]["medium"]["c"]

    defaultpattern = [vulnpatterns, cryptopatterns, cpatterns]
    

    for p in defaultpattern:
        ret = find_vuln(commit["message"], pattern=p)
        if ret:
            potential_vulnerabilities, cve_found = summary(
                commit,
                p,
                element,
                vuln_match=ret["match"]
            )
            all_potential_vulnerabilities.update(potential_vulnerabilities)
            all_cve_found.update(cve_found)
            found += 1

    return all_potential_vulnerabilities, all_cve_found, found