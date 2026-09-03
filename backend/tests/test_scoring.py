# tests/test_scoring.py
import pytest
from datetime import date, timedelta
from app.core.scoring import ScoringEngine
from app.core.models import Defect, Department


def test_score_defect():
    engine = ScoringEngine()
    
    defect = Defect(
        defect_id="TEST-001",
        description="Test defect",
        department=Department.TRACK,
        severity=4,
        overdue_days=5,
        traffic_impact=3,
        safety_critical=False,
        corridor_id="TEST-CORR",
        system_source="TEST"
    )
    
    result = engine.score_defect(defect, date.today())
    
    assert result.score > 0
    assert result.score < 100
    assert "severity_score" in result.breakdown


def test_safety_critical_score():
    engine = ScoringEngine()
    
    defect = Defect(
        defect_id="TEST-002",
        description="Safety critical defect",
        department=Department.TRACK,
        severity=1,  # Low severity
        overdue_days=0,
        traffic_impact=1,
        safety_critical=True,
        corridor_id="TEST-CORR",
        system_source="TEST"
    )
    
    result = engine.score_defect(defect, date.today())
    
    assert result.score == 100.0
    assert result.tier.value == "safety_critical"


# tests/test_optimizer.py
def test_optimizer_solves():
    from app.core.optimizer import Optimizer
    from app.core.models import SolveRequest
    
    # Create minimal test data
    # ...
    pass