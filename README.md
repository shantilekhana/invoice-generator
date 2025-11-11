# invoice-generator

Purpose: A local app that simulates an invoice-generation agent using a streamlit dashboard to trigger runs. PDFs are generated on demand for confirmation purposes.

# Files
- set_const.py
  SQLAlchemy model and DB session - used to define tables
  Setting(invoicing_last_updated)
  BillableEvent(id, client_d, amount, event_time, invoiced)
  Invoice, InvoiceLine, InvoiceRun (invoice metadata, lines, runs)
- add_event.py
  CLI helper to insert a single billable event into DB
- run_invoice2.py
  Read invoicing_last_updated
  Fetches unprocessed events
  Groups by client_id, Invoice
  Marks processed events as True
  Runs the log and updates invoicing_last_updated
- check.py
  prints DB content
- app.py
  Dashboard to trigger runs and display recently processed invoices

# Setup
  1. Create & activate your venv, install deps:

  python -m venv .venv
  . .venv/bin/activate    # or .venv\Scripts\activate on Windows
  pip install -r requirements.txt
  (requirements: sqlalchemy, streamlit, reportlab (plus your DB driver if needed))


  2. Create DB / models (one-time):

  python set_const.py
  python add_set_const.py

  3. Seed events
     python add_event.py client_abc 2000

  4. Run agent
     python run_invoice2.py

  5. Run Streamlit
     streamlit run app.py
  
