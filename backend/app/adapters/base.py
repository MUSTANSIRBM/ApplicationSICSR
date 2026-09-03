# app/adapters/base.py
from abc import ABC, abstractmethod
from typing import List
from app.core.models import Defect, TimetableSlot, GoodsForecast


class BaseAdapter(ABC):
    """Base adapter for defect management systems."""

    @abstractmethod
    def get_defects(self) -> List[Defect]:
        """Get defects from the source system."""
        pass


class BaseCOAAdapter(ABC):
    """Base adapter for Central Operations Authority (COA)."""

    @abstractmethod
    def get_timetable(self) -> List[TimetableSlot]:
        """Get train timetable slots."""
        pass

    @abstractmethod
    def get_goods_forecast(self) -> List[GoodsForecast]:
        """Get goods train forecast."""
        pass