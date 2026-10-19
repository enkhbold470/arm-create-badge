import sys, time
if "/system" not in sys.path: sys.path.insert(0, "/system")
badge.mode(HIRES | VSYNC)
import branding as brand
_, bold = brand.fonts()
names = (("A", BUTTON_A), ("B", BUTTON_B), ("C", BUTTON_C),
         ("UP", BUTTON_UP), ("DOWN", BUTTON_DOWN), ("HOME", BUTTON_HOME))
seen = {}
end = time.ticks_add(time.ticks_ms(), 180000)
while len(seen) < len(names) and time.ticks_diff(end, time.ticks_ms()) > 0:
  badge.poll()
  for n, b in names:
    # badge.pressed() is the edge the apps use; the raw pin reads 0 while held
    hit = "event" if badge.pressed(b) else ("pin" if b.value() == 0 else None)
    if hit and n not in seen:
      seen[n] = hit
      print("pressed", n, "via", hit)
  screen.pen = color.rgb(0, 0, 0); screen.clear()
  screen.font = bold
  screen.pen = brand.white
  screen.text("BUTTON TEST: press each one", 14, 8, 20)
  for i, (n, b) in enumerate(names):
    y = 44 + i * 30
    screen.pen = brand.green if n in seen else brand.muted
    screen.text(("OK  " if n in seen else "..  ") + n, 30, y, 24)
  badge.update()
print("seen", seen, "missing", [n for n, _ in names if n not in seen])
