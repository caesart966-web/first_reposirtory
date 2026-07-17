"""Реализация инструментов скилла поверх БД и модулей backend'а.

Каждая функция принимает `db` первым аргументом (тестируемость); MCP-сервер
оборачивает их, подставляя синглтон-подключение. Возвращаются JSON-совместимые
словари. Записи валидируются по JSON Schema скилла.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from . import config, media, parsers, schemas, search, vision
from .db import Database
from .ids import new_id

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
CONTRACT_TYPES = ("contract", "supplementary_agreement")
DISCLAIMER = ("Отчёт носит информационный характер, сформирован ИИ по документам и "
              "видеообходу. Не является приёмкой работ, не подтверждает скрытые работы "
              "и не заменяет освидетельствование и исполнительную документацию. Выводы с "
              "пометкой «на подтверждение» подлежат проверке специалистом.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confidence_level(c: float) -> str:
    return "low" if c < 0.5 else ("medium" if c < 0.8 else "high")


# --------------------------------------------------------------------------- #
# Документы (регистрация/загрузка) — фундамент для get_project_documents/поиска
# --------------------------------------------------------------------------- #

def register_document(db: Database, *, project_id: str, document_type: str, title: str,
                      uri: str, version: str | None = None) -> dict:
    doc = {
        "id": new_id("Document"),
        "type": "Document", "project_id": project_id, "document_type": document_type,
        "title": title, "uri": uri, "version": version, "uploaded_at": _now(),
    }
    return db.upsert(doc)


def ingest_document(db: Database, *, project_id: str, document_type: str, path: str,
                    title: str | None = None) -> dict:
    """Читает файл по расширению, регистрирует Document и индексирует текст для поиска."""
    p = Path(path)
    title = title or p.name
    doc = register_document(db, project_id=project_id, document_type=document_type,
                            title=title, uri=str(p))
    ext = p.suffix.lower()
    text = ""
    if ext == ".pdf":
        text = parsers.read_pdf(path).get("text", "")
    elif ext == ".docx":
        text = parsers.read_docx(path).get("text", "")
    elif ext in (".xlsx", ".xlsm"):
        sheets = parsers.read_xlsx(path).get("sheets", [])
        text = "\n".join(" ".join(r) for s in sheets for r in s["rows"])
    elif ext in (".txt", ".md"):
        text = p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""
    n = search.index_document_text(db, project_id=project_id, document_id=doc["id"],
                                   document_type=document_type, text=text) if text else 0
    return {"document_id": doc["id"], "title": title, "chars": len(text), "chunks_indexed": n}


# --------------------------------------------------------------------------- #
# 12 доменных функций
# --------------------------------------------------------------------------- #

def get_project_documents(db: Database, project_id: str, document_type: str | None = None) -> dict:
    docs = db.query("Document", project_id=project_id,
                    predicate=(lambda d: d.get("document_type") == document_type) if document_type else None)
    return {"documents": [{k: d.get(k) for k in ("id", "document_type", "title", "version", "uploaded_at", "uri")}
                          for d in docs]}


def search_contract(db: Database, project_id: str, query: str, top_k: int = 5) -> dict:
    hits: list[dict] = []
    for dt in CONTRACT_TYPES:
        hits += search.search(db, project_id=project_id, query=query, top_k=top_k, document_type=dt)
    hits.sort(key=lambda h: h["score"], reverse=True)
    return {"hits": hits[:top_k]}


def get_estimate_items(db: Database, project_id: str, room_id: str | None = None,
                       contractor: str | None = None) -> dict:
    def pred(e):
        if room_id and room_id not in (e.get("room_ids") or []):
            return False
        if contractor and e.get("contractor") != contractor:
            return False
        return True
    return {"items": db.query("EstimateItem", project_id=project_id, predicate=pred)}


def get_schedule_tasks(db: Database, project_id: str, room_id: str | None = None,
                       active_on: str | None = None) -> dict:
    def pred(t):
        if room_id and room_id not in (t.get("room_ids") or []):
            return False
        if active_on and t.get("planned_start") and t.get("planned_finish"):
            if not (t["planned_start"] <= active_on <= t["planned_finish"]):
                return False
        return True
    return {"tasks": db.query("ScheduleTask", project_id=project_id, predicate=pred)}


def get_floor_plan(db: Database, floor_id: str) -> dict:
    floor = db.get(floor_id) or {}
    rooms = db.query("Room", predicate=lambda r: r.get("floor_id") == floor_id)
    image_uri = None
    plan_doc_id = floor.get("floor_plan_document_id")
    if plan_doc_id:
        doc = db.get(plan_doc_id)
        image_uri = doc.get("uri") if doc else None
    return {
        "floor_id": floor_id, "image_uri": image_uri,
        "rooms": [{"room_id": r["id"], "code": r.get("code"), "name": r.get("name"),
                   "plan_polygon": r.get("plan_polygon")} for r in rooms],
    }


def get_video_segments(db: Database, inspection_id: str, room_id: str | None = None) -> dict:
    def pred(s):
        if s.get("inspection_id") != inspection_id:
            return False
        return not room_id or s.get("room_id") == room_id
    return {"segments": db.query("VideoSegment", predicate=pred)}


def get_evidence_frames(db: Database, segment_id: str | None = None, room_id: str | None = None,
                        observation_id: str | None = None, ids: list[str] | None = None) -> dict:
    if ids:
        return {"frames": [f for f in (db.get(i) for i in ids) if f]}
    if observation_id:
        obs = db.get(observation_id) or {}
        return {"frames": [f for f in (db.get(i) for i in obs.get("evidence_frame_ids", [])) if f]}

    def pred(f):
        if segment_id and f.get("segment_id") != segment_id:
            return False
        return not room_id or f.get("room_id") == room_id
    return {"frames": db.query("EvidenceFrame", predicate=pred)}


def save_progress_observation(db: Database, observation: dict) -> dict:
    observation = dict(observation)
    observation.setdefault("type", "ProgressObservation")
    observation.setdefault("review_status", "pending_review")
    if "confidence" in observation and "confidence_level" not in observation:
        observation["confidence_level"] = _confidence_level(float(observation["confidence"]))
    if not observation.get("id"):
        observation["id"] = new_id("ProgressObservation")
    schemas.validate_entity("ProgressObservation", observation)
    saved = db.upsert(observation)
    return {"observation_id": saved["id"], "validated": True}


def create_issue(db: Database, issue: dict) -> dict:
    issue = dict(issue)
    issue.setdefault("type", "Issue")
    issue.setdefault("review_status", "pending_review")
    issue.setdefault("created_at", _now())
    if not issue.get("id"):
        issue["id"] = new_id("Issue")
    if "confidence" in issue and "confidence_level" not in issue:
        issue["confidence_level"] = _confidence_level(float(issue["confidence"]))
    issue.setdefault("requires_human_review", False)
    # Правила безопасности: critical и низкая уверенность всегда на человека.
    if issue.get("severity") == "critical" or float(issue.get("confidence", 1)) < config.LOW_CONFIDENCE:
        issue["requires_human_review"] = True
    schemas.validate("issue", issue)
    saved = db.upsert(issue)
    if saved.get("requires_human_review"):
        db.add_review_request(project_id=saved.get("project_id"), entity_type="Issue",
                              entity_id=saved["id"], reason=saved.get("human_review_reason") or "critical/спорный вывод",
                              severity=saved.get("severity", "high"))
    return {"issue_id": saved["id"], "validated": True,
            "requires_human_review": bool(saved.get("requires_human_review"))}


def update_issue(db: Database, issue_id: str, patch: dict, actor: str = "human",
                 reason: str | None = None) -> dict:
    issue = db.get(issue_id)
    if not issue:
        return {"error": f"issue not found: {issue_id}"}
    for field, new_val in patch.items():
        old_val = issue.get(field)
        if old_val != new_val:
            db.add_review_log(entity_type="Issue", entity_id=issue_id, field=field,
                              system_value=old_val, human_value=new_val, action="corrected",
                              actor=actor, reason=reason)
        issue[field] = new_val
    saved = db.upsert(issue)
    return {"issue_id": issue_id, "review_status": saved.get("review_status")}


def request_human_review(db: Database, entity_type: str, entity_id: str, reason: str,
                         severity: str, suggested_options: list[str] | None = None) -> dict:
    entity = db.get(entity_id)
    project_id = entity.get("project_id") if entity else None
    rec = db.add_review_request(project_id=project_id, entity_type=entity_type, entity_id=entity_id,
                                reason=reason, severity=severity, suggested_options=suggested_options)
    if entity and "review_status" in entity:
        entity["review_status"] = "pending_review"
        db.upsert(entity)
    return {"review_request_id": rec["id"], "status": rec["status"]}


def generate_weekly_report(db: Database, project_id: str, period_from: str, period_to: str,
                           inspection_ids: list[str]) -> dict:
    project = db.get(project_id) or {}
    issues = db.query("Issue", project_id=project_id)
    issues.sort(key=lambda i: SEVERITY_ORDER.get(i.get("severity", "info"), 9))
    defects = db.query("Defect", project_id=project_id, predicate=lambda d: d.get("defect_status") != "dismissed")
    risks = db.query("Risk", project_id=project_id)
    obs = db.query("ProgressObservation", project_id=project_id,
                   predicate=lambda o: o.get("inspection_id") in inspection_ids) if inspection_ids else \
        db.query("ProgressObservation", project_id=project_id)

    actuals = [o["estimated_completion_percent"] for o in obs if o.get("estimated_completion_percent") is not None]
    planned = [i["planned_percent"] for i in issues if i.get("planned_percent") is not None]
    overall_actual = round(sum(actuals) / len(actuals), 1) if actuals else 0
    overall_planned = round(sum(planned) / len(planned), 1) if planned else 0
    kpi = {
        "overall_planned_percent": overall_planned,
        "overall_actual_percent": overall_actual,
        "overall_deviation_percent": round(overall_actual - overall_planned, 1),
        "tasks_behind": sum(1 for i in issues if (i.get("deviation_percent") or 0) < 0),
        "tasks_overdue": sum(1 for i in issues if (i.get("days_overdue") or 0) > 0),
        "open_defects": len(defects),
    }
    human_queue = [{"issue_id": i["id"], "reason": i.get("human_review_reason") or "требует проверки",
                    "severity": i.get("severity", "high")}
                   for i in issues if i.get("requires_human_review")]
    corrective = [a for i in issues for a in (i.get("recommended_actions") or [])]

    report = {
        "report_id": new_id("WeeklyReport"),
        "project_id": project_id,
        "period": {"from": period_from, "to": period_to, "inspection_ids": inspection_ids},
        "executive_summary": (
            f"За период {period_from}–{period_to} проанализировано наблюдений: {len(obs)}. "
            f"Выявлено проблем: {len(issues)} (критических: {sum(1 for i in issues if i.get('severity')=='critical')}). "
            f"Открытых дефектов: {len(defects)}. Средняя фактическая готовность по наблюдениям: {overall_actual}%. "
            "Категоричные выводы без достаточных доказательств не делаются; спорное вынесено на подтверждение."),
        "kpi": kpi,
        "ranked_issues": issues,
        "risks": risks,
        "corrective_actions": corrective,
        "human_review_queue": human_queue,
        "data_quality_notes": [
            "KPI рассчитаны по имеющимся наблюдениям/проблемам; при неполном покрытии обхода значения приблизительны.",
        ],
        "disclaimer": DISCLAIMER,
        "generated_at": _now(),
    }
    schemas.validate("weekly-report.output", report)
    saved = db.upsert({**report, "type": "WeeklyReport", "id": report["report_id"]})
    md_uri = _render_markdown(report)
    return {"report_id": report["report_id"], "report": report, "markdown_uri": md_uri}


def _render_markdown(report: dict) -> str | None:
    from . import config
    try:
        config.ensure_dirs()
        lines = [f"# Недельный отчёт строительного контроля",
                 f"\n> {report['disclaimer']}\n",
                 f"- Период: {report['period']['from']} — {report['period']['to']}",
                 f"- Сформирован: {report['generated_at']}\n",
                 "## Резюме\n", report["executive_summary"], "\n## KPI\n"]
        for k, v in report["kpi"].items():
            lines.append(f"- {k}: {v}")
        lines.append("\n## Проблемы по критичности\n")
        for i in report["ranked_issues"]:
            lines.append(f"### [{i.get('severity')}] {i.get('work_name')} — {i.get('location_label')}")
            lines.append(f"- план/факт/откл: {i.get('planned_percent')}/{i.get('actual_percent')}/"
                         f"{i.get('deviation_percent')} п.п.; просрочка {i.get('days_overdue')} дн.")
            lines.append(f"- доказательства: {i.get('evidence_description')}")
            lines.append(f"- на подтверждение человеком: {i.get('requires_human_review')}\n")
        out = config.STORAGE_DIR / f"{report['report_id']}.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        return str(out)
    except Exception:  # pragma: no cover
        return None


# --------------------------------------------------------------------------- #
# Низкоуровневые инструменты
# --------------------------------------------------------------------------- #

def read_pdf(db, path: str) -> dict:  # db не нужен, но единый интерфейс сервера
    return parsers.read_pdf(path)


def read_docx(db, path: str) -> dict:
    return parsers.read_docx(path)


def read_xlsx(db, path: str, sheet: str | None = None) -> dict:
    return parsers.read_xlsx(path, sheet)


def read_schedule(db, path: str) -> dict:
    return parsers.read_schedule(path)


def extract_frames(db, video_path: str, fps: float = 1.0, scene_change: bool = False) -> dict:
    return media.extract_frames(video_path, fps=fps, scene_change=scene_change)


def transcribe_audio(db, media_path: str, language: str = "ru") -> dict:
    return media.transcribe_audio(media_path, language=language)


def run_ocr(db, image_path: str) -> dict:
    return media.run_ocr(image_path)


def analyze_frames(db, frame_paths: list[str], prompt: str, schema: dict | None = None) -> dict:
    return vision.analyze_frames(frame_paths, prompt, schema)


def search_documents(db: Database, project_id: str, query: str, top_k: int = 5) -> dict:
    return {"hits": search.search(db, project_id=project_id, query=query, top_k=top_k)}
