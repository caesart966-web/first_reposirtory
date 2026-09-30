#!/usr/bin/env python3
"""Шортс X-PTO с озвучкой: голос → хронология → музыка → видео.

1. Каждая фраза озвучивается отдельно нейросетевым синтезатором Piper
   (женский голос «Ирина»), тишина по краям обрезается.
2. По настоящей длине фраз строится хронология и пишется в
   tools/video/short-timeline.js — сцены ролика встают ровно под голос.
3. Сочиняется своя музыка (инструменты из make-music.py, но другая
   тональность и темп) и приглушается там, где звучит голос.
4. tools/make-video.py снимает tools/video/short.html и накладывает звук.

Произношение: синтезатор читает аббревиатуры как слова, поэтому в тексте
для голоса они расписаны по буквам («пэ пэ эр»), а в субтитрах — как
положено («ППР»). Поменяли фразу — меняйте обе колонки.

Нужны: piper-tts (pip install piper-tts) и файл голоса (см. README),
numpy, ffmpeg (переменная FFMPEG или PATH), playwright.

    python3 tools/make-short.py                 # → promo-short.mp4
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
SR = 44100
# Голос — нейросетевой синтезатор Piper, женский голос «Ирина».
# Файл модели (63 МБ) в репозиторий не кладётся — см. README, «Шортс с озвучкой».
PIPER_MODEL = Path(os.environ.get("PIPER_MODEL", TOOLS / "voices" / "ru-irinia-medium.onnx"))
LENGTH_SCALE = "1.05"   # чуть медленнее обычного — спокойнее и певучее
NOISE_SCALE = "0.85"    # живость звучания
NOISE_W = "1.0"         # разброс длительностей — речь не звучит по метроному
START = 0.5      # первая фраза звучит сразу: у шортса полсекунды на то, чтобы зацепить
GAP = 0.45       # пауза между фразами
TAIL = 2.4       # финальный кадр держится после последней фразы

# (что говорит голос, что написано в субтитрах)
# Интонацию синтезатор берёт из знаков препинания: восклицания, многоточие
# и короткие рубленые фразы там, где нужен акцент.
LINES = [
    ("Сдача объекта уже горит... а документации нет?",
     "Сдача объекта уже горит... а документации нет?"),
    ("Знакомьтесь: Икс пэ тэ о! Производственно-технический отдел на аутсорсе.",
     "Знакомьтесь: X-PTO! Производственно-технический отдел на аутсорсе."),
    ("Исполнительная документация, сметы, пэ пэ эр — всё возьмём на себя!",
     "Исполнительная документация, сметы, ППР — всё возьмём на себя!"),
    ("Геодезия, обмеры, защита объёмов в ка эс два.",
     "Геодезия, обмеры, защита объёмов в КС-2."),
    ("Доводим объект до заключения о соответствии. Без возвратов. И без замечаний!",
     "Доводим объект до заключения о соответствии. Без возвратов. И без замечаний!"),
    ("Работаем по всей России: школы, спортивные объекты, аквапарки, аэропорты!",
     "Работаем по всей России: школы, спортивные объекты, аквапарки, аэропорты!"),
    ("И мы — член эс эр о проектировщиков.",
     "И мы — член СРО проектировщиков."),
    ("Оценим объём и стоимость работ всего за один день!",
     "Оценим объём и стоимость работ всего за один день!"),
    ("Оставьте заявку на сайте — ссылка в профиле!",
     "Оставьте заявку на сайте — ссылка в профиле!"),
]

# Мелодика: у этого голоса интонация ровная, и параметры синтезатора её почти
# не раскачивают (замер: разброс тона ~9,7 полутона при любых настройках).
# Поэтому голос раскладывается вокодером WORLD на тон и тембр, движения тона
# растягиваются на 30 % (диапазон ~12–13 полутонов), общий тон — на 0,7 полутона
# выше, светлее. Сильнее — голос становится «мультяшным».
MELODY = 1.3
PITCH_UP = 0.7


def ffmpeg_bin() -> str:
    f = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not f:
        sys.exit("Не найден ffmpeg: укажите путь в переменной FFMPEG")
    return f


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768
        if w.getnchannels() == 2:
            data = data.reshape(-1, 2).mean(axis=1)
    return data


def melodize(path: Path) -> None:
    """Шире движения тона, тембр прежний (WORLD: тон, огибающая, шум — отдельно)."""
    import pyworld as pw
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768
    f0, t = pw.harvest(x, sr, f0_floor=90, f0_ceil=500, frame_period=5)
    f0 = pw.stonemask(x, f0, t, sr)
    sp, ap = pw.cheaptrick(x, f0, t, sr), pw.d4c(x, f0, t, sr)
    v = f0 > 0
    idx = np.arange(len(f0))
    lf = np.interp(idx, idx[v], np.log2(f0[v]))           # тон «через» глухие звуки
    med = np.median(lf[v])
    y = pw.synthesize(np.where(v, 2 ** (med + (lf - med) * MELODY + PITCH_UP / 12), 0),
                      sp, ap, sr, frame_period=5)
    y *= np.max(np.abs(x)) / (np.max(np.abs(y)) + 1e-9)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())


def synth(text: str, out: Path, ff: str) -> np.ndarray:
    raw = out.with_suffix(".raw.wav")
    subprocess.run([sys.executable, "-m", "piper", "-m", str(PIPER_MODEL), "-f", str(raw),
                    "--length-scale", LENGTH_SCALE, "--noise-scale", NOISE_SCALE,
                    "--noise-w-scale", NOISE_W],
                   input=text.encode("utf-8"), check=True, capture_output=True)
    melodize(raw)
    # Тишина по краям — прочь. Тембр: убрать гул и «коробку» (~350 Гц), добавить
    # ясности (~2,8 кГц) и воздуха сверху, пригасить свист (~6,5 кГц); пологий
    # компрессор; плавные края фраз. Эха здесь нет: простое эхо давало металлический
    # призвук — мягкая реверберация добавляется позже, свёрткой.
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(raw), "-af",
                    "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                    "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                    "highpass=f=85,equalizer=f=350:t=q:w=1.2:g=-2.5,equalizer=f=2800:t=q:w=1:g=2,"
                    "equalizer=f=6500:t=q:w=1.5:g=-2,highshelf=f=9000:g=2,"
                    "acompressor=threshold=-20dB:ratio=2:attack=25:release=300:makeup=2,"
                    "afade=t=in:d=0.02,areverse,afade=t=in:d=0.1,areverse",
                    "-ar", str(SR), "-ac", "1", str(out)], check=True)
    return read_wav(out)


def load_music_module():
    spec = importlib.util.spec_from_file_location("make_music", TOOLS / "make-music.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def compose_music(mm, total: float, cuts: list) -> np.ndarray:
    """Своя музыка: ре мажор, 116 ударов в минуту, светлее и подвижнее первой."""
    bpm = 116
    beat = 60 / bpm
    bar = beat * 4
    n = int((total + 3) * SR)
    mm.N = n                                       # инструменты кладут звук в шину этой длины
    chords = [([62, 66, 69, 74], 50),              # D
              ([61, 64, 69, 73], 45),              # A/C#
              ([59, 62, 66, 71], 47),              # Bm
              ([55, 59, 62, 67], 43)]              # G
    pads = np.zeros((2, n)); melo = np.zeros((2, n)); beat_bus = np.zeros((2, n))
    bass = np.zeros((2, n)); fx = np.zeros((2, n))

    t = 0.0
    b = 0
    while t < total:
        notes, _ = chords[b % 4]
        length = min(bar + 1.0, total - t + 2)
        for i, m in enumerate(notes):
            mm.put(pads, mm.pad_note(m, length), t, 0.11, pan=-0.4 + i * 0.27)
        t += bar
        b += 1

    # арпеджио шестнадцатыми через одну — «тикающий» пульс
    pattern = [0, 2, 1, 3, 2, 1, 3, 2]
    k = 0
    t = 0.0
    while t < total - 1.2:
        notes, _ = chords[int(t // bar) % 4]
        mm.put(melo, mm.pluck(notes[pattern[k % 8] % len(notes)] + 12, 0.5), t, 0.075,
               pan=0.5 if k % 2 else -0.5)
        k += 1
        t += beat / 2

    i = 0
    t = 0.0
    while t < total - TAIL:
        if t >= 1.0:
            if i % 2 == 0:                          # мягкий пульс через долю, без хлопков
                mm.put(beat_bus, mm.kick(), t, 0.30)
            mm.put(beat_bus, mm.hat(), t + beat / 2, 0.08, pan=0.3)
            _, root = chords[int(t // bar) % 4]
            mm.put(bass, mm.bass_note(root, beat * 0.9), t, 0.16)
        i += 1
        t += beat

    for c in cuts:                                  # «вжух» на каждом вскрытии сцены
        s, at = mm.whoosh(c)
        mm.put(fx, s, max(0, at), 0.55)
    mm.put(fx, mm.impact(), total - TAIL - 0.2, 0.35)
    mm.put(fx, mm.bell(81, 4), total - TAIL - 0.2, 0.08)

    mix = np.vstack((mm.reverb(pads[0], mix=0.35, seed=11), mm.reverb(pads[1], mix=0.35, seed=12)))
    mix += np.vstack((mm.reverb(melo[0], mix=0.25, seed=13), mm.reverb(melo[1], mix=0.25, seed=14)))
    mix += np.vstack((mm.reverb(fx[0], mix=0.3, seed=15), mm.reverb(fx[1], mix=0.3, seed=16)))
    mix += beat_bus + bass
    return mix[:, : int(total * SR)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "promo-short.mp4"))
    ap.add_argument("--audio-only", action="store_true", help="только звук и хронология, без съёмки кадров")
    args = ap.parse_args()
    ff = ffmpeg_bin()
    if not PIPER_MODEL.exists():
        sys.exit(f"Нет модели голоса {PIPER_MODEL} — как скачать, в README («Шортс с озвучкой»)")

    tmp = Path(tempfile.mkdtemp(prefix="xpto-short-"))
    voices, timeline = [], []
    t = START
    for i, (spoken, shown) in enumerate(LINES):
        v = synth(spoken, tmp / f"l{i}.wav", ff)
        dur = len(v) / SR
        timeline.append({"s": round(t, 3), "e": round(t + dur, 3), "text": shown})
        voices.append((t, v))
        print(f"  {t:5.2f}–{t + dur:5.2f}  {shown}")
        t += dur + GAP
    total = round(timeline[-1]["e"] + TAIL, 2)

    (TOOLS / "video" / "short-timeline.js").write_text(
        "// Сгенерировано tools/make-short.py по длине озвучки. Руками не править.\n"
        f"window.TL = {json.dumps(timeline, ensure_ascii=False, indent=1)};\n", encoding="utf-8")

    # Голос
    n = int(total * SR)
    voice = np.zeros(n)
    for start, v in voices:
        i = int(start * SR)
        voice[i:i + len(v)] += v[: n - i]
    voice *= 0.9 / (np.max(np.abs(voice)) + 1e-9)
    mm = load_music_module()
    voice = mm.reverb(voice, secs=1.1, mix=0.14, seed=21)   # мягкий «зал», без эха

    # Музыка приглушается под голосом: огибающая голоса, сглаженная на 0,25 с
    cuts = [max(0.0, seg["s"] - 0.3) for seg in timeline[1:]]
    music = compose_music(mm, total, cuts)
    music /= np.max(np.abs(music)) + 1e-9
    env = np.convolve(np.abs(voice), np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
    env = np.clip(env / (np.max(env) + 1e-9) * 3, 0, 1)
    duck = 0.5 - 0.35 * env                        # под голосом музыка тише в ~3 раза
    tt = np.arange(n) / SR
    fade = np.clip(tt / 0.3, 0, 1) * np.clip((total - tt) / 1.8, 0, 1)
    mix = music * duck * fade + np.vstack((voice, voice))
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 0.89

    audio = tmp / "short-audio.wav"
    with wave.open(str(audio), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix.T * 32767).astype("<i2").tobytes())
    # Громкость — по стандарту соцсетей (−14 LUFS): громче они всё равно приглушат сами
    normed = tmp / "short-audio-14.wav"
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(audio), "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), str(normed)], check=True)
    audio = normed
    print(f"Звук: {audio} ({total} с)")
    if args.audio_only:
        shutil.copy(audio, Path(args.out).with_suffix(".wav"))
        return 0

    return subprocess.run([sys.executable, str(TOOLS / "make-video.py"),
                           "--page", "/tools/video/short.html?capture",
                           "--duration", str(total), "--music", str(audio), "--out", args.out],
                          env=os.environ).returncode


if __name__ == "__main__":
    sys.exit(main())
