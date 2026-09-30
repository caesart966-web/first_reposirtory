#!/usr/bin/env python3
"""Музыка к промо-ролику X-PTO — сочиняется программой, а не берётся готовой.

Зачем так: чужой трек в ролике — повод для блокировки за авторские права
в любой соцсети, а бесплатные библиотеки из среды сборки недоступны.
Здесь каждый звук синтезирован с нуля, поэтому музыка принадлежит
владельцу ролика целиком.

Трек привязан к хронологии tools/video/promo.html: удар на логотипе,
«вжух» на каждой смене сцены (там же, где по кадру проходит световая
линия), затишье перед финалом и акцент на призыве. Меняете время сцен
в ролике — поправьте TRANSITIONS и разделы ниже.

Запуск (нужен numpy):
    python3 tools/make-music.py                 # → promo-music.wav
    python3 tools/make-music.py --out music.wav
Склейка с видео — tools/make-video.py --music promo-music.wav
"""
import argparse
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SR = 44100
DUR = 58.0
BPM = 100
BEAT = 60 / BPM
BAR = BEAT * 4
N = int(SR * (DUR + 3))        # запас на хвосты реверберации, потом обрезаем

# Смены сцен — моменты, когда по кадру проходит световая линия (--at в promo.html + ~0.4 с)
TRANSITIONS = [4.4, 10.6, 16.6, 23.6, 29.2, 40.4, 46.6, 52.2]

# Гармония: ля минор с подъёмом — Am, F, C, G (по такту на аккорд)
CHORDS = [
    ([57, 60, 64, 69, 71], 45),   # Am(add9)
    ([53, 57, 60, 65, 67], 41),   # F(add9)
    ([55, 60, 64, 67, 72], 48),   # C
    ([55, 59, 62, 67, 74], 43),   # G
]

rng = np.random.default_rng(7)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lowpass(x, cut, order=2):
    """Мягкий фильтр в частотной области — для статичных тембров."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / cut) ** (2 * order))
    return np.fft.irfft(X, len(x))


def bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 4)) * (1 / np.sqrt(1 + (f / hi) ** 4))
    return np.fft.irfft(X, len(x))


def put(bus, sig, t, gain=1.0, pan=0.0):
    """Кладёт моно-звук в стереошину с панорамой (-1 левый … 1 правый)."""
    i = int(t * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    bus[0, i:i + len(sig)] += sig * gain * l * 1.414
    bus[1, i:i + len(sig)] += sig * gain * r * 1.414


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na) ** 2 if na else 1
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e


# ---------- инструменты ----------------------------------------------------

def pad_note(m, length):
    n = int(length * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for det in (-0.07, 0.0, 0.07):                  # три голоса с расстройкой — «хор»
        f = hz(m + det)
        for k in range(1, 10):
            s += np.sin(2 * np.pi * f * k * t + rng.uniform(0, 6.28)) / k ** 1.2
    return s * env_adsr(n, 0.9, 1.2) / 12


def pluck(m, length=0.9):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t * (5 + 4 * k)) / k ** 1.3 for k in range(1, 7))
    return s * np.minimum(1, t / 0.004)


def bell(m, length=3.5):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = hz(m)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 1.3)
         + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 2.6)
         + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 4.5))
    return s * np.minimum(1, t / 0.003)


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    freq = 44 + 90 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(freq) / SR
    return np.sin(ph) * np.exp(-t * 7) + 0.15 * rng.standard_normal(n) * np.exp(-t * 400)


def clap():
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    noise = bandpass(rng.standard_normal(n), 900, 3500)
    e = np.exp(-t * 18) + 0.6 * sum(np.exp(-np.maximum(0, t - d) * 90) * (t >= d) for d in (0.0, 0.011, 0.022))
    return noise * e * 0.5


def hat(open_=False):
    n = int((0.25 if open_ else 0.07) * SR)
    t = np.arange(n) / SR
    s = bandpass(rng.standard_normal(n), 7000, 16000)
    return s * np.exp(-t * (14 if open_ else 60))


def bass_note(m, length):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    return np.tanh(1.6 * s) * np.exp(-t * 3) * np.minimum(1, t / 0.006)


def whoosh(peak):
    """Шипящий нарастающий «вжух», пик ровно в момент смены сцены."""
    pre, post = 1.1, 0.5
    n = int((pre + post) * SR)
    t = np.arange(n) / SR - pre
    s = bandpass(rng.standard_normal(n), 400, 7000)
    e = np.where(t < 0, np.exp(t * 4.5), np.exp(-t * 9))
    return s * e * 0.35, peak - pre


def impact():
    n = int(2.5 * SR)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (38 + 40 * np.exp(-t * 6)) * t) * np.exp(-t * 2.2)
    air = lowpass(rng.standard_normal(n), 1800) * np.exp(-t * 5) * 0.4
    return boom + air


def reverb(x, secs=2.6, mix=0.28, seed=1):
    """Реверберация свёрткой с затухающим шумом — у каждого канала свой."""
    r = np.random.default_rng(seed)
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-t * 3.2)
    ir = lowpass(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + n
    size = 1 << (L - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return x * (1 - mix) + wet * mix


# ---------- аранжировка ----------------------------------------------------

def section(t):
    """Сколько всего играет в момент t: 0 — тихо, 1 — полностью."""
    if t < 4.6:
        return "intro"
    if t < 16.6:
        return "build"
    if t < 40.4:
        return "full"
    if t < 46.6:
        return "break"
    if t < 52.2:
        return "full"
    return "final"


def compose():
    pads = np.zeros((2, N))
    beat = np.zeros((2, N))
    melo = np.zeros((2, N))
    fx = np.zeros((2, N))
    bass = np.zeros((2, N))
    kick_env = np.zeros(N)

    # Подложка: аккорд на такт, с перекрытием на отпускание
    nbars = int(DUR / BAR) + 2
    for b in range(nbars):
        t0 = b * BAR
        notes, root = CHORDS[b % 4]
        if t0 > 55.2:
            break
        length = BAR + 1.2
        if t0 + BAR > 52.2:               # финал: последний аккорд тянется до конца
            notes, root = CHORDS[0]
            length = DUR - t0 + 2.5
        for i, m in enumerate(notes):
            put(pads, pad_note(m, length), t0, 0.16, pan=(-0.5 + i * 0.25))
        if t0 + BAR > 52.2:
            break

    # Арпеджио: восьмые по звукам аккорда, со второй сцены
    step = BEAT / 2
    pattern = [0, 2, 3, 4, 3, 2, 1, 2]
    k = 0
    t = 4.6
    while t < 55.5:
        sec = section(t)
        notes, _ = CHORDS[int(t // BAR) % 4]
        m = notes[pattern[k % 8]] + 12
        g = {"build": 0.10, "full": 0.12, "break": 0.13, "final": 0.08}.get(sec, 0)
        if sec == "final" and t > 55:
            g = 0
        if g:
            put(melo, pluck(m), t, g, pan=0.45 if k % 2 else -0.45)
        k += 1
        t += step

    # Ударные и бас
    nbeats = int(DUR / BEAT)
    for i in range(nbeats):
        t = i * BEAT
        sec = section(t)
        if sec == "build" and t >= 10.8:                  # мягкий пульс: удар на первую и третью долю
            if i % 2 == 0:
                put(beat, kick(), t, 0.55)
                kick_env[int(t * SR): int(t * SR) + int(0.3 * SR)] += np.exp(-np.arange(int(0.3 * SR)) / SR * 12)[: N - int(t * SR)]
            put(beat, hat(), t + BEAT / 2, 0.10, pan=0.3)
        elif sec == "full":
            put(beat, kick(), t, 0.58)
            idx = int(t * SR)
            seg = np.exp(-np.arange(int(0.3 * SR)) / SR * 12)
            kick_env[idx: idx + len(seg)] += seg[: N - idx]
            if i % 4 in (1, 3):
                put(beat, clap(), t, 0.45, pan=0.05)
            put(beat, hat(), t + BEAT / 2, 0.16, pan=0.3)
            put(beat, hat(), t + BEAT / 4 * 3, 0.06, pan=-0.3)
            if i % 8 == 7:
                put(beat, hat(True), t + BEAT / 2, 0.10, pan=0.35)
        if sec in ("full",) or (sec == "build" and t >= 10.8):
            _, root = CHORDS[int(t // BAR) % 4]
            for half in (0, 1):
                put(bass, bass_note(root, BEAT / 2 * 0.95), t + half * BEAT / 2,
                    0.24 if sec == "full" else 0.16)

    # Звуки-акценты
    put(fx, impact(), 0.15, 0.55)
    for m, at in ((81, 0.65), (88, 1.0), (84, 1.45)):        # колокольчики на лучах знака
        put(fx, bell(m), at, 0.12, pan=(at - 1) * 0.8)
    for tr in TRANSITIONS:
        s, at = whoosh(tr)
        put(fx, s, at, 1.0)
    put(fx, impact(), 52.4, 0.5)
    put(fx, bell(81, 5), 52.4, 0.10)
    put(fx, bell(76, 5), 52.45, 0.08, pan=0.4)
    # Затишье перед финалом: тихий подъём к возвращению ритма
    n = int(2.0 * SR)
    tt = np.arange(n) / SR
    riser = bandpass(rng.standard_normal(n), 1200, 9000) * (tt / 2.0) ** 3 * 0.30
    put(fx, riser, 44.6)

    # «Дыхание» подложки и баса под бочку
    duck = 1 - 0.45 * np.clip(kick_env, 0, 1)
    pads *= duck
    bass *= duck

    mix = (reverb(pads[0], mix=0.35, seed=1), reverb(pads[1], mix=0.35, seed=2))
    mix = np.vstack(mix)
    mix += np.vstack((reverb(melo[0], mix=0.3, seed=3), reverb(melo[1], mix=0.3, seed=4)))
    mix += np.vstack((reverb(fx[0], mix=0.3, seed=5), reverb(fx[1], mix=0.3, seed=6)))
    mix += beat + bass

    # Общая громкость: плавное начало, затухание к концу ролика
    t = np.arange(N) / SR
    master = np.clip(t / 0.08, 0, 1) * np.where(t > DUR - 3.5, np.clip((DUR - t) / 3.5, 0, 1) ** 1.5, 1)
    mix *= master
    mix = mix[:, : int(DUR * SR)]
    mix /= np.max(np.abs(mix)) + 1e-9
    mix = np.tanh(mix * 1.4) / np.tanh(1.4) * 0.89        # мягкий ограничитель, пик ~ −1 дБ
    return mix


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "promo-music.wav"))
    args = ap.parse_args()
    mix = compose()
    data = (mix.T * 32767).astype("<i2").tobytes()
    with wave.open(args.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)
    print(f"Готово: {args.out} ({DUR:.0f} с)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
