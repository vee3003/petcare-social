"""PetCare reel maker.

Turns a small JSON spec into a 1080x1920 MP4 reel in the PetCare look
(black, teal accent, Bricolage Grotesque + DM Sans), with a silent audio
track so Instagram accepts it. Music is added in the Instagram app.

Usage:
    python3 reels/make_reel.py reels/specs/2026-09-28.json reels/out/2026-09-28.mp4

Spec formats (see reels/specs/ for real examples):
    timeline  rows appear one by one down a line   (schedules)
    list      one big numbered card at a time      (countdowns, questions)
    chat      message bubbles, like a phone chat   (POV / relatable)
    beats     one big statement at a time          (a number, a punchline)

Text wrapped in [[double brackets]] is drawn in the teal accent.
Keep every health fact inside the playbook's fact bank.
The hook (kicker + headline, or the first beat) is on screen from frame 0:
no blank or logo-only opening, and the whole hook readable within 3 seconds.

Optional "opener": a real animal clip (Pexels/Pixabay, kept OUTSIDE the repo)
plays first with the hook drawn over it from frame 0, then fades into the
text reel. Clips are looked up in --clips DIR, $PETCARE_CLIPS or reels/clips/
(git-ignored). Never commit the clips themselves, only the finished reel.
    "opener": {"file": "pexels-123-name.mp4", "start": 2.0, "seconds": 2.2,
               "text": "top" | "bottom", "focus_x": 0.5, "focus_y": 0.5,
               "gamma": 1.0, "contrast": 1.04, "saturation": 1.08,
               "credit": "Video by NAME on Pexels", "url": "https://www.pexels.com/video/..."}
With "beats", the first beat is shown over the clip and the text reel starts at beat 2.
"""
import argparse, html, json, os, pathlib, re, shutil, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
FONTS = HERE.parent / "render" / "fonts"
FPS = 30
TEAL = "#2EC4B6"

PAW_G = ('<g transform="translate(50 50) scale(1.08) translate(-50 -52.3)">'
         '<ellipse cx="37.72" cy="25.84" rx="8.5" ry="11.3" transform="rotate(-12 37.72 25.84)"/>'
         '<ellipse cx="17.29" cy="44.76" rx="7.8" ry="10.3" transform="rotate(-36 17.29 44.76)"/>'
         '<ellipse cx="62.28" cy="25.84" rx="8.5" ry="11.3" transform="rotate(12 62.28 25.84)"/>'
         '<ellipse cx="82.71" cy="44.76" rx="7.8" ry="10.3" transform="rotate(36 82.71 44.76)"/>'
         '<g transform="translate(50 64) scale(1.06) translate(-50 -64)"><path d="M50 46 C58.5 46 65 51.5 70.5 59 '
         'C76 66.5 79.5 73.5 76 79.5 C72.8 84.8 66 85.2 60.5 83 C56 81.2 53.3 80.2 50 80.2 C46.7 80.2 44 81.2 39.5 83 '
         'C34 85.2 27.2 84.8 24 79.5 C20.5 73.5 24 66.5 29.5 59 C35 51.5 41.5 46 50 46 Z"/></g></g>')


def paw(size, fill):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 100 100" style="fill:{fill}">{PAW_G}</svg>'


def rich(text):
    """Escape text, then turn [[...]] into teal spans."""
    t = html.escape(text)
    return re.sub(r"\[\[(.+?)\]\]", rf'<span style="color:{TEAL}">\1</span>', t)


CSS = f"""
@font-face{{font-family:'DM Sans';src:url('file://{FONTS}/DMSans.ttf');font-weight:100 1000}}
@font-face{{font-family:'Bricolage Grotesque';src:url('file://{FONTS}/Bricolage.ttf');font-weight:200 800}}
@font-face{{font-family:'Poppins';src:url('file://{FONTS}/Poppins-Medium.ttf');font-weight:500}}
*{{box-sizing:border-box}} html,body{{margin:0;background:#000}}
.s{{width:1080px;height:1920px;position:relative;overflow:hidden;background:#000;color:#F5F5F7;font-family:'DM Sans',sans-serif}}
@keyframes up{{from{{opacity:0;transform:translateY(40px)}}to{{opacity:1;transform:none}}}}
@keyframes out{{to{{opacity:0;transform:translateY(-30px)}}}}
@keyframes grow{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}
@keyframes pop{{0%{{transform:scale(0)}}70%{{transform:scale(1.25)}}100%{{transform:scale(1)}}}}
@keyframes dimdot{{to{{background:#3A3A3C;box-shadow:none}}}}
@keyframes cardin{{from{{opacity:0;transform:scale(.94)}}to{{opacity:1;transform:none}}}}
@keyframes slidein{{from{{opacity:0;transform:translateX(80px)}}to{{opacity:1;transform:none}}}}
.brand{{position:absolute;left:90px;top:230px;display:flex;align-items:center;gap:14px}}
.kick{{font-size:30px;font-weight:700;letter-spacing:4px;color:{TEAL}}}
h1{{margin:18px 0 0;font-family:'Bricolage Grotesque';font-weight:800;font-size:92px;line-height:1.0;letter-spacing:-3px}}
.body{{position:absolute;inset:0}}
.foot{{position:absolute;left:90px;top:1560px;width:900px;font-size:26px;line-height:1.4;color:#8E8E93}}
.end{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:44px;padding:0 90px 260px;text-align:center}}
.end h2{{margin:0;font-family:'Bricolage Grotesque';font-weight:800;font-size:92px;line-height:1.02;letter-spacing:-3px}}
.cta{{padding:26px 54px;border-radius:999px;background:#F5F5F7;color:#000;font-size:40px;font-weight:700}}
"""


def anim(name, dur, delay, ease="ease-out"):
    return f"{name} {dur}s {delay:.2f}s {ease} both"


def build(spec):
    fmt = spec["format"]
    parts, t0 = [], 0.8  # hook is visible at frame 0; first content beat lands at 0.8 s
    head = ""
    if fmt != "beats":
        head = (f'<div style="position:absolute;left:90px;top:330px;width:900px">'
                f'<div class="kick">{rich(spec.get("kicker", ""))}</div>'
                f'<h1>{rich(spec["title"])}</h1></div>')

    if fmt == "timeline":
        rows, step = spec["rows"], 1.8
        n = len(rows)
        top = spec.get("top", 745)
        rowh = spec.get("row_height", 160)
        items = [f'<div style="position:absolute;left:21px;top:22px;width:4px;height:{rowh*(n-1)}px;'
                 f'background:#2C2C2E;transform-origin:top;animation:{anim("grow", step*(n-1), t0-0.2, "linear")}"></div>']
        for i, r in enumerate(rows):
            t = t0 + i * step
            dot_anim = f'{anim("pop", .45, t)}' + (f', {anim("dimdot", .4, t+step)}' if i < n - 1 else "")
            items.append(
                f'<div style="position:relative;display:flex;gap:44px;height:{rowh}px;animation:{anim("up", .5, t)}">'
                f'<div style="flex:none;width:46px;height:46px;border-radius:50%;background:{TEAL};'
                f'box-shadow:0 0 0 10px rgba(46,196,182,.18);animation:{dot_anim}"></div>'
                f'<div><div style="font-size:50px;font-weight:700;line-height:1.1">{rich(r["big"])}</div>'
                f'<div style="font-size:33px;line-height:1.35;color:#D1D1D6;margin-top:8px;max-width:780px">{rich(r["small"])}</div></div></div>')
        parts.append(f'<div style="position:absolute;left:90px;top:{top}px;width:900px">{"".join(items)}</div>')
        body_end = t0 + n * step + 0.4

    elif fmt == "list":
        items, step = spec["items"], spec.get("step", 2.2)
        n = len(items)
        for i, it in enumerate(items):
            t = t0 + i * step
            a = anim("slidein", .45, t)
            if i < n - 1:
                a += ", " + anim("out", .35, t + step - 0.35, "ease-in")
            parts.append(
                f'<div style="position:absolute;left:90px;top:{spec.get("top", 800)}px;width:900px;min-height:560px;'
                f'background:#1C1C1E;border-radius:36px;padding:56px 60px;animation:{a}">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<div style="width:92px;height:92px;border-radius:50%;background:{TEAL};color:#000;display:flex;'
                f'align-items:center;justify-content:center;font-family:\'Bricolage Grotesque\';font-weight:800;font-size:54px">{i+1}</div>'
                f'<div style="font-size:28px;font-weight:500;color:#8E8E93">{i+1} of {n}</div></div>'
                f'<div style="margin-top:44px;font-family:\'Bricolage Grotesque\';font-weight:800;font-size:{it.get("size", 76)}px;'
                f'line-height:1.04;letter-spacing:-2px">{rich(it["big"])}</div>'
                f'<div style="margin-top:26px;font-size:38px;line-height:1.4;color:#D1D1D6">{rich(it.get("small", ""))}</div></div>')
        body_end = t0 + n * step + 0.2

    elif fmt == "chat":
        msgs, t, bubbles = spec["messages"], t0, []
        for m in msgs:
            who = m["from"]
            if who == "action":
                bubbles.append(f'<div style="align-self:center;font-size:32px;font-style:italic;color:#8E8E93;'
                               f'animation:{anim("up", .4, t)}">{rich(m["text"])}</div>')
            else:
                me = who == "me"
                bg, fg = (TEAL, "#000") if me else ("#1C1C1E", "#F5F5F7")
                radius = "40px 40px 12px 40px" if me else "40px 40px 40px 12px"
                label = f'<div style="font-size:24px;color:#8E8E93;margin:0 12px 8px;text-align:{"right" if me else "left"}">{html.escape(m.get("name", ""))}</div>' if m.get("name") else ""
                bubbles.append(
                    f'<div style="align-self:{"flex-end" if me else "flex-start"};max-width:760px;animation:{anim("up", .4, t)}">{label}'
                    f'<div style="background:{bg};color:{fg};border-radius:{radius};padding:28px 36px;font-size:40px;'
                    f'line-height:1.3;font-weight:{600 if me else 500}">{rich(m["text"])}</div></div>')
            t += m.get("hold", 1.0 + min(len(m["text"]) / 28, 1.4))
        parts.append(f'<div style="position:absolute;left:90px;top:{spec.get("top", 760)}px;width:900px;display:flex;'
                     f'flex-direction:column;gap:30px">{"".join(bubbles)}</div>')
        body_end = t + 0.6

    elif fmt == "beats":
        beats, step, t = spec["beats"], spec.get("step", 2.4), 0.0
        n = len(beats)
        for i, b in enumerate(beats):
            a = "none" if i == 0 else anim("up", .5, t)
            if i < n - 1:
                a = (anim("out", .35, t + step - 0.35, "ease-in") if i == 0
                     else a + ", " + anim("out", .35, t + step - 0.35, "ease-in"))
            parts.append(
                f'<div style="position:absolute;left:90px;top:0;width:900px;height:1920px;display:flex;flex-direction:column;'
                f'justify-content:center;padding-bottom:180px;gap:34px;animation:{a}">'
                f'<div style="font-family:\'Bricolage Grotesque\';font-weight:800;font-size:{b.get("size", 124)}px;line-height:1.0;'
                f'letter-spacing:-4px">{rich(b["big"])}</div>'
                f'<div style="font-size:44px;line-height:1.35;color:#D1D1D6">{rich(b.get("small", ""))}</div></div>')
            t += step
        body_end = t - 0.2
    else:
        raise ValueError(f"unknown format {fmt}")

    foot = (f'<div class="foot" style="animation:{anim("up", .5, 0.8)}">{rich(spec["footnote"])}</div>'
            if spec.get("footnote") else "")
    end = spec["end"]
    end_t = body_end + 0.4
    total = end_t + end.get("hold", 2.8)
    body = (f'<div class="body" style="animation:{anim("out", .5, body_end, "ease-in")}">'
            f'<div class="brand">{paw(44, "#F5F5F7")}<span style="font-family:Poppins;font-size:34px">PetCare</span></div>'
            f'{head}{"".join(parts)}{foot}</div>')
    endcard = (f'<div class="end" style="animation:{anim("cardin", .6, end_t)}">'
               f'<div style="width:170px;height:170px;border-radius:50%;background:linear-gradient(180deg,#0F7A6E,#095B53);'
               f'display:flex;align-items:center;justify-content:center">{paw(104, "#fff")}</div>'
               f'<h2>{rich(end["title"])}</h2>'
               + (f'<div style="font-size:36px;line-height:1.4;color:#D1D1D6">{rich(end["sub"])}</div>' if end.get("sub") else "")
               + f'<div class="cta">{html.escape(end.get("cta", "Free at petcareapp.org"))}</div></div>')
    page = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="s">{body}{endcard}</div></body></html>'
    return page, total


XFADE = 0.3        # seconds of cross-fade from the clip into the text reel
TRIM_AFTER = 0.5   # skip the text reel's first half-second (its hook-only moment) after an opener


def build_overlay(spec):
    """Transparent 1080x1920 page: scrim + brand + hook, drawn over the opener clip."""
    op = spec["opener"]
    pos = op.get("text", "top")
    if spec["format"] == "beats":
        b = spec["beats"][0]
        hook = (f'<div style="font-family:\'Bricolage Grotesque\';font-weight:800;font-size:{b.get("size", 124)}px;'
                f'line-height:1.0;letter-spacing:-4px">{rich(b["big"])}</div>'
                + (f'<div style="margin-top:28px;font-size:44px;line-height:1.35;color:#E5E5EA">{rich(b["small"])}</div>'
                   if b.get("small") else ""))
    else:
        hook = f'<div class="kick">{rich(spec.get("kicker", ""))}</div><h1>{rich(spec["title"])}</h1>'
    if pos == "bottom":
        scrim = ("linear-gradient(to top,rgba(0,0,0,.86) 0%,rgba(0,0,0,.62) 26%,rgba(0,0,0,0) 52%),"
                 "linear-gradient(to bottom,rgba(0,0,0,.5) 0%,rgba(0,0,0,0) 20%)")
        block = f'<div style="position:absolute;left:90px;bottom:430px;width:820px">{hook}</div>'
    else:
        scrim = "linear-gradient(to bottom,rgba(0,0,0,.84) 0%,rgba(0,0,0,.6) 28%,rgba(0,0,0,0) 50%)"
        block = f'<div style="position:absolute;left:90px;top:330px;width:900px">{hook}</div>'
    body = (f'<div style="position:absolute;inset:0;background:{scrim}"></div>'
            f'<div class="brand">{paw(44, "#F5F5F7")}<span style="font-family:Poppins;font-size:34px">PetCare</span></div>'
            f'{block}')
    css = CSS.replace("html,body{margin:0;background:#000}", "html,body{margin:0;background:transparent}")
    css = css.replace("overflow:hidden;background:#000;", "overflow:hidden;background:transparent;")
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body><div class="s">{body}</div></body></html>'


def find_clip(name, clips_dir=None):
    dirs = [clips_dir, os.environ.get("PETCARE_CLIPS"), str(HERE / "clips")]
    for d in dirs:
        if d and (pathlib.Path(d) / name).is_file():
            return pathlib.Path(d) / name
    raise FileNotFoundError(f"opener clip {name!r} not found in {[d for d in dirs if d]}")


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    w, h = out.stdout.strip().split(",")[:2]
    return int(w), int(h)


def compose_opener(spec, clip, overlay_png, text_mp4, out_path, trim_after):
    op = spec["opener"]
    secs = float(op.get("seconds", 2.2))
    w, h = probe(clip)
    target = 1080 / 1920
    if w / h > target:   # wider than 9:16: crop the sides
        cw, ch = int(h * target) // 2 * 2, h
    else:                # taller: crop top/bottom
        cw, ch = w, int(w / target) // 2 * 2
    x = int((w - cw) * float(op.get("focus_x", 0.5)))
    y = int((h - ch) * float(op.get("focus_y", 0.5)))
    # hook in the same place before and after the cut: plain cross-fade; otherwise dip through black
    # so the two hook positions never show at once
    trans = "fade" if op.get("text", "top") == "top" and spec["format"] != "beats" else "fadeblack"
    eq = (f'eq=gamma={op.get("gamma", 1.0)}:contrast={op.get("contrast", 1.04)}:'
          f'saturation={op.get("saturation", 1.08)}')
    fc = (f"[0:v]crop={cw}:{ch}:{x}:{y},scale=1080:1920:flags=lanczos,{eq},unsharp=5:5:0.35,"
          f"fps={FPS},format=yuv420p,setsar=1,settb=AVTB[bg];"
          f"[1:v]format=rgba[ov];"
          f"[bg][ov]overlay=0:0,format=yuv420p,trim=duration={secs},setpts=PTS-STARTPTS[op];"
          f"[2:v]fps={FPS},format=yuv420p,setsar=1,settb=AVTB,setpts=PTS-STARTPTS[rl];"
          f"[op][rl]xfade=transition={trans}:duration={XFADE}:offset={secs - XFADE:.3f}[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-ss", str(op.get("start", 0)), "-t", f"{secs + 0.5}", "-i", str(clip),
                    "-loop", "1", "-t", f"{secs + 0.5}", "-i", str(overlay_png),
                    "-ss", f"{trim_after}", "-i", str(text_mp4),
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-filter_complex", fc, "-map", "[v]", "-map", "3:a", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out_path)], check=True)


def render(spec_path, out_path, clips_dir=None):
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    opener = spec.get("opener")
    clip = find_clip(opener["file"], clips_dir) if opener else None
    reel_spec = spec
    if opener and spec["format"] == "beats":  # the first beat is shown over the clip
        reel_spec = dict(spec, beats=spec["beats"][1:])
    page, total = build(reel_spec)
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(tempfile.mkdtemp(prefix="reel-"))
    (work / "reel.html").write_text(page, encoding="utf-8")
    n = int(round(total * FPS))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(f"file://{work / 'reel.html'}")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(400)
        for i in range(n):
            pg.evaluate(f"document.getAnimations().forEach(a=>{{a.pause();a.currentTime={i*1000/FPS}}})")
            pg.screenshot(path=str(work / f"{i:04d}.jpg"), type="jpeg", quality=92)
        b.close()
    text_mp4 = work / "text.mp4" if opener else out_path
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(work / "%04d.jpg"),
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(text_mp4)], check=True)
    if opener:
        (work / "overlay.html").write_text(build_overlay(spec), encoding="utf-8")
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1080, "height": 1920})
            pg.goto(f"file://{work / 'overlay.html'}")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(400)
            pg.screenshot(path=str(work / "overlay.png"), omit_background=True)
            b.close()
        trim = 0.0 if spec["format"] == "beats" else TRIM_AFTER
        compose_opener(spec, clip, work / "overlay.png", text_mp4, out_path, trim)
        total = float(opener.get("seconds", 2.2)) - XFADE + total - trim
    # keep check frames next to the video for a quick visual review
    # check-0 is the very first frame: the hook must already be readable there
    for label, frac in (("0", 0.0), ("a", 0.12), ("b", 0.6), ("c", 0.95)):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{total*frac:.3f}", "-i", str(out_path),
                        "-frames:v", "1", "-q:v", "3", str(out_path.with_suffix(f".check-{label}.jpg"))], check=True)
    shutil.rmtree(work)
    print(f"{spec_path} -> {out_path} ({total:.1f}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Render a PetCare reel from a JSON spec.")
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--clips", help="folder holding opener clips (never inside the repo)")
    a = ap.parse_args()
    render(a.spec, a.out, a.clips)
