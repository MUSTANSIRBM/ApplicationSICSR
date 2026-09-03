# app/adapters/mock_coa.py
import random
from typing import List
from datetime import datetime, timedelta
from app.adapters.base import BaseCOAAdapter
from app.core.models import TimetableSlot, GoodsForecast


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