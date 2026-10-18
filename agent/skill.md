# Skill: convert a raw txt into the issue-opener format

Turn a raw txt with tasks or notes into the file format of the
issue-opener cli, so it can bulk open the tasks as GitHub issues.
Output the converted file in one code block, ready to save as todo.txt.

## Target format

Every issue is a block of lines, issues are separated by blank lines:

```text
title: Fix the login crash
description: The login page crashes when the form is submitted
# bug , needs triage
@ username1

title: Update the README
# documentation
```

- `title:` the issue title, mandatory, starts a new issue
- `description:` starts the body, further plain lines right after
  it are appended to the body as well
- `#` a label line with comma separated lowercase names, any
  custom label is accepted (lines starting with `##` are ignored
  as headings)
- `@` an assignee line with comma separated GitHub usernames
- only `title:` is mandatory so a title alone is a valid issue

## Conversion rules

- the first line of every issue is the title, what follows is the
  body, an issue without a body is just a title
- fix grammar, spelling and punctuation mistakes and reword lines
  that read awkwardly, so titles work as clear titles and bodies
  read as clean sentences
- keep titles short and specific, move extra details from a long
  first line into the body
- keep the meaning of the raw txt, never invent tasks or details
- never use em dashes, use commas or colons instead
- blank lines usually split issues but a wrapped paragraph that
  continues the previous line stays in that issue's body
- section headings like `milestone 2 : retrieval models` are not
  issues, they set the milestone of the issues below them
- every issue gets an `mx` label where x is the number of its
  milestone, e.g. `m2` for everything under `milestone 2`
- write all labels in lowercase, the opener lowercases them anyway
- if the user gives other labeling rules follow those instead

## Example

Raw txt:

```text
milestone 1 : indexing

Fix the retry logic it fails sometimes

Create the mapping
one field per token
```

Converted:

```text
title: Fix the retry logic that fails sometimes
# m1

title: Create the mapping
description: One field per token.
# m1
```

## Quality checks

- every issue starts with `title:` and has a body only if the raw
  txt had one
- grammar, spelling and punctuation are fixed and the titles make
  sense on their own
- no em dashes anywhere
- every issue has exactly its milestone label (`m0`, `m1`, ...)
  and all labels are lowercase
- no body line starts with `#`, `@`, `title:` or `description:`,
  the opener would parse those as labels, assignees or a new issue
- exactly one blank line between issues
- after the code block note any issues that share the same title,
  the opener skips duplicate titles unless run with
  `--allow-duplicates`
