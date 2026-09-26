"""PetCare post renderer.

Turns Design-canvas artboards (.dc.html) or plain HTML slides into 1080x1350 PNGs
for Instagram, using Playwright's Chromium and the brand fonts in render/fonts/.

Usage:
    python3 render/render.py OUT_DIR slide1.dc.html slide2.dc.html ...

Slides are written to OUT_DIR as 1.png, 2.png, ... in the order given.
Fonts: render/fonts/ must hold DMSans.ttf, Bricolage.ttf and Poppins-Medium.ttf
(download them from github.com/google/fonts, folder ofl/, if missing).
"""
import os
import re
import sys
import pathlib

from playwright.sync_api import sync_playwright

ACCENT = os.environ.get("PETCARE_ACCENT", "#2EC4B6")
HERE = pathlib.Path(__file__).resolve().parent
FONTS = HERE / "fonts"

FONT_CSS = f"""
@font-face {{ font-family: 'DM Sans'; src: url('file://{FONTS}/DMSans.ttf'); font-weight: 100 1000; }}
@font-face {{ font-family: 'Bricolage Grotesque'; src: url('file://{FONTS}/Bricolage.ttf'); font-weight: 200 800; }}
@font-face {{ font-family: 'Poppins'; src: url('file://{FONTS}/Poppins-Medium.ttf'); font-weight: 500; }}
"""


def to_static_html(src: str) -> str:
    """Strip the canvas runtime so the artboard renders as plain HTML."""
    html = src
    html = html.replace('<script src="./support.js"></script>', "")
    html = re.sub(r'<script type="text/x-dc".*?</script>', "", html, flags=re.S)
    html = re.sub(r"<link[^>]*fonts\.googleapis\.com[^>]*>", "", html)
    for tag in ("<x-dc>", "</x-dc>", "<helmet>", "</helmet>"):
        html = html.replace(tag, "")
    html = html.replace("{{accent}}", ACCENT)
    if "{{" in html:
        raise ValueError("unresolved template hole left in slide")
    return html.replace("</head>", f"<style>{FONT_CSS}</style></head>", 1)


def main() -> None:
    out_dir = pathlib.Path(sys.argv[1])
    slides = [pathlib.Path(p) for p in sys.argv[2:]]
    out_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        for i, slide in enumerate(slides, start=1):
            html = to_static_html(slide.read_text(encoding="utf-8"))
            tmp = out_dir / f".slide-{i}.html"
            tmp.write_text(html, encoding="utf-8")
            page.goto(f"file://{tmp.resolve()}")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(300)
            page.screenshot(path=str(out_dir / f"{i}.png"), clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
            tmp.unlink()
            print(f"{slide.name} -> {out_dir / f'{i}.png'}")
        browser.close()


if __name__ == "__main__":
    main()
