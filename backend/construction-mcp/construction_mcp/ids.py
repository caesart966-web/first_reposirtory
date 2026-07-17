"""Генерация идентификаторов с префиксом типа (proj_, room_, issue_ ...)."""
from __future__ import annotations

import uuid

PREFIXES = {
    "Project": "proj", "Building": "bld", "Floor": "flr", "Zone": "zone",
    "Room": "room", "ContractObligation": "obl", "EstimateItem": "est",
    "ScheduleTask": "task", "Inspection": "insp", "VideoSegment": "seg",
    "EvidenceFrame": "frame", "ProgressObservation": "obs", "Defect": "def",
    "Risk": "risk", "CorrectiveAction": "act", "Issue": "issue",
    "Document": "doc", "TextChunk": "chunk", "ReviewRequest": "rev",
    "ReviewLog": "log", "WeeklyReport": "rep",
}


def new_id(entity_type: str) -> str:
    prefix = PREFIXES.get(entity_type, entity_type.lower()[:4] or "ent")
    return f"{prefix}_{uuid.uuid4().hex[:10]}"
