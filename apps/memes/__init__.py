"""
Tech memes: Arch btw, it's always DNS, rewrite it in Rust, trust me bro and more.

Controls:
* A and C = Previous and next meme (pauses the slideshow)
* Up = A random meme
* Down = Pause or resume the slideshow
* B or HOME = Back to the launcher
"""

import math
import random

badge.mode(HIRES | VSYNC)
screen.antialias = image.X2

import branding as brand

WIDTH, HEIGHT = brand.WIDTH, brand.HEIGHT
MENU = "/system/apps/menu"
LEAVE = (BUTTON_B, BUTTON_HOME)

regular_font, bold_font = brand.fonts()
term_font = font.memo

black = brand.black
white = brand.white
muted = brand.muted
orange = brand.orange_accent
cyan = brand.cyan
term_green = color.rgb(80, 250, 120)
term_red = color.rgb(255, 90, 90)
term_dim = color.rgb(140, 160, 150)
nope_red = color.rgb(230, 60, 50)
yes_green = color.rgb(90, 200, 60)
drake_top = color.rgb(255, 214, 120)
drake_bottom = color.rgb(255, 240, 200)

# --- the memes ----------------------------------------------------------------
# ("term", [(pen, line), ...])       a terminal session, typed out
# ("drake", nope, yes)               the two-panel no / yes
# ("big", top, bottom)               white type over a dark ground, top and bottom
# ("quote", text, source)            a citation, with its source
# ("count", label, number)           a safety board counter
P, O, E = "p", "o", "e"         # prompt, output, error lines

MEMES = [
    ("term", [(P, "neofetch"),
              (O, "OS:   Arch Linux ARM aarch64"),
              (O, "CPU:  2x Cortex-M33 @ 250MHz"),
              (O, "RAM:  8MB (plenty)"),
              (O, "WM:   none, real devs use tty"),
              (E, "btw, I use Arch on Arm")]),
    ("big", "It's not DNS.\nThere's no way it's DNS.", "It was DNS."),
    ("drake", "Writing it in C++", "Rewriting it in Rust\nblazingly fast"),
    ("quote", "This code is production ready.", "Source: trust me bro"),
    ("big", "It works on my machine", "Then we'll ship your machine.\nAnd that's how Docker was born."),
    ("term", [(P, "vim notes.txt"),
              (O, "~"), (O, "~"),
              (P, ":exit"), (E, "E492: Not an editor command"),
              (P, "^C ^C ^C ^Z"),
              (O, "year 3: still inside vim")]),
    ("drake", "Reading the docs", "Asking Claude"),
    ("count", "DAYS SINCE IT WAS DNS", "0"),
    ("big", "There are 2 hard problems in CS:", "cache invalidation, naming things,\nand off-by-one errors."),
    ("term", [(P, "git commit -m \"fix\""),
              (P, "git commit -m \"fix again\""),
              (P, "git commit -m \"pls work\""),
              (P, "git push --force"),
              (O, "Friday 4:59 PM"),
              (E, "on-call phone starts ringing")]),
    ("drake", "x86 in a laptop", "Arm everywhere,\neven on my lanyard"),
    ("big", "99 little bugs in the code.\nTake one down, patch it around:", "127 little bugs in the code."),
    ("quote", "Linux is only free if your time has no value.", "Jamie Zawinski"),
    ("term", [(P, "sudo rm -rf / --no-preserve-root"),
              (O, "[sudo] password for inky:"),
              (E, "inky is not in the sudoers file."),
              (E, "This incident will be reported.")]),
    ("count", "YEAR OF THE LINUX DESKTOP", "NEXT"),
    ("drake", "Using a debugger", "print(\"here\")\nprint(\"here 2\")"),
    ("big", "Have you tried turning it", "off and on again?"),
    ("term", [(P, "ping 127.0.0.1"),
              (O, "64 bytes from localhost"),
              (O, "There's no place like 127.0.0.1")]),
    ("drake", "Writing tests", "Testing in production"),
    ("big", "Me: it compiled first try", "Also me: that is deeply suspicious"),
    ("count", "DAYS WITHOUT A NEW JS FRAMEWORK", "0"),
    ("term", [(P, "./a.out"),
              (E, "Segmentation fault (core dumped)"),
              (P, "# it's fine, ship it")]),
    ("quote", "10 lines of diff: ten review comments.\n500 lines of diff:", "\"LGTM\""),
    ("drake", "Fixing the bug", "// TODO: fix later"),
    ("big", "Production is on fire", "This is fine."),
    ("quote", "Hardware is the part of the computer you can kick.", "Every PCB designer, at 2 AM"),
]


# --- layout helpers -----------------------------------------------------------
def wrap(text, size, width):
  lines = []
  for para in text.split("\n"):
    line = ""
    for word in para.split():
      candidate = word if not line else line + " " + word
      if not line or screen.measure_text(candidate, size)[0] <= width:
        line = candidate
      else:
        lines.append(line)
        line = word
    lines.append(line)
  return lines


def centred(text, cx, y, size, width, pen, pitch=1.15):
  """Wrap and centre a block on cx, starting at y. Returns where it ends."""
  screen.pen = pen
  for line in wrap(text, size, width):
    w = screen.measure_text(line, size)[0]
    screen.text(line, int(cx - w / 2), int(y), size)
    y += size * pitch
  return y


def block_height(text, size, width, pitch=1.15):
  return len(wrap(text, size, width)) * size * pitch


def fit(text, size, smallest, width, height):
  while size > smallest and block_height(text, size, width) > height:
    size -= 1
  return size


# --- the formats ----------------------------------------------------------------
TERM_X, TERM_TOP, TERM_PITCH = 12, 34, 22
CHAR_MS = 28                # typing speed


def draw_term(lines, age):
  screen.pen = color.rgb(8, 12, 10)
  screen.clear()
  # a title bar with the three lights
  screen.pen = color.rgb(40, 44, 48)
  screen.rectangle(0, 0, WIDTH, 22)
  for n, pen in enumerate((nope_red, drake_top, yes_green)):
    screen.pen = pen
    screen.shape(shape.circle(14 + n * 16, 11, 5))
  screen.font = regular_font
  screen.pen = muted
  screen.text("inky@tufty: ~", 120, 4, 13)

  screen.font = term_font
  budget = int(age / CHAR_MS)
  y = TERM_TOP
  for kind, text in lines:
    prefix = "$ " if kind == P else ""
    full = prefix + text
    shown = full[:budget]
    budget -= len(full)
    pen = term_green if kind == P else (term_red if kind == E else term_dim)
    screen.pen = pen
    screen.text(shown, TERM_X, y)
    if budget < 0:
      # the cursor sits where typing has reached
      cx = TERM_X + screen.measure_text(shown)[0] + 1
      screen.pen = term_green
      screen.rectangle(int(cx), y, 7, 14)
      break
    y += TERM_PITCH
  else:
    if (badge.ticks // 500) % 2:
      screen.pen = term_green
      screen.text("$ ", TERM_X, y)
      screen.rectangle(TERM_X + int(screen.measure_text("$ ")[0]) + 1, y, 7, 14)


def tick(cx, cy, r, pen):
  screen.pen = pen
  screen.shape(shape.circle(cx, cy, r))
  screen.pen = white
  screen.shape(shape.line(vec2(cx - r * 0.45, cy + r * 0.05),
                          vec2(cx - r * 0.1, cy + r * 0.4), 4))
  screen.shape(shape.line(vec2(cx - r * 0.1, cy + r * 0.4),
                          vec2(cx + r * 0.5, cy - r * 0.35), 4))


def cross(cx, cy, r, pen):
  screen.pen = pen
  screen.shape(shape.circle(cx, cy, r))
  screen.pen = white
  k = r * 0.4
  screen.shape(shape.line(vec2(cx - k, cy - k), vec2(cx + k, cy + k), 4))
  screen.shape(shape.line(vec2(cx - k, cy + k), vec2(cx + k, cy - k), 4))


def draw_drake(nope, yes, age):
  half = HEIGHT // 2
  screen.pen = drake_top
  screen.rectangle(0, 0, WIDTH, half)
  screen.pen = drake_bottom
  screen.rectangle(0, half, WIDTH, HEIGHT - half)
  screen.pen = black
  screen.rectangle(0, half - 1, WIDTH, 2)
  screen.rectangle(100, 0, 2, HEIGHT)

  # the gestures: a shaking no, a bobbing yes
  shake = math.sin(age / 60) * 4 if age < 900 else 0
  bob = math.sin(age / 300) * 3 if age > 900 else 0
  cross(50 + shake, half / 2, 30, nope_red)
  if age > 700:
    tick(50, half + half / 2 + bob, 30, yes_green)

  screen.font = bold_font
  for text, top, show in ((nope, 0, True), (yes, half, age > 700)):
    if not show:
      continue
    size = fit(text, 24, 14, 196, half - 16)
    h = block_height(text, size, 196)
    centred(text, 210, top + (half - h) / 2 + size * 0.05, size, 196, black)


def draw_big(top, bottom, age):
  screen.pen = color.rgb(14, 10, 24)
  screen.clear()
  screen.font = bold_font
  size = fit(top, 26, 16, 296, 90)
  centred(top, WIDTH / 2, 18, size, 296, white)
  if age > 1200:
    size = fit(bottom, 26, 16, 296, 90)
    h = block_height(bottom, size, 296)
    screen.pen = brand.orange_gradient(0, WIDTH)
    y = HEIGHT - 22 - h
    for line in wrap(bottom, size, 296):
      w = screen.measure_text(line, size)[0]
      screen.text(line, int(WIDTH / 2 - w / 2), int(y), size)
      y += size * 1.15


def draw_quote(text, source, age):
  screen.pen = color.rgb(245, 240, 228)
  screen.clear()
  screen.font = bold_font
  screen.pen = color.rgb(200, 190, 170)
  screen.text("\"", 14, -6, 90)
  size = fit(text, 24, 15, 270, 120)
  y = centred(text, WIDTH / 2, 50, size, 270, color.rgb(30, 30, 30))
  if age > 1000:
    screen.font = regular_font
    screen.pen = color.rgb(110, 100, 90)
    line = "- " + source
    w = screen.measure_text(line, 18)[0]
    screen.text(line, int(WIDTH - 20 - w), int(max(y + 14, 170)), 18)


def draw_count(label, number, age):
  screen.pen = color.rgb(20, 90, 40)
  screen.clear()
  screen.pen = white
  screen.shape(shape.rounded_rectangle(14, 14, WIDTH - 28, HEIGHT - 28, 10))
  screen.pen = color.rgb(20, 90, 40)
  screen.shape(shape.rounded_rectangle(20, 20, WIDTH - 40, HEIGHT - 40, 7))
  screen.font = bold_font
  size = fit(label, 22, 14, 260, 60)
  centred(label, WIDTH / 2, 34, size, 260, white)
  # the board flicks through numbers before it lands
  shown = number if age > 900 else str(random.randint(10, 999))
  screen.pen = color.rgb(0, 0, 0)
  screen.shape(shape.rounded_rectangle(90, 104, 140, 96, 8))
  big = 72 if len(shown) < 4 else 44
  w = screen.measure_text(shown, big)[0]
  screen.pen = drake_top
  screen.text(shown, int(WIDTH / 2 - w / 2), int(152 - big * 0.62), big)


DRAW = {"term": draw_term, "drake": draw_drake, "big": draw_big,
        "quote": draw_quote, "count": draw_count}

AUTO_MS = 9000
SLIDE_MS = 250

index = 0
shown_at = badge.ticks
auto = True

on_exit = None

while on_exit is None:
  step = 0
  if badge.pressed(BUTTON_A):
    step, auto = -1, False
  if badge.pressed(BUTTON_C):
    step, auto = 1, False
  if badge.pressed(BUTTON_UP):
    step = random.randint(1, len(MEMES) - 1)
  if badge.pressed(BUTTON_DOWN):
    auto = not auto
    shown_at = badge.ticks
  if not step and auto and badge.ticks - shown_at > AUTO_MS:
    step = 1
  if step:
    index = (index + step) % len(MEMES)
    shown_at = badge.ticks
  if any(badge.pressed(button) for button in LEAVE):
    on_exit = MENU
    break

  meme = MEMES[index]
  age = badge.ticks - shown_at
  DRAW[meme[0]](*meme[1:], age)

  # where we are, and whether it is rolling on
  screen.font = regular_font
  screen.pen = color.rgb(128, 128, 128, 160)
  screen.text("%d/%d%s" % (index + 1, len(MEMES), "" if auto else "  paused"),
              WIDTH - 78, HEIGHT - 16, 12)

  # a quick fade up from black as each meme lands
  if age < SLIDE_MS:
    screen.pen = color.rgb(0, 0, 0, int(255 * (1 - age / SLIDE_MS)))
    screen.rectangle(0, 0, WIDTH, HEIGHT)

  badge.update()

badge.mode(LORES | VSYNC)
