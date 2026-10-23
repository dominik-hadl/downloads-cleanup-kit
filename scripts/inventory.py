"""Read-only inventory of a folder: relpath, size, mtime, ext, md5 for every file.

usage: python3 -I inventory.py <root> <out.csv> [--exclude NAME ...]
  --exclude  top-level folder names to skip (e.g. a folder another tool is working in)
Small files are hashed first, so partial output is already useful while it runs.
"""
import argparse, csv, hashlib, os, time

ap = argparse.ArgumentParser()
ap.add_argument("root")
ap.add_argument("out")
ap.add_argument("--exclude", nargs="*", default=[])
a = ap.parse_args()
root = os.path.abspath(os.path.expanduser(a.root))

rows = []
for dp, dns, fns in os.walk(root, followlinks=False):
    if dp == root:
        dns[:] = [d for d in dns if d not in a.exclude]
    for fn in fns:
        p = os.path.join(dp, fn)
        if os.path.islink(p) or fn == ".DS_Store":
            continue
        try:
            st = os.stat(p)
        except OSError:
            continue
        rows.append((p, st.st_size, st.st_mtime))

rows.sort(key=lambda r: r[1])
with open(a.out, "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["relpath", "size", "mtime", "ext", "md5"])
    for i, (p, size, mtime) in enumerate(rows):
        h = hashlib.md5()
        try:
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
                    h.update(chunk)
            digest = h.hexdigest()
        except OSError as e:
            digest = "ERR:" + e.__class__.__name__
        w.writerow([os.path.relpath(p, root), size, time.strftime("%Y-%m-%d", time.localtime(mtime)),
                    os.path.splitext(p)[1].lower(), digest])
        if i % 200 == 0:
            f.flush()
            print(f"{i}/{len(rows)}", flush=True)
print("DONE", len(rows), flush=True)
