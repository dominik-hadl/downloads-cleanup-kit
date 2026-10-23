"""Apply approved trash/move actions to top-level items (files or folders) of <root>, logging each one.

usage: python3 -I apply_actions.py <root> <actions.csv> <ledger.csv> [--dry-run]
  actions.csv columns: name, action (trash|move), target (folder relative to <root>, for move), label
Names are matched Unicode-normalised (macOS stores names in NFD). Never overwrites.
"""
import argparse, csv, hashlib, os, shutil, subprocess, time, unicodedata

ap = argparse.ArgumentParser()
ap.add_argument("root"); ap.add_argument("actions"); ap.add_argument("ledger")
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
root = os.path.expanduser(a.root)
N = lambda s: unicodedata.normalize("NFC", s)
on_disk = {N(n): n for n in os.listdir(root)}
TRASH = ["osascript", "-e", "on run argv", "-e", "set f to POSIX file ((item 1 of argv) as text)",
         "-e", 'tell application "Finder" to delete f', "-e", "end run"]


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


ok = bad = 0
new_ledger = not os.path.exists(a.ledger)
with open(a.ledger, "a", newline="") as lf:
    w = csv.writer(lf, lineterminator="\n")
    if new_ledger:
        w.writerow(["path", "size", "md5", "action", "target", "timestamp"])
    for act in csv.DictReader(open(a.actions)):
        real = on_disk.get(N(act["name"]))
        if real is None:
            print("MISSING", act["name"]); bad += 1; continue
        p = os.path.join(root, real)
        isdir = os.path.isdir(p)
        if a.dry_run:
            print(act["action"].upper(), real, "->", act.get("target", "")); ok += 1; continue
        size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs) if isdir else os.path.getsize(p)
        digest = "" if isdir else md5(p)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        if act["action"] == "trash":
            subprocess.run(TRASH + [p], capture_output=True)
            if os.path.exists(p):
                print("TRASH FAILED", real); bad += 1; continue
            w.writerow([p, size, digest, "trash-folder" if isdir else "trash", act["label"], ts])
        elif act["action"] == "move":
            dest_dir = os.path.join(root, act["target"])
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, real)
            if os.path.exists(dest):
                print("TARGET EXISTS", dest); bad += 1; continue
            shutil.move(p, dest)
            w.writerow([p, size, digest, "move-folder" if isdir else "move", f"{act['label']} -> {dest}", ts])
        else:
            print("UNKNOWN ACTION", act["action"]); bad += 1; continue
        ok += 1
        lf.flush()
print(f"{'checked' if a.dry_run else 'done'} {ok}, problems {bad}")
