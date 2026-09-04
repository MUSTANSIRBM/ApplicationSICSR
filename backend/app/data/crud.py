# app/data/crud.py
from sqlmodel import Session, select, and_, update
from typing import List, Optional,Dict
from datetime import datetime, timedelta
from uuid import UUID
from app.data.database import (
    DefectDB, CorridorDB, TimetableSlotDB,
    GoodsForecastDB, BlockDB
)

from app.core.models import Defect, Corridor, Block, DefectStatus, BlockStatus
from app.core.models import Defect, Corridor, TimetableSlot, GoodsForecast, Block, Department, DefectStatus, BlockStatus


class CRUD:
    def __init__(self, session: Session):
        self.session = session

    # Defect CRUD
    def create_defect(self, defect: Defect) -> Defect:
        # Handle department as either Enum or string
        department_value = defect.department.value if hasattr(defect.department, 'value') else str(defect.department)
        status_value = defect.status.value if hasattr(defect.status, 'value') else str(defect.status)

        db_defect = DefectDB(
            id=defect.id,
            defect_id=defect.defect_id,
            description=defect.description,
            department=department_value,
            severity=defect.severity,
            overdue_days=defect.overdue_days,
            traffic_impact=defect.traffic_impact,
            safety_critical=defect.safety_critical,
            corridor_id=defect.corridor_id,
            system_source=defect.system_source,
            status=status_value,
            score=defect.score
        )
        self.session.add(db_defect)
        self.session.commit()
        self.session.refresh(db_defect)
        return self._defect_from_db(db_defect)

    def get_defect(self, defect_id: UUID) -> Optional[Defect]:
        db_defect = self.session.get(DefectDB, defect_id)
        if db_defect:
            return self._defect_from_db(db_defect)
        return None

    def get_all_defects(self) -> List[Defect]:
        db_defects = self.session.exec(select(DefectDB)).all()
        return [self._defect_from_db(d) for d in db_defects]

    def get_defects_by_department(self, department: str) -> List[Defect]:
        db_defects = self.session.exec(
            select(DefectDB).where(DefectDB.department == department)
        ).all()
        return [self._defect_from_db(d) for d in db_defects]

    def update_defect_status(self, defect_id: UUID, status: str) -> Optional[Defect]:
        db_defect = self.session.get(DefectDB, defect_id)
        if db_defect:
            db_defect.status = status
            self.session.commit()
            self.session.refresh(db_defect)
            return self._defect_from_db(db_defect)
        return None

    # Corridor CRUD
    def create_corridor(self, corridor: Corridor) -> Corridor:
        db_corridor = CorridorDB(
            id=corridor.id,
            corridor_id=corridor.corridor_id,
            name=corridor.name,
            capacity=corridor.capacity,
            available_from=corridor.available_from,
            available_to=corridor.available_to
        )
        self.session.add(db_corridor)
        self.session.commit()
        self.session.refresh(db_corridor)
        return self._corridor_from_db(db_corridor)

    def get_all_corridors(self) -> List[Corridor]:
        db_corridors = self.session.exec(select(CorridorDB)).all()
        return [self._corridor_from_db(c) for c in db_corridors]

    # Block CRUD
    def create_block(self, block: Block) -> Block:
        # Handle department as either Enum or string
        department_value = block.department.value if hasattr(block.department, 'value') else str(
            block.department) if block.department else ""
        status_value = block.status.value if hasattr(block.status, 'value') else str(block.status)
        combined_depts = ",".join(d.value if hasattr(d, 'value') else str(d) for d in block.combined_departments)

        db_block = BlockDB(
            id=block.id,
            corridor_id=block.corridor_id,
            start_time=block.start_time,
            end_time=block.end_time,
            department=department_value,
            defect_ids=",".join(str(d) for d in block.defect_ids),
            is_combined=block.is_combined,
            combined_departments=combined_depts,
            status=status_value
        )
        self.session.add(db_block)
        self.session.commit()
        self.session.refresh(db_block)
        return self._block_from_db(db_block)

    def get_blocks(self, start_date: datetime, end_date: datetime) -> List[Block]:
        db_blocks = self.session.exec(
            select(BlockDB).where(
                and_(
                    BlockDB.start_time >= start_date,
                    BlockDB.end_time <= end_date
                )
            )
        ).all()
        return [self._block_from_db(b) for b in db_blocks]

    def update_block_status(self, block_id: UUID, status: str) -> Optional[Block]:
        db_block = self.session.get(BlockDB, block_id)
        if db_block:
            db_block.status = status
            if status == "LOCKED":
                db_block.locked_at = datetime.now()
            elif status == "EXECUTED":
                db_block.executed_at = datetime.now()
            self.session.commit()
            self.session.refresh(db_block)
            return self._block_from_db(db_block)
        return None

    # Helper conversion functions
    def _defect_from_db(self, db_defect: DefectDB) -> Defect:
        # Handle department - convert string to Enum
        department_value = db_defect.department
        if isinstance(department_value, str):
            try:
                department_enum = Department(department_value)
            except ValueError:
                # If the string doesn't match, try to find by value
                for dept in Department:
                    if dept.value == department_value:
                        department_enum = dept
                        break
                else:
                    department_enum = Department.TRACK  # Default
        else:
            department_enum = department_value

        # Handle status - convert string to Enum
        status_value = db_defect.status
        if isinstance(status_value, str):
            try:
                status_enum = DefectStatus(status_value)
            except ValueError:
                for stat in DefectStatus:
                    if stat.value == status_value:
                        status_enum = stat
                        break
                else:
                    status_enum = DefectStatus.NEW
        else:
            status_enum = status_value

        return Defect(
            id=db_defect.id,
            defect_id=db_defect.defect_id,
            description=db_defect.description,
            department=department_enum,
            severity=db_defect.severity,
            overdue_days=db_defect.overdue_days,
            traffic_impact=db_defect.traffic_impact,
            safety_critical=db_defect.safety_critical,
            corridor_id=db_defect.corridor_id,
            system_source=db_defect.system_source,
            created_at=db_defect.created_at,
            status=status_enum,
            score=db_defect.score
        )

    def _corridor_from_db(self, db_corridor: CorridorDB) -> Corridor:
        return Corridor(
            id=db_corridor.id,
            corridor_id=db_corridor.corridor_id,
            name=db_corridor.name,
            capacity=db_corridor.capacity,
            available_from=db_corridor.available_from,
            available_to=db_corridor.available_to
        )

    def _block_from_db(self, db_block: BlockDB) -> Block:
        # Handle department - convert string to Enum
        dept_value = db_block.department
        if dept_value and isinstance(dept_value, str):
            try:
                dept_enum = Department(dept_value)
            except ValueError:
                for dept in Department:
                    if dept.value == dept_value:
                        dept_enum = dept
                        break
                else:
                    dept_enum = None
        else:
            dept_enum = dept_value if dept_value else None

        # Handle status - convert string to Enum
        status_value = db_block.status
        if isinstance(status_value, str):
            try:
                status_enum = BlockStatus(status_value)
            except ValueError:
                for stat in BlockStatus:
                    if stat.value == status_value:
                        status_enum = stat
                        break
                else:
                    status_enum = BlockStatus.PROPOSED
        else:
            status_enum = status_value

        # Handle combined departments
        combined_depts = []
        if db_block.combined_departments:
            for d in db_block.combined_departments.split(","):
                if d:
                    try:
                        combined_depts.append(Department(d))
                    except ValueError:
                        for dept in Department:
                            if dept.value == d:
                                combined_depts.append(dept)
                                break

        return Block(
            id=db_block.id,
            corridor_id=db_block.corridor_id,
            start_time=db_block.start_time,
            end_time=db_block.end_time,
            department=dept_enum,
            defect_ids=[UUID(d) for d in db_block.defect_ids.split(",") if d],
            is_combined=db_block.is_combined,
            combined_departments=combined_depts,
            status=status_enum,
            locked_at=db_block.locked_at,
            executed_at=db_block.executed_at
        )

    def update_defect(self, defect_id: UUID, status: Optional[str] = None, deferral_reason: Optional[str] = None) -> \
    Optional[Defect]:
        """Update defect status and/or deferral reason."""
        db_defect = self.session.get(DefectDB, defect_id)
        if not db_defect:
            return None

        if status is not None:
            # Validate status
            valid_statuses = [s.value for s in DefectStatus]
            if status.upper() in valid_statuses:
                db_defect.status = status.upper()

        if deferral_reason is not None:
            db_defect.deferral_reason = deferral_reason

        self.session.commit()
        self.session.refresh(db_defect)
        return self._defect_from_db(db_defect)

    def delete_defect(self, defect_id: UUID, soft_delete: bool = True) -> bool:
        """Delete or soft-delete a defect."""
        db_defect = self.session.get(DefectDB, defect_id)
        if not db_defect:
            return False

        if soft_delete:
            # Soft delete - update status to something like "CANCELLED"
            db_defect.status = "CANCELLED"
            self.session.commit()
        else:
            # Hard delete
            self.session.delete(db_defect)
            self.session.commit()

        return True

    def update_block_status(self, block_id: UUID, status: str) -> Optional[Block]:
        """Update block status (APPROVED, LOCKED, etc.)."""
        db_block = self.session.get(BlockDB, block_id)
        if not db_block:
            return None

        # Validate status
        valid_statuses = [s.value for s in BlockStatus]
        if status.upper() in valid_statuses:
            db_block.status = status.upper()

            if status.upper() == "LOCKED":
                db_block.locked_at = datetime.now()

        self.session.commit()
        self.session.refresh(db_block)
        return self._block_from_db(db_block)

    def get_trains_and_goods(self, start_date: datetime, end_date: datetime) -> Dict[str, List[Dict]]:
        """Get trains and goods for occupancy data."""
        from app.data.database import TimetableSlotDB, GoodsForecastDB

        # Get trains
        trains = []
        db_trains = self.session.exec(
            select(TimetableSlotDB).where(
                and_(
                    TimetableSlotDB.start_time >= start_date,
                    TimetableSlotDB.end_time <= end_date
                )
            )
        ).all()

        for t in db_trains:
            trains.append({
                "corridor_id": t.corridor_id,
                "start_time": t.start_time.isoformat(),
                "end_time": t.end_time.isoformat(),
                "train_id": t.train_id
            })

        # Get goods
        goods = []
        db_goods = self.session.exec(
            select(GoodsForecastDB).where(
                and_(
                    GoodsForecastDB.start_time >= start_date,
                    GoodsForecastDB.end_time <= end_date
                )
            )
        ).all()

        for g in db_goods:
            goods.append({
                "corridor_id": g.corridor_id,
                "start_time": g.start_time.isoformat(),
                "end_time": g.end_time.isoformat(),
                "train_id": g.train_id
            })

        return {"trains": trains, "goods": goods}

    def get_weekly_trend(self, start_date: datetime) -> List[Dict]:
        """Get weekly trend data for impact dashboard."""
        # Get blocks from the week
        end_date = start_date + timedelta(days=7)
        blocks = self.get_blocks(start_date, end_date)

        # Group by day
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        result = []

        for i, day in enumerate(days):
            day_date = start_date + timedelta(days=i)
            day_blocks = [b for b in blocks if b.start_time.date() == day_date.date()]

            result.append({
                "day": day,
                "planned": len(day_blocks),
                "actual": len(day_blocks)  # In real system, could be different
            })

        return result

    def get_defects_by_department(self) -> Dict[str, int]:
        """Get defect counts by department."""
        defects = self.get_all_defects()
        result = {}
        for defect in defects:
            dept = defect.department.value if hasattr(defect.department, 'value') else str(defect.department)
            result[dept.lower()] = result.get(dept.lower(), 0) + 1
        return result

    def get_critical_waiting_count(self) -> int:
        """Get count of critical defects waiting."""
        defects = self.get_all_defects()
        return len([
            d for d in defects
            if d.safety_critical and str(d.status).upper() in ["NEW", "SCORED"]
        ])

    def get_conflicts_resolved_count(self) -> int:
        """Get count of conflicts resolved (blocks that resolved conflicts)."""
        blocks = self.get_blocks(
            datetime.now() - timedelta(days=7),
            datetime.now()
        )
        # Count combined blocks as resolved conflicts
        return sum(1 for b in blocks if b.is_combined)