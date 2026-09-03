"""
adapters/tms.py — the ONLY code that knows what a TMS record looks like.
Translation rule: TMS priority P1 = safety (Tier 1), P2..P5 -> severity.
"""
from planner.models import Defect, SourceSystem, TaskStatus

_PRIORITY = {"P1": 5, "P2": 4, "P3": 3, "P4": 2, "P5": 1}


class TMSAdapter:
    def __init__(self, records, corridor_ids, department_id):
        self.records = records
        self.corridor_ids = corridor_ids          # {"NGP-BSL": 1, ...}
        self.department_id = department_id

    def fetch_defects(self):
        return [Defect(
            source_ref=r["defect_no"],
            source_system=SourceSystem.TMS,
            department_id=self.department_id,
            corridor_id=self.corridor_ids[r["section"]],
            title=f'{r["nature"].replace("_", " ").title()} near km {r["km_post"]}',
            description=r["remarks"],
            defect_type=r["nature"],
            severity=_PRIORITY[r["priority"]],
            safety_flag=(r["priority"] == "P1"),
            reported_at=r["reported"],
            due_by=r["target"],
            base_duration_min=int(round(r["block_hrs_req"] * 60)),
            status=TaskStatus.NEW,
        ) for r in self.records]

if __name__ == "__main__":
    from adapters.raw_sources import build_all
    _IDS = {"NGP-BSL": 1, "ET-NGP": 2, "BSL-MMR": 3, "SC-GTL": 4, "MAS-TRY": 5}
    defects = TMSAdapter(build_all()["tms"], _IDS, 1).fetch_defects()
    d = defects[0]
    print(f"TMS adapter: {len(defects)} defects")
    print(f"sample: {d.source_ref} | {d.defect_type} | sev {d.severity} | safety {d.safety_flag}")
    print("ADAPTER SMOKE TEST OK")
