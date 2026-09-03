"""
adapters/smms.py — SMMS adapter (TRD / OHE power defects).
Translation rule: urgency EMERG = safety, HIGH -> sev 4, NORM -> sev 2.
"""
from planner.models import Defect, SourceSystem, TaskStatus

_URGENCY = {"EMERG": 5, "HIGH": 4, "NORM": 2}


class SMMSAdapter:
    def __init__(self, records, corridor_ids, department_id):
        self.records = records
        self.corridor_ids = corridor_ids
        self.department_id = department_id

    def fetch_defects(self):
        return [Defect(
            source_ref=r["smms_ref"],
            source_system=SourceSystem.SMMS,
            department_id=self.department_id,
            corridor_id=self.corridor_ids[r["section"]],
            title=f'{r["equipment"].replace("_", " ").title()} near km {r["km_post"]}',
            description=r["notes"],
            defect_type=r["equipment"],
            severity=_URGENCY[r["urgency"]],
            safety_flag=(r["urgency"] == "EMERG"),
            reported_at=r["logged"],
            due_by=r["due"],
            base_duration_min=int(round(r["crew_hrs"] * 60)),
            status=TaskStatus.NEW,
        ) for r in self.records]


if __name__ == "__main__":
    from adapters.raw_sources import build_all
    _IDS = {"NGP-BSL": 1, "ET-NGP": 2, "BSL-MMR": 3, "SC-GTL": 4, "MAS-TRY": 5}
    defects = SMMSAdapter(build_all()["smms"], _IDS, 2).fetch_defects()
    d = defects[0]
    print(f"SMMS adapter: {len(defects)} defects")
    print(f"sample: {d.source_ref} | {d.defect_type} | sev {d.severity} | safety {d.safety_flag}")
    print("ADAPTER SMOKE TEST OK")
