from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Dict, List, Tuple

from .io import infer_cost_basis, is_purchase_type


@dataclass
class AnalysisResult:
    rows: List[dict]
    purchases_all: List[dict]
    real_purchases: List[dict]
    non_executed: List[dict]
    inferred_rows: List[Tuple[dict, Decimal, str]]
    total_btc: Decimal
    total_eur: Decimal
    avg_price: Decimal
    monthly: Dict[str, dict]
    quarterly: Dict[str, dict]
    fee_eur_total: Decimal
    fee_btc_total: Decimal
    deposits: List[dict]
    withdrawals: List[dict]
    sends: List[dict]
    send_reversals: List[dict]
    deposit_total: Decimal
    withdrawal_total: Decimal
    send_total_btc: Decimal
    send_total_btc_excl_rev: Decimal
    purchase_days: int
    multi_purchase_days: int
    max_per_day: int
    non_exec_by_desc: Counter
    non_exec_amount_eur: Decimal
    deposit_counts: Counter
    start_date: date | None
    end_date: date | None


def analyze(rows: List[dict]) -> AnalysisResult:
    rows = [r for r in rows if r.get("dt") is not None]
    rows.sort(key=lambda r: r["dt"])

    purchases_all = [r for r in rows if is_purchase_type(r)]
    real_purchases = [r for r in purchases_all if r.get("amount_btc") is not None]
    non_executed = [r for r in purchases_all if r.get("amount_btc") is None]

    total_btc = Decimal("0")
    total_eur = Decimal("0")
    inferred_rows: List[Tuple[dict, Decimal, str]] = []
    for r in real_purchases:
        cost, source = infer_cost_basis(r)
        total_btc += r.get("amount_btc") or Decimal("0")
        total_eur += cost
        if source != "provided":
            inferred_rows.append((r, cost, source))

    avg_price = (total_eur / total_btc) if total_btc else Decimal("0")

    monthly = defaultdict(lambda: {
        "eur": Decimal("0"),
        "btc": Decimal("0"),
        "count": 0,
        "min_price": None,
        "max_price": None,
    })
    quarterly = defaultdict(lambda: {"eur": Decimal("0"), "btc": Decimal("0"), "count": 0})

    for r in real_purchases:
        month_key = r["dt"].strftime("%Y-%m")
        cost, _ = infer_cost_basis(r)
        monthly[month_key]["eur"] += cost
        monthly[month_key]["btc"] += r.get("amount_btc") or Decimal("0")
        monthly[month_key]["count"] += 1

        q = (r["dt"].month - 1) // 3 + 1
        q_key = f"{r['dt'].year}-Q{q}"
        quarterly[q_key]["eur"] += cost
        quarterly[q_key]["btc"] += r.get("amount_btc") or Decimal("0")
        quarterly[q_key]["count"] += 1

        price = r.get("price")
        if price is not None:
            if monthly[month_key]["min_price"] is None or price < monthly[month_key]["min_price"]:
                monthly[month_key]["min_price"] = price
            if monthly[month_key]["max_price"] is None or price > monthly[month_key]["max_price"]:
                monthly[month_key]["max_price"] = price

    fee_eur_total = sum(((r.get("fee_eur") or Decimal("0")) for r in rows), Decimal("0"))
    fee_btc_total = sum(((r.get("fee_btc") or Decimal("0")) for r in rows), Decimal("0"))

    deposits = [r for r in rows if (r.get("Transaction Type") or r.get("raw_type")) == "Deposit"]
    withdrawals = [r for r in rows if (r.get("Transaction Type") or r.get("raw_type")) == "Withdrawal"]
    sends = [r for r in rows if (r.get("Transaction Type") or r.get("raw_type")) == "Send"]
    send_reversals = [r for r in sends if (r.get("Description") or "").strip().lower() == "reversal"]

    deposit_total = sum(((r.get("amount_eur") or Decimal("0")) for r in deposits), Decimal("0"))
    withdrawal_total = sum(((r.get("amount_eur") or Decimal("0")) for r in withdrawals), Decimal("0"))
    send_total_btc = sum(((r.get("amount_btc") or Decimal("0")) for r in sends), Decimal("0"))
    send_total_btc_excl_rev = sum(
        ((r.get("amount_btc") or Decimal("0")) for r in sends if r not in send_reversals),
        Decimal("0"),
    )

    by_day = defaultdict(int)
    for r in real_purchases:
        by_day[r["dt"].date()] += 1
    purchase_days = len(by_day)
    multi_purchase_days = sum(1 for v in by_day.values() if v > 1)
    max_per_day = max(by_day.values()) if by_day else 0

    non_exec_by_desc = Counter((r.get("Description") or "").strip() for r in non_executed)
    non_exec_amount_eur = sum(((r.get("amount_eur") or Decimal("0")) for r in non_executed), Decimal("0"))

    deposit_counts = Counter(float(r["amount_eur"]) for r in deposits if r.get("amount_eur") is not None)

    start_date = rows[0]["dt"].date() if rows else None
    end_date = rows[-1]["dt"].date() if rows else None

    return AnalysisResult(
        rows=rows,
        purchases_all=purchases_all,
        real_purchases=real_purchases,
        non_executed=non_executed,
        inferred_rows=inferred_rows,
        total_btc=total_btc,
        total_eur=total_eur,
        avg_price=avg_price,
        monthly=monthly,
        quarterly=quarterly,
        fee_eur_total=fee_eur_total,
        fee_btc_total=fee_btc_total,
        deposits=deposits,
        withdrawals=withdrawals,
        sends=sends,
        send_reversals=send_reversals,
        deposit_total=deposit_total,
        withdrawal_total=withdrawal_total,
        send_total_btc=send_total_btc,
        send_total_btc_excl_rev=send_total_btc_excl_rev,
        purchase_days=purchase_days,
        multi_purchase_days=multi_purchase_days,
        max_per_day=max_per_day,
        non_exec_by_desc=non_exec_by_desc,
        non_exec_amount_eur=non_exec_amount_eur,
        deposit_counts=deposit_counts,
        start_date=start_date,
        end_date=end_date,
    )
