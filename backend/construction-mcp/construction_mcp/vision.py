"""Мультимодальный анализ кадров.

В онлайн-режиме (задан ANTHROPIC_API_KEY и установлен пакет anthropic) отправляет
кадры в модель Claude и требует строгий JSON по переданной схеме. В офлайн-режиме
возвращает детерминированную заглушку, помеченную низкой уверенностью и
`requires_human_review`, чтобы конвейер работал без ключей и никогда не выдавал
недоказанный «факт».
"""
from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any

from . import config


def _encode_image(path: str) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    media_type = mimetypes.guess_type(str(p))[0] or "image/jpeg"
    data = base64.standard_b64encode(p.read_bytes()).decode("ascii")
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}


def analyze_frames(frame_paths: list[str], prompt: str, schema: dict | None = None,
                   *, model: str | None = None) -> dict:
    """Анализ кадров. Возвращает {available, result, note}.

    result — JSON-объект (в идеале по schema). В офлайн-режиме result помечен
    как неподтверждённый (низкая confidence).
    """
    if config.OFFLINE:
        return {
            "available": False,
            "result": {
                "detected_labels": [],
                "status": "started" if frame_paths else "not_started",
                "estimated_completion_percent": 0,
                "confidence": 0.2,
                "confidence_level": "low",
                "requires_human_review": True,
                "note": "офлайн-режим: мультимодальная модель не вызвана; вывод не является доказательством",
            },
            "note": "OFFLINE — задайте ANTHROPIC_API_KEY для реального анализа кадров",
        }

    try:
        import anthropic
    except ImportError:  # pragma: no cover
        return {"available": False, "result": {}, "note": "пакет anthropic не установлен"}

    blocks: list[dict[str, Any]] = []
    for fp in frame_paths:
        enc = _encode_image(fp)
        if enc:
            blocks.append(enc)
    instruction = prompt
    if schema is not None:
        instruction += ("\n\nВерни ТОЛЬКО валидный JSON по схеме (без markdown, без пояснений):\n"
                        + json.dumps(schema, ensure_ascii=False))
    blocks.append({"type": "text", "text": instruction})

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    try:
        resp = client.messages.create(
            model=model or config.VISION_MODEL,
            max_tokens=2000,
            system=("Ты — инспектор строительного контроля. Отвечай строго по кадрам-"
                    "доказательствам, только валидным JSON. Не выдумывай того, чего не видно."),
            messages=[{"role": "user", "content": blocks}],
        )
    except Exception as exc:  # pragma: no cover
        return {"available": False, "result": {}, "note": f"anthropic error: {exc}"}

    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        result = json.loads(text[start:end + 1]) if start >= 0 and end > start else {"raw": text}
    return {"available": True, "result": result, "note": ""}
