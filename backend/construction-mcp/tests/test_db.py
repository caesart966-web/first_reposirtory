def test_upsert_get_query(db):
    p = db.upsert({"type": "Project", "name": "Демо ЖК"})
    assert p["id"].startswith("proj_")
    assert db.get(p["id"])["name"] == "Демо ЖК"

    r1 = db.upsert({"type": "Room", "project_id": p["id"], "floor_id": "flr_1", "code": "301"})
    db.upsert({"type": "Room", "project_id": p["id"], "floor_id": "flr_1", "code": "302"})
    rooms = db.query("Room", project_id=p["id"])
    assert len(rooms) == 2

    # update in place keeps id, changes data
    r1["name"] = "Офис"
    db.upsert(r1)
    assert db.get(r1["id"])["name"] == "Офис"
    assert len(db.query("Room", project_id=p["id"])) == 2


def test_review_request_and_log(db):
    req = db.add_review_request(entity_type="Issue", entity_id="issue_1",
                                reason="critical", severity="critical")
    assert req["status"] == "queued"
    rows = db.conn.execute("SELECT * FROM review_requests").fetchall()
    assert len(rows) == 1

    db.add_review_log(entity_type="Issue", entity_id="issue_1", field="actual_percent",
                      system_value=40, human_value=55, action="corrected", actor="инженер")
    logs = db.conn.execute("SELECT * FROM review_log").fetchall()
    assert len(logs) == 1
