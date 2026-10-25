#!/usr/bin/env python3
"""Рилс «Усадьба Архангельское»: tools/video/arhangelskoe.html → MP4 1080×1920, 60 кадров/с.

Три шага:
1. Отрезки видео (tools/video/reels/arhangelskoe.json) режутся в кадры по 60 в секунду:
   исходники сняты на 30, промежуточные кадры дорисовывает minterpolate — движение ровное.
2. Музыка — своя пьеса в духе классицизма конца XVIII века (D-dur, 120 ударов, такт = 2 с),
   записанная нотами здесь же и сыгранная сэмплами настоящих инструментов из SoundFont
   MuseScore General (MIT): струнные, валторны, флейта, гобой, арфа, литавры, трубы.
   Смены кадров ролика стоят на долях, оркестровый акцент — ровно на 34 с (генподрядчик).
3. Кадры снимает tools/make-video.py, звук нормализуется в −14 LUFS.

Нужны: ffmpeg, fluidsynth и SoundFont (apt install fluidsynth musescore-general-soundfont),
python-пакеты playwright и mido.

    python3 tools/make-arhangelskoe.py --out rils.mp4
    python3 tools/make-arhangelskoe.py --frames 2 6 16 31 35 39 --out kadr.png   # контрольные кадры
    python3 tools/make-arhangelskoe.py --music-only --out music.wav
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
REEL = TOOLS / "video" / "reels" / "arhangelskoe"
CFG = json.loads((TOOLS / "video" / "reels" / "arhangelskoe.json").read_text(encoding="utf-8"))
PAGE = "/tools/video/arhangelskoe.html?capture"
SOUNDFONTS = ["/usr/share/sounds/sf3/MuseScore_General_Full.sf3", "/usr/share/sounds/sf3/MuseScore_General.sf3",
              "/usr/share/sounds/sf2/FluidR3_GM.sf2"]


def ffmpeg_bin():
    ff = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not ff:
        sys.exit("Не найден ffmpeg: укажите путь в переменной FFMPEG")
    return ff


# ---------------------------------------------------------------- кадры клипов
def cut_clips(ff):
    fps = CFG["fps"]
    for c in CFG["clips"]:
        out = REEL / "_frames" / c["name"]
        n = round((c["until"] - c["at"]) * fps)
        stamp = out / "stamp.json"
        key = json.dumps(c, sort_keys=True)
        if stamp.exists() and stamp.read_text() == key and len(list(out.glob("*.jpg"))) >= n:
            continue
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        k = (c["until"] - c["at"]) / (c["to"] - c["from"])
        w, h = c["w"], c["h"]
        vf = (f"setpts=(PTS-STARTPTS)*{k:.5f},"
              f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
              f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},"
              f"unsharp=5:5:0.55:5:5:0,eq=contrast=1.04:saturation=1.06")
        subprocess.run([ff, "-y", "-loglevel", "error", "-ss", f"{c['from']}", "-t", f"{c['to'] - c['from'] + 0.2}",
                        "-i", str(REEL / c["src"]), "-vf", vf, "-frames:v", str(n), "-q:v", "2",
                        str(out / "%04d.jpg")], check=True)
        got = len(list(out.glob("*.jpg")))
        if got < n:
            sys.exit(f"Клип {c['name']}: {got} кадров из {n}")
        stamp.write_text(key)
        print(f"  клип {c['name']}: {n} кадров")


# ---------------------------------------------------------------- музыка
BPM = 120
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(n):
    """'F#5' → номер MIDI."""
    name, octave = n[:-1], int(n[-1])
    v = NOTE[name[0]] + name.count("#") - name.count("b")
    return 12 * (octave + 1) + v


# Гармония: по аккорду на полтакта (2 доли). Такт 1 начинается в 0 с, такт = 2 с.
CHORDS = {
    "D": ["D", "F#", "A"], "G": ["G", "B", "D"], "A": ["A", "C#", "E"], "A7": ["A", "C#", "E", "G"],
    "Em": ["E", "G", "B"], "Em7": ["E", "G", "B", "D"], "Bm": ["B", "D", "F#"], "D/F#": ["F#", "A", "D"],
}
HARM = [  # такты 1–20
    ("D", "D"), ("G", "A7"),                                   # заставка 0–4
    ("D", "D"), ("A7", "D"), ("G", "D"), ("Em", "A7"), ("G", "A7"),   # панорамы и залы 4–14
    ("D", "D"), ("G", "A"), ("Bm", "A7"),                      # стройка 14–20
    ("G", "D"), ("Em7", "A7"), ("D", "G"),                     # выезд 20–26 (офис с 25)
    ("D/F#", "Em"), ("A", "A7"),                               # офис 26–30
    ("G", "A"), ("A", "A7"),                                   # нарастание 30–34
    ("D", "D"), ("Bm", "G"), ("A7", "D"),                      # акцент, генподрядчик, финал 34–40
]

# Мелодия: «нота:доли», r — пауза. Каждая строка — такт (4 доли).
MELODY = [
    "r:4", "r:4",
    "D5:1.5 E5:.5 F#5:1 A5:1",
    "G5:1 E5:1 F#5:1 D5:1",
    "B5:1 G5:.5 B5:.5 A5:1 F#5:1",
    "G5:.5 F#5:.5 E5:.5 B4:.5 C#5:1 E5:1",
    "D5:.5 E5:.5 F#5:.5 G5:.5 A5:.5 B5:.5 C#6:.5 E6:.5",
    "D6:1.5 A5:.5 F#5:1 A5:1",
    "B5:1 G5:1 C#6:1 A5:1",
    "D6:.5 C#6:.5 B5:.5 F#5:.5 G5:1 E5:1",
    "B5:.5 B5:.25 C#6:.25 D6:.5 B5:.5 A5:.5 A5:.25 B5:.25 F#5:1",
    "G5:.5 G5:.25 A5:.25 B5:.5 G5:.5 A5:1 G5:1",
    "F#5:2 G5:1 B5:1",
    "A5:1.5 F#5:.5 G5:1 E5:1",
    "E5:2 C#5:1 E5:1",
    "D5:.5 E5:.5 F#5:.5 G5:.5 A5:.5 B5:.5 C#6:.5 D6:.5",
    "E6:1 D6:.5 C#6:.5 B5:.5 C#6:.5 D6:.5 E6:.5",
    "F#6:1 r:1 A5:1 F#5:1",
    "B5:1.5 A5:.5 G5:1 B5:1",
    "A5:1 G5:.5 E5:.5 D5:3",
]

GM = {"strings": 48, "slow": 49, "cello": 42, "bass": 43, "pizz": 45, "horn": 60, "flute": 73, "oboe": 68,
      "harp": 46, "timp": 47, "trumpet": 56, "violin": 40}


def section(bar):
    """Раздел ролика по номеру такта (с 0)."""
    t = bar * 2
    if t < 4: return "intro"
    if t < 14: return "theme"
    if t < 20: return "works"
    if t < 25: return "field"
    if t < 30: return "office"
    if t < 34: return "build"
    if t < 37: return "accent"
    return "end"


def compose():
    """Список нот (канал, программа, нота, начало в долях, длина в долях, сила) и кривые громкости."""
    notes, cc = [], []
    ch = {"mel": (0, GM["strings"]), "fl": (1, GM["flute"]), "ob": (2, GM["oboe"]), "acc": (3, GM["strings"]),
          "pad": (4, GM["slow"]), "vc": (5, GM["cello"]), "cb": (6, GM["bass"]), "pz": (7, GM["pizz"]),
          "hn": (8, GM["horn"]), "hp": (10, GM["harp"]), "tp": (11, GM["timp"]), "tr": (12, GM["trumpet"])}

    def add(key, n, start, dur, vel):
        c, p = ch[key]
        notes.append((c, p, n if isinstance(n, int) else midi(n), start, dur, max(1, min(127, int(vel)))))

    # мелодия
    beat = 0.0
    for bar, line in enumerate(MELODY):
        pos = bar * 4.0
        sec = section(bar)
        for tok in line.split():
            name, d = tok.split(":")
            d = float(d)
            if name != "r":
                base = {"theme": 84, "works": 92, "field": 94, "office": 80, "build": 98, "accent": 70, "end": 72}.get(sec, 80)
                if bar == 17 and pos == 68:      # удар на 34 с
                    base = 118
                add("mel", name, pos, d * 0.97, base)
                if sec in ("theme", "office", "accent", "end") or bar == 17:
                    add("fl", midi(name) + (12 if sec in ("accent", "end") else 0), pos, d * 0.95, base - 14)
                if sec in ("works", "field", "build"):
                    add("ob", name, pos, d * 0.92, base - 12)
            pos += d
        beat = pos

    def tones(name, low, high):
        out = []
        for nm in CHORDS[name]:
            for o in range(1, 8):
                m = midi(nm + str(o))
                if low <= m <= high:
                    out.append(m)
        return sorted(out)

    for bar, halves in enumerate(HARM):
        sec = section(bar)
        for hi, chord in enumerate(halves):
            s = bar * 4 + hi * 2
            root = CHORDS[chord][0] if chord != "D/F#" else "F#"
            r2 = midi(root + "2"); r2 = r2 if r2 >= midi("C2") else r2 + 12
            if r2 > midi("B2"): r2 -= 12
            mid = tones(chord, midi("F#3"), midi("D5"))[:4]
            if sec == "intro":
                for m in mid: add("pad", m, s, 2.05, 64 + bar * 10)
                add("vc", r2 + 12, s, 2.05, 70); add("cb", r2, s, 2.05, 66)
                add("hn", tones(chord, midi("A3"), midi("A4"))[0], s, 2.05, 58 + bar * 8)
                for i, m in enumerate(tones(chord, midi("D4"), midi("D6"))[:8]):   # арфа поднимается
                    add("hp", m, s + i * 0.25, 2.0 - i * 0.2, 70 + i * 3)
            elif sec in ("theme",):
                add("pz", r2 + 12, s, .5, 84); add("pz", tones(chord, r2 + 12, r2 + 24)[min(2, len(tones(chord, r2 + 12, r2 + 24)) - 1)], s + 1, .5, 72)
                add("cb", r2, s, 1.9, 58)
                al = tones(chord, midi("A3"), midi("A4"))
                pat = [al[0], al[-1], al[1 % len(al)], al[-1]]
                for i in range(4):                       # «альбертиевы басы» восьмыми
                    add("acc", pat[i], s + i * .5, .45, 58)
                for m in mid[:3]: add("pad", m, s, 2.0, 46)
            elif sec in ("works", "field"):
                for i in range(4):                       # пульс восьмыми — движение стройки
                    add("vc", r2 + 12, s + i * .5, .42, 82 if i % 2 == 0 else 70)
                add("cb", r2, s, 1.95, 72)
                for i in range(4):
                    for m in mid[:3]:
                        add("acc", m, s + i * .5, .4, 62 if i % 2 == 0 else 52)
                add("hn", tones(chord, midi("A3"), midi("A4"))[0], s, 2.0, 62)
                if hi == 0 and sec == "works":
                    add("tp", midi("D3") if chord in ("D", "Bm", "G") else midi("A2"), s, .5, 78)
            elif sec == "office":
                for m in mid: add("pad", m, s, 2.05, 66)
                add("vc", r2 + 12, s, 2.0, 70); add("cb", r2, s, 2.0, 62)
                for m in tones(chord, midi("A3"), midi("F#4"))[:2]: add("hn", m, s, 2.0, 64)
                for i, m in enumerate(tones(chord, midi("D4"), midi("A5"))[:4]):
                    add("hp", m, s + i * .5, 1.5, 58)
            elif sec == "build":
                k = (bar - 15) * 2 + hi                  # 0..3 — нарастание
                for i in range(8):                        # тремоло шестнадцатыми
                    for m in mid[:3]:
                        add("acc", m, s + i * .25, .23, 48 + k * 9 + i * 1.2)
                add("cb", midi("A1") if bar == 16 else r2, s, 2.0, 74 + k * 8)
                for i in range(4): add("vc", (midi("A2") if bar == 16 else r2 + 12), s + i * .5, .45, 76 + k * 8)
                for m in tones(chord, midi("A3"), midi("E4"))[:2]: add("hn", m, s, 2.0, 66 + k * 10)
                if bar == 16:                              # раскат литавр к удару
                    for i in range(16): add("tp", midi("A2"), s + i * .125, .12, 50 + k * 14 + i * 2)
            elif sec == "accent":
                if bar == 17 and hi == 0:                  # 34 с: тутти
                    for m in tones("D", midi("D3"), midi("D6")): add("acc", m, s, 1.2, 120)
                    for m in tones("D", midi("A4"), midi("F#6")): add("mel", m, s, 1.2, 122)
                    for m in [midi("D4"), midi("F#4"), midi("A4"), midi("D5")]: add("tr", m, s, 1.0, 112)
                    for m in [midi("D3"), midi("A3"), midi("F#4")]: add("hn", m, s, 1.6, 108)
                    add("tp", midi("D3"), s, 1.0, 124); add("cb", midi("D2"), s, 2.0, 108); add("vc", midi("D3"), s, 2.0, 108)
                    for i, m in enumerate(tones("D", midi("D5"), midi("D7"))[:7]):   # арфа рассыпается вниз
                        add("hp", m, s + 1.0 + (6 - i) * .17, 1.6, 66)
                else:
                    for m in mid: add("pad", m, s, 2.05, 54)
                    add("cb", r2, s, 2.0, 52)
                    for i, m in enumerate(tones(chord, midi("D4"), midi("B5"))[:6]): add("hp", m, s + i * .33, 1.6, 52)
            elif sec == "end":
                last = bar == 19 and hi == 1
                dur = 5.5 if last else 2.05
                for m in mid: add("pad", m, s, dur, 60 if not last else 66)
                add("cb", r2, s, dur, 60); add("vc", r2 + 12, s, dur, 62)
                for m in tones(chord, midi("A3"), midi("F#4"))[:2]: add("hn", m, s, dur, 54)
                hp = tones(chord, midi("D3"), midi("D6"))[:10]
                for i, m in enumerate(hp): add("hp", m, s + i * .12, dur - i * .12, 64)
                if last:
                    add("tp", midi("D3"), s, 1.0, 64)
                    add("fl", midi("D6"), s, 5.0, 56)

    # громкость партий (CC7) и общий нарастающий «вдох» в заставке и перед акцентом (CC11)
    vol = {0: 104, 1: 70, 2: 66, 3: 76, 4: 84, 5: 92, 6: 92, 7: 92, 8: 78, 10: 92, 11: 100, 12: 92}
    for c, v in vol.items():
        cc.append((c, 7, v, 0.0)); cc.append((c, 91, 92, 0.0)); cc.append((c, 93, 30, 0.0))
    for i in range(41):                                     # заставка: из тишины
        for c in (4, 5, 6, 8): cc.append((c, 11, int(50 + 77 * i / 40), i * 0.1))
    for i in range(33):                                     # нарастание 30–34 с
        for c in (3, 5, 6, 8): cc.append((c, 11, int(80 + 47 * i / 32), 60 + i * 0.25))
    for c in (3, 4, 5, 6, 8): cc.append((c, 11, 100, 70.0))
    return notes, cc


def write_midi(path):
    import mido
    notes, cc = compose()
    tpb = 480
    ev = []
    progs = {}
    for c, p, n, s, d, v in notes:
        progs[c] = p
        ev.append((s, 1, mido.Message("note_on", channel=c, note=n, velocity=v)))
        ev.append((s + d, 0, mido.Message("note_off", channel=c, note=n, velocity=0)))
    for c, num, val, s in cc:
        ev.append((s, -1, mido.Message("control_change", channel=c, control=num, value=val)))
    head = [mido.MetaMessage("set_tempo", tempo=int(60_000_000 / BPM), time=0)]
    for c, p in sorted(progs.items()):
        head.append(mido.Message("program_change", channel=c, program=p, time=0))
    ev.sort(key=lambda e: (e[0], e[1]))
    tr = mido.MidiTrack(head)
    last = 0
    for s, _, m in ev:
        tick = int(round(s * tpb))
        m.time = tick - last
        last = tick
        tr.append(m)
    mf = mido.MidiFile(ticks_per_beat=tpb)
    mf.tracks.append(tr)
    mf.save(path)


def render_music(ff, out):
    fs = shutil.which("fluidsynth")
    sf = next((s for s in SOUNDFONTS if Path(s).exists()), None)
    if not fs or not sf:
        sys.exit("Нужны fluidsynth и SoundFont: apt install fluidsynth musescore-general-soundfont")
    tmp = Path(tempfile.mkdtemp(prefix="xpto-arh-"))
    mid, raw = tmp / "music.mid", tmp / "raw.wav"
    write_midi(mid)
    subprocess.run([fs, "-ni", "-q", "-g", "0.55", "-r", "48000", "-o", "synth.reverb.room-size=0.78",
                    "-o", "synth.reverb.damp=0.35", "-o", "synth.reverb.width=0.9", "-o", "synth.reverb.level=0.62",
                    "-o", "synth.chorus.active=0", "-F", str(raw), sf, str(mid)], check=True, stdout=subprocess.DEVNULL)
    dur = CFG["duration"]
    shaped = tmp / "shaped.wav"
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(raw), "-af",
                    f"atrim=0:{dur},afade=t=out:st={dur - 1.2}:d=1.2,"
                    "equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=9000:t=h:w=4000:g=2", str(shaped)], check=True)
    # громкость — одним множителем на весь трек (−14 LUFS), а не следящим loudnorm:
    # он выравнивал динамику, и оркестровый удар на 34 с тонул
    log = subprocess.run([ff, "-hide_banner", "-i", str(shaped), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    lufs = float([l for l in log.splitlines() if l.strip().startswith("I:")][-1].split()[1])
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(shaped), "-af",
                    f"volume={-14 - lufs:.2f}dB,alimiter=limit=0.84:attack=3:release=60:level=disabled",
                    "-ar", "48000", str(out)], check=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "rils-arhangelskoe.mp4"))
    ap.add_argument("--frames", type=float, nargs="*", help="только контрольные кадры (секунды) в PNG")
    ap.add_argument("--music-only", action="store_true", help="только музыка в WAV (--out)")
    args = ap.parse_args()
    ff = ffmpeg_bin()
    if args.music_only:
        render_music(ff, args.out)
        print(f"Музыка: {args.out}")
        return 0
    cut_clips(ff)
    if args.frames is not None:
        return subprocess.run([sys.executable, str(TOOLS / "make-video.py"), "--page", PAGE, "--out", args.out,
                               "--frames", *map(str, args.frames)]).returncode
    music = Path(tempfile.mkdtemp(prefix="xpto-arh-")) / "music.wav"
    render_music(ff, music)
    return subprocess.run([sys.executable, str(TOOLS / "make-video.py"), "--page", PAGE, "--fps", str(CFG["fps"]),
                           "--duration", str(CFG["duration"]), "--music", str(music), "--out", args.out]).returncode


if __name__ == "__main__":
    sys.exit(main())
