"""Upload approved files to Google Drive with the `gws` CLI, verify the md5 Drive reports, and only then move
the local file to the macOS Trash. Every step goes to the ledger.

usage:
  python3 -I drive_upload.py mkdir <parent_id> <name>          prints the folder id (reuses an existing one)
  python3 -I drive_upload.py upload <root> <plan.csv> <ledger.csv> <label> [--keep-local]
      plan.csv columns: relpath (relative to <root>), parent_id
Before uploading, check the target folder for an existing copy: Drive allows duplicate names and never overwrites.
A failed upload leaves the local file untouched.
"""
import csv, hashlib, json, os, subprocess, sys, time, unicodedata

TRASH = ["osascript", "-e", "on run argv", "-e", "set f to POSIX file ((item 1 of argv) as text)",
         "-e", 'tell application "Finder" to delete f', "-e", "end run"]


def gws(args, cwd=None):
    r = subprocess.run(["gws", "drive", "files"] + args, capture_output=True, text=True, cwd=cwd)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"_error": (r.stderr or r.stdout).strip()[-400:]}


def q(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def mkdir(parent, name):
    name = unicodedata.normalize("NFC", name)
    found = gws(["list", "--params", json.dumps({
        "q": f"'{parent}' in parents and name = '{q(name)}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
        "supportsAllDrives": True, "includeItemsFromAllDrives": True, "corpora": "allDrives", "fields": "files(id,name)"})])
    if found.get("files"):
        return found["files"][0]["id"]
    made = gws(["create", "--params", json.dumps({"supportsAllDrives": True, "fields": "id"}),
                "--json", json.dumps({"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent]})])
    if "id" not in made:
        sys.exit(f"mkdir failed: {made}")
    return made["id"]


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def upload(root, plan_csv, ledger_csv, label, keep_local):
    root = os.path.expanduser(root)
    new_ledger = not os.path.exists(ledger_csv)
    done = failed = 0
    with open(ledger_csv, "a", newline="") as lf:
        w = csv.writer(lf, lineterminator="\n")
        if new_ledger:
            w.writerow(["path", "size", "md5", "action", "target", "timestamp"])
        for r in csv.DictReader(open(plan_csv)):
            p = os.path.join(root, r["relpath"])
            if not os.path.isfile(p):
                print("SKIP missing", r["relpath"], flush=True); failed += 1; continue
            local, size = md5(p), os.path.getsize(p)
            d, base = os.path.split(p)  # gws only uploads files under its cwd
            t0 = time.time()
            res = gws(["create", "--upload", base,
                       "--params", json.dumps({"supportsAllDrives": True, "fields": "id,md5Checksum,size"}),
                       "--json", json.dumps({"name": unicodedata.normalize("NFC", base), "parents": [r["parent_id"]]})], cwd=d)
            if res.get("md5Checksum") != local:
                print(f"FAIL upload {r['relpath']}: {res}", flush=True); failed += 1; continue
            ts = time.strftime("%Y-%m-%dT%H:%M:%S")
            w.writerow([p, size, local, "upload", f"{label}; drive {res['id']} parent {r['parent_id']}", ts])
            if not keep_local:
                subprocess.run(TRASH + [p], capture_output=True)
                if os.path.exists(p):
                    print("WARN uploaded but trash failed", r["relpath"], flush=True); failed += 1; lf.flush(); continue
                w.writerow([p, size, local, "trash", f"{label}; verified drive {res['id']}", ts])
            done += 1
            lf.flush()
            print(f"OK {size/1e6:8.1f}MB {time.time()-t0:6.1f}s {r['relpath']}", flush=True)
    print(f"DONE {done}, failed {failed}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "mkdir":
        print(mkdir(sys.argv[2], sys.argv[3]))
    elif sys.argv[1] == "upload":
        upload(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], "--keep-local" in sys.argv[6:])
    else:
        sys.exit(__doc__)
