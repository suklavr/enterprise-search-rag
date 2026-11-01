"""Record a screen-capture demo of the web UI with Playwright.

Usage: .venv/bin/python tools/record_demo.py [--url http://127.0.0.1:8000] [--out docs/demo]
Requires `pip install playwright imageio-ffmpeg && python -m playwright install chromium` and a running `python -m rag serve`.
Writes demo.webm, demo.mp4 and demo.gif into --out.
"""
import argparse, shutil, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

W, H = 1280, 800
CURSOR_JS = """
(() => {
  const c = document.createElement('div');
  c.id = '__cursor';
  Object.assign(c.style, {position:'fixed', left:'0px', top:'0px', width:'18px', height:'18px', zIndex: 999999,
    pointerEvents:'none', borderRadius:'50%', background:'rgba(11,95,255,0.85)', border:'2px solid white',
    boxShadow:'0 0 0 2px rgba(0,0,0,0.25)', transform:'translate(-50%,-50%)', transition:'width .12s, height .12s'});
  document.addEventListener('DOMContentLoaded', () => document.body.appendChild(c));
  window.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  window.addEventListener('mousedown', () => { c.style.width = '30px'; c.style.height = '30px'; }, true);
  window.addEventListener('mouseup', () => { c.style.width = '18px'; c.style.height = '18px'; }, true);
})();
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default="docs/demo")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_video"; shutil.rmtree(tmp, ignore_errors=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": W, "height": H}, color_scheme="light",
                                  record_video_dir=str(tmp), record_video_size={"width": W, "height": H})
        ctx.add_init_script(CURSOR_JS)
        page = ctx.new_page()
        m = page.mouse

        def move(x, y, steps=25): m.move(x, y, steps=steps)
        def click(sel):
            b = page.locator(sel).first.bounding_box()
            move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2); page.wait_for_timeout(250); m.down(); page.wait_for_timeout(90); m.up()
        def pause(ms): page.wait_for_timeout(ms)
        def ask(q, delay=38):
            click("#q"); page.keyboard.press("Meta+A"); page.keyboard.press("Backspace"); pause(200)
            page.keyboard.type(q, delay=delay); pause(600); click("button.primary"); pause(1800)
        def scroll_through():
            for _ in range(4): m.wheel(0, 220); pause(650)
            pause(900)
            for _ in range(4): m.wheel(0, -220); pause(350)
            pause(700)

        page.goto(a.url); page.wait_for_selector("#status:not(:empty)"); move(640, 300, 5); pause(1800)

        # Scene 1: FAQ near-duplicate, default hybrid
        ask("How do I download a loss metrics report?"); scroll_through()

        # Scene 2: identifier query, keyword-only on product docs
        click("button[data-a='0']"); pause(700)
        page.select_option("#collection", "product-docs"); pause(700)
        ask("Which scenarios use the hybrid footprint HFP?"); scroll_through()

        # Scene 3: paraphrase on policies, drag slider toward semantic
        page.select_option("#collection", "policies"); pause(600)
        s = page.locator("#alpha").bounding_box()
        y = s["y"] + s["height"] / 2
        move(s["x"] + 2, y); pause(300); m.down(); move(s["x"] + s["width"] * 0.75, y, steps=30); pause(250); m.up(); pause(900)
        ask("can I paste client data into ChatGPT?"); scroll_through()

        # Scene 4: no answer in corpus -> generator declines
        page.select_option("#collection", ""); click("button[data-a='0.5']"); pause(700)
        ask("What is the guest wifi password in the Tokyo office?"); pause(3200)

        video = page.video
        ctx.close(); browser.close()
        src = video.path()

    webm = out / "demo.webm"; shutil.move(src, webm); shutil.rmtree(tmp, ignore_errors=True)
    ff = shutil.which("ffmpeg")
    if not ff:
        try:
            import imageio_ffmpeg; ff = imageio_ffmpeg.get_ffmpeg_exe()   # full build; Playwright's own ffmpeg only writes webm
        except ImportError:
            print(f"wrote {webm}; install ffmpeg or imageio-ffmpeg for mp4/gif"); return
    mp4 = out / "demo.mp4"; gif = out / "demo.gif"
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(webm), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22", "-movflags", "+faststart", str(mp4)], check=True)
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(webm), "-filter_complex",
                    "[0:v]fps=8,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=5",
                    str(gif)], check=True)
    for f in (webm, mp4, gif): print(f"wrote {f} ({f.stat().st_size/1e6:.1f} MB)")

if __name__ == "__main__":
    main()
