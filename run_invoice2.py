import datetime
import uuid
from collections import defaultdict

from sqlalchemy.exc import IntegrityError

from set_const import (
    SessionLocal, Setting, BillableEvent,
    Invoice, InvoiceLine, InvoiceRun
)

def get_last_updated(db):
    row = db.query(Setting).filter(Setting.key == "invoicing_last_updated").first()
    if not row or not row.value:
        return None
    return datetime.datetime.fromisoformat(row.value)
from datetime import timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))


def set_last_updated(db, ts):
    """Update invoicing_last_updated in the settings table."""
    iso = ts.isoformat()
    row = db.query(Setting).filter(Setting.key == "invoicing_last_updated").first()
    if not row:
        row = Setting(key="invoicing_last_updated", value=iso)
        db.add(row)
    else:
        row.value = iso
    db.commit()
    print(f"✅ Updated invoicing_last_updated to {iso}")


def run_invoicing_create_invoices():
    db = SessionLocal()
    run_id = str(uuid.uuid4())
    now = datetime.datetime.now(IST)


    run = InvoiceRun(
        id=run_id,
        started_at=now,
        status="running",
        start_time_used=None,
        end_time_used=None
    )
    db.add(run)
    db.commit() 

    try:
        start_time = get_last_updated(db)
        if start_time is None:
            start_time = datetime.datetime(1970,1,1)
        end_time = datetime.datetime.now(IST)        
        run.start_time_used = start_time
        run.end_time_used = end_time
        db.commit()    
        events = (
            db.query(BillableEvent)
              .filter(BillableEvent.event_time >= start_time,
                      BillableEvent.event_time < end_time,
                      BillableEvent.invoiced == False)
              .order_by(BillableEvent.event_time.asc())
              .all()
        )      
        by_client = defaultdict(list)
        for ev in events:
            by_client[ev.client_id].append(ev)

        created_invoices = 0
        created_lines = 0

        
        for client_id, ev_list in by_client.items():
            invoice_id = str(uuid.uuid4())
            total_amount = sum(float(e.amount) for e in ev_list)

            invoice = Invoice(
                id=invoice_id,
                client_id=client_id,
                period_start=start_time,
                period_end=end_time,
                amount=total_amount,
                status="draft",
                run_id=run_id
            )
            invoice.sent_at = datetime.datetime.now(IST)
            db.add(invoice)
            db.commit()  

            for ev in ev_list:
                line = InvoiceLine(invoice_id=invoice_id, event_id=ev.id, amount=ev.amount)
                db.add(line)
                try:
                    db.commit()
                    created_lines += 1
                  
                    ev.invoiced = True
                    db.add(ev)
                    db.commit()
                except IntegrityError:
                  
                    db.rollback()
                    print(f"Skipped event {ev.id} (likely already invoiced).")
            created_invoices += 1

        run.ended_at = datetime.datetime.now(IST)
        run.status = "success"
        db.add(run)
        db.commit()


        set_last_updated(db, end_time)

        print(f"Run {run_id} complete: invoices_created={created_invoices}, invoice_lines_created={created_lines}")
        print(f"Window: {start_time.isoformat()} -> {end_time.isoformat()}")
        return {"run_id": run_id, "invoices": created_invoices, "lines": created_lines}

    except Exception as e:
      
        db.rollback()
        run.ended_at = datetime.datetime.now(IST)
        run.status = "failed"
        run.error_message = str(e)
        db.add(run)
        db.commit()
        print(f"Run {run_id} failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_invoicing_create_invoices()
