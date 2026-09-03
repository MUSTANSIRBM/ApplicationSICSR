"""
adapters/raw_sources.py — the fake TMS / SMMS / TDMS / COA.

These generators speak SOURCE shapes, not our schema. The adapters
translate. Later, swap this file for real system clients and nothing
downstream changes — that's the whole point of the adapter wall.

DETERMINISM: numpy default_rng(42) + Faker(seed=42), created inside
build_all(). Same data every run, every machine, dead WiFi or not.

*** FLAGGED DESIGN DECISION ***
Train slots are SEQUENTIAL per corridor (single-line occupancy style):
no two trains/goods ever occupy one corridor at the same time. Why:
our locked solver hygiene puts trains as FIXED intervals inside each
corridor's AddNoOverlap set — mutually overlapping trains would make
that set infeasible before we place a single block. Real double-line
corridors run parallel trains; this is a fidelity trade-off, flagged
per our working rules, not silently changed.

The tight 20-90 min gaps between trains are the pressure: blocks must
squeeze into the gaps, bundle into them, or defer with reasons.

SAFETY IS RARE: only defect #1 per source is safety-flagged (one
guaranteed Tier-1 task per department). The rest are routine —
random safety rolls would put half the workload in Tier 1 and the
hard tier would stop meaning anything.
"""
from datetime import timedelta

import numpy as np
from faker import Faker

from planner.reference import CORRIDORS, PLAN_DAYS, PLAN_START

SEED = 42

# (hh, mm, train_no, train_name, train_type, direction, transit_min)
# Hand-laid per corridor: sequential, tight day gaps, varied night space.
TRAIN_PATTERNS = {
    "NGP-BSL": [  # HEAVY — night max ~90 min: a 180-min block cannot fit here
        (0, 10,  "12621", "Tamil Nadu Express",      "EXPRESS",   "UP",   210),
        (5, 10,  "68741", "NGP-BSL MEMU",            "MEMU",      "DOWN", 270),
        (10, 10, "12105", "Vidarbha Express",        "EXPRESS",   "UP",   270),
        (15, 10, "12809", "Howrah Mail",             "EXPRESS",   "DOWN", 240),
        (20, 10, "12722", "Dakshin Express",         "EXPRESS",   "DOWN", 120),
    ],
    "ET-NGP": [  # MEDIUM — one big ~240 min night window: the easy corridor
        (0, 30,  "12627", "Karnataka Express",       "EXPRESS",   "UP",   240),
        (5, 0,   "68713", "ET-NGP MEMU",             "MEMU",      "UP",   150),
        (8, 0,   "51261", "Itarsi-Nagpur Passenger", "PASSENGER", "UP",   180),
        (11, 30, "12615", "Grand Trunk Express",     "EXPRESS",   "UP",   210),
        (15, 30, "12721", "Dakshin Express",         "EXPRESS",   "DOWN", 150),
        (18, 30, "51262", "Nagpur-Itarsi Passenger", "PASSENGER", "DOWN", 120),
    ],
    "BSL-MMR": [  # LIGHT — huge windows: the bundling playground
        (2, 0,   "12138", "Punjab Mail",             "EXPRESS",   "UP",   150),
        (8, 0,   "51115", "BSL-MMR Passenger",       "PASSENGER", "DOWN", 210),
        (16, 0,  "17001", "SF Express",              "EXPRESS",   "UP",   150),
    ],
    "SC-GTL": [  # MEDIUM — no window >= 3h anywhere: constant squeeze
        (23, 30, "12707", "Andhra Pradesh Express",  "EXPRESS",   "UP",   270),
        (5, 0,   "17417", "Rayalaseema Express",     "EXPRESS",   "DOWN", 210),
        (9, 30,  "17205", "Kacheguda SF Express",    "EXPRESS",   "UP",   240),
        (14, 30, "12786", "SF Express",              "EXPRESS",   "DOWN", 240),
        (19, 30, "57311", "Guntakal Passenger",      "PASSENGER", "UP",   150),
    ],
    "MAS-TRY": [  # LIGHT — two ~110-120 min night windows + evening space
        (0, 10,  "12635", "Vaigai Express",          "EXPRESS",   "UP",   120),
        (4, 0,   "12636", "Vaigai Express",          "EXPRESS",   "DOWN", 120),
        (8, 0,   "56705", "Chengalpattu Passenger",  "PASSENGER", "UP",   300),
        (15, 0,  "16853", "Chennai-Trichy Express",  "EXPRESS",   "UP",   300),
    ],
}

# (weekdays, start_min_from_midnight, duration_min, label, rakes) — Mon=0.
# Each goods slot is placed INSIDE a train gap, so the corridor's
# no-overlap set stays feasible. No jitter on goods (they're a forecast).
GOODS_PATTERNS = {
    "NGP-BSL": [((2, 5), 1350, 60,  "BOXN rakes to ICD Nagpur",      2)],
    "ET-NGP":  [((0, 3), 1260, 150, "BOXN rakes to ICD Nagpur",      2)],
    "BSL-MMR": [((2,),   1170, 240, "Coal rakes to Manmad yard",     1)],
    "SC-GTL":  [((1, 4), 1335, 60,  "BOXN rakes to ICD Sanathnagar", 2)],
    "MAS-TRY": [((0, 1, 2, 3, 4, 5, 6), 140, 85, "Cement rakes to Trichy", 1)],
}

_TMS_TYPES = [
    ("RAIL_FRACTURE", True),
    ("WELD_FAILURE", False),
    ("SLEEPER_RENEWAL", False),
    ("TRACK_GEOMETRY", False),
    ("BALLAST_ATTENTION", False),
]
_SMMS_TYPES = [
    ("OHE_DROP", True),
    ("INSULATOR_FLASHOVER", False),
    ("MAST_REPAIR", False),
    ("POWER_SUPPLY_FAULT", False),
]
_TDMS_TYPES = [
    ("SIGNAL_FAILURE", True),
    ("POINT_MACHINE_DEFECT", True),
    ("TRACK_CIRCUIT_FAULT", False),
    ("RELAY_RENEWAL", False),
    ("AXLE_COUNTER_FAULT", False),
]

_DEPT_LOAD = [("TMS", _TMS_TYPES, 12), ("SMMS", _SMMS_TYPES, 9), ("TDMS", _TDMS_TYPES, 9)]

# must match CORRIDORS order in planner.reference
_CORRIDOR_WEIGHTS = np.array([0.30, 0.18, 0.15, 0.22, 0.15])

_DURATIONS = [30, 60, 90, 120, 180, 240]
_DUR_P = [0.08, 0.22, 0.25, 0.22, 0.15, 0.08]


def _defects(rng, fake, source, types, count, prefix):
    """Build source-shaped defect records. Defect #1 per source is
    safety-flagged, guaranteed — every department gets a Tier-1 task.
    Everything else is routine."""
    codes = [c["code"] for c in CORRIDORS]
    kmrange = {c["code"]: (c["km_start"], c["km_end"]) for c in CORRIDORS}
    routine = [t for t in types if not t[1]]
    out = []
    for i in range(count):
        if i == 0:
            dtype, is_safety = types[0]
        else:
            dtype, is_safety = routine[int(rng.integers(0, len(routine)))]

        code = str(rng.choice(codes, p=_CORRIDOR_WEIGHTS))
        lo, hi = kmrange[code]
        km = round(float(rng.uniform(lo, hi)), 1)
        safety = bool(is_safety)
        severity = 5 if safety else int(rng.integers(2, 5))
        dur = int(rng.choice(_DURATIONS, p=_DUR_P))

        reported = PLAN_START + timedelta(
            days=int(rng.integers(0, 16)),
            hours=int(rng.integers(8, 19)),
            minutes=int(rng.choice([0, 15, 30, 45])),
        )
        if safety:                      # safety: fix within 1-2 days
            due = reported + timedelta(hours=int(rng.integers(24, 49)))
        elif severity >= 4:             # high severity: within a week
            due = reported + timedelta(days=int(rng.integers(3, 7)))
        else:                           # routine: 1-3 weeks
            due = reported + timedelta(days=int(rng.integers(7, 22)))

        if source == "TMS":
            out.append({
                "defect_no": f"{prefix}-{i+1:04d}",
                "section": code, "km_post": km,
                "nature": dtype,
                "priority": "P1" if safety else f"P{6 - severity}",
                "reported": reported, "target": due,
                "block_hrs_req": round(dur / 60, 1),
                "remarks": fake.sentence(nb_words=6),
            })
        elif source == "SMMS":
            out.append({
                "smms_ref": f"{prefix}-{i+1:04d}",
                "section": code, "km_post": km,
                "equipment": dtype,
                "urgency": "EMERG" if safety else ("HIGH" if severity >= 4 else "NORM"),
                "logged": reported, "due": due,
                "crew_hrs": round(dur / 60, 1),
                "notes": fake.sentence(nb_words=6),
            })
        else:  # TDMS
            out.append({
                "tdms_ref": f"{prefix}-{i+1:04d}",
                "section": code, "km_post": km,
                "asset": dtype,
                "criticality": "C1" if safety else ("C2" if severity >= 4 else "C3"),
                "logged": reported, "due": due,
                "duration_min": dur,
                "note": fake.sentence(nb_words=6),
            })
    return out


def _timetable(rng):
    """Daily train patterns, repeated across the window with ±5 min jitter.
    Jitter is bounded so the min 20-min gaps can never close."""
    rows = []
    for code, trains in TRAIN_PATTERNS.items():
        for day in range(PLAN_DAYS):
            day0 = PLAN_START + timedelta(days=day)
            for hh, mm, no, name, ttype, direction, transit in trains:
                jitter = int(rng.integers(-5, 6))
                start = day0 + timedelta(minutes=hh * 60 + mm + jitter)
                rows.append({
                    "section": code, "train_no": no, "train_name": name,
                    "train_type": ttype, "direction": direction,
                    "start": start, "end": start + timedelta(minutes=transit),
                })
    return rows


def _goods(rng):
    rows = []
    for code, patterns in GOODS_PATTERNS.items():
        for weekdays, start_min, dur, label, rakes in patterns:
            for day in range(PLAN_DAYS):
                d = PLAN_START + timedelta(days=day)
                if d.weekday() in weekdays:
                    start = d + timedelta(minutes=start_min)
                    rows.append({
                        "section": code, "label": label,
                        "start": start, "end": start + timedelta(minutes=dur),
                        "expected_rakes": rakes,
                    })
    return rows


def build_all():
    """One call, everything, deterministic. Seed lives HERE — any caller
    of build_all() gets identical data, including tests."""
    rng = np.random.default_rng(SEED)
    fake = Faker(locale="en_IN", seed=SEED)
    return {
        "tms":       _defects(rng, fake, "TMS",  _TMS_TYPES,  12, "TMS-24"),
        "smms":      _defects(rng, fake, "SMMS", _SMMS_TYPES, 9,  "SMMS/OHE"),
        "tdms":      _defects(rng, fake, "TDMS", _TDMS_TYPES, 9,  "TDMS/SNT"),
        "timetable": _timetable(rng),
        "goods":     _goods(rng),
    }


if __name__ == "__main__":
    data = build_all()
    print("raw counts:", {k: len(v) for k, v in data.items()})
    print("sample TMS :", {k: v for k, v in data["tms"][0].items() if k != "remarks"})
    print("sample COA :", data["timetable"][0])
    print("SEED SMOKE TEST OK")
