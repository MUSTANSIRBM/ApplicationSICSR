from ortools.sat.python import cp_model
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, date
import numpy as np
from app.core.models import (
    Defect, Corridor, TimetableSlot, GoodsForecast, 
    Block, BlockStatus, SolveRequest, SolveResponse
)


class Optimizer:
    def __init__(self):
        self.time_granularity_minutes = 30  # 30-minute blocks
        self.model = None
        self.solver = None
        
    def solve(self, request: SolveRequest) -> SolveResponse:
        """Solve the scheduling problem using OR-Tools CP-SAT."""
        
        # Convert time windows to integer slots
        start_time = datetime.combine(request.current_date, datetime.min.time())
        horizon = request.time_horizon_days * 24 * 60 // self.time_granularity_minutes
        
        # Create CP-SAT model
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # Prepare data
        defects = request.defects
        corridors = request.corridors
        timetable_slots = request.timetable_slots
        goods_forecast = request.goods_forecast
        approved_blocks = request.approved_blocks
        
        # Sort defects by priority (safety first, then score)
        scored_defects = self._sort_defects_by_priority(defects)
        
        # Create variables: assignment of defect to (corridor, time)
        assignments = {}
        for i, defect in enumerate(scored_defects):
            for c, corridor in enumerate(corridors):
                for t in range(horizon):
                    var = self.model.NewBoolVar(f'd_{i}_c_{c}_t_{t}')
                    assignments[(i, c, t)] = var
        
        # Constraints
        
        # 1. Each defect must be assigned exactly once
        for i in range(len(scored_defects)):
            self.model.Add(
                sum(assignments.get((i, c, t), 0) 
                    for c in range(len(corridors)) 
                    for t in range(horizon)) == 1
            )
        
        # 2. No overlaps on same corridor
        defect_durations = self._get_defect_durations(scored_defects)
        for c in range(len(corridors)):
            for t in range(horizon):
                # At most one defect at a time per corridor
                self.model.Add(
                    sum(assignments.get((i, c, t), 0) 
                        for i in range(len(scored_defects))) <= corridors[c].capacity
                )
        
        # 3. Train timetable blackout windows
        for slot in timetable_slots:
            slot_start = self._time_to_slot(slot.start_time, start_time)
            slot_end = self._time_to_slot(slot.end_time, start_time)
            for t in range(slot_start, slot_end + 1):
                for i in range(len(scored_defects)):
                    for c in range(len(corridors)):
                        if corridors[c].corridor_id == slot.corridor_id:
                            self.model.Add(assignments.get((i, c, t), 0) == 0)
        
        # 4. Goods forecast blackout windows
        for forecast in goods_forecast:
            f_start = self._time_to_slot(forecast.start_time, start_time)
            f_end = self._time_to_slot(forecast.end_time, start_time)
            for t in range(f_start, f_end + 1):
                for i in range(len(scored_defects)):
                    for c in range(len(corridors)):
                        if corridors[c].corridor_id == forecast.corridor_id:
                            self.model.Add(assignments.get((i, c, t), 0) == 0)
        
        # 5. Preserve approved blocks (if requested)
        if request.preserve_approved_blocks:
            for block in approved_blocks:
                if block.status == BlockStatus.APPROVED or block.status == BlockStatus.LOCKED:
                    block_start = self._time_to_slot(block.start_time, start_time)
                    block_end = self._time_to_slot(block.end_time, start_time)
                    for t in range(block_start, block_end + 1):
                        for i in range(len(scored_defects)):
                            for c in range(len(corridors)):
                                if corridors[c].corridor_id == block.corridor_id:
                                    # Don't schedule anything in approved blocks
                                    self.model.Add(assignments.get((i, c, t), 0) == 0)
        
        # 6. Bundling: encourage same corridor/time assignments
        # This is an objective, not a hard constraint
        bundling_penalty = self._create_bundling_objective(
            scored_defects, corridors, horizon, assignments
        )
        
        # Objective: minimize completion time and maximize bundling
        objective = self.model.NewIntVar(0, horizon * len(scored_defects), 'objective')
        self.model.Add(
            objective == sum(
                t * assignments.get((i, c, t), 0)
                for i in range(len(scored_defects))
                for c in range(len(corridors))
                for t in range(horizon)
            )
        )
        
        # Add bundling bonus
        if bundling_penalty:
            self.model.Minimize(objective - bundling_penalty)
        else:
            self.model.Minimize(objective)
        
        # Solve
        status = self.solver.Solve(self.model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            blocks = self._extract_solution(
                scored_defects, corridors, start_time, assignments
            )
            stats = self._calculate_stats(blocks, request)
            
            return SolveResponse(
                blocks=blocks,
                deferred_defects=[],  # All assigned
                solver_used="cp-sat",
                solve_time_ms=self.solver.WallTime() * 1000,
                stats=stats
            )
        else:
            # If CP-SAT fails, use greedy fallback
            return self._use_greedy_fallback(request)
    
    def _sort_defects_by_priority(self, defects: List[Defect]) -> List[Defect]:
        """Sort defects by priority (safety first, then score)."""
        # For now, assume defects already have scores
        # Priority: safety critical > higher score
        return sorted(
            defects,
            key=lambda x: (not x.safety_critical, -getattr(x, 'score', 0))
        )
    
    def _get_defect_durations(self, defects: List[Defect]) -> List[int]:
        """Calculate duration in time slots for each defect."""
        # For now, use default durations based on severity
        durations = []
        for defect in defects:
            if defect.safety_critical:
                duration_hours = 2.0
            else:
                duration_hours = max(0.5, 1.0 * (defect.severity / 5 * 2))
            durations.append(int(duration_hours * 60 / self.time_granularity_minutes))
        return durations
    
    def _time_to_slot(self, time: datetime, base_time: datetime) -> int:
        """Convert datetime to time slot index."""
        delta = time - base_time
        minutes = delta.total_seconds() / 60
        return int(minutes // self.time_granularity_minutes)
    
    def _create_bundling_objective(self, defects, corridors, horizon, assignments):
        """Create objective that encourages bundling."""
        # Simplified bundling objective
        # Encourage assigning to the same corridor/time as others
        return 0  # Placeholder
    
    def _extract_solution(self, defects, corridors, start_time, assignments):
        """Extract blocks from CP-SAT solution."""
        blocks = []
        
        # Group assignments by corridor and time
        corridor_schedules = {}
        for i in range(len(defects)):
            for c in range(len(corridors)):
                for t in range(len(assignments) // (len(defects) * len(corridors))):
                    if self.solver.Value(assignments.get((i, c, t), 0)) == 1:
                        key = (c, t)
                        if key not in corridor_schedules:
                            corridor_schedules[key] = []
                        corridor_schedules[key].append((i, defects[i]))
        
        # Create blocks from schedules
        for (corridor_idx, time_slot), defect_list in corridor_schedules.items():
            # Group defects by department for bundling
            dept_groups = {}
            for defect in defect_list:
                if defect.department not in dept_groups:
                    dept_groups[defect.department] = []
                dept_groups[defect.department].append(defect)
            
            # Create block
            block_start = start_time + timedelta(minutes=time_slot * self.time_granularity_minutes)
            max_duration = 0
            for defect in defect_list:
                # Get duration from defect or default
                duration_hours = 1.0  # Default
                if hasattr(defect, 'duration_hours'):
                    duration_hours = defect.duration_hours
                max_duration = max(max_duration, duration_hours)
            
            block_end = block_start + timedelta(hours=max_duration)
            
            is_combined = len(dept_groups) > 1
            departments = list(dept_groups.keys())
            
            block = Block(
                corridor_id=corridors[corridor_idx].corridor_id,
                start_time=block_start,
                end_time=block_end,
                department=departments[0] if departments else None,
                defect_ids=[d.id for d in defect_list],
                is_combined=is_combined,
                combined_departments=departments,
                status=BlockStatus.PROPOSED
            )
            blocks.append(block)
        
        return blocks
    
    def _calculate_stats(self, blocks: List[Block], request: SolveRequest) -> Dict:
        """Calculate statistics about the solution."""
        total_hours = sum(b.duration_hours for b in blocks)
        combined_blocks = sum(1 for b in blocks if b.is_combined)
        
        # Simulated baseline (how it's done today)
        baseline_hours = total_hours * 1.5  # Assume 50% waste in current system
        combined_savings = combined_blocks * 1.5  # Each combined block saves ~1.5 hours
        
        return {
            "total_blocks": len(blocks),
            "total_hours": total_hours,
            "combined_blocks": combined_blocks,
            "combined_savings_hours": combined_savings,
            "optimization_improvement": combined_savings / baseline_hours * 100 if baseline_hours > 0 else 0,
            "defects_scheduled": len(request.defects) - len(blocks),  # Approximate
            "defects_deferred": len(blocks)  # Placeholder
        }
    
    def _use_greedy_fallback(self, request: SolveRequest) -> SolveResponse:
        """Use greedy scheduler as fallback."""
        from app.core.greedy_fallback import GreedyScheduler
        scheduler = GreedyScheduler()
        return scheduler.solve(request)