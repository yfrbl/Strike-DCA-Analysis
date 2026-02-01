from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from .utils import dec, parse_dt, parse_dt_parts, q8


Row = Dict[str, Any]


def load_rows(path: Path | str) -> List[Row]:
    path = Path(path)
    rows: List[Row] = []
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        if "Date & Time (UTC)" in headers:
            for r in reader:
                r["dt"] = parse_dt(r["Date & Time (UTC)"])
                r["amount_eur"] = dec(r["Amount EUR"])
                r["fee_eur"] = dec(r["Fee EUR"])
                r["amount_btc"] = dec(r["Amount BTC"])
                r["fee_btc"] = dec(r["Fee BTC"])
                r["price"] = dec(r["BTC Price"])
                r["cost_basis"] = dec(r["Cost Basis (EUR)"])
                r["raw_type"] = r.get("Transaction Type")
                rows.append(r)
        else:
            for r in reader:
                dt = parse_dt_parts(r.get("Completed Date (UTC)"), r.get("Completed Time (UTC)"))
                if dt is None:
                    dt = parse_dt_parts(r.get("Initiated Date (UTC)"), r.get("Initiated Time (UTC)"))
                r["dt"] = dt

                amount1 = dec(r.get("Amount 1"))
                amount2 = dec(r.get("Amount 2"))
                fee1 = dec(r.get("Fee 1"))
                fee2 = dec(r.get("Fee 2"))
                c1 = (r.get("Currency 1") or "").strip()
                c2 = (r.get("Currency 2") or "").strip()

                r["amount_eur"] = amount1 if c1 == "EUR" else amount2 if c2 == "EUR" else None
                r["fee_eur"] = fee1 if c1 == "EUR" else fee2 if c2 == "EUR" else None
                r["amount_btc"] = amount1 if c1 == "BTC" else amount2 if c2 == "BTC" else None
                r["fee_btc"] = fee1 if c1 == "BTC" else fee2 if c2 == "BTC" else None
                r["price"] = dec(r.get("BTC Price"))
                r["cost_basis"] = abs(r["amount_eur"]) if r["amount_eur"] is not None else None
                r["raw_type"] = r.get("Transaction Type")
                rows.append(r)
    return rows


def infer_cost_basis(row: Row) -> tuple[Decimal, str]:
    if row.get("cost_basis") is not None:
        return row["cost_basis"], "provided"
    if row.get("amount_eur") is not None:
        return abs(row["amount_eur"]), "amount_eur"
    if row.get("amount_btc") is not None and row.get("price") is not None:
        return q8(row["amount_btc"] * row["price"]), "btc*price"
    return Decimal("0"), "missing"


def is_purchase_type(row: Row) -> bool:
    t = (row.get("Transaction Type") or row.get("raw_type") or "").lower()
    return t in {"purchase", "trade"}
