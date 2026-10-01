"""PetCare clip reel maker: real footage first, text second.

Built for Vee's own phone clips of his pets (the format Instagram and Facebook
recommend: original footage, not majority text). Cuts 1-6 shots together at
1080x1920, adds a short caption line per shot (meme/subtitle style, never more
than two lines), and a small PetCare tag on the last 1.5 seconds. No logo at the
start, no full-screen text cards. Silent audio track; music is added in the app.

Usage:
    python3 reels/make_clip_reel.py reels/specs/clip-2026-10-02.json reels/out/2026-10-02.mp4 --clips DIR

Spec:
{
  "shots": [
    {"file": "IMG_1234.MOV", "start": 1.0, "dur": 2.5,
     "text": "Me: [[it's just a quick weigh-in]]", "pos": "top",   # top | middle | bottom
     "focus_x": 0.5, "focus_y": 0.5, "speed": 1.0}
  ],
  "tag": "Every weigh-in, charted · petcareapp.org",   # optional, shown over the last 1.5 s
  "grade": {"gamma": 1.0, "contrast": 1.04, "saturation": 1.08}
}
[[text]] = teal. Keep each caption under ~8 words: the footage carries the reel.
Clips stay OUTSIDE the repo (--clips, $PETCARE_CLIPS or reels/clips/, git-ignored).
"""
import argparse, json, os, pathlib, shutil, subprocess, tempfile
from playwright.sync_api import sync_playwright
from make_reel import CSS, rich, paw, find_clip, probe, FPS

TAG_SECS = 1.5
TCSS = (CSS.replace("html,body{margin:0;background:#000}", "html,body{margin:0;background:transparent}")
           .replace("overflow:hidden;background:#000;", "overflow:hidden;background:transparent;"))


def caption_page(text, pos):
    top = {"top": "top:300px", "middle": "top:820px", "bottom": "bottom:520px"}[pos]
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{TCSS}</style></head><body><div class="s">'
            f'<div style="position:absolute;left:70px;right:70px;{top};display:flex;justify-content:center">'
            f'<div style="max-width:880px;text-align:center;font-family:\'Bricolage Grotesque\';font-weight:800;'
            f'font-size:72px;line-height:1.08;letter-spacing:-1.5px;color:#fff;background:rgba(0,0,0,.55);'
            f'border-radius:28px;padding:22px 34px;box-decoration-break:clone">{rich(text)}</div></div></div></body></html>')


def tag_page(text):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{TCSS}</style></head><body><div class="s">'
            f'<div style="position:absolute;left:0;right:0;bottom:430px;display:flex;justify-content:center">'
            f'<div style="display:flex;align-items:center;gap:16px;background:rgba(0,0,0,.72);border-radius:999px;'
            f'padding:18px 30px 18px 22px;font-size:34px;font-weight:600;color:#F5F5F7">'
            f'<div style="width:52px;height:52px;border-radius:50%;background:linear-gradient(180deg,#0F7A6E,#095B53);'
            f'display:flex;align-items:center;justify-content:center">{paw(32, "#fff")}</div>{rich(text)}</div></div>'
            f'</div></body></html>')


def shoot_png(pages, work):
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        for name, html in pages.items():
            f = work / f"{name}.html"
            f.write_text(html, encoding="utf-8")
            pg.goto(f"file://{f}")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(250)
            out[name] = work / f"{name}.png"
            pg.screenshot(path=str(out[name]), omit_background=True)
        b.close()
    return out


def crop_filter(w, h, fx, fy):
    target = 1080 / 1920
    if w / h > target:
        cw, ch = int(h * target) // 2 * 2, h
    else:
        cw, ch = w, int(w / target) // 2 * 2
    return f"crop={cw}:{ch}:{int((w - cw) * fx)}:{int((h - ch) * fy)},scale=1080:1920:flags=lanczos"


def render(spec_path, out_path, clips_dir=None):
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    shots = spec["shots"]
    g = spec.get("grade", {})
    eq = f'eq=gamma={g.get("gamma", 1.0)}:contrast={g.get("contrast", 1.04)}:saturation={g.get("saturation", 1.08)}'
    work = pathlib.Path(tempfile.mkdtemp(prefix="clipreel-"))
    pages = {f"cap{i}": caption_page(s["text"], s.get("pos", "top")) for i, s in enumerate(shots) if s.get("text")}
    if spec.get("tag"):
        pages["tag"] = tag_page(spec["tag"])
    pngs = shoot_png(pages, work)
    segs, total = [], 0.0
    for i, s in enumerate(shots):
        clip = find_clip(s["file"], clips_dir)
        w, h = probe(clip)
        dur, speed = float(s["dur"]), float(s.get("speed", 1.0))
        last = i == len(shots) - 1
        inputs = ["-ss", str(s.get("start", 0)), "-t", f"{dur * speed + 0.5}", "-i", str(clip)]
        fc = (f"[0:v]setpts=(PTS-STARTPTS)/{speed},{crop_filter(w, h, float(s.get('focus_x', .5)), float(s.get('focus_y', .5)))},"
              f"{eq},unsharp=5:5:0.3,fps={FPS},format=yuv420p,setsar=1[v0];")
        cur, n = "v0", 1
        if f"cap{i}" in pngs:
            inputs += ["-loop", "1", "-t", f"{dur + 0.5}", "-i", str(pngs[f'cap{i}'])]
            fc += f"[{n}:v]format=rgba[c{n}];[{cur}][c{n}]overlay=0:0[v{n}];"
            cur, n = f"v{n}", n + 1
        if last and "tag" in pngs:
            inputs += ["-loop", "1", "-t", f"{dur + 0.5}", "-i", str(pngs["tag"])]
            t0 = max(0.0, dur - TAG_SECS)
            fc += f"[{n}:v]format=rgba[c{n}];[{cur}][c{n}]overlay=0:0:enable='gte(t,{t0:.2f})'[v{n}];"
            cur, n = f"v{n}", n + 1
        fc += f"[{cur}]trim=duration={dur},setpts=PTS-STARTPTS,format=yuv420p[out]"
        seg = work / f"seg{i}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, "-map", "[out]",
                        "-r", str(FPS), "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
                        str(seg)], check=True)
        segs.append(seg)
        total += dur
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in segs))
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out_path)], check=True)
    for label, frac in (("0", 0.0), ("a", 0.12), ("b", 0.6), ("c", 0.95)):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{total*frac:.3f}", "-i", str(out_path),
                        "-frames:v", "1", "-q:v", "3", str(out_path.with_suffix(f".check-{label}.jpg"))], check=True)
    shutil.rmtree(work)
    print(f"{spec_path} -> {out_path} ({total:.1f}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Cut a PetCare reel from real clips.")
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--clips", help="folder holding the clips (never inside the repo)")
    a = ap.parse_args()
    render(a.spec, a.out, a.clips)
