"""
planner/reference.py — static reference data + the planning clock.

Corridors and departments belong to OUR unified world, not to any one
source system. TMS, SMMS, TDMS, COA all reference them by code.
"""
from datetime import datetime, timedelta

# The clock: Monday 2024-06-03, 4 weeks. Generators, solver and API all
# speak these two constants. Naive on purpose (the clock rule).
PLAN_START = datetime(2024, 6, 3, 0, 0)
PLAN_DAYS = 28
PLAN_END = PLAN_START + timedelta(days=PLAN_DAYS)

CORRIDORS = [
    {"code": "NGP-BSL", "name": "Nagpur Jn - Bhusaval Jn",        "zone": "CR",  "km_start": 0.0, "km_end": 310.5, "lines": 2, "traffic": "HEAVY"},
    {"code": "ET-NGP",  "name": "Itarsi Jn - Nagpur Jn",          "zone": "CR",  "km_start": 0.0, "km_end": 178.0, "lines": 2, "traffic": "MEDIUM"},
    {"code": "BSL-MMR", "name": "Bhusaval Jn - Manmad Jn",        "zone": "CR",  "km_start": 0.0, "km_end": 105.2, "lines": 2, "traffic": "LIGHT"},
    {"code": "SC-GTL",  "name": "Secunderabad Jn - Guntakal Jn",  "zone": "SCR", "km_start": 0.0, "km_end": 308.0, "lines": 2, "traffic": "MEDIUM"},
    {"code": "MAS-TRY", "name": "Chennai Egmore - Tiruchchirappalli", "zone": "SR", "km_start": 0.0, "km_end": 336.0, "lines": 2, "traffic": "LIGHT"},
]

DEPARTMENTS = [
    {"code": "ENG", "name": "Engineering / Track", "source": "TMS"},
    {"code": "TRD", "name": "TRD / Power (OHE)",   "source": "SMMS"},
    {"code": "SNT", "name": "S&T / Signalling",    "source": "TDMS"},
]


if __name__ == "__main__":
    print(f"window     : {PLAN_START} -> {PLAN_END}")
    print(f"corridors  : {[c['code'] for c in CORRIDORS]}")
    print(f"departments: {[d['code'] for d in DEPARTMENTS]}")
