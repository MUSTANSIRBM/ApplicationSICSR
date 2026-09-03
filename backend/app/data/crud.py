# app/data/crud.py
from sqlmodel import Session, select, and_
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.data.database import (
    DefectDB, CorridorDB, TimetableSlotDB,
    GoodsForecastDB, BlockDB
)
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