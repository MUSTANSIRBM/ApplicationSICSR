from typing import List, Dict
from datetime import datetime, timedelta
from app.core.models import (
    Defect, Corridor, TimetableSlot, GoodsForecast,
    Block, BlockStatus, SolveRequest, SolveResponse
)


class GreedyScheduler:
    def __init__(self):
        self.time_granularity_minutes = 30
    
    def solve(self, request: SolveRequest) -> SolveResponse:
        """Greedy scheduling algorithm as fallback."""
        defects = sorted(
            request.defects,
            key=lambda x: (not x.safety_critical, -getattr(x, 'score', 0))
        )
        
        blocks = []
        deferred = []
        
        for defect in defects:
            # Find best available slot
            best_slot = self._find_best_slot(defect, request)
            
            if best_slot:
                block = Block(
                    corridor_id=best_slot['corridor_id'],
                    start_time=best_slot['start'],
                    end_time=best_slot['end'],
                    department=defect.department,
                    defect_ids=[defect.id],
                    is_combined=False,
                    combined_departments=[defect.department],
                    status=BlockStatus.PROPOSED
                )
                blocks.append(block)
            else:
                deferred.append({
                    "defect_id": defect.id,
                    "reason": "No available slots found"
                })
        
        stats = self._calculate_stats(blocks, request)
        
        return SolveResponse(
            blocks=blocks,
            deferred_defects=deferred,
            solver_used="greedy",
            solve_time_ms=0,  # Not tracking for now
            stats=stats
        )
    
    def _find_best_slot(self, defect: Defect, request: SolveRequest):
        """Find the best available slot for a defect."""
        # Simplified: try each corridor, find first available slot
        
        # Calculate required duration
        if defect.safety_critical:
            duration_hours = 2.0
        else:
            duration_hours = max(0.5, 1.0 * (defect.severity / 5 * 2))
        
        current_time = datetime.combine(request.current_date, datetime.min.time())
        max_time = current_time + timedelta(days=request.time_horizon_days)
        
        for corridor in request.corridors:
            # Check time slots
            slot_start = current_time
            while slot_start < max_time:
                slot_end = slot_start + timedelta(hours=duration_hours)
                
                # Check for conflicts
                if self._is_slot_available(
                    corridor.corridor_id, slot_start, slot_end, request
                ):
                    return {
                        'corridor_id': corridor.corridor_id,
                        'start': slot_start,
                        'end': slot_end
                    }
                
                slot_start += timedelta(minutes=self.time_granularity_minutes)
        
        return None
    
    def _is_slot_available(self, corridor_id: str, start: datetime, 
                          end: datetime, request: SolveRequest) -> bool:
        """Check if a slot is available considering all constraints."""
        # Check timetable slots
        for slot in request.timetable_slots:
            if slot.corridor_id == corridor_id:
                if not (end <= slot.start_time or start >= slot.end_time):
                    return False
        
        # Check goods forecast
        for forecast in request.goods_forecast:
            if forecast.corridor_id == corridor_id:
                if not (end <= forecast.start_time or start >= forecast.end_time):
                    return False
        
        return True
    
    def _calculate_stats(self, blocks: List[Block], request: SolveRequest) -> Dict:
        """Calculate statistics for greedy solution."""
        total_hours = sum(b.duration_hours for b in blocks)
        
        return {
            "total_blocks": len(blocks),
            "total_hours": total_hours,
            "combined_blocks": 0,  # Greedy doesn't bundle
            "combined_savings_hours": 0,
            "optimization_improvement": 0,
            "defects_scheduled": len(blocks),
            "defects_deferred": len(request.defects) - len(blocks)
        }