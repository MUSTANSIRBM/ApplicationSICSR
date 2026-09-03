# app/data/seed.py
import random
from datetime import datetime, timedelta
from faker import Faker
import numpy as np
from app.data.database import get_session, create_db_and_tables
from app.data.crud import CRUD
from app.core.models import Department, Defect, Corridor, TimetableSlot, GoodsForecast

fake = Faker()

# Seed for reproducibility
np.random.seed(42)
random.seed(42)


class DataSeeder:
    def __init__(self):
        self.corridors = []
        self.defects = []

    def seed_all(self):
        """Seed the entire database with synthetic data."""
        create_db_and_tables()

        session = get_session()
        try:
            crud = CRUD(session)

            # Check if data already exists
            existing_corridors = crud.get_all_corridors()
            if existing_corridors:
                print(f"✅ Database already has {len(existing_corridors)} corridors. Skipping seed.")
                return

            # Create corridors
            corridors = self._create_corridors()
            for corridor in corridors:
                crud.create_corridor(corridor)

            # Create defects
            defects = self._create_defects(corridors)
            for defect in defects:
                crud.create_defect(defect)

            print(f"✅ Seeded database with {len(corridors)} corridors, {len(defects)} defects")
        finally:
            session.close()

    def _create_corridors(self) -> list:
        """Create 5 sample corridors."""
        corridor_names = [
            ("DEL-AGRA", "Delhi-Agra"),
            ("MUM-PUNE", "Mumbai-Pune"),
            ("KOL-HOW", "Kolkata-Howrah"),
            ("CHN-BGLR", "Chennai-Bangalore"),
            ("HYB-SEC", "Hyderabad-Secunderabad")
        ]

        corridors = []
        base_date = datetime.now()

        for corridor_id, name in corridor_names:
            corridor = Corridor(
                corridor_id=corridor_id,
                name=name,
                capacity=1,
                available_from=base_date,
                available_to=base_date + timedelta(days=30)
            )
            corridors.append(corridor)

        return corridors

    def _create_defects(self, corridors: list) -> list:
        """Create realistic defect records."""
        defects = []

        # Defect descriptions by department
        defect_descriptions = {
            Department.TRACK: [
                "Rail crack detected near junction",
                "Track misalignment at curve",
                "Broken rail joint",
                "Track buckling from heat",
                "Frog points need replacement"
            ],
            Department.POWER: [
                "Overhead wire tension low",
                "Power substation maintenance",
                "Signal power supply failure",
                "Catenary wire damage",
                "Transformer oil leak"
            ],
            Department.SIGNALS: [
                "Signal light not working",
                "Signaling cable damaged",
                "Circuit board needs replacement",
                "Track circuit failure",
                "Signal interlocking fault"
            ]
        }

        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Generate ~30 defects across departments
        for i in range(30):
            dept = random.choice(list(Department))
            corridor = random.choice(corridors)

            # Create defect with realistic attributes
            severity = random.choices([1, 2, 3, 4, 5], weights=[10, 20, 30, 25, 15])[0]
            overdue_days = random.choices(
                [0, 1, 2, 5, 10, 15, 20, 30],
                weights=[20, 20, 15, 15, 10, 10, 5, 5]
            )[0]
            traffic_impact = random.choices([1, 2, 3, 4, 5], weights=[10, 20, 30, 25, 15])[0]
            safety_critical = random.random() < 0.1  # 10% safety critical

            defect = Defect(
                defect_id=f"DEF-{random.randint(10000, 99999)}",
                description=random.choice(defect_descriptions.get(dept, ["General maintenance"])),
                department=dept,
                severity=severity,
                overdue_days=overdue_days,
                traffic_impact=traffic_impact,
                safety_critical=safety_critical,
                corridor_id=corridor.corridor_id,
                system_source=dept.value.upper()[:3] if dept == Department.TRACK else
                "SMMS" if dept == Department.SIGNALS else "TDMS"
            )
            defects.append(defect)

        # Add some defects scheduled in the past (for baseline)
        for i in range(5):
            dept = random.choice(list(Department))
            corridor = random.choice(corridors)
            past_date = base_date - timedelta(days=random.randint(1, 5))

            defect = Defect(
                defect_id=f"DEF-OLD-{random.randint(10000, 99999)}",
                description=f"Historical defect - {random.choice(['Crack', 'Signal fault', 'Power issue'])}",
                department=dept,
                severity=random.randint(1, 3),
                overdue_days=random.randint(0, 3),
                traffic_impact=random.randint(1, 3),
                safety_critical=False,
                corridor_id=corridor.corridor_id,
                system_source="LEGACY",
                created_at=past_date
            )
            defects.append(defect)

        return defects


# Run seeder
if __name__ == "__main__":
    seeder = DataSeeder()
    seeder.seed_all()