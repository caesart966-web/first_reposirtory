"""Поиск по документам/видеоархиву.

MVP: лексический поиск (нормализованное совпадение токенов, RU-дружественный),
работает без внешних сервисов. Точка расширения: если задан провайдер эмбеддингов,
чанки индексируются векторно и ранжируются по косинусной близости — интерфейс
`embed()` ниже (по умолчанию None -> лексика).
"""
from __future__ import annotations

import re
from typing import Callable

from .db import Database

_TOKEN_RE = re.compile(r"[\wёЁ]+", re.UNICODE)

# Провайдер эмбеддингов можно внедрить извне: search.embed = lambda texts -> list[list[float]]
embed: Callable[[list[str]], list[list[float]]] | None = None


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _lexical_score(query_tokens: list[str], text: str) -> float:
    toks = tokenize(text)
    if not toks:
        return 0.0
    counts = {}
    for t in toks:
        counts[t] = counts.get(t, 0) + 1
    qset = set(query_tokens)
    hit = sum(counts.get(q, 0) for q in qset)
    coverage = sum(1 for q in qset if q in counts) / max(len(qset), 1)
    return (hit / len(toks)) * (0.5 + 0.5 * coverage)


def index_document_text(db: Database, *, project_id: str, document_id: str,
                        document_type: str, text: str, locator: str | None = None,
                        page: int | None = None, chunk_chars: int = 800) -> int:
    """Режет текст на чанки и индексирует. Возвращает число чанков."""
    text = text or ""
    n = 0
    for i in range(0, len(text), chunk_chars):
        chunk = text[i:i + chunk_chars].strip()
        if not chunk:
            continue
        emb = embed([chunk])[0] if embed else None
        db.add_chunk(chunk, project_id=project_id, document_id=document_id,
                     document_type=document_type, locator=locator, page=page, embedding=emb)
        n += 1
    return n


def _cosine(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def search(db: Database, *, project_id: str, query: str, top_k: int = 5,
           document_type: str | None = None) -> list[dict]:
    chunks = db.chunks(project_id=project_id, document_type=document_type)
    if not chunks:
        return []
    scored = []
    if embed:
        qv = embed([query])[0]
        for c in chunks:
            import json
            cv = json.loads(c["embedding"]) if c.get("embedding") else None
            score = _cosine(qv, cv) if cv else 0.0
            scored.append((score, c))
    else:
        qtok = tokenize(query)
        for c in chunks:
            scored.append((_lexical_score(qtok, c["text"]), c))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, c in scored[:top_k]:
        if score <= 0:
            continue
        out.append({
            "document_id": c["document_id"], "document_type": c["document_type"],
            "locator": c["locator"], "page": c["page"],
            "quote": c["text"][:300], "score": round(float(score), 4),
        })
    return out
