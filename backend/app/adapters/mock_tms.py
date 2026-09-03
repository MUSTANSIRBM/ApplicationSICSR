# app/adapters/base.py
from abc import ABC, abstractmethod
from typing import List
from app.core.models import Defect, TimetableSlot, GoodsForecast


class BaseAdapter(ABC):
    @abstractmethod
    def get_defects(self) -> List[Defect]:
        pass


class BaseCOAAdapter(ABC):
    @abstractmethod
    def get_timetable(self) -> List[TimetableSlot]:
        pass
    
    @abstractmethod
    def get_goods_forecast(self) -> List[GoodsForecast]:
        pass


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


# app/adapters/mock_smms.py
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


# app/adapters/mock_tdms.py
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


# app/adapters/mock_coa.py
class MockCOAAdapter(BaseCOAAdapter):
    """Mock adapter for Central Operations Authority."""
    
    def get_timetable(self) -> List[TimetableSlot]:
        """Generate mock train timetable."""
        slots = []
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        corridors = ["DEL-AGRA", "MUM-PUNE", "KOL-HOW", "CHN-BGLR", "HYB-SEC"]
        
        for corridor in corridors[:3]:
            for day in range(7):
                for hour in [6, 9, 12, 15, 18, 21]:
                    slot_time = base_date + timedelta(days=day, hours=hour)
                    slot = TimetableSlot(
                        corridor_id=corridor,
                        train_id=f"TRAIN-{random.randint(1000, 9999)}",
                        start_time=slot_time,
                        end_time=slot_time + timedelta(hours=2),
                        is_goods=False,
                        priority=1
                    )
                    slots.append(slot)
        
        return slots
    
    def get_goods_forecast(self) -> List[GoodsForecast]:
        """Generate mock goods train forecast."""
        forecasts = []
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        corridors = ["DEL-AGRA", "MUM-PUNE", "KOL-HOW", "CHN-BGLR", "HYB-SEC"]
        
        for corridor in corridors:
            for day in range(7):
                for _ in range(random.randint(1, 2)):
                    hour = random.randint(1, 23)
                    forecast_time = base_date + timedelta(days=day, hours=hour)
                    forecast = GoodsForecast(
                        corridor_id=corridor,
                        train_id=f"GOODS-{random.randint(1000, 9999)}",
                        start_time=forecast_time,
                        end_time=forecast_time + timedelta(hours=random.randint(3, 6)),
                        forecast_type=random.choice(["scheduled", "estimated"])
                    )
                    forecasts.append(forecast)
        
        return forecasts