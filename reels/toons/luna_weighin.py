"""Animated reel: Luna's monthly weigh-in (PetCare toons, episode 1).

Luna (cat) hops on a kitchen scale, sees the number, gives the camera a look,
pushes the scale off the table and licks her paw. 8.5 s, 1080x1920, 30 fps.
Everything is drawn in SVG and animated by render(t) in the page, stepped frame
by frame with Playwright, then encoded with ffmpeg (silent track: music is added
in the Instagram app).

    python3 reels/toons/luna_weighin.py reels/out/2026-10-02-luna-weighin.mp4
"""
import pathlib, subprocess, sys, tempfile, shutil
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
FONTS = HERE.parent.parent / "render" / "fonts"
FPS, DUR = 30, 8.5
TEAL = "#2EC4B6"

FUR, FUR_D, CREAM, PINK, INK = "#9AA1AB", "#7E8590", "#EFE9E1", "#F0A3B3", "#2B2F36"

PAW_PATH = ('<g transform="translate(50 50) scale(1.08) translate(-50 -52.3)">'
            '<ellipse cx="37.72" cy="25.84" rx="8.5" ry="11.3" transform="rotate(-12 37.72 25.84)"/>'
            '<ellipse cx="17.29" cy="44.76" rx="7.8" ry="10.3" transform="rotate(-36 17.29 44.76)"/>'
            '<ellipse cx="62.28" cy="25.84" rx="8.5" ry="11.3" transform="rotate(12 62.28 25.84)"/>'
            '<ellipse cx="82.71" cy="44.76" rx="7.8" ry="10.3" transform="rotate(36 82.71 44.76)"/>'
            '<path d="M50 46 C58.5 46 65 51.5 70.5 59 C76 66.5 79.5 73.5 76 79.5 C72.8 84.8 66 85.2 60.5 83 '
            'C56 81.2 53.3 80.2 50 80.2 C46.7 80.2 44 81.2 39.5 83 C34 85.2 27.2 84.8 24 79.5 C20.5 73.5 24 66.5 '
            '29.5 59 C35 51.5 41.5 46 50 46 Z"/></g>')


def eye(cx, side):
    return f'''
  <g id="eye{side}" transform="translate({cx} -8)">
    <clipPath id="clip{side}"><ellipse id="eyeShape{side}" cx="0" cy="0" rx="27" ry="33"/></clipPath>
    <g id="eyeOpen{side}">
      <ellipse id="eyeBall{side}" cx="0" cy="0" rx="27" ry="33" fill="#F4E39A" stroke="{INK}" stroke-width="4"/>
      <g clip-path="url(#clip{side})">
        <ellipse id="pupil{side}" cx="0" cy="0" rx="12" ry="22" fill="{INK}"/>
        <circle id="glint{side}" cx="7" cy="-11" r="6" fill="#fff"/>
        <rect id="lid{side}" x="-32" y="-40" width="64" height="0" fill="{FUR}"/>
        <line id="lidLine{side}" x1="-30" x2="30" y1="-40" y2="-40" stroke="{INK}" stroke-width="5" stroke-linecap="round" opacity="0"/>
      </g>
    </g>
    <path id="eyeHappy{side}" d="M -22 4 Q 0 -18 22 4" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round" opacity="0"/>
    <line id="brow{side}" x1="-22" x2="22" y1="-48" y2="-48" stroke="{INK}" stroke-width="6" stroke-linecap="round" opacity="0"/>
  </g>'''


def luna_svg():
    return f'''
<g id="luna">
  <ellipse id="lunaShadow" cx="0" cy="4" rx="138" ry="16" fill="#000" opacity=".13"/>
  <g id="lunaBody">
    <g id="tail"><path id="tailPath" d="M 80 -24 C 185 -14, 215 -120, 160 -205" fill="none" stroke="{FUR_D}" stroke-width="36" stroke-linecap="round"/></g>
    <path d="M -128 0 C -152 -120, -104 -236, 0 -246 C 104 -236, 152 -120, 128 0 Z" fill="{FUR}"/>
    <path d="M -60 -150 C -40 -175 40 -175 60 -150" fill="none" stroke="{FUR_D}" stroke-width="10" stroke-linecap="round" opacity=".55"/>
    <ellipse cx="0" cy="-92" rx="74" ry="94" fill="{CREAM}"/>
    <g id="armR" opacity="0">
      <line id="armRLine" x1="62" y1="-150" x2="150" y2="-60" stroke="{FUR}" stroke-width="42" stroke-linecap="round"/>
      <ellipse id="armRPaw" cx="150" cy="-60" rx="26" ry="20" fill="{CREAM}" stroke="{FUR}" stroke-width="6"/>
    </g>
    <g id="armL" opacity="0">
      <line id="armLLine" x1="-58" y1="-150" x2="-30" y2="-250" stroke="{FUR}" stroke-width="42" stroke-linecap="round"/>
      <ellipse id="armLPaw" cx="-30" cy="-250" rx="26" ry="20" fill="{CREAM}" stroke="{FUR}" stroke-width="6"/>
    </g>
    <ellipse id="pawL" cx="-46" cy="-12" rx="36" ry="21" fill="{CREAM}"/>
    <ellipse id="pawR" cx="46" cy="-12" rx="36" ry="21" fill="{CREAM}"/>
    <g id="head" transform="translate(0 -300)">
      <path d="M -100 -40 L -86 -158 L -18 -92 Z" fill="{FUR}" stroke="{FUR}" stroke-width="22" stroke-linejoin="round"/>
      <path d="M -84 -62 L -76 -128 L -38 -92 Z" fill="{PINK}" stroke="{PINK}" stroke-width="8" stroke-linejoin="round"/>
      <path d="M 100 -40 L 86 -158 L 18 -92 Z" fill="{FUR}" stroke="{FUR}" stroke-width="22" stroke-linejoin="round"/>
      <path d="M 84 -62 L 76 -128 L 38 -92 Z" fill="{PINK}" stroke="{PINK}" stroke-width="8" stroke-linejoin="round"/>
      <ellipse cx="0" cy="0" rx="118" ry="102" fill="{FUR}"/>
      <path d="M -30 -98 L -22 -62 M 0 -102 L 0 -64 M 30 -98 L 22 -62" stroke="{FUR_D}" stroke-width="9" stroke-linecap="round"/>
      <ellipse cx="0" cy="40" rx="74" ry="50" fill="{CREAM}"/>
      {eye(-46, "L")}
      {eye(46, "R")}
      <path d="M -13 22 L 13 22 L 0 36 Z" fill="#E58C9C" stroke="#E58C9C" stroke-width="5" stroke-linejoin="round"/>
      <path id="mouth" d="M 0 37 Q -12 54 -26 45 M 0 37 Q 12 54 26 45" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>
      <ellipse id="tongue" cx="0" cy="56" rx="11" ry="13" fill="#E86F86" opacity="0"/>
      <g stroke="{INK}" stroke-width="3.5" stroke-linecap="round" opacity=".75">
        <line x1="-48" y1="34" x2="-128" y2="22"/><line x1="-48" y1="44" x2="-126" y2="48"/>
        <line x1="48" y1="34" x2="128" y2="22"/><line x1="48" y1="44" x2="126" y2="48"/>
      </g>
      <g id="shock" opacity="0" transform="translate(120 -120)">
        <text x="0" y="0" font-family="Bricolage Grotesque" font-weight="800" font-size="96" fill="#E5484D">!</text>
        <text x="44" y="-22" font-family="Bricolage Grotesque" font-weight="800" font-size="70" fill="#E5484D">!</text>
      </g>
    </g>
  </g>
</g>'''


def scale_svg():
    return f'''
<g id="scale">
  <ellipse cx="720" cy="1294" rx="135" ry="13" fill="#000" opacity=".12"/>
  <rect x="600" y="1222" width="240" height="68" rx="20" fill="#F7F7F5" stroke="#C9CCD1" stroke-width="4"/>
  <rect x="648" y="1236" width="144" height="40" rx="10" fill="#0E2422"/>
  <text id="digits" x="740" y="1266" text-anchor="end" font-family="DM Sans" font-weight="700" font-size="30" fill="{TEAL}"
        style="font-variant-numeric: tabular-nums">0.0</text>
  <text x="782" y="1266" text-anchor="end" font-family="DM Sans" font-weight="600" font-size="18" fill="{TEAL}">kg</text>
  <rect x="588" y="1200" width="264" height="24" rx="12" fill="#E3E6EA" stroke="#C9CCD1" stroke-width="4"/>
</g>'''


def page():
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:'DM Sans';src:url('file://{FONTS}/DMSans.ttf');font-weight:100 1000}}
@font-face{{font-family:'Bricolage Grotesque';src:url('file://{FONTS}/Bricolage.ttf');font-weight:200 800}}
html,body{{margin:0;background:#000}}
.s{{width:1080px;height:1920px;position:relative;overflow:hidden}}
.cap{{position:absolute;left:70px;right:70px;top:300px;display:flex;justify-content:center}}
.cap div{{max-width:900px;text-align:center;font-family:'Bricolage Grotesque';font-weight:800;font-size:76px;line-height:1.06;
  letter-spacing:-1.5px;color:#fff;background:rgba(20,22,26,.82);border-radius:30px;padding:24px 38px}}
.tag{{position:absolute;left:0;right:0;bottom:430px;display:flex;justify-content:center}}
.tag div{{display:flex;align-items:center;gap:16px;background:rgba(20,22,26,.86);border-radius:999px;
  padding:18px 32px 18px 22px;font-family:'DM Sans';font-size:34px;font-weight:600;color:#F5F5F7}}
</style></head><body><div class="s">
<svg width="1080" height="1920" viewBox="0 0 1080 1920">
  <defs>
    <linearGradient id="wall" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#F6EEE2"/><stop offset="1" stop-color="#E9DAC4"/></linearGradient>
    <radialGradient id="glow" cx=".25" cy=".25" r=".6"><stop offset="0" stop-color="#FFF8EC" stop-opacity=".9"/><stop offset="1" stop-color="#FFF8EC" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="1080" height="1920" fill="url(#wall)"/>
  <rect width="1080" height="1920" fill="url(#glow)"/>
  <path d="M 640 0 L 1080 0 L 1080 760 L 900 760 Z" fill="#FFF9EF" opacity=".55"/>
  <g id="cam">
  <rect x="0" y="1520" width="1080" height="400" fill="#D9C4A6"/>
  <rect x="820" y="1340" width="44" height="600" fill="#8E5E3B"/>
  <rect x="-40" y="1290" width="920" height="52" rx="10" fill="#B9794B"/>
  <rect x="-40" y="1290" width="920" height="14" rx="7" fill="#CF9364"/>
  <rect x="-40" y="1342" width="920" height="10" fill="#000" opacity=".08"/>
  {scale_svg()}
  {luna_svg()}
  <g id="crash" opacity="0" transform="translate(850 1470)">
    <path d="M0 -90 L22 -30 L86 -50 L42 2 L90 50 L26 40 L10 100 L-14 42 L-80 62 L-40 8 L-92 -34 L-26 -30 Z" fill="#FFD45C" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>
    <text x="-30" y="-110" text-anchor="middle" font-family="Bricolage Grotesque" font-weight="800" font-size="64" fill="{INK}">CLANG!</text>
  </g>
  </g>
</svg>
<div class="cap" id="cap1"><div>Luna's monthly weigh-in</div></div>
<div class="cap" id="cap2" style="opacity:0"><div>Weigh-in postponed. <span style="color:{TEAL}">Indefinitely.</span></div></div>
<div class="tag" id="tag" style="opacity:0"><div><svg width="52" height="52" viewBox="0 0 52 52"><circle cx="26" cy="26" r="26" fill="#0F7A6E"/>
<g transform="translate(10 10) scale(.32)" fill="#fff">{PAW_PATH}</g></svg>Every weigh-in, charted · petcareapp.org</div></div>
</div>
<script>
const $ = id => document.getElementById(id);
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const seg=(t,a,b)=>clamp((t-a)/(b-a),0,1);
const io=p=>p<.5?2*p*p:1-Math.pow(-2*p+2,2)/2;
const out=p=>1-Math.pow(1-p,3);
const lerp=(a,b,p)=>a+(b-a)*p;
const set=(id,attrs)=>{{const e=$(id);for(const k in attrs)e.setAttribute(k,attrs[k]);}};
const PUSHES=[4.6,5.0,5.35];

function render(t){{
  // ---- Luna position, hops and squash
  let x=360,y=1290;
  if(t>=0.35&&t<0.95){{const p=seg(t,.35,.95);x=lerp(360,720,io(p));y=lerp(1290,1200,p)-130*Math.sin(Math.PI*p);}}
  else if(t>=0.95&&t<3.8){{x=720;y=1200;}}
  else if(t>=3.8&&t<4.4){{const p=seg(t,3.8,4.4);x=lerp(720,470,io(p));y=lerp(1200,1290,p)-100*Math.sin(Math.PI*p);}}
  let pushed=0;for(const tk of PUSHES)pushed+=out(seg(t,tk,tk+.14));
  const dx=55*pushed;
  if(t>=4.4)x=470+dx;
  let s=0;for(const ti of [0.35,0.95,3.8,4.4]){{const d=t-ti;if(d>-.08&&d<.2)s+=(d<0?(d+.08)/.08:1-d/.2)*.12;}}
  const sx=1+s*.7, sy=1-s;
  set('luna',{{transform:`translate(${{x}},${{y}}) scale(${{sx}},${{sy}})`}});
  $('lunaShadow').setAttribute('opacity', (y<1285? .06 : .13));

  // ---- tail
  const shock=t>=2.4&&t<3.0;
  const swish=shock? 22*Math.sin(t*22) : 12*Math.sin(t*3.2);
  set('tail',{{transform:`rotate(${{swish}} 80 -24)`}});
  $('tailPath').setAttribute('stroke-width', shock? 52 : 36);

  // ---- eyes and expression
  let pupX=0,pupY=0,pupRx=12,pupRy=22,lid=0,eyeRy=33,brow=0,happy=false,headRot=0,headY=-300;
  if(t>=1.05&&t<2.4){{pupY=14;headRot=-4;headY=-294;}}
  if(shock){{pupRx=7;pupRy=7;eyeRy=38;}}
  if(t>=3.0&&t<3.8){{lid=.48;brow=1;}}
  if(t>=3.8&&t<4.4){{lid=.25;}}
  if(t>=4.4&&t<5.6){{lid=.42;brow=1;}}
  if(t>=5.6&&t<6.3){{pupX=14;pupY=12;lid=.1;}}
  if(t>=6.3){{happy=true;headRot=-7;}}
  const blink=(tb)=>{{const d=Math.abs(t-tb);return d<.09?1-d/.09:0;}};
  lid=Math.max(lid,blink(0.18),blink(1.9));
  for(const S of ['L','R']){{
    set('pupil'+S,{{cx:pupX,cy:pupY,rx:pupRx,ry:pupRy}});
    set('glint'+S,{{cx:pupX+7,cy:pupY-11,r:shock?3:6}});
    set('eyeBall'+S,{{ry:eyeRy}});set('eyeShape'+S,{{ry:eyeRy}});
    const top=-eyeRy-4,h=(2*eyeRy+8)*lid;
    set('lid'+S,{{y:top,height:h}});
    set('lidLine'+S,{{y1:top+h,y2:top+h,opacity:lid>.05&&lid<.98?1:0}});
    $('eyeOpen'+S).setAttribute('opacity',happy?0:1);
    $('eyeHappy'+S).setAttribute('opacity',happy?1:0);
    const ang=(S==='L'?14:-14)*brow;
    set('brow'+S,{{opacity:brow,transform:`rotate(${{ang}})`}});
  }}
  set('head',{{transform:`translate(0 ${{headY}}) rotate(${{headRot}})`}});
  $('shock').setAttribute('opacity',shock?1:0);
  if(shock){{const p=seg(t,2.4,2.55);const k=p<1?lerp(.2,1.2,p):1+.2*Math.max(0,1-(t-2.55)/.2);
    set('shock',{{transform:`translate(120 -120) scale(${{k}})`}});}}

  // ---- scale digits
  let w=0; if(t>=1.05)w=lerp(0,5.3,out(seg(t,1.05,2.4)));
  $('digits').textContent=w.toFixed(1);
  $('digits').setAttribute('opacity', shock && Math.floor(t/0.12)%2? .25 : 1);

  // ---- pushing arm
  let armOn=t>=4.42&&t<5.8, e=0;
  if(armOn){{e=lerp(0,.82,seg(t,4.42,4.58));
    for(const tk of PUSHES){{const d=t-tk;if(d>=0&&d<.3)e=Math.max(e,.82+.18*Math.sin(Math.PI*clamp(d/.3,0,1)));}}
    if(t>5.55)e=lerp(e,0,seg(t,5.55,5.8));}}
  const tipX=lerp(62,150,e/1), tipY=lerp(-150,-60,e/1);
  set('armR',{{opacity:e>.02?1:0}});set('armRLine',{{x2:tipX,y2:tipY}});set('armRPaw',{{cx:tipX,cy:tipY}});
  $('pawR').setAttribute('opacity',e>.02?0:1);

  // ---- scale motion: pushed, tips over the edge, falls
  let ang=0,fx=0,fy=0;
  if(t>=5.5){{ang=lerp(0,38,Math.pow(seg(t,5.5,5.85),2));}}
  if(t>=5.85){{const f=t-5.85;ang=38+260*f;fx=120*f;fy=2600*f*f;}}
  set('scale',{{transform:`translate(${{dx+fx}},${{fy}}) rotate(${{ang}} ${{880-dx}} 1290)`}});

  // ---- crash burst
  const c=t>=6.22&&t<6.95; $('crash').setAttribute('opacity',c?1-seg(t,6.75,6.95):0);
  if(c){{const k=lerp(.3,1,out(seg(t,6.22,6.36)));set('crash',{{transform:`translate(850 1470) scale(${{k}})`}});}}

  // ---- licking paw
  const lick=t>=6.4; set('armL',{{opacity:lick?1:0}}); $('pawL').setAttribute('opacity',lick?0:1);
  if(lick){{const p=out(seg(t,6.4,6.65));const bob=8*Math.sin((t-6.65)*12)*(t>6.65?1:0);
    const lx=lerp(-50,-30,p),ly=lerp(-30,-252,p)+bob;
    set('armLLine',{{x2:lx,y2:ly}});set('armLPaw',{{cx:lx,cy:ly}});}}
  let tongue=0;for(const tl of [6.8,7.3,7.8]){{if(t>=tl&&t<tl+.22)tongue=1;}}
  $('tongue').setAttribute('opacity',tongue);

  // ---- captions and tag
  $('cap1').style.opacity=1-seg(t,6.2,6.35);
  $('cap2').style.opacity=seg(t,6.35,6.5);
  $('tag').style.opacity=seg(t,7.0,7.15);

  // ---- camera: framed on the action, dramatic zoom on the shock, shake on the clang
  let z=1.3,cx=620,cy=1060;
  const zin=out(seg(t,2.4,2.52)), zback=io(seg(t,2.98,3.3));
  const zk=zin*(1-zback);
  z=lerp(z,2.15,zk);cx=lerp(cx,720,zk);cy=lerp(cy,905,zk);
  let shx=0,shy=0; if(t>=6.22&&t<6.45){{const a=10*(1-seg(t,6.22,6.45));shx=a*Math.sin(t*90);shy=a*Math.cos(t*77);}}
  set('cam',{{transform:`translate(${{540+shx}},${{960+shy}}) scale(${{z}}) translate(${{-cx}},${{-cy}})`}});
}}
render(0);
</script></body></html>'''


def main(out):
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(tempfile.mkdtemp(prefix="toon-"))
    (work / "scene.html").write_text(page(), encoding="utf-8")
    n = int(round(DUR * FPS))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(f"file://{work / 'scene.html'}")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(400)
        for i in range(n):
            pg.evaluate(f"render({i / FPS})")
            pg.screenshot(path=str(work / f"{i:04d}.jpg"), type="jpeg", quality=93)
        b.close()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(work / "%04d.jpg"),
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)], check=True)
    for label, frac in (("0", 0.0), ("a", 0.12), ("b", 0.6), ("c", 0.95)):
        shutil.copy(work / f"{min(n - 1, int(n * frac)):04d}.jpg", out.with_suffix(f".check-{label}.jpg"))
    shutil.rmtree(work)
    print(f"-> {out} ({DUR}s)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "luna-weighin.mp4")
