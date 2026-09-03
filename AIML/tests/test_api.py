"""
API tests — the §6 contract, enforced, plus the money moment:
approve a block, inject a safety defect, re-solve — the approved block
must come back UNTOUCHED and the safety defect must get a block.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from api.main import app
from planner.db import engine
from planner.models import (
    Block, BlockStatus, Corridor, Defect, Solve, TaskStatus,
)
from planner.monthly import run_monthly
from planner.run_solve import run
from planner.seed import seed


@pytest.fixture(name="client")
def client_fixture():
    seed(reset=True)
    run_monthly(verbose=False)
    run(verbose=False)                      # week 1 solve exists
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_reference(client):
    j = client.get("/api/reference").json()
    assert len(j["corridors"]) == 5
    assert len(j["departments"]) == 3
    assert j["plan_start"].startswith("2024-06-03")


def test_defects_list_and_filter(client):
    assert len(client.get("/api/defects").json()) == 30
    js = client.get("/api/defects", params={"corridor": "NGP-BSL"}).json()
    assert js and all(d["corridor"] == "NGP-BSL" for d in js)
    for k in ("source_ref", "tier", "status", "safety_flag",
              "base_duration_min", "due_by"):
        assert k in js[0]


def test_plan_shape(client):
    j = client.get("/api/plan").json()
    assert j["blocks"], "week-1 solve must have blocks"
    assert j["occupancy"], "trains must be served for the timeline"
    assert "reservations" in j
    for b in j["blocks"]:
        assert b["closure_minutes"] >= 15
        assert isinstance(b["is_combined"], bool)
        assert b["source_refs"]
    for o in j["occupancy"]:
        assert o["kind"] in ("train", "goods")


def test_score_endpoint(client):
    with Session(engine) as s:
        d = s.exec(select(Defect).where(
            Defect.status == TaskStatus.SCHEDULED)).first()
    r = client.get(f"/api/defects/{d.id}/score")
    assert r.status_code == 200
    j = r.json()
    assert set(j["components"]) == {"severity", "overdue_days",
                                    "traffic_impact", "aging_boost"}
    for comp in j["components"].values():
        assert "value" in comp and "detail" in comp


def test_solve_post(client):
    r = client.post("/api/solve", json={"week_start": "2024-06-10"})
    assert r.status_code == 200
    j = r.json()
    assert j["solve_id"]
    assert j["stats"]["in_scope"] >= 1
    assert client.get("/api/solves").json()[0]["id"] == j["solve_id"]


def test_inject_money_moment(client):
    # THE demo, as an assertion.
    with Session(engine) as s:
        et_id = s.exec(select(Corridor).where(
            Corridor.code == "ET-NGP")).one().id
        blk = next(b for b in s.exec(select(Block).where(
            Block.status == BlockStatus.PROPOSED)).all()
            if b.corridor_id == et_id)
        blk_id, approved_start = blk.id, blk.start
        blk.status = BlockStatus.APPROVED
        s.add(blk)
        s.commit()

    r = client.post("/api/defects", json={
        "corridor": "ET-NGP", "department": "TRD",
        "defect_type": "OHE_DROP", "safety_flag": True,
        "base_duration_min": 120})
    assert r.status_code == 200
    j = r.json()
    assert j["replanned"] is True

    diff = j["diff"]
    assert diff["new"], "injected safety defect must get a block"
    assert any(j["defect_id"] in b["task_ids"] for b in diff["new"])
    assert any(b["block_id"] == blk_id for b in diff["unchanged"]), \
        "the APPROVED block must appear untouched in the diff"

    with Session(engine) as s:
        blk2 = s.get(Block, blk_id)
        assert blk2.status == BlockStatus.APPROVED
        assert blk2.start == approved_start, "pinned block must not move"
        inj = s.get(Defect, j["defect_id"])
        assert inj.status == TaskStatus.SCHEDULED


def test_inject_non_safety_queues(client):
    with Session(engine) as s:
        n_before = len(s.exec(select(Solve)).all())
    r = client.post("/api/defects", json={
        "corridor": "BSL-MMR", "department": "ENG",
        "defect_type": "SLEEPER_RENEWAL", "safety_flag": False,
        "base_duration_min": 90})
    assert r.status_code == 200
    j = r.json()
    assert j["replanned"] is False
    with Session(engine) as s:
        assert len(s.exec(select(Solve)).all()) == n_before
        assert s.get(Defect, j["defect_id"]).status == TaskStatus.NEW


def test_impact(client):
    r = client.get("/api/impact")
    assert r.status_code == 200
    j = r.json()
    for section in ("baseline", "planner"):
        for k in ("scheduled", "deferred", "closure_minutes",
                  "cross_dept_conflicts", "method"):
            assert k in j[section]
    assert j["planner"]["cross_dept_conflicts"] == 0
