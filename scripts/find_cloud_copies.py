"""Read-only: for files in some folders of <root>, find identical copies in iCloud Drive and the Photos library.

usage: python3 -I find_cloud_copies.py <root> <out.csv> <folder> [<folder> ...]
  folders are relative to <root> (e.g. Personal)
Matching: size first, then md5. Cloud-only (not downloaded) iCloud files are never read, so nothing gets
downloaded; for those a name + size match is reported instead, to be confirmed with `brctl download` + md5.
"""
import collections, csv, glob, hashlib, os, stat, sys, unicodedata

HOME = os.path.expanduser("~")
root, out_csv = os.path.expanduser(sys.argv[1]), sys.argv[2]
ROOTS = [os.path.join(root, r) for r in sys.argv[3:]]
ICLOUD = os.path.join(HOME, "Library/Mobile Documents/com~apple~CloudDocs")
PHOTOS = glob.glob(os.path.join(HOME, "Pictures/*.photoslibrary/originals"))
SF_DATALESS = 0x40000000
N = lambda x: unicodedata.normalize("NFC", x)


def walk(top):
    for d, _, fs in os.walk(top):
        for f in fs:
            if f == ".DS_Store":
                continue
            p = os.path.join(d, f)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if stat.S_ISREG(st.st_mode):
                yield p, st


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(8 << 20), b""):
            h.update(c)
    return h.hexdigest()


mine = [(p, st.st_size) for r in ROOTS for p, st in walk(r)]
sizes = {s for _, s in mine}
cand = collections.defaultdict(list)
dataless = collections.Counter()
by_name_size = {}
for top, label in [(ICLOUD, "iCloud Drive")] + [(r, "Photos library") for r in PHOTOS]:
    for p, st in walk(top):
        if getattr(st, "st_flags", 0) & SF_DATALESS:
            dataless[label] += 1
            by_name_size.setdefault((N(os.path.basename(p)), st.st_size), p)
        elif st.st_size in sizes:
            cand[st.st_size].append((p, label))

my_md5, by_md5, cache = {}, collections.defaultdict(list), {}
for p, s in mine:
    my_md5[p] = md5(p)
    by_md5[my_md5[p]].append(p)

with open(out_csv, "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["path", "size", "md5", "copy_in", "copy_path", "internal_dupes"])
    for p, s in mine:
        hit_lab = hit_p = ""
        for cp, lab in cand.get(s, []):
            if cp not in cache:
                cache[cp] = md5(cp)
            if cache[cp] == my_md5[p]:
                hit_lab, hit_p = lab, cp
                break
        if not hit_lab and (N(os.path.basename(p)), s) in by_name_size:
            hit_lab, hit_p = "iCloud, not downloaded (name + size only)", by_name_size[(N(os.path.basename(p)), s)]
        w.writerow([os.path.relpath(p, root), s, my_md5[p], hit_lab, hit_p, len(by_md5[my_md5[p]]) - 1])
print("Photos libraries:", PHOTOS or "none found")
print("cloud-only files skipped:", dict(dataless))
print("size candidates hashed:", len(cache))
