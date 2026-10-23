# Downloads cleanup kit

A method and a few small scripts for cleaning up a large, years-old `~/Downloads` folder on macOS **without losing anything**, together with an AI coding agent such as [Claude Code](https://claude.com/claude-code).

The agent does the tedious part: inventory, hashing, matching files against your cloud storage and mailbox, sorting the rest into groups, proposing a target for each file. You approve every group before anything moves. Nothing is deleted outright: files go to the macOS Trash only once a verified copy exists elsewhere, and every action is written to a ledger.

Real results with this method: 54 GB → 2 MB in two days on one machine, and 209 GB → 0.3 GB over a week on another (about 6,500 logged actions, nothing lost).

## What is in here

| File | What it is |
|---|---|
| [`PLAYBOOK.md`](PLAYBOOK.md) | The method: rules, phases, decisions to make up front, and the lessons learned |
| [`CLAUDE.md`](CLAUDE.md) | Instructions Claude Code reads automatically when started in this folder |
| `scripts/inventory.py` | Read-only inventory: path, size, date, extension and md5 of every file |
| `scripts/analyze.py` | Duplicates inside the folder, and files that already exist in Google Drive |
| `scripts/zipcheck.py` | Checks whether every file inside each zip already exists somewhere else |
| `scripts/find_cloud_copies.py` | Finds identical copies in iCloud Drive and the Photos library, without downloading cloud-only files |
| `scripts/trash_group.py` | Moves an approved group to the Trash after re-checking each md5 |
| `scripts/apply_actions.py` | Trashes or moves approved top-level files and folders |
| `scripts/move_plan.py` | Moves files to any destination (for example iCloud Drive) without overwriting |
| `scripts/drive_upload.py` | Uploads to Google Drive, verifies the md5, then trashes the local copy |
| `scripts/pdftext.js` | Extracts PDF text with macOS PDFKit, no extra tools needed |

Every script that changes something writes to the ledger and has a `--dry-run` mode (`drive_upload.py` has `--keep-local` instead).

## Requirements

- macOS (the Trash, iCloud and PDF parts use Finder, file flags and PDFKit)
- Python 3, standard library only
- Optional: the [`gws`](https://github.com/googleworkspace/cli) CLI for Google Drive and Gmail checks
- Optional: an AI coding agent; the kit also works by hand

## Quick start with Claude Code

```sh
git clone <this repo> ~/downloads-cleanup-kit
cd ~/downloads-cleanup-kit
claude
```

Then say:

> Read PLAYBOOK.md and start the cleanup of ~/Downloads. Never act without my confirmation.

The agent will ask the questions in PLAYBOOK.md §3 first (where things should go, what counts as safely stored), take an inventory, and come back with the first group of files to approve. Working files and the ledger go into `work/`, which is git-ignored.

## Safety model

1. Nothing is ever deleted with `rm`. Files go to the macOS Trash, so *Put Back* works, and you empty the Trash yourself.
2. A file goes to the Trash only if an identical copy (same md5, or same name and size for mail attachments) is verified somewhere you trust, or you say it is worthless.
3. Every action is appended to `work/ledger.csv` (`path,size,md5,action,target,timestamp`).
4. Downloaded files are treated as untrusted data: never executed, Python always runs with `-I`, archives are only read.

## Licence

MIT, see [LICENSE](LICENSE).
