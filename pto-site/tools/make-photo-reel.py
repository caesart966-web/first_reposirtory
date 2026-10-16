#!/usr/bin/env python3
"""Фото-рилс: tools/video/photo-reel.html + сценарий tools/video/reels/<имя>.json → MP4.

Музыка — тот же синтез, что у роликов по статьям (tools/make-article-video.py), только на смену
кадра вместо шороха листа идёт «вжух». Длительности считаются в тактах (поле "bars" в сценарии),
поэтому каждая смена кадра попадает в сильную долю.

Запуск:
    FFMPEG=/путь/к/ffmpeg python3 tools/make-photo-reel.py --name na-obekte --out rilс.mp4
    python3 tools/make-photo-reel.py --name na-obekte --frames 2 7.5 30   # контрольные кадры в PNG
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
REELS = TOOLS / "video" / "reels"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def timeline(reel):
    bar = 60 / reel["music"]["bpm"] * 4
    b = reel["bars"]
    scenes = [{"type": "hook" if i == 0 else "photo", "dur": bar * (b["hook"] if i == 0 else b["shot"])}
              for i in range(len(reel["shots"]))]
    scenes.append({"type": "final", "dur": bar * b["final"]})
    return scenes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--name", required=True, help="имя сценария в tools/video/reels без .json")
    ap.add_argument("--out", help="файл ролика")
    ap.add_argument("--frames", type=float, nargs="*", help="снять только эти моменты в PNG (рядом с --out)")
    args = ap.parse_args()
    reel = json.loads((REELS / f"{args.name}.json").read_text(encoding="utf-8"))
    scenes = timeline(reel)
    total = sum(s["dur"] for s in scenes)
    page = f"/tools/video/photo-reel.html?capture&r={args.name}"
    out = args.out or str(ROOT / f"reel-{args.name}.mp4")
    if args.frames is not None:
        return subprocess.run([sys.executable, str(TOOLS / "make-video.py"), "--page", page,
                               "--out", out, "--frames", *map(str, args.frames)]).returncode

    ff = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not ff:
        sys.exit("Не найден ffmpeg: укажите путь в переменной FFMPEG")
    av = load(TOOLS / "make-article-video.py", "make_article_video")
    video = {"music": reel["music"], "scenes": scenes, "cut_fx": "whoosh"}
    mix, _ = av.compose(av.load_music_module(), video, args.name)
    tmp = Path(tempfile.mkdtemp(prefix="xpto-reel-"))
    raw, audio = tmp / "music.wav", tmp / "music-14.wav"
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(av.SR)
        w.writeframes((mix.T * 32767).astype("<i2").tobytes())
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(raw), "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(av.SR), str(audio)], check=True)
    print(f"{args.name}: {total:.1f} с")
    return subprocess.run([sys.executable, str(TOOLS / "make-video.py"), "--page", page,
                           "--duration", f"{total:.2f}", "--music", str(audio), "--out", out],
                          env=os.environ).returncode


if __name__ == "__main__":
    sys.exit(main())
