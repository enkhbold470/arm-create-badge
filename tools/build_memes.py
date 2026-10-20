"""
Build the photo memes for the badge: download each template from imgflip,
lay it out for the 320x240 screen, caption it, and save a baseline JPEG
(the badge cannot read progressive ones).

  uv run --with pillow tools/build_memes.py [--sheet preview.jpg]

The templates are other people's images, so the downloads and the built
JPEGs stay out of git: templates go to tools/.meme-cache, output to
apps/memes/img, both ignored. Captions and layouts live in tools/memes.json.
"""

import json
import os
import re
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "tools", "memes.json")
CACHE = os.path.join(ROOT, "tools", ".meme-cache")
OUT = os.path.join(ROOT, "apps", "memes", "img")

W, H = 320, 240
IMPACT = "/System/Library/Fonts/Supplemental/Impact.ttf"
INK = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
SMALLEST = 9

# imgflip does not list every template by name
EXTRA_URLS = {"most_interesting_man": "https://i.imgflip.com/1bh8.jpg"}


def slug(name):
  return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def template_urls():
  with urllib.request.urlopen("https://api.imgflip.com/get_memes", timeout=20) as r:
    memes = json.load(r)["data"]["memes"]
  urls = {slug(m["name"]): m["url"] for m in memes}
  urls.update(EXTRA_URLS)
  return urls


def fetch(ids):
  os.makedirs(CACHE, exist_ok=True)
  have = {os.path.splitext(f)[0]: f for f in os.listdir(CACHE)}
  missing = [i for i in ids if i not in have]
  if missing:
    urls = template_urls()
    for i in missing:
      url = urls[i]
      path = os.path.join(CACHE, i + os.path.splitext(url)[1])
      urllib.request.urlretrieve(url, path)
      have[i] = os.path.basename(path)
  return {i: os.path.join(CACHE, have[i]) for i in ids}


def place(canvas, src, piece):
  sx0, sy0, sx1, sy1, dx, dy, dw, dh, mode = piece
  sw, sh = src.size
  part = src.crop((int(sx0 * sw), int(sy0 * sh), int(sx1 * sw), int(sy1 * sh)))
  pw, ph = part.size
  if mode == "cover":
    scale = max(dw / pw, dh / ph)
  else:
    scale = min(dw / pw, dh / ph)
  part = part.resize((max(1, round(pw * scale)), max(1, round(ph * scale))),
                     Image.LANCZOS)
  pw, ph = part.size
  if mode == "cover":
    left, top = (pw - dw) // 2, (ph - dh) // 2
    canvas.paste(part.crop((left, top, left + dw, top + dh)), (dx, dy))
  else:
    canvas.paste(part, (dx + (dw - pw) // 2, dy + (dh - ph) // 2))


def wrap(draw, text, face, width):
  lines = []
  for para in text.split("\n"):
    line = ""
    for word in para.split():
      trial = word if not line else line + " " + word
      if not line or draw.textlength(trial, font=face) <= width:
        line = trial
      else:
        lines.append(line)
        line = word
    lines.append(line)
  return lines


def caption(draw, text, x, y, w, h, style, size):
  impact = style == "impact"
  if impact:
    text = text.upper()
  path = IMPACT if impact else INK
  while True:
    face = ImageFont.truetype(path, size)
    lines = wrap(draw, text, face, w)
    pitch = size * (1.05 if impact else 1.15)
    widest = max(draw.textlength(l, font=face) for l in lines)
    if (len(lines) * pitch <= h and widest <= w) or size <= SMALLEST:
      break
    size -= 1
  top = y + (h - len(lines) * pitch) / 2
  for n, line in enumerate(lines):
    lw = draw.textlength(line, font=face)
    at = (x + (w - lw) / 2, top + n * pitch)
    if impact:
      draw.text(at, line, font=face, fill="white",
                stroke_width=max(1, size // 12), stroke_fill="black")
    else:
      draw.text(at, line, font=face, fill=(20, 20, 20))


def build(meme, src_path, guides=False):
  src = Image.open(src_path).convert("RGB")
  canvas = Image.new("RGB", (W, H), meme.get("bg", "#000000"))
  for piece in meme.get("pieces", [[0, 0, 1, 1, 0, 0, W, H, "cover"]]):
    place(canvas, src, piece)
  draw = ImageDraw.Draw(canvas)
  for text, x, y, w, h, style, size in meme["caps"]:
    if guides:
      draw.rectangle((x, y, x + w, y + h), outline=(255, 0, 255))
    caption(draw, text, x, y, w, h, style, size)
  return canvas


def main():
  spec = json.load(open(SPEC))["memes"]
  sources = fetch([m["id"] for m in spec])
  os.makedirs(OUT, exist_ok=True)
  for old in os.listdir(OUT):
    os.remove(os.path.join(OUT, old))
  built = []
  for meme in spec:
    image = build(meme, sources[meme["id"]])
    name = meme["id"] + ".jpg"
    image.save(os.path.join(OUT, name), quality=85, progressive=False,
               optimize=True)
    built.append(name)
  with open(os.path.join(OUT, "index.txt"), "w") as f:
    f.write("\n".join(built) + "\n")
  print("built %d memes into %s" % (len(built), OUT))

  if "--sheet" in sys.argv:
    # sheets of a dozen, small enough to read at a glance
    stem = os.path.splitext(sys.argv[sys.argv.index("--sheet") + 1])[0]
    guides = "--guides" in sys.argv
    cols, per = 3, 12
    for page in range(0, len(spec), per):
      batch = spec[page:page + per]
      rows = (len(batch) + cols - 1) // cols
      sheet = Image.new("RGB", (cols * (W + 8), rows * (H + 8)), "#444")
      for n, meme in enumerate(batch):
        tile = build(meme, sources[meme["id"]], guides)
        sheet.paste(tile, ((n % cols) * (W + 8) + 4, (n // cols) * (H + 8) + 4))
      out = "%s-%d.jpg" % (stem, page // per + 1)
      sheet.save(out, quality=85)
      print("preview sheet at", out)


if __name__ == "__main__":
  main()
