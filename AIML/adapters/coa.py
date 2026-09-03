"""
adapters/coa.py — COA adapter: timetable + goods forecast.
Translation rule: train type -> traffic priority (EXPRESS=1, PAX=2, MEMU=3).
"""
from planner.models import (
    Direction, GoodsForecastSlot, TimetableSlot, TrainType,
)

_TYPE_TO_PRIORITY = {"EXPRESS": 1, "PASSENGER": 2, "MEMU": 3}


class COAAdapter:
    def __init__(self, timetable, goods, corridor_ids):
        self.timetable = timetable
        self.goods = goods
        self.corridor_ids = corridor_ids

    def fetch_timetable_slots(self):
        return [TimetableSlot(
            corridor_id=self.corridor_ids[r["section"]],
            train_no=r["train_no"],
            train_name=r["train_name"],
            train_type=TrainType[r["train_type"]],
            direction=Direction[r["direction"]],
            start=r["start"],
            end=r["end"],
            priority=_TYPE_TO_PRIORITY[r["train_type"]],
        ) for r in self.timetable]

    def fetch_goods_slots(self):
        return [GoodsForecastSlot(
            corridor_id=self.corridor_ids[r["section"]],
            label=r["label"],
            start=r["start"],
            end=r["end"],
            expected_rakes=r["expected_rakes"],
        ) for r in self.goods]


if __name__ == "__main__":
    from adapters.raw_sources import build_all
    _IDS = {"NGP-BSL": 1, "ET-NGP": 2, "BSL-MMR": 3, "SC-GTL": 4, "MAS-TRY": 5}
    raw = build_all()
    coa = COAAdapter(raw["timetable"], raw["goods"], _IDS)
    slots = coa.fetch_timetable_slots()
    goods = coa.fetch_goods_slots()
    print(f"COA adapter: {len(slots)} train slots, {len(goods)} goods slots")
    print("ADAPTER SMOKE TEST OK")
