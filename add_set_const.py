from set_const import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE invoices ADD COLUMN sent_at TEXT"))
    conn.execute(text("ALTER TABLE invoices ADD COLUMN client_name TEXT"))
    conn.commit()

print("✅ Columns added successfully.")
