"""
Write manifest.json: every app file the badge's updater may install, with its
sha256. The updater downloads only files whose hash differs from its copy.

  python3 tools/make_manifest.py

Run by the pre-commit hook in .githooks, so the manifest never lags the apps.
The meme photos are not listed: they are built locally and stay out of git.
"""

import hashlib
import json
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"img", "__pycache__"}


def files():
  apps = os.path.join(ROOT, "apps")
  for app in sorted(os.listdir(apps)):
    for folder, dirs, names in os.walk(os.path.join(apps, app)):
      dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
      for name in sorted(names):
        if name.startswith("."):
          continue
        path = os.path.join(folder, name)
        yield os.path.relpath(path, ROOT).replace(os.sep, "/"), path


def main():
  entries = []
  for rel, path in files():
    data = open(path, "rb").read()
    entries.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(),
                    "size": len(data)})
  manifest = {"version": time.strftime("%Y-%m-%d %H:%M", time.gmtime()) + " UTC",
              "files": entries}
  out = os.path.join(ROOT, "manifest.json")
  old = json.load(open(out)) if os.path.exists(out) else {}
  if old.get("files") == entries:
    return                      # nothing changed: keep the old version stamp
  with open(out, "w") as f:
    json.dump(manifest, f, indent=1)
    f.write("\n")
  print("manifest.json: %d files" % len(entries))


if __name__ == "__main__":
  main()
