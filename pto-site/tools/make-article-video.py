#!/usr/bin/env python3
"""Ролик по статье: tools/video/article-ks.html + своя спокойная музыка → MP4.

Голоса нет — всё сказано текстом на экране. Музыка тише и медленнее, чем в промо:
ролик читают, и ритм не должен подгонять. Шорох листа попадает ровно в смену
сцены, скрип ручки — в зачёркивание строк акта, глухой удар — в печать.

Длительности сцен берутся из массива DUR в самой странице, чтобы звук
и картинка не разошлись после правки одной из них.

Запуск:
    FFMPEG=/путь/к/ffmpeg python3 tools/make-article-video.py --out ~/rolik-ks.mp4
    python3 tools/make-article-video.py --audio-only      # только звук, WAV
"""
import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
PAGE = TOOLS / "video" / "article-ks.html"
SR = 44100


def load_music_module():
    spec = importlib.util.spec_from_file_location("make_music", TOOLS / "make-music.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scene_times():
    m = re.search(r"var DUR = \[([^\]]+)\]", PAGE.read_text(encoding="utf-8"))
    dur = [float(x) for x in m.group(1).split(",")]
    starts = [sum(dur[:i]) for i in range(len(dur))]
    return starts, sum(dur)


def scratch(mm, length=0.48):
    """Скрип ручки по бумаге: узкая полоса шума с мелкой неровностью нажима."""
    n = int(length * SR)
    t = np.arange(n) / SR
    s = mm.bandpass(np.random.default_rng(5).standard_normal(n), 2500, 7500)
    grain = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 23 * t + 3 * np.sin(2 * np.pi * 5 * t)))
    return s * grain * np.minimum(1, t / 0.03) * np.minimum(1, (length - t) / 0.06) * 0.5


def paper(mm):
    """Шорох листа: короткий мягкий шум, высокие частоты."""
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    s = mm.bandpass(np.random.default_rng(9).standard_normal(n), 1500, 11000)
    return s * np.minimum(1, t / 0.12) * np.exp(-np.maximum(0, t - 0.12) * 7) * 0.5


def thump(mm):
    """Печать: глухой удар и щелчок."""
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (70 + 60 * np.exp(-t * 30)) * t) * np.exp(-t * 14)
    click = mm.bandpass(np.random.default_rng(3).standard_normal(n), 1500, 6000) * np.exp(-t * 120) * 0.5
    return body + click


def compose(mm, total, starts):
    """Фа мажор, 84 удара в минуту: пэд, тихое арпеджио, мягкий пульс."""
    bpm = 84
    beat = 60 / bpm
    bar = beat * 4
    n = int((total + 3) * SR)
    mm.N = n
    chords = [([65, 69, 72, 77], 41),      # F
              ([62, 65, 69, 74], 38),      # Dm
              ([58, 62, 65, 70], 46),      # Bb
              ([60, 64, 67, 72], 36)]      # C
    pads, melo, pulse, bass, fx = (np.zeros((2, n)) for _ in range(5))

    t, b = 0.0, 0
    while t < total:
        notes, _ = chords[b % 4]
        for i, m in enumerate(notes):
            mm.put(pads, mm.pad_note(m, min(bar + 1.2, total - t + 2)), t, 0.10, pan=-0.35 + i * 0.23)
        t += bar
        b += 1

    pattern = [0, 2, 1, 3, 2, 3, 1, 2]
    k, t = 0, 1.0
    while t < total - 1.5:
        notes, _ = chords[int(t // bar) % 4]
        mm.put(melo, mm.pluck(notes[pattern[k % 8]] + 12, 0.8), t, 0.06, pan=0.45 if k % 2 else -0.45)
        k += 1
        t += beat / 2

    i, t = 0, bar                                   # пульс с второго такта, без хлопков
    while t < total - 2.0:
        if i % 2 == 0:
            mm.put(pulse, mm.kick(), t, 0.22)
        mm.put(pulse, mm.hat(), t + beat / 2, 0.05, pan=0.3)
        _, root = chords[int(t // bar) % 4]
        mm.put(bass, mm.bass_note(root, beat * 0.95), t, 0.13)
        i += 1
        t += beat

    for s in starts[1:]:                            # шорох листа на каждой смене
        mm.put(fx, paper(mm), s - 0.2, 0.55, pan=0.2)
    for at in (1.1, 1.772, 2.444):                  # ручка зачёркивает строки акта (сцена 1)
        mm.put(fx, scratch(mm), at, 0.45, pan=-0.2)
    mm.put(fx, thump(mm), 3.3 + 0.12, 0.5)          # «срезано»
    mm.put(fx, thump(mm), starts[-1] + 2.2 + 0.12, 0.5)   # печать в финале
    mm.put(fx, mm.bell(77, 4), starts[-1] + 0.4, 0.07)

    mix = np.vstack((mm.reverb(pads[0], mix=0.35, seed=31), mm.reverb(pads[1], mix=0.35, seed=32)))
    mix += np.vstack((mm.reverb(melo[0], mix=0.3, seed=33), mm.reverb(melo[1], mix=0.3, seed=34)))
    mix += np.vstack((mm.reverb(fx[0], mix=0.15, seed=35), mm.reverb(fx[1], mix=0.15, seed=36)))
    mix += pulse + bass
    mix = mix[:, : int(total * SR)]
    tt = np.arange(mix.shape[1]) / SR
    mix *= np.clip(tt / 0.4, 0, 1) * np.clip((total - tt) / 2.0, 0, 1)
    return mix / (np.max(np.abs(mix)) + 1e-9) * 0.89


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "article-ks.mp4"))
    ap.add_argument("--audio-only", action="store_true")
    args = ap.parse_args()
    ff = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not ff:
        sys.exit("Не найден ffmpeg: укажите путь в переменной FFMPEG")

    starts, total = scene_times()
    mix = compose(load_music_module(), total, starts)
    tmp = Path(tempfile.mkdtemp(prefix="xpto-article-"))
    raw = tmp / "music.wav"
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix.T * 32767).astype("<i2").tobytes())
    audio = tmp / "music-14.wav"                    # громкость по стандарту соцсетей
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(raw), "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), str(audio)], check=True)
    print(f"Звук: {audio} ({total:.1f} с)")
    if args.audio_only:
        shutil.copy(audio, Path(args.out).with_suffix(".wav"))
        return 0
    return subprocess.run([sys.executable, str(TOOLS / "make-video.py"),
                           "--page", "/tools/video/article-ks.html?capture",
                           "--duration", f"{total:.2f}", "--music", str(audio), "--out", args.out],
                          env=os.environ).returncode


if __name__ == "__main__":
    sys.exit(main())
