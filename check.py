from set_const import SessionLocal, Invoice, InvoiceLine, BillableEvent

db = SessionLocal()

print("Invoices:")
for inv in db.query(Invoice).all():
    print(inv.id, inv.client_id, inv.amount, inv.period_start, inv.period_end)

print("\nInvoice Lines:")
for line in db.query(InvoiceLine).all():
    print(line.invoice_id, line.event_id, line.amount)

print("\nEvents:")
for ev in db.query(BillableEvent).all():
    print(ev.id, ev.client_id, ev.amount, ev.event_time, ev.invoiced)
