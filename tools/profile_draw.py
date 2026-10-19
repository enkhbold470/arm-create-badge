import sys, time
if "/system" not in sys.path: sys.path.insert(0, "/system")
badge.mode(HIRES | VSYNC)
screen.antialias = image.X2
import branding as brand
reg, bold = brand.fonts()
def t(name, fn, n=10):
  s = time.ticks_us()
  for _ in range(n): fn()
  print(name, time.ticks_diff(time.ticks_us(), s) // n, "us")
t("background", brand.draw_background)
t("header", brand.draw_header)
bg = color.rgb(0,0,0,150)
def rr():
  screen.pen = bg
  for i in range(7): screen.shape(shape.rounded_rectangle(8, 46, 98, 42, 6))
t("7 rrects", rr)
def txt():
  screen.font = bold; screen.pen = brand.white
  for i in range(14): screen.text("123 KB", 10, 50, 17)
t("14 texts", txt)
def bars():
  for i in range(120): screen.rectangle(10 + i*2, 150, 2, 30)
t("120 rects", bars)
def upd(): badge.update()
t("update", upd, 5)
screen.antialias = image.OFF
t("7 rrects noAA", rr)
t("14 texts noAA", txt)
