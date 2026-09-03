# app/adapters/mock_tms.py
import random
from typing import List
from datetime import datetime, timedelta
from app.adapters.base import BaseAdapter
from app.core.models import Defect, Department


class MockTMSAdapter(BaseAdapter):
    """Mock adapter for Track Management System."""

    def get_defects(self) -> List[Defect]:
        """Generate mock track defects."""
        defects = []
        descriptions = [
            "Rail crack detected",
            "Track misalignment",
            "Broken rail joint",
            "Track buckling",
            "Frog points worn out",
            "Missing track fasteners",
            "Sleeper decay"
        ]

        for i in range(8):
            defect = Defect(
                defect_id=f"TMS-{1000 + i}",
                description=random.choice(descriptions),
                department=Department.TRACK,
                severity=random.randint(2, 5),
                overdue_days=random.randint(0, 10),
                traffic_impact=random.randint(2, 4),
                safety_critical=random.random() < 0.15,
                corridor_id=random.choice(["DEL-AGRA", "MUM-PUNE", "KOL-HOW"]),
                system_source="TMS"
            )
            defects.append(defect)

        return defects