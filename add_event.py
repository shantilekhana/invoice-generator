import sys
import uuid
import datetime
from datetime import timezone, timedelta

from set_const import SessionLocal, BillableEvent


IST = timezone(timedelta(hours=5, minutes=30))

def make_event(client_id="client_abc", amount=42.0):
    db = SessionLocal()
    try:
        now = datetime.datetime.now(IST)
        
        naive_now = now.replace(tzinfo=None)
        ext_id = f"sim-{uuid.uuid4().hex[:12]}"
        ev = BillableEvent(
            external_id=ext_id,
            client_id=client_id,
            amount=amount,
            event_time=naive_now,
            invoiced=False
        )
        db.add(ev)
        db.commit()
        print("Inserted event:", ext_id, "client:", client_id, "amount:", amount, "time:", now.strftime("%Y-%m-%d %H:%M:%S IST"))
    finally:
        db.close()

if __name__ == "__main__":
    
    client = sys.argv[1] if len(sys.argv) > 1 else "client_abc"
    amt = float(sys.argv[2]) if len(sys.argv) > 2 else 99.99
    make_event(client, amt)
