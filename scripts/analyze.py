"""Find duplicates inside the inventory, and files that already exist in Google Drive (same md5).

usage: python3 -I analyze.py <inventory.csv> <drive_all.ndjson> <out_dir>
  drive_all.ndjson: one JSON page per line from `gws drive files list --page-all` (see PLAYBOOK.md)
Writes <out_dir>/dupes.csv and <out_dir>/in_drive.csv. The drive_path column shows where the copy is;
"My Drive" or "?" means it is not in a shared drive and may not count as safely stored.
"""
import collections, csv, json, sys

inv_path, drive_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]

files, more = [], False
with open(drive_path) as f:
    for line in f:
        if line.strip():
            page = json.loads(line)
            more = bool(page.get("nextPageToken"))
            files.extend(page.get("files", []))
byid = {x["id"]: x for x in files}


def path_of(fid):
    parts, cur, seen = [], byid.get(fid), set()
    while cur and cur["id"] not in seen:
        seen.add(cur["id"])
        parts.append(cur["name"])
        ps = cur.get("parents") or []
        nxt = ps[0] if ps else None
        if nxt and nxt == cur.get("driveId"):
            parts.append(f"[shared drive {nxt}]"); break
        cur = byid.get(nxt)
        if cur is None and nxt:
            parts.append("My Drive" if not byid[fid].get("driveId") else "?")
    return " › ".join(reversed(parts))


drive_md5 = collections.defaultdict(list)
for x in files:
    if x.get("md5Checksum"):
        drive_md5[x["md5Checksum"]].append(x)

inv = list(csv.DictReader(open(inv_path)))
by_md5 = collections.defaultdict(list)
for r in inv:
    by_md5[r["md5"]].append(r)

n_groups = n_extra = extra_bytes = 0
with open(f"{out_dir}/dupes.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["md5", "size", "count", "relpath"])
    for m, rs in sorted(by_md5.items(), key=lambda kv: -int(kv[1][0]["size"]) * (len(kv[1]) - 1)):
        if len(rs) < 2 or int(rs[0]["size"]) == 0:
            continue
        n_groups += 1; n_extra += len(rs) - 1; extra_bytes += int(rs[0]["size"]) * (len(rs) - 1)
        for r in rs:
            w.writerow([m, r["size"], len(rs), r["relpath"]])

n_in = in_bytes = 0
with open(f"{out_dir}/in_drive.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["relpath", "size", "md5", "drive_id", "drive_path"])
    for r in inv:
        hits = drive_md5.get(r["md5"])
        if hits and int(r["size"]) > 0:
            n_in += 1; in_bytes += int(r["size"])
            w.writerow([r["relpath"], r["size"], r["md5"], hits[0]["id"], path_of(hits[0]["id"])])

total = sum(int(r["size"]) for r in inv)
print(f"Drive items: {len(files)} (listing incomplete: {more})")
print(f"Local files: {len(inv)}, {total/1e9:.2f} GB")
print(f"Duplicate groups: {n_groups}, redundant copies: {n_extra}, {extra_bytes/1e9:.2f} GB")
print(f"Already in Drive (md5): {n_in}, {in_bytes/1e9:.2f} GB")
