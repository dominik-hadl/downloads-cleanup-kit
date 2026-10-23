"""For each top-level zip in <root>: md5 every member (streamed, nothing extracted) and check whether an
identical copy exists in Drive, among uploaded files in the ledger, or as a live local file outside the zip.

usage: python3 -I zipcheck.py <root> <workdir>
  workdir must contain drive_all.ndjson, inventory.csv and (optionally) ledger.csv; writes zipcheck.csv
A zip whose members are all covered can be trashed; the rest needs a look.
"""
import csv, glob, hashlib, json, os, sys, zipfile

root, wd = os.path.expanduser(sys.argv[1]), sys.argv[2]


def md5_stream(fh):
    h = hashlib.md5()
    for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
        h.update(chunk)
    return h.hexdigest()


known = {}
for line in open(f"{wd}/drive_all.ndjson"):
    if line.strip():
        for f in json.loads(line).get("files", []):
            if f.get("md5Checksum"):
                known.setdefault(f["md5Checksum"], "Drive: " + f["name"])
if os.path.exists(f"{wd}/ledger.csv"):
    for r in csv.DictReader(open(f"{wd}/ledger.csv")):
        if r["action"] == "upload" and r["md5"]:
            known.setdefault(r["md5"], "uploaded: " + os.path.basename(r["path"]))
local = {}
for r in csv.DictReader(open(f"{wd}/inventory.csv")):
    if os.path.exists(os.path.join(root, r["relpath"])):
        local.setdefault(r["md5"], []).append(r["relpath"])

with open(f"{wd}/zipcheck.csv", "w", newline="") as f:
    out = csv.writer(f, lineterminator="\n")
    out.writerow(["zip", "zip_size", "zip_md5", "members", "covered", "missing_examples"])
    for z in sorted(glob.glob(os.path.join(root, "*.zip"))):
        zname = os.path.basename(z)
        try:
            zf = zipfile.ZipFile(z)
        except Exception as e:
            out.writerow([zname, os.path.getsize(z), "", 0, 0, f"unreadable: {e}"]); continue
        members = covered = 0
        missing = []
        for info in zf.infolist():
            n = info.filename
            if info.is_dir() or "__MACOSX" in n or n.endswith(".DS_Store") or info.file_size == 0:
                continue
            members += 1
            with zf.open(info) as fh:
                m = md5_stream(fh)
            if m in known or any(p != zname for p in local.get(m, [])):
                covered += 1
            else:
                missing.append(n)
        with open(z, "rb") as fh:
            zmd5 = md5_stream(fh)
        out.writerow([zname, os.path.getsize(z), zmd5, members, covered, " | ".join(missing[:4])])
        print(f"{covered:4d}/{members:<4d} {os.path.getsize(z)/1e6:8.1f}MB {zname}"
              f"  {'MISSING: ' + ' | '.join(missing[:3]) if missing else ''}", flush=True)
