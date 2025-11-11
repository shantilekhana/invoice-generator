import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Boolean, Numeric, Text,
    CheckConstraint, UniqueConstraint, ForeignKey, event
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError

# CONFIG
DATABASE_URL = "sqlite:///./invoices_constraints.db"


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_connection, connection_record):
   
    dbapi_connection.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=True)

class BillableEvent(Base):
    __tablename__ = "billable_events"
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, nullable=False, unique=True, index=True)  # unique id from source system
    client_id = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    event_time = Column(DateTime, default=datetime.datetime.utcnow)
    invoiced = Column(Boolean, default=False)

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_amount_positive"),
    )

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(String, primary_key=True, index=True)  # uuid string
    client_id = Column(String, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    amount = Column(Numeric, nullable=False)
    status = Column(String, default="draft")  # draft | sending | sent | failed
    run_id = Column(String, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    client_name = Column(String, nullable=True)

class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(String, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(Integer, ForeignKey("billable_events.id", ondelete="RESTRICT"), nullable=False)
    amount = Column(Numeric, nullable=False)

    __table_args__ = (
        UniqueConstraint("event_id", name="uq_invoice_line_event"),
    )

class InvoiceRun(Base):
    __tablename__ = "invoice_runs"
    id = Column(String, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String, default="running")  # running | success | failed
    start_time_used = Column(DateTime, nullable=True)
    end_time_used = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


def create_schema():
    print("Creating schema (if not exists)...")
    Base.metadata.create_all(bind=engine)
    print("Schema ready.")


def seed_events():
    db = SessionLocal()
    try:
        if db.query(BillableEvent).count() > 0:
            print("Events already seeded, skipping.")
            return

        now = datetime.datetime.utcnow()
        samples = [
            {"external_id": "src-1001", "client_id": "client_abc", "amount": 120.50, "event_time": now - datetime.timedelta(days=2)},
            {"external_id": "src-1002", "client_id": "client_abc", "amount": 75.00,  "event_time": now - datetime.timedelta(days=1, hours=3)},
            {"external_id": "src-2001", "client_id": "client_xyz", "amount": 300.00, "event_time": now - datetime.timedelta(hours=20)},
            {"external_id": "src-2002", "client_id": "client_xyz", "amount": 50.00,  "event_time": now - datetime.timedelta(hours=2)},
        ]
        for s in samples:
            ev = BillableEvent(**s)
            db.add(ev)
        db.commit()
        print(f"Seeded {len(samples)} events.")
    finally:
        db.close()

# small test: try to insert duplicate external_id to show constraint works
def test_unique_constraint():
    db = SessionLocal()
    try:
        ev = BillableEvent(external_id="src-1001", client_id="client_dup", amount=10.0)
        db.add(ev)
        try:
            db.commit()
            print("ERROR: duplicate external_id inserted (unexpected).")
        except IntegrityError as e:
            db.rollback()
            print("IntegrityError caught as expected for duplicate external_id:", e.orig)
    finally:
        db.close()

if __name__ == "__main__":
    create_schema()
    seed_events()
    test_unique_constraint()
    print("Done. DB file: invoices_constraints.db")
