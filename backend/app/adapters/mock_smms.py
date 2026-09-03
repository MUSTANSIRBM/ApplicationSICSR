# app/adapters/mock_smms.py
import random
from typing import List
from datetime import datetime, timedelta
from app.adapters.base import BaseAdapter
from app.core.models import Defect, Department


class MockSMMSAdapter(BaseAdapter):
    """Mock adapter for Signal Management System."""

    def get_defects(self) -> List[Defect]:
        """Generate mock signal defects."""
        defects = []
        descriptions = [
            "Signal light failure",
            "Damaged signaling cable",
            "Circuit board fault",
            "Track circuit malfunction",
            "Signal interlocking issue",
            "Switch point problem"
        ]

        for i in range(6):
            defect = Defect(
                defect_id=f"SMMS-{1000 + i}",
                description=random.choice(descriptions),
                department=Department.SIGNALS,
                severity=random.randint(1, 5),
                overdue_days=random.randint(0, 8),
                traffic_impact=random.randint(3, 5),
                safety_critical=random.random() < 0.1,
                corridor_id=random.choice(["DEL-AGRA", "MUM-PUNE", "CHN-BGLR"]),
                system_source="SMMS"
            )
            defects.append(defect)

        return defects