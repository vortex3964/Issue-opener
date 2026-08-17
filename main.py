# Doc : Description
# cli tool that reads a structured .txt file and bulk opens
# github issues, it supports labels, assignees and duplicate
# detection through the github rest api

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

import requests


# Doc code : Issue
# a single github issue to open, has a title, a description,
# a set of labels and an optional list of assignees, the labels
# are checked against githubs allowed labels


@dataclass
class Issue:
    title: str
    description: str
    labels: set[str] = field(default_factory=set)
    assign: list[str] = field(default_factory=list)


# Doc end

# Doc : githubs allowed labels
# we have a set with githubs allowed labels that we init
# these labels include among others : bug , invalid ...etch
ALLOWED_LABELS = {
    "accessibility",
    "bug",
    "documentation",
    "duplicate",
    "enhancement",
    "good first issue",
    "help wanted",
    "invalid",
    "question",
    "wontfix",
}


# Doc code : run
# runs a shell command and returns its stripped stdout,
# raises a RuntimeError when the command exits non-zero


def run(cmd, cwd=None):
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=False)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed:{' '.join(cmd)}\n{res.stderr}")
    return res.stdout.strip()


# Doc end

# Doc code : get_repo_slug
# reads the origin remote url of the git repo and extracts
# the owner/repo slug from it, raises a ValueError when the
# url is not a github one


def get_repo_slug(path: str):
    url = run(["git", "remote", "get-url", "origin"], cwd=path)
    match = re.search(r"github\.com[:/](.+?)(\.git)?$", url)
    if not match:
        raise ValueError(f"couldnt parse github repo from remote url:{url}")
    return match.group(1)


# Doc end

# Doc code : get_credentials
# resolves the repo slug and the github token, the token comes
# from the gh cli when logged in or from the GITHUB_TOKEN
# environment variable, raises a RuntimeError when there is none


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


# Doc end

# Doc: parse_file
# parses the todo txt file into a list of issues, a title: line
# starts a new issue and only the title is mandatory, optional
# description:, # and @ lines hold the description, the labels and
# the assignees, plain lines are appended to the description, lines
# before a title and unknown labels or headings are ignored, blank
# lines are skipped so the fields can be spread out freely


def parse_file(file_path: str) -> list[Issue] | None:
    if not os.path.isfile(file_path):
        return None
    with open(file_path, "r") as f:
        content = f.read()
    issues = []
    current = None
    for raw in content.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        low = stripped.lower()
        if low.startswith("title:"):
            # a new title line starts the next issue
            if current is not None:
                issues.append(current)
            current = Issue(title=stripped[len("title:") :].strip(), description="")
        elif current is None:
            # no title yet, stray lines are ignored
            continue
        elif low.startswith("description:"):
            text = stripped[len("description:") :].strip()
            current.description = (
                f"{current.description}\n{text}" if current.description else text
            )
        elif stripped.startswith("#"):
            # unknown labels and headings like ## TODO are dropped
            current.labels |= {
                l.strip()
                for l in stripped.lstrip("#").split(",")
                if l.strip() in ALLOWED_LABELS
            }
        elif stripped.startswith("@"):
            current.assign = [
                a.strip().lstrip("@")
                for a in stripped.lstrip("@").split(",")
                if a.strip()
            ]
        else:
            current.description = (
                f"{current.description}\n{stripped}" if current.description else stripped
            )
    if current is not None:
        issues.append(current)
    return issues if issues else None


# Doc: get_existing_issue_titles
# fetches the titles of every open and closed issue so that
# duplicates can be skipped by title, paginates through the
# issues endpoint and filters pull requests out of the response


def get_existing_issue_titles(slug: str, token: str) -> set[str]:
    titles = set()
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/repos/{slug}/issues",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            params={"state": "all", "per_page": 100, "page": page},
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch issues: {resp.status_code} {resp.text}"
            )
        data = resp.json()
        if not data:
            break
        for item in data:
            # the issues endpoint also returns pull requests, filter those out
            if "pull_request" not in item:
                titles.add(item["title"].strip())
        page += 1
    return titles


# Doc : open_issues
# creates every issue with the github rest api, skips duplicates
# by title by default, on a rate limit it sleeps until the reset
# time and retries the issue and it sleeps between requests to
# avoid secondary rate limits, it reports the result of every issue


def open_issues(
    issues: list[Issue], slug: str, token: str, skip_duplicates: bool = True
):
    existing_titles = (
        get_existing_issue_titles(slug, token) if skip_duplicates else set()
    )

    results = []
    for i, issue in enumerate(issues):
        if skip_duplicates and issue.title.strip() in existing_titles:
            print(f"[{i + 1}/{len(issues)}] SKIPPED (duplicate): {issue.title}")
            continue

        payload: dict[str, Any] = {"title": issue.title, "body": issue.description}
        if issue.labels:
            payload["labels"] = list(issue.labels)
        if issue.assign:
            payload["assignees"] = issue.assign

        resp = requests.post(
            f"https://api.github.com/repos/{slug}/issues",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json=payload,
        )

        if resp.status_code == 201:
            data = resp.json()
            print(f"[{i + 1}/{len(issues)}] Opened #{data['number']}: {issue.title}")
            existing_titles.add(issue.title.strip())
            results.append(data)
        elif resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - time.time(), 1)
            print(f"Rate limited, sleeping {wait:.0f}s...")
            time.sleep(wait)
            issues.insert(i + 1, issue)  # retry this one next
        elif resp.status_code == 422:
            print(
                f"[{i + 1}/{len(issues)}] FAILED (422 - check the labels exist and the assignees have access): {resp.text}"
            )
        else:
            print(f"[{i + 1}/{len(issues)}] FAILED: {resp.status_code} {resp.text}")

        time.sleep(1)  # pacing to avoid secondary rate limits

    return results


# Doc : update helpers
# the update check compares the installed copy against the latest
# commit on github, it runs at the end of main so the issue opening
# is never slowed down by the network, it stays quiet when there
# is no connection or a rate limit and it skips dev checkouts

REPO = "vortex3964/Issue-opener"
BRANCH = "main"
COMMITS_URL = f"https://api.github.com/repos/{REPO}/commits/{BRANCH}"
TARBALL_URL = f"https://github.com/{REPO}/archive/refs/heads/{BRANCH}.tar.gz"


def get_install_dir() -> str | None:
    # the launcher runs main.py from the install dir, so the script's
    # own location is the install, a dev checkout has a .git folder
    d = os.path.dirname(os.path.realpath(__file__))
    if os.path.isdir(os.path.join(d, ".git")):
        return None
    return d


def fetch_latest_commit() -> str | None:
    try:
        with urllib.request.urlopen(COMMITS_URL, timeout=5) as resp:
            data = json.load(resp)
        return data.get("sha")
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None


def apply_update(install_dir: str, latest: str) -> bool:
    tmp = tempfile.mkdtemp(prefix="issue-opener-")
    try:
        tarball = os.path.join(tmp, "issue-opener.tar.gz")
        urllib.request.urlretrieve(TARBALL_URL, tarball)
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(tmp)

        # find the extracted project folder, a broken tarball
        # simply has no main.py and the update is aborted, the
        # .venv of the install is never in the archive so it
        # survives the update untouched
        src = None
        for entry in os.listdir(tmp):
            if os.path.isfile(os.path.join(tmp, entry, "main.py")):
                src = os.path.join(tmp, entry)
                break
        if src is None:
            return False

        for entry in os.listdir(src):
            source = os.path.join(src, entry)
            target = os.path.join(install_dir, entry)
            if os.path.isdir(source):
                shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(source, target)
            else:
                try:
                    os.replace(source, target)
                except OSError:
                    shutil.copy2(source, target)

        with open(os.path.join(install_dir, ".commit"), "w") as f:
            f.write(latest)
        return True
    except (urllib.error.URLError, OSError, tarfile.ReadError, EOFError):
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def read_stamp(commit_file: str) -> str | None:
    try:
        if not os.path.isfile(commit_file):
            return None
        with open(commit_file) as f:
            return f.read().strip()
    except OSError:
        return None


def check_for_update(apply: bool):
    install_dir = get_install_dir()
    if install_dir is None:
        if apply:
            print(
                "issue-opener --update only works on an installed copy, use git pull in a dev checkout"
            )
        return

    latest = fetch_latest_commit()
    if latest is None:
        if apply:
            print("couldn't check for updates, check your network connection")
        return

    current = read_stamp(os.path.join(install_dir, ".commit"))

    if current is not None and current == latest:
        if apply:
            print(f"issue-opener is already up to date ({current[:7]})")
        return

    if not apply:
        print("a new version of issue-opener is available, run 'issue-opener --update' to update")
        return

    if apply_update(install_dir, latest):
        print(
            f"issue-opener updated: {current[:7] if current else 'unknown'} -> {latest[:7]}"
        )
    else:
        print("update failed, try again later")


# Doc  : main
# parses the command line arguments to get the project path and
# the todo file name, reads and parses the todo file into issues,
# resolves the credentials and opens every issue in github, the
# update flag only updates the tool itself and skips the issue run


def main():
    parser = argparse.ArgumentParser(description="cli tool to bulk open github issues")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="path to project root",
    )
    parser.add_argument(
        "file_path",
        nargs="?",
        default="todo",
        help="name of the file we will read from",
    )
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="don't skip issues whose title already exists in the repo",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="check for and apply the latest version, skips the issue run",
    )
    args = parser.parse_args()

    # the update flag only updates the tool, nothing else runs
    if args.update:
        check_for_update(apply=True)
        return

    full_file_path = os.path.join(args.path, f"{args.file_path}.txt")

    issues = parse_file(full_file_path)
    if issues is None:
        print("Malformed issues folder or empty")
        sys.exit(1)

    try:
        slug, token = get_credentials(args.path)
    except RuntimeError as e:
        print(str(e))
        sys.exit(1)

    print(f"Found {len(issues)} issue(s) to open in {slug}")
    open_issues(issues, slug, token, skip_duplicates=not args.allow_duplicates)

    # the update check runs at the end so the issue opening is
    # never slowed down by the network
    check_for_update(apply=False)


if __name__ == "__main__":
    main()
