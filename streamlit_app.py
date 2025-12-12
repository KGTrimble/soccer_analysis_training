from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from invoice_app.categories import MARKETING_COST_CATEGORIES, suggest_marketing_category
from invoice_app.db import (
    connect,
    fetch_invoices,
    init_db,
    insert_invoice,
    list_distinct_users,
    update_invoice_category_and_notes,
)
from invoice_app.parse import parse_invoice_fields
from invoice_app.pdf_text import extract_text_from_pdf_bytes


APP_TITLE = "Invoice Library (Marketing Costs)"
DATA_DIR = Path("data")
INVOICES_DIR = DATA_DIR / "invoices"
DB_PATH = DATA_DIR / "invoices.db"


@st.cache_resource
def get_conn():
    conn = connect(DB_PATH)
    init_db(conn)
    return conn


def _save_pdf_bytes(pdf_bytes: bytes) -> tuple[str, str]:
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    stored_filename = f"{sha256}.pdf"
    INVOICES_DIR.mkdir(parents=True, exist_ok=True)
    target = INVOICES_DIR / stored_filename
    if not target.exists():
        target.write_bytes(pdf_bytes)
    return sha256, stored_filename


def page_upload(conn) -> None:
    st.subheader("Upload invoice PDF")

    with st.form("upload_form", clear_on_submit=True):
        uploaded_by = st.text_input("Uploaded by (user name / email)", placeholder="e.g. alex@company.com")
        pdf_file = st.file_uploader("Invoice PDF", type=["pdf"])
        notes = st.text_area("Notes (optional)", placeholder="Anything useful for accounting / reviewers…")
        submitted = st.form_submit_button("Upload")

    if not submitted:
        return

    if not uploaded_by.strip():
        st.error("Please provide the uploader name.")
        return
    if pdf_file is None:
        st.error("Please choose a PDF file.")
        return

    pdf_bytes = pdf_file.getvalue()
    sha256, stored_filename = _save_pdf_bytes(pdf_bytes)

    extracted_text = extract_text_from_pdf_bytes(pdf_bytes)
    if not extracted_text.strip():
        st.warning(
            "No readable text extracted from this PDF. If it’s a scanned invoice, you’ll need OCR to extract text."
        )

    parsed = parse_invoice_fields(extracted_text)
    suggestion = suggest_marketing_category(extracted_text)

    st.info(
        f"Category suggestion: **{suggestion.category}**"
        + (f" (keywords: {', '.join(suggestion.matched_keywords)})" if suggestion.matched_keywords else "")
    )
    chosen_category = st.selectbox(
        "Marketing cost category",
        MARKETING_COST_CATEGORIES,
        index=MARKETING_COST_CATEGORIES.index(suggestion.category)
        if suggestion.category in MARKETING_COST_CATEGORIES
        else len(MARKETING_COST_CATEGORIES) - 1,
    )

    if st.button("Save invoice to library"):
        invoice_id = insert_invoice(
            conn=conn,
            original_filename=pdf_file.name,
            stored_filename=stored_filename,
            sha256=sha256,
            uploaded_by=uploaded_by.strip(),
            category=chosen_category,
            vendor=parsed.vendor,
            invoice_date=parsed.invoice_date,
            total_amount=parsed.total_amount,
            currency=parsed.currency,
            notes=notes.strip() or None,
            extracted_text=extracted_text,
        )
        st.success(f"Saved invoice #{invoice_id}.")


def page_library(conn) -> None:
    st.subheader("Invoice library")

    users = ["All"] + list_distinct_users(conn)
    category_filter = st.selectbox("Filter by category", ["All"] + MARKETING_COST_CATEGORIES, index=0)
    user_filter = st.selectbox("Filter by uploader", users, index=0)

    invoices = fetch_invoices(conn=conn, category=category_filter, uploaded_by=user_filter)
    if not invoices:
        st.info("No invoices yet. Upload one from the Upload page.")
        return

    df = pd.DataFrame(
        [
            {
                "id": inv.id,
                "uploaded_at": inv.uploaded_at,
                "uploaded_by": inv.uploaded_by,
                "category": inv.category,
                "vendor": inv.vendor,
                "invoice_date": inv.invoice_date,
                "total": inv.total_amount,
                "currency": inv.currency,
                "filename": inv.original_filename,
                "sha256": inv.sha256[:12],
            }
            for inv in invoices
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("View / update an invoice")
    selected_id = st.selectbox("Invoice id", df["id"].tolist(), index=0)
    selected = next(i for i in invoices if i.id == selected_id)

    left, right = st.columns([2, 3])
    with left:
        st.write("**Metadata**")
        st.write(f"- **Uploader**: {selected.uploaded_by}")
        st.write(f"- **Uploaded at**: {selected.uploaded_at}")
        st.write(f"- **Vendor (guess)**: {selected.vendor or '—'}")
        st.write(f"- **Invoice date (guess)**: {selected.invoice_date or '—'}")
        if selected.total_amount is not None:
            st.write(f"- **Total (guess)**: {selected.total_amount} {selected.currency or ''}".strip())
        st.write(f"- **Original filename**: {selected.original_filename}")

        new_category = st.selectbox(
            "Category",
            MARKETING_COST_CATEGORIES,
            index=MARKETING_COST_CATEGORIES.index(selected.category)
            if selected.category in MARKETING_COST_CATEGORIES
            else len(MARKETING_COST_CATEGORIES) - 1,
            key=f"cat_{selected.id}",
        )
        new_notes = st.text_area("Notes", value=selected.notes or "", key=f"notes_{selected.id}")
        if st.button("Update category/notes", key=f"update_{selected.id}"):
            update_invoice_category_and_notes(
                conn=conn,
                invoice_id=selected.id,
                category=new_category,
                notes=new_notes.strip() or None,
            )
            st.success("Updated. Refreshing…")
            st.rerun()

        pdf_path = INVOICES_DIR / selected.stored_filename
        if pdf_path.exists():
            st.download_button(
                "Download PDF",
                data=pdf_path.read_bytes(),
                file_name=selected.original_filename,
                mime="application/pdf",
            )

    with right:
        st.write("**Extracted text (preview)**")
        preview = selected.extracted_text.strip()[:6000]
        if preview:
            st.code(preview)
        else:
            st.info("No extracted text stored for this invoice.")


def page_analytics(conn) -> None:
    st.subheader("Analytics")
    invoices = fetch_invoices(conn=conn)
    if not invoices:
        st.info("No invoices yet.")
        return

    df = pd.DataFrame(
        [
            {
                "category": inv.category,
                "uploaded_by": inv.uploaded_by,
                "total_amount": inv.total_amount,
                "currency": inv.currency,
            }
            for inv in invoices
        ]
    )

    st.write("**Count by category**")
    counts = df.groupby("category", dropna=False).size().sort_values(ascending=False)
    st.bar_chart(counts)

    st.write("**Totals by category (numeric totals only; mixed currencies not converted)**")
    totals = (
        df.dropna(subset=["total_amount"])
        .groupby(["category", "currency"], dropna=False)["total_amount"]
        .sum()
        .reset_index()
        .sort_values("total_amount", ascending=False)
    )
    st.dataframe(totals, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)

    conn = get_conn()

    page = st.sidebar.radio("Page", ["Upload", "Library", "Analytics"], index=0)
    if page == "Upload":
        page_upload(conn)
    elif page == "Library":
        page_library(conn)
    else:
        page_analytics(conn)


if __name__ == "__main__":
    main()

