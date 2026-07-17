"""construction-mcp — референс-backend ИИ-ассистента строительного контроля.

MCP-сервер, реализующий доменные функции скилла /construction-control:
get_project_documents, search_contract, get_estimate_items, get_schedule_tasks,
get_floor_plan, get_video_segments, get_evidence_frames, save_progress_observation,
create_issue, update_issue, generate_weekly_report, request_human_review — плюс
низкоуровневые инструменты (чтение PDF/DOCX/XLSX, кадры, ASR, OCR, поиск).

MVP работает на локальной БД (SQLite) и деградирует до офлайн-заглушек, когда
внешние сервисы (мультимодальная LLM, OCR, ASR, ffmpeg) не сконфигурированы.
"""

__version__ = "0.1.0"
