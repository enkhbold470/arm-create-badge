"""
HeyPCB: AI-native PCB design. Scan the code to try it at heypcb.ai.

Controls:
* A, C, up or down = Switch between the pitch card and the big code
* B or HOME = Back to the launcher
"""

import math
import random

import qrcode

badge.mode(HIRES | VSYNC)
screen.antialias = image.X2

import branding as brand

WIDTH, HEIGHT = brand.WIDTH, brand.HEIGHT
MENU = "/system/apps/menu"
LEAVE = (BUTTON_B, BUTTON_HOME)
FLIP = (BUTTON_A, BUTTON_C, BUTTON_UP, BUTTON_DOWN)

URL = "https://heypcb.ai"
TITLE = "HeyPCB"
TAGLINE = "AI-native PCB design"
PITCH = "Describe a board. Get a layout."
CALL = "Scan to try it"

_, bold_font = brand.fonts()
regular_font, _ = brand.fonts()

# solder-mask green and copper, for the traces behind everything
mask = color.rgb(4, 40, 22)
copper = color.rgb(30, 120, 70)
copper_dim = color.rgb(16, 70, 40)
spark = color.rgb(190, 255, 120)
white = brand.white
muted = brand.muted

# --- the board: Manhattan traces with signals running along them ------------
GRID = 16
TRACE_W = 2
PAD_R = 3


def make_trace():
  """A random walk on the grid that only turns at right angles."""
  x = random.randint(0, WIDTH // GRID) * GRID
  y = random.randint(0, HEIGHT // GRID) * GRID
  points = [(x, y)]
  horizontal = random.getrandbits(1)
  for _ in range(random.randint(2, 4)):
    run = random.randint(2, 7) * GRID * random.choice((-1, 1))
    if horizontal:
      x = max(0, min(WIDTH, x + run))
    else:
      y = max(0, min(HEIGHT, y + run))
    points.append((x, y))
    horizontal = not horizontal
  return points


def length(points):
  return sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(points, points[1:]))


def point_along(points, d):
  for a, b in zip(points, points[1:]):
    seg = abs(b[0] - a[0]) + abs(b[1] - a[1])
    if d <= seg:
      t = d / seg if seg else 0
      return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
    d -= seg
  return points[-1]


random.seed(2350)
TRACES = []
for _ in range(14):
  pts = make_trace()
  total = length(pts)
  if total:
    TRACES.append((pts, total, random.randint(60, 140), random.randint(0, 4000)))

# the board is static, so it is drawn once into an image and blitted
board = image(WIDTH, HEIGHT)
board.pen = mask
board.clear()
for pts, _, _, _ in TRACES:
  board.pen = copper_dim
  for a, b in zip(pts, pts[1:]):
    x, y = min(a[0], b[0]), min(a[1], b[1])
    board.rectangle(x - 1, y - 1, abs(b[0] - a[0]) + TRACE_W, abs(b[1] - a[1]) + TRACE_W)
  board.pen = copper
  for px, py in (pts[0], pts[-1]):
    board.shape(shape.circle(px, py, PAD_R))


def draw_board():
  screen.blit(board, 0, 0)
  t = badge.ticks
  screen.pen = spark
  for pts, total, speed, phase in TRACES:
    d = ((t + phase) * speed / 1000) % (total + 60)
    if d <= total:
      x, y = point_along(pts, d)
      screen.shape(shape.circle(x, y, 2.5))


# --- the code ---------------------------------------------------------------
def build_code(block, plate_side):
  code = qrcode.QRCode(qrcode.ECC_MEDIUM)
  code.set_text(URL)
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


small_code = build_code(100, 116)
big_code = build_code(176, 196)


def glow_pen():
  # a slow breathe between the two ends of Arm's orange ramp
  k = 0.5 - 0.5 * math.cos(badge.ticks / 1600 * math.pi * 2)
  return color.rgb(242 + int(13 * k), 100 + int(74 * k), 25 + int(20 * k))


def panel(x, y, w, h):
  screen.pen = color.rgb(0, 0, 0, 170)
  screen.shape(shape.rounded_rectangle(x, y, w, h, 8))


def draw_pitch():
  panel(10, 50, 300, 160)

  screen.font = bold_font
  screen.pen = glow_pen()
  screen.text(TITLE, 22, 58, 40)

  screen.pen = white
  screen.text(TAGLINE, rect(22, 104, 160, 48), 18)

  screen.font = regular_font
  screen.pen = muted
  screen.text(PITCH, rect(22, 150, 160, 44), 15)

  screen.blit(small_code, 186, 62)
  screen.font = bold_font
  screen.pen = spark
  w = screen.measure_text(CALL, 13)[0]
  screen.text(CALL, int(186 + 58 - w / 2), 182, 13)


def draw_big():
  side = big_code.width
  x, y = (WIDTH - side) // 2, (HEIGHT - side) // 2 + 6
  screen.pen = glow_pen()
  screen.shape(shape.rounded_rectangle(x - 4, y - 4, side + 8, side + 8, 6))
  screen.blit(big_code, x, y)


CARDS = (draw_pitch, draw_big)
card = 0

on_exit = None

while on_exit is None:
  if any(badge.pressed(button) for button in FLIP):
    card = (card + 1) % len(CARDS)
  if any(badge.pressed(button) for button in LEAVE):
    on_exit = MENU
    break

  draw_board()
  CARDS[card]()
  brand.draw_header()
  badge.update()

badge.mode(LORES | VSYNC)
