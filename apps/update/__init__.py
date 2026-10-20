"""
Update over WiFi: pull the newest apps from github.com/enkhbold470/arm-create-badge.

Reads manifest.json at the newest commit, compares each file's hash with the
one on the badge, and downloads only what changed. Every file is checked
against its hash before it replaces the old one. Your profile, photo and
secrets are never in the manifest, so they are never touched.

Controls:
* B = Check, then install, then restart
* HOME = Back to the launcher
"""

import binascii
import hashlib
import json
import os

import machine
import requests
import rp2

badge.mode(HIRES | VSYNC)
screen.antialias = image.X2

import branding as brand

WIDTH, HEIGHT = brand.WIDTH, brand.HEIGHT
MENU = "/system/apps/menu"

REPO = "enkhbold470/arm-create-badge"
BRANCH = "main"
ROOT = "/system/"
# GitHub's API rejects requests without one
HEADERS = {"User-Agent": "tufty-badge-updater"}

regular_font, bold_font = brand.fonts()
white, muted, green = brand.white, brand.muted, brand.green
orange = brand.orange_accent

try:
  import secrets
  HAVE_WIFI = bool(getattr(secrets, "WIFI_SSID", ""))
except ImportError:
  HAVE_WIFI = False

if HAVE_WIFI:
  import wifi
  wifi.connect(timeout=10, retries=100000)

installed = {"version": "", "commit": ""}
State.load("update", installed)

# idle -> connecting -> ready (changes listed) -> done; or error, or current
phase = "idle"
title, detail = "Update over WiFi", "Press B to check GitHub for new apps."
changes = []
commit = ""
version = ""


def file_hash(path):
  digest = hashlib.sha256()
  try:
    with open(path, "rb") as f:
      while True:
        chunk = f.read(2048)
        if not chunk:
          break
        digest.update(chunk)
  except OSError:
    return None
  return binascii.hexlify(digest.digest()).decode()


def fetch(url, accept=None):
  headers = dict(HEADERS)
  if accept:
    headers["Accept"] = accept
  reply = requests.get(url, headers=headers)
  try:
    if reply.status_code != 200:
      raise OSError("HTTP %d from %s" % (reply.status_code, url.split("/")[2]))
    return reply.content
  finally:
    reply.close()


def raw(path):
  # addressed by commit, so GitHub's cache can never hand back an older copy
  return fetch("https://raw.githubusercontent.com/%s/%s/%s" % (REPO, commit, path))


def check():
  global commit, version, changes
  # asked for the sha media type, the API answers with the bare 40 characters
  commit = fetch("https://api.github.com/repos/%s/commits/%s" % (REPO, BRANCH),
                 "application/vnd.github.sha").decode().strip()
  manifest = json.loads(raw("manifest.json"))
  version = manifest.get("version", commit[:7])
  changes = [f for f in manifest["files"]
             if file_hash(ROOT + f["path"]) != f["sha256"]]


def make_dirs(path):
  parts = path.split("/")[:-1]
  for n in range(2, len(parts) + 1):
    folder = "/".join(parts[:n])
    try:
      os.mkdir(folder)
    except OSError:
      pass                      # already there


def install(entry):
  data = raw(entry["path"])
  if binascii.hexlify(hashlib.sha256(data).digest()).decode() != entry["sha256"]:
    raise OSError("%s arrived damaged" % entry["path"])
  path = ROOT + entry["path"]
  make_dirs(path)
  with open(path + ".new", "wb") as f:
    f.write(data)
  try:
    os.remove(path)
  except OSError:
    pass
  os.rename(path + ".new", path)


def card(heading, body, pen=white):
  brand.draw_background()
  screen.pen = color.rgb(0, 0, 0, 170)
  screen.shape(shape.rounded_rectangle(10, 48, 300, 166, 10))
  screen.font = bold_font
  screen.pen = pen
  screen.text(heading, 22, 56, 24)
  screen.font = regular_font
  screen.pen = white
  screen.text(body, rect(22, 92, 276, 116), 16)
  if installed["version"]:
    screen.pen = muted
    screen.text("On this badge: %s" % installed["version"], 22, 196, 12)
  brand.draw_header()


def show(heading, body, pen=white):
  card(heading, body, pen)
  badge.update()


def run_install():
  global phase, title, detail
  for n, entry in enumerate(changes):
    show("Installing %d/%d" % (n + 1, len(changes)), entry["path"], orange)
    install(entry)
  installed["version"], installed["commit"] = version, commit
  State.save("update", installed)
  phase = "done"
  title = "Updated to %s" % version
  detail = "%d files installed. Press B to restart into the new apps." % len(changes)


on_exit = None

while on_exit is None:
  if badge.pressed(BUTTON_HOME):
    on_exit = MENU
    break

  if badge.pressed(BUTTON_B):
    if phase in ("idle", "current", "error"):
      if not HAVE_WIFI:
        phase, title, detail = "error", "No WiFi details", "Add WIFI_SSID and WIFI_PASSWORD to secrets.py."
      elif rp2.is_msc_busy():
        # the computer and the badge writing at once can corrupt the disk
        phase, title, detail = "error", "Eject the badge first", "It is open as a drive on your computer. Eject TUFTY, then press B."
      else:
        phase, title, detail = "connecting", "Connecting...", "Joining WiFi."
    elif phase == "ready":
      try:
        run_install()
      except Exception as reason:
        phase, title, detail = "error", "Update stopped", "%s. Files already installed are complete; press B to try again." % reason
    elif phase == "done":
      show("Restarting...", "See you in a second.")
      machine.reset()

  if phase == "connecting" and wifi.connect():
    show("Checking GitHub...", "Comparing the files on this badge with %s." % REPO)
    try:
      check()
      if changes:
        names = sorted(set(f["path"].split("/")[1] for f in changes))
        phase, title = "ready", "%d files to update" % len(changes)
        detail = "New in %s: %s. Press B to install." % (version, ", ".join(names))
      else:
        phase, title, detail = "current", "Up to date", "Everything matches %s." % version
        installed["version"], installed["commit"] = version, commit
        State.save("update", installed)
    except Exception as reason:
      phase, title, detail = "error", "Couldn't check", "%s. Press B to try again." % reason

  pen = {"error": orange, "current": green, "done": green}.get(phase, white)
  card(title, detail, pen)
  badge.update()

badge.mode(LORES | VSYNC)
