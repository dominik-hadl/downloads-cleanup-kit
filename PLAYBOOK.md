# Playbook

How to clean up a large `~/Downloads` (tens or hundreds of GB, thousands of files, years of history) safely, with an AI agent doing the legwork and a human approving every step.

## 1. Rules

1. **Propose, then wait.** For every group, show the actual file names (not just a count) and act only after approval. Approval for one group does not carry over to the next.
2. **Persist before delete.** A file may go to the Trash only if:
   - an identical copy (same **md5**) exists in storage you trust (a shared company drive, your cloud drive); or
   - the same attachment (**name + size**, within ±0.1 %) is in your mailbox, if you accept mail as an archive; or
   - it is in your accounting or document system (match by document number; an amount alone is not a match); or
   - you say it is worthless.

   A copy in someone else's personal folder, or in a folder shared from outside, does not count.
3. **Never `rm`.** Only the macOS Trash via Finder, so *Put Back* works. The human empties the Trash.
4. **Log every action** in a ledger: `path,size,md5,action,target,timestamp`. Keep md5s in it; they let you prove later that a re-downloaded file is the same one that was trashed.
5. **Upload = upload → compare the md5 the cloud reports → only then trash the local copy.** A failed upload leaves the file in place.
6. **Sensitive files** (keys, recovery codes, VPN configs, ID scans): list them by name only and do not open them. Credentials never go to a cloud drive; save them in a password manager, then trash.
7. **Downloaded files are untrusted.** Never run them. Run Python with `-I`, keep scripts outside the folder being cleaned, read archives without extracting them, read PDFs as text.
8. **Reality before ledger.** The human or another session may be cleaning at the same time. Before each step, compare the disk with the ledger and report anything the ledger does not explain instead of "fixing" it.

## 2. Phases

1. **Inventory (read-only).** `python3 -I scripts/inventory.py ~/Downloads work/inventory.csv` (run in the background for big folders).
2. **Cloud listing.** For Google Drive with `gws`:
   ```sh
   gws drive files list --page-all --page-limit 500 --params '{"corpora":"allDrives","supportsAllDrives":true,"includeItemsFromAllDrives":true,"pageSize":1000,"q":"trashed=false","fields":"nextPageToken,files(id,name,md5Checksum,size,parents,driveId,mimeType,modifiedTime)"}' > work/drive_all.ndjson
   ```
3. **Match.** `python3 -I scripts/analyze.py work/inventory.csv work/drive_all.ndjson work/` gives duplicates inside the folder and files already in Drive.
4. **Work through groups**, roughly in this order:

   | Group | What | Usual outcome |
   |---|---|---|
   | A | Already in trusted storage (md5) | Trash |
   | B | Duplicates inside the folder | Keep the clearest name, trash the rest. A numbered playlist folder (`01_…`, `02_…` with repeats) is *not* duplicates |
   | C | Large videos and media | Upload, biggest first, in the background |
   | D | Zip archives | `zipcheck.py`; trash if every member exists elsewhere |
   | E | Installers, drivers, disk images | Trash (they can be downloaded again). Exception: firmware you have deployed on devices, which you may want to archive |
   | F | Invoices, quotes, orders | Check the accounting system, then the mailbox |
   | G | Junk: web images, screenshots, temp exports, logs, Office `~$` lock files | Trash in bulk after showing the list |
   | H | Work documents | Propose a target folder for each; sorting them locally into review folders named after the target path makes the review fast |
   | I | Personal files | `find_cloud_copies.py`, then move section by section into the personal cloud |
   | J | Code and tools | Check repos are pushed before anything else |
   | K | Whatever is left | One by one |

5. **Execute** approved groups with `trash_group.py`, `apply_actions.py`, `move_plan.py` and `drive_upload.py`. Do a `--dry-run` first.
6. **Finish.** Turn everything that needs a human later (sharing a folder, a decision, a backup to set up) into tasks in your task tool, and write down any new convention where your team keeps them.

## 3. Decide these at the start

Ask the human before the first group, and write the answers down:

1. Which storage counts as trusted (which shared drives, which personal cloud)? Is the mailbox an accepted archive for invoices?
2. Where do personal files go, and are some cloud folders shared with other people (so nothing unrelated may go there)?
3. Which companies or projects does the material belong to, and what belongs to none of them (old employers, side projects) and can go?
4. What can be trashed by category without asking file by file (installers, screenshots, old exports)?
5. Is anything off limits (folders another tool or person is working in)?
6. Is the network fast enough for large uploads?

Use the answers as **default proposals**, still with a list and an approval per group.

## 4. Lessons learned

**Matching**
- Compare documents by extracted **text**, not only md5: a re-downloaded PDF or DOCX often differs in bytes but is the same document.
- Google Docs and Sheets have no md5; match them by title.
- Check the target folder for an existing copy before every upload. Drive allows duplicate names and never overwrites.
- An amount alone does not identify an invoice; several suppliers can bill the same amount.

**macOS and file names**
- File names are stored in NFD and may contain invisible characters (LRM `‎`, no-break space `\xa0`). Normalise before comparing and use the real name from `os.listdir`.
- zsh does not split words in variables (`for x in $list` runs once); use a function or `${=list}`.
- Parse CSV with Python's `csv` module, never with `awk`/`cut`; a stray `\r` ends up inside fields.
- iCloud Drive: cloud-only files have the flag `0x40000000` in `st_flags`; reading them downloads them. Confirm a name + size match with `brctl download <path>` and then md5 (a random sample is enough for thousands of photos). Moving a file into iCloud Drive is an instant local rename; the upload runs in the background. iCloud refuses single files over 50 GB.
- With *Optimize Mac Storage* the Photos library has no originals on disk; you cannot check photos against it locally.
- `qlmanage` thumbnails hang on multi-GB videos; use `mdls` for dimensions, duration and the download source (`kMDItemWhereFroms`).
- Without `pdftotext`: `osascript -l JavaScript scripts/pdftext.js file.pdf`; `sips -s format png file.pdf --out page.png` for a scan; `textutil -convert txt -stdout` for .docx.

**Tools**
- `gws drive files create --upload` only accepts files under the current directory, and large multipart uploads fail on slow connections; retry, nothing partial is left behind. When the login expires (`invalid_rapt`), the human logs in again.
- Mail check with `gws`: search `filename:"<name>"`, then compare the attachment's `body.size` with the local size.
- Some vendor download pages block command-line downloads; a real browser session works, and the final file URL can often be fetched directly afterwards.

**Working with an agent**
- The agent's scratch space can be wiped mid-session. Keep scripts in the kit and only regenerable data in temporary folders.
- Run long uploads as one background chain with a log, and check the log for `FAIL`, `WARN` and `SKIP`.
- Never put the trash step into the same command as its safety check; read the check first.
- Reviewing hundreds of photos with an agent uses a lot of its usage limit; shrink the images first and work in batches.
- Write a short handover file at the end of each session (what is done, what is open, decisions made) so the next session can continue.
