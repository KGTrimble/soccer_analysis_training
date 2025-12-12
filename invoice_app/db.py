from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class InvoiceRow:
    id: int
    original_filename: str
    stored_filename: str
    sha256: str
    uploaded_by: str
    uploaded_at: str
    category: str
    vendor: Optional[str]
    invoice_date: Optional[str]
    total_amount: Optional[float]
    currency: Optional[str]
    notes: Optional[str]
    extracted_text: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            uploaded_by TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            category TEXT NOT NULL,
            vendor TEXT,
            invoice_date TEXT,
            total_amount REAL,
            currency TEXT,
            notes TEXT,
            extracted_text TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_invoices_category ON invoices(category)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_invoices_uploaded_by ON invoices(uploaded_by)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_invoices_uploaded_at ON invoices(uploaded_at)"
    )
    conn.commit()


def insert_invoice(
    *,
    conn: sqlite3.Connection,
    original_filename: str,
    stored_filename: str,
    sha256: str,
    uploaded_by: str,
    category: str,
    vendor: Optional[str],
    invoice_date: Optional[date],
    total_amount: Optional[float],
    currency: Optional[str],
    notes: Optional[str],
    extracted_text: str,
) -> int:
    uploaded_at = _utc_now_iso()
    invoice_date_str = invoice_date.isoformat() if invoice_date else None
    cur = conn.execute(
        """
        INSERT INTO invoices (
            original_filename, stored_filename, sha256,
            uploaded_by, uploaded_at,
            category, vendor, invoice_date, total_amount, currency, notes,
            extracted_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            original_filename,
            stored_filename,
            sha256,
            uploaded_by,
            uploaded_at,
            category,
            vendor,
            invoice_date_str,
            total_amount,
            currency,
            notes,
            extracted_text,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_invoice_category_and_notes(
    *,
    conn: sqlite3.Connection,
    invoice_id: int,
    category: str,
    notes: Optional[str],
) -> None:
    conn.execute(
        "UPDATE invoices SET category = ?, notes = ? WHERE id = ?",
        (category, notes, invoice_id),
    )
    conn.commit()


def fetch_invoices(
    *,
    conn: sqlite3.Connection,
    category: Optional[str] = None,
    uploaded_by: Optional[str] = None,
) -> list[InvoiceRow]:
    where: list[str] = []
    params: list[Any] = []
    if category and category != "All":
        where.append("category = ?")
        params.append(category)
    if uploaded_by and uploaded_by != "All":
        where.append("uploaded_by = ?")
        params.append(uploaded_by)

    sql = "SELECT * FROM invoices"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY uploaded_at DESC"

    rows = conn.execute(sql, params).fetchall()
    return [
        InvoiceRow(
            id=int(r["id"]),
            original_filename=str(r["original_filename"]),
            stored_filename=str(r["stored_filename"]),
            sha256=str(r["sha256"]),
            uploaded_by=str(r["uploaded_by"]),
            uploaded_at=str(r["uploaded_at"]),
            category=str(r["category"]),
            vendor=r["vendor"],
            invoice_date=r["invoice_date"],
            total_amount=r["total_amount"],
            currency=r["currency"],
            notes=r["notes"],
            extracted_text=str(r["extracted_text"] or ""),
        )
        for r in rows
    ]


def list_distinct_users(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT uploaded_by FROM invoices ORDER BY uploaded_by"
    ).fetchall()
    return [str(r[0]) for r in rows if r[0] is not None]


def list_distinct_categories(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT category FROM invoices ORDER BY category"
    ).fetchall()
    return [str(r[0]) for r in rows if r[0] is not None]

