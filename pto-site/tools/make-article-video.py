#!/usr/bin/env python3
"""Ролики по статьям: tools/video/article.html + сцены из tools/video/articles/<адрес>.json → MP4.

Голоса нет — всё сказано текстом на экране. Музыка у каждого ролика своя: тональность
и темп записаны в том же JSON, что и сцены («music»: {"bpm": …, "prog": ["F", "Dm", …]}).
Звук собирается по длительностям сцен из этого файла, поэтому шорох листа попадает
ровно в смену сцены, а скрип ручки, удар печати и щелчки — в анимацию первой сцены.

Аранжировка: пэд, который «дышит» в такт бочке, электропиано с мелодией
(фраза A A B A, по аккордам), арпеджио, бас, мягкий бит; в сцене-цитате бит
уходит, перед финалом — нарастающий шум и удар. Всё синтезируется здесь,
чужих сэмплов нет (авторские права).

Запуск:
    FFMPEG=/путь/к/ffmpeg python3 tools/make-article-video.py --all --out-dir ~/rolik
    python3 tools/make-article-video.py --slug proverka-smety --out rolik.mp4
    python3 tools/make-article-video.py --slug proverka-smety --audio-only
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

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
SCENES = TOOLS / "video" / "articles"
SR = 44100

NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def chord(name):
    """«F#m» → (ноты аккорда в среднем регистре, бас)."""
    root = NOTE[name[0]] + (1 if "#" in name else -1 if "b" in name[1:2] else 0)
    minor = name.endswith("m")
    base = 57 + (root - 9) % 12                          # от ля малой до соль-диез первой
    third = 3 if minor else 4
    return [base, base + third, base + 7, base + 12, base + 14], 36 + (root % 12)


def load_music_module():
    spec = importlib.util.spec_from_file_location("make_music", TOOLS / "make-music.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def keys(mm, m, length=1.6):
    """Электропиано: обертоны гаснут быстрее основного тона, лёгкое тремоло."""
    n = int(length * SR)
    t = np.arange(n) / SR
    f = mm.hz(m)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2)
         + .45 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 3.6)
         + .18 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 5.5)
         + .07 * np.sin(2 * np.pi * 4.02 * f * t) * np.exp(-t * 9))
    s *= 1 + .06 * np.sin(2 * np.pi * 5.2 * t)
    return s * np.minimum(1, t / .005) * np.minimum(1, (length - t) / .08)


def noise(seed, n):
    return np.random.default_rng(seed).standard_normal(n)


def paper(mm, seed=9):
    n = int(.7 * SR)
    t = np.arange(n) / SR
    s = mm.bandpass(noise(seed, n), 1500, 11000)
    return s * np.minimum(1, t / .12) * np.exp(-np.maximum(0, t - .12) * 7) * .5


def scratch(mm, length=.48):
    n = int(length * SR)
    t = np.arange(n) / SR
    s = mm.bandpass(noise(5, n), 2500, 7500)
    grain = .6 + .4 * np.abs(np.sin(2 * np.pi * 23 * t + 3 * np.sin(2 * np.pi * 5 * t)))
    return s * grain * np.minimum(1, t / .03) * np.minimum(1, (length - t) / .06) * .5


def thump(mm):
    n = int(.5 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (70 + 60 * np.exp(-t * 30)) * t) * np.exp(-t * 14)
    return body + mm.bandpass(noise(3, n), 1500, 6000) * np.exp(-t * 120) * .5


def riser(mm, length=2.2):
    n = int(length * SR)
    t = np.arange(n) / SR
    s = mm.bandpass(noise(17, n), 600, 9000)
    return s * (t / length) ** 2.2 * .5


# Звуки к анимации первой сцены — время от начала ролика (сцена 1 начинается с нуля)
def hook_fx(mm, visual, put):
    if visual == "act":
        for at in (1.1, 1.772, 2.444):
            put(scratch(mm), at, .45)
        put(thump(mm), 3.42, .5)
    elif visual == "stamp":
        put(thump(mm), 2.05, .75)
    elif visual == "estimate":
        put(thump(mm), 3.42, .5)
    elif visual == "docs":
        for i in range(6):
            put(paper(mm, 40 + i), .4 + i * .42 + .25, .35)
    elif visual == "survey":
        for at in (1.6, 2.2, 2.8, 3.3):
            put(mm.pluck(88, .5), at + .1, .12)
    elif visual == "crane":
        put(thump(mm), 3.6, .3)


def compose(mm, video, slug):
    music = video["music"]
    bpm = music["bpm"]
    beat = 60 / bpm
    bar = beat * 4
    chords = [chord(c) for c in music["prog"]]
    durs = [s["dur"] for s in video["scenes"]]
    starts = [sum(durs[:i]) for i in range(len(durs))]
    total = sum(durs)
    n = int((total + 3) * SR)
    mm.N = n
    rng = np.random.default_rng(sum(map(ord, slug)))   # у каждой статьи своя мелодия, но одна и та же при каждой сборке

    quote = [(starts[i], starts[i] + durs[i]) for i, s in enumerate(video["scenes"]) if s["type"] == "quote"]
    final_at = starts[-1]

    def drums_on(t):
        return t >= starts[1] - beat and not any(a <= t < b for a, b in quote)

    pads, ep, arp, beat_bus, bass, fx = (np.zeros((2, n)) for _ in range(6))

    def put(bus):
        return lambda sig, t, g=1.0, pan=0.0: mm.put(bus, sig, t, g, pan)

    # пэд по аккорду на такт
    t, b = 0.0, 0
    while t < total:
        notes, _ = chords[b % 4]
        for i, m in enumerate(notes[:4]):
            mm.put(pads, mm.pad_note(m, min(bar + 1.2, total - t + 2)), t, .095, pan=-.4 + i * .27)
        t += bar
        b += 1

    # «дыхание» пэда в такт бочке — то самое современное качание
    tt = np.arange(n) / SR
    since = (tt % beat)
    pump = 1 - .38 * np.exp(-since * 9)
    on = np.zeros(n, bool)                        # где играет бит (по 10 мс)
    for i in range(0, n, 441):
        on[i:i + 441] = drums_on(i / SR)
    pads *= np.where(on, pump, 1.0)

    # арпеджио восьмыми, тихо, по всей длине
    pattern = [0, 2, 1, 3, 2, 4, 1, 3]
    k, t = 0, .5
    while t < total - 1.5:
        notes, _ = chords[int(t // bar) % 4]
        mm.put(arp, mm.pluck(notes[pattern[k % 8]] + 12, .6), t, .045, pan=.5 if k % 2 else -.5)
        k += 1
        t += beat / 2

    # мелодия электропиано: фразы по два такта, порядок A A B A
    rhythms = [[0, 1, 1.5, 2.5, 3, 4, 5.5, 6],        # позиции в долях внутри двух тактов
               [0, .5, 1, 2, 3.5, 4, 4.5, 6],
               [0, 1.5, 2, 3, 4, 5, 5.5, 6.5]]
    def phrase(seed):
        r = np.random.default_rng(seed)
        rh = rhythms[r.integers(len(rhythms))]
        idx, out = int(r.integers(1, 4)), []
        for p in rh:
            out.append((p, idx))
            idx = int(np.clip(idx + r.choice([-1, 1, 1, -2, 2]), 0, 4))
        return out
    A, B = phrase(rng.integers(1 << 30)), phrase(rng.integers(1 << 30))
    t0 = starts[1]
    t0 = np.ceil(t0 / (2 * bar)) * 2 * bar             # мелодия входит с начала фразы
    ph = 0
    while t0 < total - 2 * bar:
        P = [A, A, B, A][ph % 4]
        if not any(a <= t0 < b for a, b in quote):
            for pos, idx in P:
                at = t0 + pos * beat
                notes, _ = chords[int(at // bar) % 4]
                mm.put(ep, keys(mm, notes[idx] + 12, 1.4), at, .16, pan=.15)
        t0 += 2 * bar
        ph += 1

    # бит и бас
    i, t = 0, 0.0
    while t < total - 1.6:
        if drums_on(t):
            pos = i % 4
            if pos in (0, 2):
                mm.put(beat_bus, mm.kick(), t, .3)
            if pos in (1, 3):
                mm.put(beat_bus, mm.clap(), t, .11, pan=.1)
            mm.put(beat_bus, mm.hat(), t + beat / 2, .05 + .02 * (pos % 2), pan=.3)
            if pos == 3:
                mm.put(beat_bus, mm.hat(True), t + beat / 2, .04, pan=-.3)
            _, root = chords[int(t // bar) % 4]
            if pos in (0, 2):
                mm.put(bass, mm.bass_note(root, beat * 1.4), t, .15)
            if pos == 3:
                mm.put(bass, mm.bass_note(root + 12, beat * .4), t + beat / 2, .08)
        i += 1
        t += beat

    # звуки
    for s in starts[1:]:
        mm.put(fx, paper(mm), s - .2, .5, pan=.2)
        mm.put(fx, mm.bell(chords[0][0][2] + 24, 2.5), s + .05, .035, pan=-.3)
    hook_fx(mm, video["scenes"][0].get("visual"), put(fx))
    mm.put(fx, riser(mm), final_at - 2.2, .5)
    mm.put(fx, mm.impact(), final_at, .35)
    mm.put(fx, thump(mm), final_at + 2.2 + .12, .35)
    mm.put(fx, mm.bell(chords[0][0][0] + 24, 4), final_at + .3, .07)

    mix = np.vstack((mm.reverb(pads[0], mix=.35, seed=31), mm.reverb(pads[1], mix=.35, seed=32)))
    mix += np.vstack((mm.reverb(ep[0], mix=.3, seed=33), mm.reverb(ep[1], mix=.3, seed=34)))
    mix += np.vstack((mm.reverb(arp[0], mix=.3, seed=37), mm.reverb(arp[1], mix=.3, seed=38)))
    mix += np.vstack((mm.reverb(fx[0], mix=.15, seed=35), mm.reverb(fx[1], mix=.15, seed=36)))
    mix += beat_bus + bass
    mix = mix[:, : int(total * SR)]
    tt = np.arange(mix.shape[1]) / SR
    mix *= np.clip(tt / .4, 0, 1) * np.clip((total - tt) / 2.0, 0, 1)
    return mix / (np.max(np.abs(mix)) + 1e-9) * .89, total


def render(slug, out, ff, audio_only=False):
    video = json.loads((SCENES / f"{slug}.json").read_text(encoding="utf-8"))
    mix, total = compose(load_music_module(), video, slug)
    tmp = Path(tempfile.mkdtemp(prefix="xpto-article-"))
    raw = tmp / "music.wav"
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix.T * 32767).astype("<i2").tobytes())
    audio = tmp / "music-14.wav"                        # громкость по стандарту соцсетей
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(raw), "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), str(audio)], check=True)
    print(f"{slug}: звук {total:.1f} с")
    if audio_only:
        shutil.copy(audio, Path(out).with_suffix(".wav"))
        return 0
    return subprocess.run([sys.executable, str(TOOLS / "make-video.py"),
                           "--page", f"/tools/video/article.html?capture&a={slug}",
                           "--duration", f"{total:.2f}", "--music", str(audio), "--out", str(out)],
                          env=os.environ).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", help="адрес статьи (имя файла в tools/video/articles без .json)")
    ap.add_argument("--all", action="store_true", help="все ролики подряд")
    ap.add_argument("--out", help="файл ролика (для одного --slug)")
    ap.add_argument("--out-dir", default=str(ROOT), help="папка для роликов при --all")
    ap.add_argument("--audio-only", action="store_true")
    args = ap.parse_args()
    ff = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not ff:
        sys.exit("Не найден ffmpeg: укажите путь в переменной FFMPEG")
    slugs = sorted(p.stem for p in SCENES.glob("*.json")) if args.all else [args.slug]
    if not slugs or not slugs[0]:
        sys.exit("Укажите --slug или --all")
    code = 0
    for slug in slugs:
        out = args.out if (args.out and not args.all) else Path(args.out_dir) / f"rolik-{slug}.mp4"
        code |= render(slug, out, ff, args.audio_only)
    return code


if __name__ == "__main__":
    sys.exit(main())
