# Issue-opener

A small CLI tool that bulk opens GitHub issues from a structured `.txt` file using the GitHub REST API.

## Requirements

- Python 3.10+
- `pip install requests`
- a git repo with a GitHub remote (used to find the repo slug)
- auth: `gh auth login` or set the `GITHUB_TOKEN` environment variable

## Usage

```
python3 main.py [path] [file_path] [--allow-duplicates]
```

| Argument | Description |
| --- | --- |
| `path` | project root, defaults to the current directory |
| `file_path` | name of the file to read (`.txt` is appended), defaults to `todo` |
| `--allow-duplicates` | don't skip issues whose title already exists in the repo |

Example:

```
python3 main.py . todo
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