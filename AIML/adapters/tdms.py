"""
adapters/tdms.py — TDMS adapter (S&T signalling defects).
Translation rule: criticality C1 = safety, C2 -> sev 4, C3 -> sev 2.
"""
from planner.models import Defect, SourceSystem, TaskStatus

_CRIT = {"C1": 5, "C2": 4, "C3": 2}


class TDMSAdapter:
    def __init__(self, records, corridor_ids, department_id):
        self.records = records
        self.corridor_ids = corridor_ids
        self.department_id = department_id

    def fetch_defects(self):
        return [Defect(
            source_ref=r["tdms_ref"],
            source_system=SourceSystem.TDMS,
            department_id=self.department_id,
            corridor_id=self.corridor_ids[r["section"]],
            title=f'{r["asset"].replace("_", " ").title()} near km {r["km_post"]}',
            description=r["note"],
            defect_type=r["asset"],
            severity=_CRIT[r["criticality"]],
            safety_flag=(r["criticality"] == "C1"),
            reported_at=r["logged"],
            due_by=r["due"],
            base_duration_min=r["duration_min"],
            status=TaskStatus.NEW,
        ) for r in self.records]

if __name__ == "__main__":
    from adapters.raw_sources import build_all
    _IDS = {"NGP-BSL": 1, "ET-NGP": 2, "BSL-MMR": 3, "SC-GTL": 4, "MAS-TRY": 5}
    defects = TDMSAdapter(build_all()["tdms"], _IDS, 3).fetch_defects()
    d = defects[0]
    print(f"TDMS adapter: {len(defects)} defects")
    print(f"sample: {d.source_ref} | {d.defect_type} | sev {d.severity} | safety {d.safety_flag}")
    print("ADAPTER SMOKE TEST OK")
