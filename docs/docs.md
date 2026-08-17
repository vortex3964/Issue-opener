# ./main.py

## Description

cli tool that reads a structured .txt file and bulk opens  
github issues, it supports labels, assignees and duplicate  
detection through the github rest api  

## Issue

a single github issue to open, has a title, a description,  
a set of labels and an optional list of assignees, the labels  
are checked against githubs allowed labels  

```py
@dataclass
class Issue:
    title: str
    description: str
    labels: set[str] = field(default_factory=set)
    assign: list[str] = field(default_factory=list)
```

## githubs allowed labels

we have a set with githubs allowed labels that we init  
these labels include among others : bug , invalid ...etch  

## run

runs a shell command and returns its stripped stdout,  
raises a RuntimeError when the command exits non-zero  

```py
def run(cmd, cwd=None):
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=False)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed:{' '.join(cmd)}\n{res.stderr}")
    return res.stdout.strip()
```

## get_repo_slug

reads the origin remote url of the git repo and extracts  
the owner/repo slug from it, raises a ValueError when the  
url is not a github one  

```py
def get_repo_slug(path: str):
    url = run(["git", "remote", "get-url", "origin"], cwd=path)
    match = re.search(r"github\.com[:/](.+?)(\.git)?$", url)
    if not match:
        raise ValueError(f"couldnt parse github repo from remote url:{url}")
    return match.group(1)
```

## get_credentials

resolves the repo slug and the github token, the token comes  
from the gh cli when logged in or from the GITHUB_TOKEN  
environment variable, raises a RuntimeError when there is none  

```py
def get_credentials(path: str):
    slug = get_repo_slug(path)
    try:
        token = run(["gh", "auth", "token"])
    except (RuntimeError, FileNotFoundError):
        token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "no github token found run gh auth login or set GITHUB_TOKEN"
        )
    return slug, token
```

## parse_file

parses the todo txt file into a list of issues, a title: line  
starts a new issue and only the title is mandatory, optional  
description:, # and @ lines hold the description, the labels and  
the assignees, plain lines are appended to the description, lines  
before a title and unknown labels or headings are ignored, blank  
lines are skipped so the fields can be spread out freely  

## get_existing_issue_titles

fetches the titles of every open and closed issue so that  
duplicates can be skipped by title, paginates through the  
issues endpoint and filters pull requests out of the response  

## open_issues

creates every issue with the github rest api, skips duplicates  
by title by default, on a rate limit it sleeps until the reset  
time and retries the issue and it sleeps between requests to  
avoid secondary rate limits, it reports the result of every issue  

## update helpers

the update check compares the installed copy against the latest  
commit on github, it runs at the end of main so the issue opening  
is never slowed down by the network, it stays quiet when there  
is no connection or a rate limit and it skips dev checkouts  

## uninstall helper

removes the launcher, the install dir with its venv and the  
path lines the installer added to the shell configs, a dev  
checkout is left alone  

## main

parses the command line arguments to get the project path and  
the todo file name, reads and parses the todo file into issues,  
resolves the credentials and opens every issue in github, the  
update and uninstall flags only manage the tool itself and  
skip the issue run
