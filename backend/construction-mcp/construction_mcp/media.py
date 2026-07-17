"""Низкоуровневая работа с видео: извлечение кадров, ASR, OCR.

Стратегия MVP: если внешний инструмент доступен (ffmpeg, ASR/OCR-провайдер) —
используем его; иначе возвращаем корректную «пустую» структуру с флагом
`available: False`, чтобы пайплайн деградировал, а не падал. Точки расширения
на прод описаны в README (Whisper/облачный ASR, Tesseract/облачный OCR,
py360convert для разворота 360°).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import config

FFMPEG = shutil.which("ffmpeg")


def ffmpeg_available() -> bool:
    return FFMPEG is not None


def extract_frames(video_path: str, *, fps: float = 1.0, scene_change: bool = False,
                   out_dir: str | None = None) -> dict:
    """Извлекает кадры из видео. Возвращает {available, frames:[{timestamp_ms,image_uri,quality_flags}], note}."""
    video_path = str(video_path)
    if not Path(video_path).exists():
        return {"available": False, "frames": [], "note": f"file not found: {video_path}"}
    if not FFMPEG:
        return {"available": False, "frames": [],
                "note": "ffmpeg не установлен; кадры не извлечены (см. README: установка ffmpeg)"}

    out = Path(out_dir) if out_dir else (config.STORAGE_DIR / "frames" / Path(video_path).stem)
    out.mkdir(parents=True, exist_ok=True)
    vf = f"select='gt(scene,0.4)',showinfo" if scene_change else f"fps={fps}"
    pattern = str(out / "frame_%05d.jpg")
    cmd = [FFMPEG, "-y", "-i", video_path, "-vf", vf, "-vsync", "vfr", pattern]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:  # pragma: no cover
        return {"available": True, "frames": [], "note": f"ffmpeg error: {exc}"}

    frames = []
    for idx, img in enumerate(sorted(out.glob("frame_*.jpg"))):
        ts = int(idx / fps * 1000) if fps and not scene_change else idx * 1000
        frames.append({"timestamp_ms": ts, "image_uri": str(img), "quality_flags": ["ok"]})
    return {"available": True, "frames": frames, "note": ""}


def transcribe_audio(media_path: str, *, language: str = "ru") -> dict:
    """ASR. Провайдер задаётся CONSTRUCTION_MCP_ASR_CMD (шаблон с {path} {lang}),
    который должен напечатать JSON-массив [{start_ms,end_ms,text}]. Иначе — офлайн-заглушка."""
    cmd_tpl = os.environ.get("CONSTRUCTION_MCP_ASR_CMD")
    if not cmd_tpl:
        return {"available": False, "segments": [],
                "note": "ASR не сконфигурирован (CONSTRUCTION_MCP_ASR_CMD); расшифровка недоступна"}
    import json as _json
    cmd = cmd_tpl.format(path=media_path, lang=language)
    try:
        res = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=1200)
        return {"available": True, "segments": _json.loads(res.stdout), "note": ""}
    except Exception as exc:  # pragma: no cover
        return {"available": True, "segments": [], "note": f"ASR error: {exc}"}


def run_ocr(image_path: str) -> dict:
    """OCR таблички/маркировки. Провайдер — CONSTRUCTION_MCP_OCR_CMD (шаблон с {path}),
    печатает распознанный текст. Иначе — офлайн-заглушка."""
    cmd_tpl = os.environ.get("CONSTRUCTION_MCP_OCR_CMD")
    if not cmd_tpl:
        return {"available": False, "text": "",
                "note": "OCR не сконфигурирован (CONSTRUCTION_MCP_OCR_CMD)"}
    cmd = cmd_tpl.format(path=image_path)
    try:
        res = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=120)
        return {"available": True, "text": res.stdout.strip(), "note": ""}
    except Exception as exc:  # pragma: no cover
        return {"available": True, "text": "", "note": f"OCR error: {exc}"}
