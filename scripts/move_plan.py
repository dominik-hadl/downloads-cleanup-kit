"""Move files or folders from <root> to any destination folder (e.g. iCloud Drive), logging each move.

usage: python3 -I move_plan.py <root> <plan.csv> <ledger.csv> [--dry-run]
  plan.csv columns: src (path relative to <root>), dest_dir (absolute), label
Unicode-safe, never overwrites: a name that already exists in the destination is left in place and reported.
"""
import argparse, csv, os, shutil, time, unicodedata

ap = argparse.ArgumentParser()
ap.add_argument("root"); ap.add_argument("plan"); ap.add_argument("ledger")
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
R = os.path.expanduser(a.root)
N = lambda s: unicodedata.normalize("NFC", s)


def resolve(rel):
    cur = R
    for part in rel.split("/"):
        names = {N(n): n for n in os.listdir(cur)}
        if N(part) not in names:
            return None
        cur = os.path.join(cur, names[N(part)])
    return cur


def size(p):
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs) if os.path.isdir(p) else os.path.getsize(p)


ok = bad = 0
new_ledger = not os.path.exists(a.ledger)
with open(a.ledger, "a", newline="") as lf:
    w = csv.writer(lf, lineterminator="\n")
    if new_ledger:
        w.writerow(["path", "size", "md5", "action", "target", "timestamp"])
    for m in csv.DictReader(open(a.plan)):
        src = resolve(m["src"])
        dest_dir = os.path.expanduser(m["dest_dir"])
        if not src:
            print("MISSING", m["src"]); bad += 1; continue
        name = os.path.basename(src)
        if os.path.isdir(dest_dir) and N(name) in {N(n) for n in os.listdir(dest_dir)}:
            print("CONFLICT (left in place)", m["src"], "->", dest_dir); bad += 1; continue
        if a.dry_run:
            print("MOVE", m["src"], "->", dest_dir); ok += 1; continue
        os.makedirs(dest_dir, exist_ok=True)
        isdir, sz = os.path.isdir(src), size(src)
        shutil.move(src, os.path.join(dest_dir, name))
        w.writerow([src, sz, "", "move-folder" if isdir else "move", f"{m['label']} -> {os.path.join(dest_dir, name)}",
                    time.strftime("%Y-%m-%dT%H:%M:%S")])
        lf.flush(); ok += 1
print(f"{'checked' if a.dry_run else 'moved'} {ok}, problems {bad}")
