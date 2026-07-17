from construction_mcp import tools


def _seed_project(db):
    p = db.upsert({"type": "Project", "name": "Демо ЖК"})
    pid = p["id"]
    floor = db.upsert({"type": "Floor", "project_id": pid, "building_id": "bld_1", "level": 3,
                       "floor_plan_document_id": None})
    room = db.upsert({"type": "Room", "project_id": pid, "floor_id": floor["id"],
                      "code": "305", "name": "Офис"})
    db.upsert({"type": "EstimateItem", "project_id": pid, "work_name": "Штукатурка стен",
               "unit": "м2", "quantity": 100, "contractor": "ООО Отделка",
               "room_ids": [room["id"]],
               "source": {"document_id": "doc_1", "document_type": "estimate", "locator": "поз. 0-1-15"}})
    db.upsert({"type": "ScheduleTask", "project_id": pid, "name": "Штукатурка стен",
               "planned_start": "2026-06-01", "planned_finish": "2026-07-01",
               "room_ids": [room["id"]],
               "source": {"document_id": "doc_2", "document_type": "schedule", "locator": "строка 42"}})
    return pid, floor, room


def test_getters_and_filters(db):
    pid, floor, room = _seed_project(db)
    assert len(tools.get_estimate_items(db, pid, room_id=room["id"])["items"]) == 1
    assert len(tools.get_estimate_items(db, pid, contractor="ООО Отделка")["items"]) == 1
    assert len(tools.get_estimate_items(db, pid, contractor="Другой")["items"]) == 0
    assert len(tools.get_schedule_tasks(db, pid, active_on="2026-06-15")["tasks"]) == 1
    assert len(tools.get_schedule_tasks(db, pid, active_on="2026-08-15")["tasks"]) == 0
    fp = tools.get_floor_plan(db, floor["id"])
    assert len(fp["rooms"]) == 1 and fp["rooms"][0]["code"] == "305"


def test_ingest_and_search(db, tmp_path):
    pid, *_ = _seed_project(db)
    f = tmp_path / "contract.txt"
    f.write_text("Подрядчик обязан завершить штукатурные работы до 1 июля 2026. "
                 "За нарушение срока — штраф 0.1% от цены этапа за каждый день просрочки.",
                 encoding="utf-8")
    res = tools.ingest_document(db, project_id=pid, document_type="contract", path=str(f))
    assert res["chunks_indexed"] >= 1
    docs = tools.get_project_documents(db, pid, document_type="contract")["documents"]
    assert len(docs) == 1
    hits = tools.search_contract(db, pid, "штраф за просрочку срока", top_k=3)["hits"]
    assert hits and "штраф" in hits[0]["quote"].lower()


def test_observation_and_issue_flow(db):
    pid, floor, room = _seed_project(db)
    obs = tools.save_progress_observation(db, {
        "project_id": pid, "inspection_id": "insp_1", "room_id": room["id"],
        "work_name": "Штукатурка стен", "status": "in_progress",
        "estimated_completion_percent": 40, "confidence": 0.72,
        "evidence_frame_ids": ["frame_1", "frame_2"],
        "evidence_description": "Низ стен оштукатурен, откосы нет."})
    assert obs["validated"] is True

    issue = {
        "project_id": pid, "issue_kind": "schedule_deviation", "object": "Корпус 1",
        "location_label": "Корпус 1, этаж 3, пом. 305", "work_name": "Штукатурка стен",
        "contractor": "ООО Отделка", "planned_percent": 100, "actual_percent": 40,
        "deviation_percent": -60, "days_overdue": 18, "severity": "critical",
        "confidence": 0.72, "evidence_description": "На кадрах ~40% готовности.",
        "evidence_frame_ids": ["frame_1"],
        "possible_causes": ["нехватка звена"], "consequences": ["сдвиг малярных работ"],
        "recommended_actions": [{"id": "act_1", "type": "CorrectiveAction", "project_id": pid,
                                 "action": "Добавить звено штукатуров", "responsible": "Прораб"}],
        "created_by_agent": "schedule_control"}
    ci = tools.create_issue(db, issue)
    assert ci["validated"] is True
    assert ci["requires_human_review"] is True  # critical -> на человека
    reqs = db.conn.execute("SELECT * FROM review_requests").fetchall()
    assert len(reqs) == 1  # автоматически поставлено в очередь HITL

    up = tools.update_issue(db, ci["issue_id"], {"actual_percent": 55}, actor="инженер СК",
                            reason="виден участок за перегородкой")
    assert up["issue_id"] == ci["issue_id"]
    logs = db.conn.execute("SELECT * FROM review_log").fetchall()
    assert len(logs) == 1  # правка человека сохранена


def test_hidden_work_defect_not_confirmed_and_report(db):
    pid, floor, room = _seed_project(db)
    tools.save_progress_observation(db, {
        "project_id": pid, "inspection_id": "insp_1", "room_id": room["id"],
        "work_name": "Штукатурка стен", "status": "in_progress",
        "estimated_completion_percent": 40, "confidence": 0.72,
        "evidence_frame_ids": ["frame_1"]})
    db.upsert({"type": "Defect", "project_id": pid, "room_id": room["id"],
               "defect_status": "needs_instrumental_check", "description": "Возможна неровность стяжки",
               "severity": "medium", "confidence": 0.4})
    rep = tools.generate_weekly_report(db, pid, "2026-07-10", "2026-07-17", ["insp_1"])
    assert rep["report"]["disclaimer"]
    assert rep["report"]["kpi"]["open_defects"] == 1
    assert "приёмкой работ" in rep["report"]["disclaimer"]


def test_request_human_review_sets_status(db):
    pid, floor, room = _seed_project(db)
    d = db.upsert({"type": "Risk", "project_id": pid, "category": "schedule",
                   "description": "Риск срыва вехи", "likelihood": "high", "impact": "high",
                   "review_status": "pending_review"})
    res = tools.request_human_review(db, "Risk", d["id"], reason="критический риск",
                                     severity="critical", suggested_options=["подтвердить", "отклонить"])
    assert res["status"] == "queued"
