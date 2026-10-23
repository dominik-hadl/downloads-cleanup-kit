"""Move approved files to the macOS Trash (via Finder, so Put Back works) after re-checking size and md5,
and append every action to the ledger.

usage: python3 -I trash_group.py <root> <group.csv> <ledger.csv> <label> [--dry-run]
  group.csv columns: relpath,size,md5[,drive_id,drive_path]  (relpath relative to <root>)
A file that changed since the inventory is skipped, never trashed.
"""
import argparse, csv, hashlib, os, subprocess, time

ap = argparse.ArgumentParser()
ap.add_argument("root"); ap.add_argument("group"); ap.add_argument("ledger"); ap.add_argument("label")
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
root = os.path.expanduser(a.root)

APPLESCRIPT = ["on run argv", "repeat with p in argv", "set f to POSIX file (p as text)",
               'tell application "Finder" to delete f', "end repeat", "end run"]


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


ok, skipped = [], []
for r in csv.DictReader(open(a.group)):
    p = os.path.join(root, r["relpath"])
    if not os.path.isfile(p):
        skipped.append((r, "missing")); continue
    if str(os.path.getsize(p)) != r["size"] or md5(p) != r["md5"]:
        skipped.append((r, "changed since inventory")); continue
    ok.append((r, p))

if a.dry_run:
    print(f"would trash: {len(ok)}, skip: {len(skipped)}")
    for r, why in skipped:
        print("  SKIP", r["relpath"], "-", why)
    raise SystemExit

new_ledger = not os.path.exists(a.ledger)
with open(a.ledger, "a", newline="") as lf:
    w = csv.writer(lf, lineterminator="\n")
    if new_ledger:
        w.writerow(["path", "size", "md5", "action", "target", "timestamp"])
    for i in range(0, len(ok), 40):
        batch = ok[i:i + 40]
        args = ["osascript"] + sum([["-e", l] for l in APPLESCRIPT], []) + [p for _, p in batch]
        res = subprocess.run(args, capture_output=True, text=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        for r, p in batch:
            if os.path.exists(p):
                skipped.append((r, "trash failed: " + res.stderr.strip()[:120])); continue
            target = f'{a.label}; {r.get("drive_id", "")} {r.get("drive_path", "")}'.strip()
            w.writerow([p, r["size"], r["md5"], "trash", target, ts])
        lf.flush()

failed = sum(1 for _, why in skipped if why.startswith("trash failed"))
print(f"trashed: {len(ok) - failed}, skipped: {len(skipped)}")
for r, why in skipped:
    print("  SKIP", r["relpath"], "-", why)
