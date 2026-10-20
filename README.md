# Arm Create badge hacks

Custom apps and config for the Arm Create 2026 digital badge: a Pimoroni
Tufty 2350 (RP2350, 2x Arm Cortex-M33 @ 250 MHz, 320x240 screen, MicroPython
with Pimoroni's badgeware).

## Apps

| App | What it does | Buttons |
| --- | --- | --- |
| `heypcb` | HeyPCB promo card over animated PCB traces, QR to heypcb.ai | A/C/up/down: pitch card / full-screen QR |
| `sysmon` | Live CPU, core temp, RAM, flash, battery, uptime, 1-minute graph | A: case lights off/on/temp-pulse, C/down/up: switch graph |
| `memes` | 40 classic meme templates (Drake, Distracted Boyfriend, Expanding Brain, Gru's Plan...) captioned for devs, plus 26 live-drawn text memes, as one slideshow | A/C: prev/next, up: random, down: pause/resume |

B or HOME leaves any of them for the launcher.

## Layout

- `apps/` - one folder per app; the launcher lists every folder in `/system/apps`
  with an `__init__.py` (its docstring is the card text) and `icon.svg`.
- `config/` - `profile.py` and `profile.png` (name card), `secrets.example.py`
  (Wi-Fi, region, timezone). Copy it to `config/secrets.py` to fill in Wi-Fi;
  that file is git-ignored.
- `tools/` - `install.sh` copies everything to the badge, `run.sh` runs an app
  from RAM over serial, plus a button test and draw/sensor profilers.

The badge's stock filesystem is not in this repo: it carries Arm's artwork and
a commercial font. Back yours up before changing anything (see below).

## Back up first

With the badge in Disk mode, copy all of `/Volumes/TUFTY` somewhere safe.
That is the whole `/system` folder, stock apps included.

## Photo memes

The meme templates belong to their creators, so they are not in this repo.
`tools/build_memes.py` downloads them from imgflip, lays each one out for the
320x240 screen and captions it from `tools/memes.json`:

    uv run --with pillow tools/build_memes.py --sheet /tmp/preview.jpg --guides

That writes `apps/memes/img/*.jpg` (ignored by git), which `tools/install.sh`
copies over with the app. The `--sheet` previews show the caption boxes, so
a layout can be checked without the badge. It uses macOS's Impact font. The
JPEGs must be baseline: the badge refuses progressive ones.

## Install

1. Double-press RESET so the badge mounts as `/Volumes/TUFTY`.
2. `tools/install.sh`
3. Eject TUFTY, press RESET.

To try an app without installing: `uv tool install mpremote`, then
`tools/run.sh apps/memes/__init__.py`.

## Notes from poking at it

- `/Volumes/TUFTY` is the badge's `/system`; `mpremote cp -r` fails on it, copy
  file by file.
- Delete macOS `._*` files after copying, or the launcher shows them as apps.
- `gc.mem_free()` walks the 8 MB heap and takes ~44 ms; don't call it per frame.
- `badge.ticks` only advances on `badge.update()`.
- `badge.caselights(v)` sets all four case LEDs, `badge.caselights(a, b, c, d)`
  each one.
- Core temp: `machine.ADC(machine.ADC.CORE_TEMP)`, 0.706 V at 27 C, -1.721 mV/C.
- Buttons: A GPIO7, B GPIO9, C GPIO10, UP GPIO11, DOWN GPIO6, HOME GPIO22.
- Hardware check (tools/button_test.py): all six buttons read low on their
  pins when pressed. `badge.pressed()` stays false when a script is started
  with `mpremote run`, since the button events are only fed under the
  firmware's `launch()`; test input through the launcher, not `run.sh`.
- The stock badge app links LinkedIn through `https://lnkd.in/in/<handle>`,
  which is LinkedIn's shortener rather than a profile path. On this badge the
  `NETWORKS` entry in `/system/apps/badge/__init__.py` was changed to
  `https://www.linkedin.com/in/<handle>` and moved after X, so the cards run
  name, GitHub, X, LinkedIn.
