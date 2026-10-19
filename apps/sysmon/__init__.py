"""
System monitor: live RP2350 stats from the dual Cortex-M33 inside your badge.

Controls:
* A = Case lights off, on, or pulsing with the core temperature
* C or down = Next graph: temperature, light, battery
* Up = Previous graph
* B or HOME = Back to the launcher
"""

import gc
import time

import machine

badge.mode(HIRES | VSYNC)
screen.antialias = image.X2

import branding as brand

WIDTH, HEIGHT = brand.WIDTH, brand.HEIGHT
MENU = "/system/apps/menu"
LEAVE = (BUTTON_B, BUTTON_HOME)

regular_font, bold_font = brand.fonts()
white = brand.white
muted = brand.muted
cyan = brand.cyan
green = brand.green
orange = brand.orange_accent
tile_bg = color.rgb(0, 0, 0, 150)
track = color.rgb(255, 255, 255, 40)

sensor = machine.ADC(machine.ADC.CORE_TEMP)


def core_temp():
  # RP2350 datasheet: 0.706V at 27C, falling 1.721mV per degree
  volts = sensor.read_u16() * 3.3 / 65535
  return 27 - (volts - 0.706) / 0.001721


# --- sampled history for the graph -------------------------------------------
SAMPLE_MS = 500
HISTORY = 120               # one minute of samples

GRAPHS = (
    # name, unit, how to read it, floor, ceiling, pen
    ("Core temp", "C", core_temp, 15, 60, orange),
    ("Light", "", lambda: badge.light_level(), 0, 4095, cyan),
    ("Battery", "V", lambda: badge.battery_voltage(), 3.0, 4.3, green),
)
history = [[] for _ in GRAPHS]
graph = 0
last_sample = -SAMPLE_MS


# the slow readings: walking the heap for mem_free() alone takes 44ms, so
# they are taken with the samples rather than every frame
stats = {}


def sample():
  stats["free"], stats["used"] = gc.mem_free(), gc.mem_alloc()
  stats["disk_total"], stats["disk_used"], _ = badge.disk_free()
  stats["level"] = badge.battery_level()
  stats["volts"] = badge.battery_voltage()
  stats["charging"] = badge.is_charging()
  for series, (_, _, read, _, _, _) in zip(history, GRAPHS):
    series.append(read())
    if len(series) > HISTORY:
      series.pop(0)


# --- case lights --------------------------------------------------------------
LIGHT_MODES = ("OFF", "ON", "TEMP")
light_mode = 0


def drive_lights(temp):
  if light_mode == 0:
    badge.caselights(0)
  elif light_mode == 1:
    badge.caselights(0.6)
  else:
    # warmer chip, faster and brighter pulse, chasing round the four lights
    heat = max(0.0, min(1.0, (temp - 20) / 25))
    period = 1400 - 1000 * heat
    phase = (badge.ticks % period) / period
    levels = []
    for n in range(4):
      p = (phase + n / 4) % 1.0
      levels.append((0.1 + 0.9 * heat) * (1 - abs(p * 2 - 1)))
    badge.caselights(*levels)


# --- drawing --------------------------------------------------------------------
def tile(x, y, w, h, label, value, pen=white):
  screen.pen = tile_bg
  screen.shape(shape.rounded_rectangle(x, y, w, h, 6))
  screen.font = regular_font
  screen.pen = muted
  screen.text(label, x + 7, y + 3, 12)
  screen.font = bold_font
  screen.pen = pen
  screen.text(value, x + 7, y + 16, 17)


def bar(x, y, w, fraction, pen):
  screen.pen = track
  screen.rectangle(x, y, w, 3)
  screen.pen = pen
  screen.rectangle(x, y, max(1, int(w * min(1.0, fraction))), 3)


def uptime(ms):
  s = ms // 1000
  return "%d:%02d:%02d" % (s // 3600, s // 60 % 60, s % 60)


GRAPH_X, GRAPH_Y, GRAPH_W, GRAPH_H = 8, 138, 304, 72


def draw_graph():
  name, unit, _, floor, ceiling, pen = GRAPHS[graph]
  series = history[graph]
  screen.pen = tile_bg
  screen.shape(shape.rounded_rectangle(GRAPH_X, GRAPH_Y, GRAPH_W, GRAPH_H, 6))

  screen.font = regular_font
  screen.pen = muted
  screen.text("%s, last minute" % name, GRAPH_X + 7, GRAPH_Y + 3, 12)
  if series:
    now = series[-1]
    text = ("%.0f" % now if not unit else "%.1f %s" % (now, unit))
    screen.font = bold_font
    screen.pen = pen
    w = screen.measure_text(text, 14)[0]
    screen.text(text, GRAPH_X + GRAPH_W - 8 - int(w), GRAPH_Y + 2, 14)

  # one bar per sample, newest on the right
  top, bottom = GRAPH_Y + 22, GRAPH_Y + GRAPH_H - 6
  span = bottom - top
  step = (GRAPH_W - 14) / HISTORY
  left = GRAPH_X + 7 + (HISTORY - len(series)) * step
  screen.pen = pen
  for i, v in enumerate(series):
    k = max(0.0, min(1.0, (v - floor) / (ceiling - floor)))
    h = max(1, int(span * k))
    screen.rectangle(int(left + i * step), bottom - h, max(1, int(step)), h)


frames = 0
fps = 0
fps_from = badge.ticks

on_exit = None

while on_exit is None:
  if badge.pressed(BUTTON_A):
    light_mode = (light_mode + 1) % len(LIGHT_MODES)
  if badge.pressed(BUTTON_C) or badge.pressed(BUTTON_DOWN):
    graph = (graph + 1) % len(GRAPHS)
  if badge.pressed(BUTTON_UP):
    graph = (graph - 1) % len(GRAPHS)
  if any(badge.pressed(button) for button in LEAVE):
    on_exit = MENU
    break

  now = badge.ticks
  if now - last_sample >= SAMPLE_MS:
    last_sample = now
    sample()

  frames += 1
  if now - fps_from >= 1000:
    fps = frames * 1000 // (now - fps_from)
    frames, fps_from = 0, now

  temp = history[0][-1] if history[0] else core_temp()
  drive_lights(temp)

  free, used = stats["free"], stats["used"]
  disk_total, disk_used = stats["disk_total"], stats["disk_used"]
  level = stats["level"]

  brand.draw_background()

  # three columns by two rows of tiles
  W, H, G = 98, 42, 5
  x0, y0 = 8, 46
  col = [x0, x0 + W + G, x0 + 2 * (W + G)]
  row = [y0, y0 + H + G]

  tile(col[0], row[0], W, H, "CPU 2x M33", "%d MHz" % (machine.freq() // 1000000), cyan)
  tile(col[1], row[0], W, H, "Core temp", "%.1f C" % temp, orange)
  tile(col[2], row[0], W, H, "Uptime", uptime(time.ticks_ms()))

  tile(col[0], row[1], W, H, "RAM free", "%d KB" % (free // 1024))
  bar(col[0] + 7, row[1] + H - 7, W - 14, used / (free + used), cyan)
  tile(col[1], row[1], W, H, "Flash used", "%d KB" % (disk_used // 1024))
  bar(col[1] + 7, row[1] + H - 7, W - 14, disk_used / disk_total, orange)
  charge = "+" if stats["charging"] else ""
  tile(col[2], row[1], W, H, "Battery %.2fV" % stats["volts"],
       "%d%%%s" % (level, charge), green if level > 20 else orange)

  draw_graph()

  screen.font = regular_font
  screen.pen = muted
  status = "%d fps  A: lights %s  C/up/down: graph" % (fps, LIGHT_MODES[light_mode])
  screen.text(status, 10, 220, 12)

  brand.draw_header()
  badge.update()

badge.caselights(0)
badge.mode(LORES | VSYNC)
