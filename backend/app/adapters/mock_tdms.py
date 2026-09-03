# app/adapters/mock_tdms.py
import random
from typing import List
from datetime import datetime, timedelta
from app.adapters.base import BaseAdapter
from app.core.models import Defect, Department


class MockTDMSAdapter(BaseAdapter):
    """Mock adapter for Traction Distribution Management System."""

    def get_defects(self) -> List[Defect]:
        """Generate mock power defects."""
        defects = []
        descriptions = [
            "Low OHE tension",
            "Substation maintenance needed",
            "Catenary wire damage",
            "Transformer issue",
            "Power supply interruption",
            "Overhead wire sagging"
        ]

        for i in range(6):
            defect = Defect(
                defect_id=f"TDMS-{1000 + i}",
                description=random.choice(descriptions),
                department=Department.POWER,
                severity=random.randint(1, 4),
                overdue_days=random.randint(0, 7),
                traffic_impact=random.randint(1, 4),
                safety_critical=random.random() < 0.08,
                corridor_id=random.choice(["MUM-PUNE", "KOL-HOW", "HYB-SEC"]),
                system_source="TDMS"
            )
            defects.append(defect)

        return defects