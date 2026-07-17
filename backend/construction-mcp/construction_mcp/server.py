"""MCP-сервер construction-mcp (stdio). Публикует доменные и низкоуровневые
инструменты скилла /construction-control для сессии Claude Code."""
from __future__ import annotations

import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from . import tools
from .db import get_db

# name -> (handler(db, **args), description, input_schema)
_STR = {"type": "string"}
_OBJ = {"type": "object"}

TOOL_SPECS: list[dict] = [
    {"name": "get_project_documents", "handler": tools.get_project_documents,
     "description": "Список и метаданные загруженных документов проекта.",
     "schema": {"type": "object", "properties": {"project_id": _STR, "document_type": _STR},
                "required": ["project_id"]}},
    {"name": "search_contract", "handler": tools.search_contract,
     "description": "Поиск по договору и доп. соглашениям (лексический/векторный).",
     "schema": {"type": "object", "properties": {"project_id": _STR, "query": _STR,
                "top_k": {"type": "integer"}}, "required": ["project_id", "query"]}},
    {"name": "get_estimate_items", "handler": tools.get_estimate_items,
     "description": "Позиции сметы/ВОР, фильтр по помещению/подрядчику.",
     "schema": {"type": "object", "properties": {"project_id": _STR, "room_id": _STR,
                "contractor": _STR}, "required": ["project_id"]}},
    {"name": "get_schedule_tasks", "handler": tools.get_schedule_tasks,
     "description": "Строки графика, фильтр по помещению и активности на дату.",
     "schema": {"type": "object", "properties": {"project_id": _STR, "room_id": _STR,
                "active_on": _STR}, "required": ["project_id"]}},
    {"name": "get_floor_plan", "handler": tools.get_floor_plan,
     "description": "План этажа: изображение и разметка помещений.",
     "schema": {"type": "object", "properties": {"floor_id": _STR}, "required": ["floor_id"]}},
    {"name": "get_video_segments", "handler": tools.get_video_segments,
     "description": "Сегменты видео обхода, фильтр по помещению.",
     "schema": {"type": "object", "properties": {"inspection_id": _STR, "room_id": _STR},
                "required": ["inspection_id"]}},
    {"name": "get_evidence_frames", "handler": tools.get_evidence_frames,
     "description": "Ключевые кадры по сегменту/помещению/наблюдению/списку id.",
     "schema": {"type": "object", "properties": {"segment_id": _STR, "room_id": _STR,
                "observation_id": _STR, "ids": {"type": "array", "items": _STR}}}},
    {"name": "save_progress_observation", "handler": tools.save_progress_observation,
     "description": "Сохранить наблюдение прогресса (валидация по схеме).",
     "schema": {"type": "object", "properties": {"observation": _OBJ}, "required": ["observation"]}},
    {"name": "create_issue", "handler": tools.create_issue,
     "description": "Создать проблему Issue (валидация; critical -> на человека).",
     "schema": {"type": "object", "properties": {"issue": _OBJ}, "required": ["issue"]}},
    {"name": "update_issue", "handler": tools.update_issue,
     "description": "Обновить проблему (правки человека логируются).",
     "schema": {"type": "object", "properties": {"issue_id": _STR, "patch": _OBJ,
                "actor": _STR, "reason": _STR}, "required": ["issue_id", "patch"]}},
    {"name": "generate_weekly_report", "handler": tools.generate_weekly_report,
     "description": "Сформировать недельный отчёт (JSON + markdown).",
     "schema": {"type": "object", "properties": {"project_id": _STR, "period_from": _STR,
                "period_to": _STR, "inspection_ids": {"type": "array", "items": _STR}},
                "required": ["project_id", "period_from", "period_to", "inspection_ids"]}},
    {"name": "request_human_review", "handler": tools.request_human_review,
     "description": "Отправить вывод на подтверждение специалисту.",
     "schema": {"type": "object", "properties": {"entity_type": _STR, "entity_id": _STR,
                "reason": _STR, "severity": _STR, "suggested_options": {"type": "array", "items": _STR}},
                "required": ["entity_type", "entity_id", "reason", "severity"]}},
    # ---- низкоуровневые ----
    {"name": "ingest_document", "handler": tools.ingest_document,
     "description": "Прочитать файл (PDF/DOCX/XLSX/TXT), зарегистрировать документ и проиндексировать.",
     "schema": {"type": "object", "properties": {"project_id": _STR, "document_type": _STR,
                "path": _STR, "title": _STR}, "required": ["project_id", "document_type", "path"]}},
    {"name": "read_pdf", "handler": tools.read_pdf, "description": "Прочитать PDF (текст+страницы).",
     "schema": {"type": "object", "properties": {"path": _STR}, "required": ["path"]}},
    {"name": "read_docx", "handler": tools.read_docx, "description": "Прочитать DOCX.",
     "schema": {"type": "object", "properties": {"path": _STR}, "required": ["path"]}},
    {"name": "read_xlsx", "handler": tools.read_xlsx, "description": "Прочитать XLSX.",
     "schema": {"type": "object", "properties": {"path": _STR, "sheet": _STR}, "required": ["path"]}},
    {"name": "read_schedule", "handler": tools.read_schedule, "description": "Разобрать график из XLSX.",
     "schema": {"type": "object", "properties": {"path": _STR}, "required": ["path"]}},
    {"name": "extract_frames", "handler": tools.extract_frames, "description": "Извлечь кадры из видео (ffmpeg).",
     "schema": {"type": "object", "properties": {"video_path": _STR, "fps": {"type": "number"},
                "scene_change": {"type": "boolean"}}, "required": ["video_path"]}},
    {"name": "transcribe_audio", "handler": tools.transcribe_audio, "description": "ASR расшифровка речи.",
     "schema": {"type": "object", "properties": {"media_path": _STR, "language": _STR}, "required": ["media_path"]}},
    {"name": "run_ocr", "handler": tools.run_ocr, "description": "OCR текста на кадре.",
     "schema": {"type": "object", "properties": {"image_path": _STR}, "required": ["image_path"]}},
    {"name": "analyze_frames", "handler": tools.analyze_frames,
     "description": "Мультимодальный анализ кадров (Claude; офлайн-заглушка без ключа).",
     "schema": {"type": "object", "properties": {"frame_paths": {"type": "array", "items": _STR},
                "prompt": _STR, "schema": _OBJ}, "required": ["frame_paths", "prompt"]}},
    {"name": "search_documents", "handler": tools.search_documents, "description": "Поиск по всем документам проекта.",
     "schema": {"type": "object", "properties": {"project_id": _STR, "query": _STR,
                "top_k": {"type": "integer"}}, "required": ["project_id", "query"]}},
]

_HANDLERS = {s["name"]: s["handler"] for s in TOOL_SPECS}

server = Server("construction-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [Tool(name=s["name"], description=s["description"], inputSchema=s["schema"])
            for s in TOOL_SPECS]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handler = _HANDLERS.get(name)
    if handler is None:
        return [TextContent(type="text", text=json.dumps({"error": f"unknown tool: {name}"}))]
    try:
        result = handler(get_db(), **(arguments or {}))
    except Exception as exc:  # возвращаем ошибку как данные, не роняем сервер
        result = {"error": f"{type(exc).__name__}: {exc}"}
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]


async def amain() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    import anyio
    anyio.run(amain)
