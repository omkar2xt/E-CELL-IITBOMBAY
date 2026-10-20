# StorePulse AI — Database Initialization & Migrations
# Developer: Omkar Gurav

import os
import sys
import json
import time

# Ensure root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.database.connection import engine, SessionLocal
from backend.database.models import Base, Store, ZoneModel, AuditLog
from backend.zone_analytics import ZoneAnalyticsEngine


def init_database():
    """
    Safely initialize all database tables and seed required reference records.
    Never drops existing tables or deletes data.
    """
    print("[Database] Creating tables if not exist...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Seed Default Store
        existing_store = db.query(Store).filter(Store.id == "store-01").first()
        if not existing_store:
            store = Store(
                id="store-01",
                name="StorePulse Flagship Store #1",
                created_at=time.time()
            )
            db.add(store)
            db.commit()
            print("[Database] Seeded default store 'store-01'")

        # 2. Seed Default Zones from ZoneAnalyticsEngine
        default_zones = ZoneAnalyticsEngine.default_zones()
        for z in default_zones:
            existing_zone = db.query(ZoneModel).filter(ZoneModel.id == z.id).first()
            if not existing_zone:
                zm = ZoneModel(
                    id=z.id,
                    store_id="store-01",
                    name=z.name,
                    zone_type=z.type,
                    configuration=json.dumps(z.polygon),
                    capacity=z.capacity,
                    dwell_alert_seconds=z.dwell_alert_seconds,
                    created_at=time.time()
                )
                db.add(zm)
        db.commit()
        print(f"[Database] Verified {len(default_zones)} default retail zones")

        # 3. Seed Default Baseline Layout
        from backend.database.models import LayoutModel
        from backend.simulator import layout_store
        existing_baseline = db.query(LayoutModel).filter(LayoutModel.is_baseline == True).first()
        if not existing_baseline:
            layout_store._persist_to_db(layout_store._default_baseline_config())
            print("[Database] Seeded default store baseline layout into database")

        # 4. Record Audit Log Entry
        audit = AuditLog(
            event_type="SYSTEM_INIT",
            description="Database initialized and verified successfully",
            timestamp=time.time(),
            details_json=json.dumps({"version": "1.1.0", "storage": "postgres_ready"})
        )
        db.add(audit)
        db.commit()
        print("[Database] Initialization complete. Schema ready.")

    except Exception as e:
        db.rollback()
        print(f"[Database] Error initializing database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
