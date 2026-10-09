"""Render docs/demo.gif: a typed terminal session driven by gitku's real output.

    python scripts/make_demo_gif.py [REPO]   # REPO defaults to /tmp/gitku-demo (see examples/make_demo_repo.sh)
"""
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
REPO = sys.argv[1] if len(sys.argv) > 1 else "/tmp/gitku-demo"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

BG, BAR, FG, DIM = (22, 20, 17), (36, 33, 28), (238, 232, 218), (140, 132, 112)
ACCENT, GREEN = (230, 102, 74), (140, 190, 120)
W, H, SZ, LH, PAD = 900, 470, 15, 21, 22
f, fb = ImageFont.truetype(FONT, SZ), ImageFont.truetype(BOLD, SZ)
CW = f.getlength("M")


def run(*args):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), GITKU_NO_CMUDICT="1")
    out = subprocess.run([sys.executable, "-m", "gitku", *args], cwd=REPO, env=env, capture_output=True, text=True, check=True)
    return out.stdout.rstrip("\n").split("\n")


def colour(line):
    if line.startswith(("╭", "╰")):
        return DIM
    if line.startswith("  —"):
        return DIM
    if "♕" in line or line.startswith("Poet"):
        return ACCENT
    return FG


def frame(lines, cursor=True):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 34], fill=BAR)
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([16 + i * 22, 11, 28 + i * 22, 23], fill=c)
    d.text((W / 2, 17), "gitku — ~/my-project", font=f, fill=DIM, anchor="mm")
    visible = lines[-((H - 34 - PAD) // LH):]
    y = 34 + PAD // 2
    for text, kind in visible:
        if kind == "prompt":
            d.text((PAD, y), "$", font=fb, fill=GREEN)
            d.text((PAD + CW * 2, y), text, font=f, fill=FG)
        else:
            d.text((PAD, y), text, font=f, fill=kind)
        y += LH
    if cursor and visible:
        t, k = visible[-1]
        x = PAD + CW * (len(t) + (2 if k == "prompt" else 0)) + 2
        d.rectangle([x, y - LH + 3, x + CW - 2, y - 4], fill=FG)
    return im


frames, durs = [], []


def add(lines, ms, cursor=True):
    frames.append(frame(lines, cursor))
    durs.append(ms)


def type_cmd(history, cmd):
    for i in range(1, len(cmd) + 1):
        add(history + [(cmd[:i], "prompt")], 55)
    add(history + [(cmd, "prompt")], 350)
    return history + [(cmd, "prompt")]


def show(history, output, per_line=45):
    out = [(l, colour(l)) for l in output]
    for i in range(1, len(out) + 1):
        add(history + out[:i], per_line)
    return history + out


h = []
add([("", FG)], 500)
h = type_cmd([], "gitku scan")
scan = run("scan", "-n", "2")
h = show(h, scan)
add(h, 2600, cursor=False)
h = type_cmd([], "gitku laureate")
h = show(h, run("laureate"), per_line=110)
add(h, 3800, cursor=False)

out = ROOT / "docs" / "demo.gif"
out.parent.mkdir(exist_ok=True)
frames[0].save(out, save_all=True, append_images=frames[1:], duration=durs, loop=0, optimize=True, disposal=2)
print(out, len(frames), "frames", out.stat().st_size // 1024, "KB")
