"""
Message wall: people scan the code, send a message, and it lands here live.

Messages go through a small relay (server/ in the repo), which the badge
polls with the WALL_TOKEN from secrets.py.

Controls:
* A and C = Older and newer messages
* Up = Show the code full screen, for scanning from further away
* Down = Hide the message on screen, for good
* B or HOME = Back to the launcher
"""

import time

import qrcode
import requests

badge.mode(HIRES | VSYNC)
screen.antialias = image.X2

import branding as brand

WIDTH, HEIGHT = brand.WIDTH, brand.HEIGHT
MENU = "/system/apps/menu"
LEAVE = (BUTTON_B, BUTTON_HOME)

SERVER = "https://badge-wall.enkhbold470.workers.dev"
POLL_MS = 6000
KEEP = 30                   # messages held on the badge between visits
SPLASH_MS = 5000            # how long a new arrival takes the whole screen

regular_font, bold_font = brand.fonts()
white, muted, cyan = brand.white, brand.muted, brand.cyan
orange = brand.orange_accent
panel = color.rgb(0, 0, 0, 160)

try:
  import secrets
  TOKEN = getattr(secrets, "WALL_TOKEN", "")
  TIMEZONE = getattr(secrets, "TIMEZONE", 0)
  HAVE_WIFI = bool(getattr(secrets, "WIFI_SSID", ""))
except ImportError:
  TOKEN, TIMEZONE, HAVE_WIFI = "", 0, False

if HAVE_WIFI:
  import wifi
  wifi.connect(timeout=10, retries=100000)


# --- the code people scan ---------------------------------------------------------
def build_code(block, plate_side):
  code = qrcode.QRCode(qrcode.ECC_MEDIUM)
  code.set_text(SERVER)
  modules = code.get_size()[0]
  step = block / modules
  edge = (plate_side - block) // 2
  plate = image(plate_side, plate_side)
  plate.pen = white
  plate.clear()
  plate.pen = brand.black
  for y in range(modules):
    top = edge + int(round(y * step))
    depth = edge + int(round((y + 1) * step)) - top
    for x in range(modules):
      if code.get_module(x, y):
        left = edge + int(round(x * step))
        plate.rectangle(left, top, edge + int(round((x + 1) * step)) - left, depth)
  return plate


small_code = build_code(96, 108)
big_code = build_code(180, 196)


# --- messages, kept between visits ------------------------------------------------
state = {"after": 0, "messages": []}
State.load("wall", state)
messages = state["messages"]
index = len(messages) - 1       # the newest is shown first
splash_until = 0
last_poll = -POLL_MS
trouble = None if TOKEN else "Add WALL_TOKEN to secrets.py"


def poll():
  """Fetch anything newer than the last message seen. Blocks for a moment."""
  global index, splash_until, trouble
  try:
    reply = requests.get("%s/api/inbox?after=%d" % (SERVER, state["after"]),
                         headers={"authorization": "Bearer " + TOKEN})
    status = reply.status_code
    body = reply.json() if status == 200 else None
    reply.close()
  except Exception as reason:
    trouble = "Offline: %s" % reason
    return
  if body is None:
    trouble = "Relay said %d" % status
    return
  trouble = None
  fresh = body.get("messages", [])
  if not fresh:
    return
  for m in fresh:
    messages.append([m["id"], m["name"], m["text"], m["ts"]])
  del messages[:-KEEP]
  state["after"] = messages[-1][0]
  State.save("wall", state)
  index = len(messages) - 1
  splash_until = badge.ticks + SPLASH_MS


def hide(current):
  """Take a message off the badge, and off the relay so it never returns."""
  global index
  try:
    requests.post(SERVER + "/api/hide", json={"id": current[0]},
                  headers={"authorization": "Bearer " + TOKEN}).close()
  except Exception:
    pass                        # it is gone from this badge either way
  messages.remove(current)
  State.save("wall", state)
  index = min(index, len(messages) - 1)


# --- drawing -------------------------------------------------------------------------
def wrap(text, size, width):
  lines, line = [], ""
  for word in text.split():
    trial = word if not line else line + " " + word
    if not line or screen.measure_text(trial, size)[0] <= width:
      line = trial
    else:
      lines.append(line)
      line = word
  if line:
    lines.append(line)
  return lines


def fitted(text, size, smallest, width, height):
  while size > smallest:
    lines = wrap(text, size, width)
    if len(lines) * size * 1.15 <= height:
      return size, lines
    size -= 1
  return size, wrap(text, size, width)


def clock(ts):
  minutes = (ts // 60 + TIMEZONE * 60) % (24 * 60)
  return "%d:%02d" % (minutes // 60, minutes % 60)


def draw_message(m, x, y, w, h, biggest):
  _, name, text, ts = m
  screen.font = bold_font
  screen.pen = orange
  screen.text(name, x, y, 16)
  screen.font = regular_font
  screen.pen = muted
  stamp = clock(ts)
  sw = screen.measure_text(stamp, 13)[0]
  screen.text(stamp, int(x + w - sw), y + 2, 13)
  screen.font = bold_font
  size, lines = fitted(text, biggest, 13, w, h - 24)
  screen.pen = white
  top = y + 24
  for line in lines:
    screen.text(line, x, int(top), size)
    top += size * 1.15


def draw_lights():
  # a quick chase round the case while a new message is up
  left = splash_until - badge.ticks
  if left <= 0:
    badge.caselights(0)
    return
  step = (badge.ticks // 120) % 4
  badge.caselights(*[1.0 if n == step else 0.15 for n in range(4)])


def draw_wall():
  brand.draw_background()

  # the code and its invitation on the left
  screen.pen = panel
  screen.shape(shape.rounded_rectangle(8, 48, 120, 166, 8))
  screen.blit(small_code, 14, 54)
  screen.font = bold_font
  screen.pen = white
  for n, line in enumerate(("Scan to", "message me")):
    w = screen.measure_text(line, 15)[0]
    screen.text(line, int(68 - w / 2), 166 + n * 18, 15)

  # the message on the right
  screen.pen = panel
  screen.shape(shape.rounded_rectangle(136, 48, 176, 166, 8))
  if messages:
    draw_message(messages[index], 146, 56, 156, 150, 22)
    screen.font = regular_font
    screen.pen = muted
    screen.text("%d/%d" % (index + 1, len(messages)), 146, 196, 12)
  else:
    screen.font = bold_font
    screen.pen = muted
    screen.text("No messages yet. Be the first!", rect(146, 90, 156, 80), 18)

  # what the connection is doing, along the bottom
  screen.font = regular_font
  if trouble:
    screen.pen = orange
    note = trouble
  elif HAVE_WIFI and not wifi.is_connected():
    screen.pen = muted
    note = "Connecting to WiFi..."
  else:
    screen.pen = muted
    note = "Live: badge-wall.enkhbold470.workers.dev"
  screen.text(note[:52], 10, 222, 12)


def draw_splash(m):
  screen.pen = color.rgb(14, 10, 24)
  screen.clear()
  screen.font = bold_font
  screen.pen = brand.orange_gradient(0, WIDTH)
  screen.text("New message!", 14, 10, 24)
  draw_message(m, 14, 50, 292, 180, 34)


def draw_big_code():
  screen.pen = brand.black
  screen.clear()
  side = big_code.width
  screen.blit(big_code, (WIDTH - side) // 2, 4)
  screen.font = bold_font
  screen.pen = white
  line = "Scan to message me"
  w = screen.measure_text(line, 16)[0]
  screen.text(line, int((WIDTH - w) / 2), 216, 16)


big = False
on_exit = None

while on_exit is None:
  if badge.pressed(BUTTON_A) and messages:
    index = max(0, index - 1)
    splash_until = 0
  if badge.pressed(BUTTON_C) and messages:
    index = min(len(messages) - 1, index + 1)
    splash_until = 0
  if badge.pressed(BUTTON_UP):
    big = not big
  if badge.pressed(BUTTON_DOWN) and messages:
    hide(messages[index])
    splash_until = 0
  if any(badge.pressed(button) for button in LEAVE):
    on_exit = MENU
    break

  online = TOKEN and (not HAVE_WIFI or wifi.connect())
  if online and badge.ticks - last_poll >= POLL_MS:
    last_poll = badge.ticks
    poll()

  if big:
    draw_big_code()
  elif badge.ticks < splash_until and messages:
    draw_splash(messages[-1])
  else:
    draw_wall()
    brand.draw_header()
  draw_lights()
  badge.update()

badge.caselights(0)
badge.mode(LORES | VSYNC)
