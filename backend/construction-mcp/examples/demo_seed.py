"""Демо сквозного прохода backend'а без внешних сервисов.

Создаёт мини-проект, наблюдение прогресса, считает отклонение детерминированной
арифметикой, оформляет Issue и выпускает недельный отчёт. Запуск из
backend/construction-mcp:  .venv/bin/python examples/demo_seed.py
"""
import json
import tempfile

from construction_mcp import deviation, tools
from construction_mcp.db import Database


def main():
    db = Database(tempfile.mktemp(suffix=".db"))

    # 1) структура проекта
    proj = db.upsert({"type": "Project", "name": "ЖК «Демонстрация»", "customer": "Заказчик",
                      "general_contractor": "Генподрядчик"})
    pid = proj["id"]
    bld = db.upsert({"type": "Building", "project_id": pid, "name": "Корпус 1"})
    flr = db.upsert({"type": "Floor", "project_id": pid, "building_id": bld["id"], "level": 3})
    room = db.upsert({"type": "Room", "project_id": pid, "floor_id": flr["id"], "code": "305",
                      "name": "Офис", "area_m2": 24})
    task = db.upsert({"type": "ScheduleTask", "project_id": pid, "name": "Штукатурка стен",
                      "planned_start": "2026-06-01", "planned_finish": "2026-07-01",
                      "responsible": "ООО Отделка", "is_hidden_work": False,
                      "room_ids": [room["id"]],
                      "source": {"document_id": "doc_s", "document_type": "schedule", "locator": "строка 42"}})

    # 2) наблюдение фактической готовности по кадрам (в проде — из Visual Progress Agent)
    tools.save_progress_observation(db, {
        "project_id": pid, "inspection_id": "insp_1", "room_id": room["id"],
        "work_name": "Штукатурка стен", "status": "in_progress",
        "estimated_completion_percent": 40, "confidence": 0.72,
        "schedule_task_id": task["id"], "evidence_frame_ids": ["frame_1", "frame_2"],
        "evidence_description": "Низ стен оштукатурен, откосы и верх не выполнены."})

    # 3) детерминированный расчёт отклонения (обычная арифметика)
    ev = deviation.evaluate_task(
        {**task, "room_id": room["id"]},
        {"actual_percent": 40, "confidence": 0.72},
        as_of="2026-07-01", prev_obs={"date": "2026-06-24", "actual": 25},
        on_critical_path=True)
    print("Расчёт отклонения:")
    print(json.dumps(ev, ensure_ascii=False, indent=2))

    # 4) оформление проблемы
    issue = tools.create_issue(db, {
        "project_id": pid, "issue_kind": "schedule_deviation", "object": "Корпус 1",
        "building_id": bld["id"], "floor_id": flr["id"], "room_id": room["id"],
        "location_label": "Корпус 1, этаж 3, пом. 305", "work_name": "Штукатурка стен",
        "contractor": "ООО Отделка", "schedule_task_id": task["id"],
        "planned_percent": ev["planned_percent"], "actual_percent": ev["actual_percent"],
        "deviation_percent": ev["deviation_percent"], "days_overdue": ev["days_overdue"],
        "forecast_finish": ev["forecast_finish"], "severity": ev["severity"],
        "confidence": ev["confidence"], "evidence_description": ev["basis"],
        "evidence_frame_ids": ["frame_1", "frame_2"],
        "possible_causes": ["нехватка звена штукатуров"],
        "consequences": ["сдвиг малярных работ", "риск срыва вехи этажа"],
        "recommended_actions": [{"id": "act_1", "type": "CorrectiveAction", "project_id": pid,
                                 "action": "Усилить звено на пом. 305–310", "responsible": "Прораб отделки",
                                 "due_date": "2026-07-05", "priority": "high"}],
        "responsible": "Прораб отделки", "due_date": "2026-07-05",
        "created_by_agent": "schedule_control"})
    print("\nСоздан Issue:", issue)

    # 5) недельный отчёт
    rep = tools.generate_weekly_report(db, pid, "2026-06-25", "2026-07-01", ["insp_1"])
    r = rep["report"]
    print("\nНедельный отчёт:")
    print("  KPI:", json.dumps(r["kpi"], ensure_ascii=False))
    print("  проблем:", len(r["ranked_issues"]), "| на подтверждение человеком:", len(r["human_review_queue"]))
    print("  markdown:", rep["markdown_uri"])
    print("  disclaimer:", r["disclaimer"][:60], "...")
    print("\nДемо OK — весь путь (факт → расчёт → Issue → отчёт) отработал без внешних сервисов.")


if __name__ == "__main__":
    main()
