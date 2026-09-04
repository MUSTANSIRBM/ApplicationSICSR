"""
planner/demo_state.py — python -m planner.demo_state

One command to a demo-ready database:
  fresh seed -> monthly plan -> weekly solves for all 4 weeks
  -> one block APPROVED (pinned) for the money moment.

Pinned-block selection is robust: prefer ET-NGP in the latest solve,
fall back to any corridor in the latest solve, and if that solve has
no blocks, walk back through earlier solves until one does.

*** FLAG: overlaps DB-team work order item B. If they ship their own
reset script, keep the better one and delete the other. ***

After this, the demo sequence is:
  uvicorn api.main:app --port 8000
  GET  /api/plan           -> rich 4-week timeline
  GET  /api/impact         -> baseline vs planner on the latest (meatiest) week
  POST /api/defects (safety) -> money moment: pinned block untouched,
                                new safety block slots in, moved list ~empty
"""
from datetime import timedelta

from sqlmodel import Session, select

from planner.db import engine
from planner.models import (
    Block, BlockStatus, Corridor, Defect, Solve, SolveKind,
)
from planner.monthly import run_monthly
from planner.reference import PLAN_START
from planner.run_solve import run
from planner.seed import seed


def _pick_block_to_pin(session, solve_ids):
    """Prefer ET-NGP in the newest solve; else any block in the newest
    solve; else any block in earlier solves. Returns a Block or None."""
    et = session.exec(select(Corridor).where(
        Corridor.code == "ET-NGP")).first()

    for sid in reversed(solve_ids):           # newest first
        blocks = session.exec(select(Block).where(
            Block.solve_id == sid,
            Block.status == BlockStatus.PROPOSED)).all()
        if not blocks:
            continue
        if et:
            et_block = next(
                (b for b in blocks if b.corridor_id == et.id), None)
            if et_block:
                return et_block
        return blocks[0]
    return None


def build(verbose=True):
    seed(reset=True)
    run_monthly(verbose=False)
    solve_ids = [run(week_start=PLAN_START + timedelta(weeks=w), verbose=False)
                 for w in range(4)]

    approved_ref = None
    with Session(engine) as s:
        blk = _pick_block_to_pin(s, solve_ids)
        if blk:
            blk.status = BlockStatus.APPROVED
            s.add(blk)
            s.commit()
            s.refresh(blk)
            refs = [d.source_ref for d in s.exec(select(Defect).where(
                Defect.block_id == blk.id)).all()]
            cor = s.get(Corridor, blk.corridor_id)
            approved_ref = (blk.id, cor.code, refs, blk.start, blk.end)

        last = s.get(Solve, solve_ids[-1])
        n_prop = len(s.exec(select(Block).where(
            Block.status == BlockStatus.PROPOSED)).all())
        n_appr = len(s.exec(select(Block).where(
            Block.status == BlockStatus.APPROVED)).all())
        st = last.stats
        last_id = solve_ids[-1]

    if verbose:
        print("=" * 64)
        print("DEMO STATE READY")
        print(f"weekly solves : {len(solve_ids)} (ids {solve_ids})")
        print(f"latest week   : {last.horizon_start:%Y-%m-%d} "
              f"(in scope {st['in_scope']}, scheduled {st['scheduled']}, "
              f"deferred {st['deferred']}, bundled {st['bundled_blocks']}, "
              f"closure saved {st['closure_saved_min']} min)")
        print(f"blocks        : {n_prop} proposed, {n_appr} approved (pinned)")
        if approved_ref:
            bid, code, refs, bs, be = approved_ref
            print(f"pinned block  : #{bid} {code} {bs:%a %d %H:%M}-"
                  f"{be:%H:%M} ({', '.join(refs)})")
        print("-" * 64)
        print("demo sequence:")
        print("  uvicorn api.main:app --port 8000")
        print("  GET  /api/plan    (rich timeline, 4 weeks)")
        print("  GET  /api/impact  (baseline vs planner, latest week)")
        print("  POST /api/defects corridor=<pinned corridor> "
              "dept=TRD safety=true dur=120")
        print("     -> pinned block untouched, minimal moved list")
        print("=" * 64)
    return last_id


if __name__ == "__main__":
    build()

