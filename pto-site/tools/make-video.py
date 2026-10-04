#!/usr/bin/env python3
"""Промо-ролик X-PTO: страница tools/video/promo.html → MP4.

Страница — обычная CSS-анимация. Скрипт останавливает все анимации
и снимает кадр за кадром, выставляя время вручную: так каждый кадр
ровный, сколько бы ни тормозил компьютер, и ролик выходит одинаковым
при каждом запуске.

Запуск:
    python3 tools/make-video.py                      # весь ролик → promo-video.mp4
    python3 tools/make-video.py --frames 2 10.5 33   # только контрольные кадры в PNG
    python3 tools/make-video.py --out ~/rolik.mp4
    python3 tools/make-video.py --music promo-music.wav          # ролик сразу с музыкой
    python3 tools/make-video.py --mux-only ролик.mp4 --music promo-music.wav --out итог.mp4

Нужны playwright (как для make-og.py) и ffmpeg с кодеком libx264.
ffmpeg ищется в переменной FFMPEG, затем в PATH.
"""
import argparse
import functools
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGE = "/tools/video/promo.html?capture"
W, H = 1080, 1920


def find_chrome():
    for c in ("/opt/pw-browsers/chromium/chrome-linux/chrome", "/opt/pw-browsers/chromium"):
        p = Path(c)
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    return None


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "promo-video.mp4"))
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--page", default=PAGE, help="страница с анимацией (от папки сайта)")
    ap.add_argument("--duration", type=float, default=58.0, help="длина ролика, секунд")
    ap.add_argument("--frames", type=float, nargs="*", help="снять только эти моменты (секунды) в PNG")
    ap.add_argument("--music", help="WAV с музыкой (tools/make-music.py) — наложить на ролик")
    ap.add_argument("--mux-only", metavar="VIDEO",
                    help="не снимать кадры заново, а только наложить --music на готовое видео")
    args = ap.parse_args()

    if args.mux_only:
        ffmpeg = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
        if not ffmpeg or not args.music:
            return print("Нужны ffmpeg и --music") or 1
        return mux(ffmpeg, args.mux_only, args.music, args.out)

    ffmpeg = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if args.frames is None and not ffmpeg:
        return print("Не найден ffmpeg: укажите путь в переменной FFMPEG") or 1

    srv = serve()
    url = f"http://127.0.0.1:{srv.server_address[1]}{args.page}"
    chrome = find_chrome()
    with sync_playwright() as p:
        browser = p.chromium.launch(**({"executable_path": chrome} if chrome else {}))
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto(url, wait_until="networkidle")
        # Шрифты и картинки должны быть готовы до первого кадра
        page.evaluate("""async () => {
            await (window.READY || Promise.resolve());   // страница может собирать сцены из данных
            await document.fonts.ready;
            await Promise.all([...document.images].map(i => i.decode().catch(() => {})));
        }""")

        if args.frames is not None:
            for t in args.frames:
                page.evaluate(f"window.seek({t})")
                out = Path(args.out).with_name(f"kadr-{t:05.1f}.png")
                page.screenshot(path=str(out))
                print(f"  {out}")
            browser.close()
            srv.shutdown()
            return 0

        total = int(round(args.duration * args.fps))
        enc = subprocess.Popen(
            [ffmpeg, "-y", "-loglevel", "error",
             "-f", "image2pipe", "-framerate", str(args.fps), "-c:v", "mjpeg", "-i", "-",
             "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", args.out],
            stdin=subprocess.PIPE)
        for i in range(total):
            page.evaluate(f"window.seek({i / args.fps})")
            enc.stdin.write(page.screenshot(type="jpeg", quality=95))
            if i % args.fps == 0:
                print(f"\r  {i // args.fps} / {int(args.duration)} с", end="", flush=True)
        enc.stdin.close()
        enc.wait()
        browser.close()
    srv.shutdown()
    if args.music and enc.returncode == 0:
        silent = args.out + ".silent.mp4"
        os.replace(args.out, silent)
        code = mux(ffmpeg, silent, args.music, args.out)
        os.remove(silent)
        return code
    print(f"\nГотово: {args.out}")
    return enc.returncode


def mux(ffmpeg: str, video: str, music: str, out: str) -> int:
    """Музыка поверх готового видео: картинка копируется без пережатия."""
    code = subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", video, "-i", music,
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]).returncode
    print(f"\nГотово: {out} (с музыкой)")
    return code


if __name__ == "__main__":
    sys.exit(main())
