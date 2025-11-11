import io
import os
from datetime import datetime, timezone, timedelta

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


from run_invoice2 import run_invoicing_create_invoices as RUN_FN
from set_const import SessionLocal, Setting, Invoice

st.set_page_config(page_title="Invoice Agent", layout="centered")
st.markdown(
    """
    <style>
    /* card look */
    .card {background:#ffffff;padding:18px;border-radius:12px;box-shadow:0 6px 20px rgba(12,22,46,0.06); margin-bottom:16px}
    .muted {color:#6b7280;font-size:13px}
    .small {font-size:13px;color:#6b7280}
    .badge {display:inline-block;padding:4px 8px;border-radius:999px;background:#e6fffa;color:#035f52;font-size:12px}

    /* Make Streamlit buttons and download buttons non-wrapping and with min width */
    .stButton>button, .stDownloadButton>button {
      white-space: nowrap;
      min-width: 92px;
      padding: 8px 12px;
      border-radius: 8px;
    }

    /* Make the Run button larger */
    .run-button-style .stButton>button {
      background-color: #0f766e;
      color: white;
      font-weight: 700;
      padding: 10px 20px;
      min-width: 120px;
    }

    /* Narrow table cells shouldn't cause wrapping of button text */
    .invoice-action-col .stDownloadButton>button { min-width: 100px; }

    </style>
    """,
    unsafe_allow_html=True,
)


IST = timezone(timedelta(hours=5, minutes=30))


def format_ist(dt):
    if dt is None:
        return "N/A"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def get_last_updated():
    db = SessionLocal()
    try:
        row = db.query(Setting).filter(Setting.key == "invoicing_last_updated").first()
        return row.value if row else None
    finally:
        db.close()


def get_invoices(limit=10, client_query=None):
    db = SessionLocal()
    try:
        q = db.query(Invoice)
        if client_query:
            q = q.filter(Invoice.client_id.ilike(f"%{client_query}%"))

        try:
            rows = q.order_by(Invoice.sent_at.desc()).limit(limit).all()
        except Exception:
            rows = q.order_by(Invoice.id.desc()).limit(limit).all()
        return rows
    finally:
        db.close()


def render_invoice_confirmation_pdf_bytes(inv):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    x, y = 50, h - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, "INVOICE CONFIRMATION")
    y -= 36
    c.setFont("Helvetica", 11)
    fields = [
        ("Invoice ID", getattr(inv, "id", "N/A")),
        ("Client ID", getattr(inv, "client_id", "N/A")),
        ("Client Name", getattr(inv, "client_name", "N/A")),
        ("Status", getattr(inv, "status", "Processed")),
        ("Processed At", format_ist(getattr(inv, "sent_at", None))),
    ]
    for label, val in fields:
        c.drawString(x, y, f"{label}: {val}")
        y -= 18
    y -= 12
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(x, y, "This document confirms invoice processing. No financial data is included.")
    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

if "last_run" not in st.session_state:
    st.session_state["last_run"] = None
if "running" not in st.session_state:
    st.session_state["running"] = False
if "query" not in st.session_state:
    st.session_state["query"] = ""



st.markdown("### 📦 Invoice Agent")
left_col, right_col = st.columns([3, 1])
with left_col:
    last_ts = get_last_updated()
    st.markdown("**Last checkpoint (invoicing last updated):**")
    st.markdown(f"**{format_ist(last_ts)}**")
with right_col:

    st.markdown("<div class='run-button-style'>", unsafe_allow_html=True)
    run_clicked = st.button("Run", key="run_btn")
    st.markdown("</div>", unsafe_allow_html=True)


    if st.session_state["running"]:
        st.info("Running agent...")
    elif st.session_state["last_run"] is not None:
        if isinstance(st.session_state["last_run"], dict):
            st.success("Agent finished successfully.")
            st.json(st.session_state["last_run"])
        else:
            st.error(f"Agent raised exception: {st.session_state['last_run']}")
st.markdown("</div>", unsafe_allow_html=True)

#run
if run_clicked:

    st.session_state["running"] = True
    st.session_state["last_run"] = None
   
    try:
        result = RUN_FN()
        st.session_state["last_run"] = result
    except Exception as e:
        st.session_state["last_run"] = repr(e)
    finally:
        st.session_state["running"] = False
    


# ---------- search + invoice list ----------

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("### Recent processed invoices")


query = st.text_input("Search by client name or id", value=st.session_state.get("query", ""))

st.session_state["query"] = query

invoices = get_invoices(limit=50, client_query=(query.strip() if query.strip() else None))

if not invoices:
    st.markdown("No processed invoices found.")
else:
    # header
    header_cols = st.columns([2, 2, 3, 3, 1])
    header_cols[0].markdown("**Processed At**")
    header_cols[1].markdown("**Client ID**")
    header_cols[2].markdown("**Client Name**")
    header_cols[3].markdown("**Invoice ID**")
    header_cols[4].markdown("**Actions**")
    st.markdown("---")

    for inv in invoices:
        sent_val = getattr(inv, "sent_at", None)
        sent_str = format_ist(sent_val) if sent_val else "N/A"
        row_cols = st.columns([2, 2, 3, 3, 1])
        row_cols[0].markdown(sent_str)
        row_cols[1].markdown(getattr(inv, "client_id", "N/A"))
        row_cols[2].markdown(getattr(inv, "client_name", "N/A"))
        row_cols[3].markdown(f"`{getattr(inv, 'id', 'N/A')}`")

      
        try:
            pdf_bytes = render_invoice_confirmation_pdf_bytes(inv)
            
            btn_key = f"download_{getattr(inv, 'id')}"
           
            with st.container():
                row_cols[4].download_button(
                    label="Open PDF",
                    data=pdf_bytes,
                    file_name=f"{getattr(inv, 'id', 'invoice')}.pdf",
                    mime="application/pdf",
                    key=btn_key,
                )
        except Exception as e:
            row_cols[4].write("Error generating PDF")
st.markdown("</div>", unsafe_allow_html=True)
