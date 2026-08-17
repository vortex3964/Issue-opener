# Issue-opener

A small CLI tool that bulk opens GitHub issues from a structured `.txt` file using the GitHub REST API.

## Requirements

- Python 3.10+ (checked by the installer)
- a git repo with a GitHub remote (used to find the repo slug)
- auth: `gh auth login` or set the `GITHUB_TOKEN` environment variable

## Install

```
curl -fsSL https://raw.githubusercontent.com/vortex3964/Issue-opener/main/install/install.sh | bash
```

Windows:

```
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/vortex3964/Issue-opener/main/install/install.ps1 | iex"
```

or from a local copy:

```
bash install/install.sh --local /path/to/Issue-opener
```

The installer creates a virtual environment with the dependencies and a `issue-opener` launcher, no manual `pip install` needed. It installs to `~/.local/share/issue-opener` with the launcher at `~/.local/bin/issue-opener` (Windows: `%LOCALAPPDATA%\issue-opener`, launcher `issue-opener.cmd` on the user PATH).

Uninstall:

```
bash install/uninstall.sh                    # Linux/macOS
powershell -File install/uninstall.ps1       # Windows
```

## Updating

`issue-opener --update` checks for and applies the latest version, it only updates and skips the issue run:

```
issue-opener --update
```

Every normal run also checks for updates at the end and prints a note when a newer version is available, the check runs after the issues are opened so it never slows the run down. The update replaces the code only, the virtual environment is left untouched. If a future version adds new dependencies, re-run the installer.

## Usage

```
issue-opener [path] [file_path] [--allow-duplicates]
```

| Argument | Description |
| --- | --- |
| `path` | project root, defaults to the current directory |
| `file_path` | name of the file to read (`.txt` is appended), defaults to `todo` |
| `--allow-duplicates` | don't skip issues whose title already exists in the repo |
| `--update` | update issue-opener to the latest version, skips the issue run |

Example:

```
issue-opener . todo
```

## Issue file format

Issues are blocks of lines separated by blank lines:

- first line: the issue title
- second line: `#` followed by comma-separated labels (must be valid GitHub labels)
- optional line starting with `@`: comma-separated assignees (must have access to the repo)
- the remaining lines: the issue description

Example `todo.txt`:

```
Add dark mode

# enhancement

Users should be able to switch to dark mode

@username1 , username2

Fix login crash

# bug , help wanted

The login page crashes when the form is submitted
```

## Notes

- issues whose title already exists in the repo are skipped by default
- sleeps between requests and backs off on rate limits to stay within GitHub's limits