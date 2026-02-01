from __future__ import annotations

import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

from .analysis import AnalysisResult
from .utils import btc, fmt_dt, money, month_abbr, percent, q2


def build_markdown(result: AnalysisResult, current_price_eur: Decimal | None = None,
                   current_price_date: str | None = None,
                   fx_rate: str | None = None,
                   fx_date: str | None = None) -> str:
    start_year = result.start_date.year if result.start_date else None
    end_year = result.end_date.year if result.end_date else None

    if start_year and end_year:
        if start_year == end_year:
            period_label = f"In {start_year}"
        else:
            period_label = f"In {start_year}–{end_year}"
    else:
        period_label = "In the analysis period"

    lines: list[str] = []
    title_year = f"{start_year}" if start_year == end_year and start_year else "Analysis"
    if start_year and end_year and start_year != end_year:
        title_year = f"{start_year}-{end_year}"

    lines.append(f"# Strike {title_year} DCA Analysis (Real Purchases)")
    lines.append("")

    lines.append("## Executive Summary")
    lines.append(
        f"{period_label} {btc(result.total_btc)} BTC were purchased for {money(result.total_eur)} EUR; "
        f"the weighted average entry price is {money(result.avg_price)} EUR/BTC."
    )

    quarter_parts: list[str] = []
    for q_key in sorted(result.quarterly.keys()):
        q_eur = result.quarterly[q_key]["eur"]
        q_btc = result.quarterly[q_key]["btc"]
        q_avg = (q_eur / q_btc) if q_btc else Decimal("0")
        quarter_parts.append(f"{q_key}: {money(q_avg)}")
    if quarter_parts:
        lines.append("Quarterly average buy price (EUR/BTC): " + "; ".join(quarter_parts) + ".")

    if current_price_eur is not None:
        delta = ((current_price_eur - result.avg_price) / result.avg_price) * Decimal("100")
        current_value = current_price_eur * result.total_btc
        pnl = current_value - result.total_eur
        pnl_pct = (pnl / result.total_eur) * Decimal("100") if result.total_eur else Decimal("0")
        direction = "above" if delta >= 0 else "below"
        fx_note = f"; FX {fx_date}: 1 EUR = {fx_rate} USD" if fx_rate and fx_date else ""
        date_note = f" (as of {current_price_date}{fx_note})" if current_price_date else ""
        lines.append(
            f"At a current BTC price of {money(current_price_eur)} EUR{date_note}, the market price is "
            f"about {q2(abs(delta))}% {direction} the average entry; unrealized P/L is "
            f"{money(pnl)} EUR ({percent(pnl_pct)}) based on purchased BTC."
        )

    lines.append("")

    lines.append("## Definitions")
    lines.append("- **Real purchases**: `Transaction Type = Purchase/Trade` **and** `Amount BTC` present.")
    lines.append("- **Cost basis**: if empty, derived from `Amount EUR` or `Amount BTC * BTC Price`.")
    lines.append("- **Non-executed purchases**: Purchase rows without BTC amount (e.g., initiated/cancelled target orders).")
    lines.append("")

    lines.append("## Overview")
    if result.start_date and result.end_date:
        lines.append(f"- Period: {result.start_date} to {result.end_date}")
    lines.append(f"- Real purchases: {len(result.real_purchases)}")
    lines.append(
        f"- Purchase days: {result.purchase_days} (days with >1 purchase: {result.multi_purchase_days}, "
        f"max/day: {result.max_per_day})"
    )
    lines.append(f"- BTC purchased: {btc(result.total_btc)}")
    lines.append(f"- Invested (EUR, cost basis): {money(result.total_eur)}")
    lines.append(f"- Average entry price: {money(result.avg_price)} EUR/BTC")
    lines.append("")

    lines.append("## Fees")
    lines.append(f"- Total EUR fees: {money(result.fee_eur_total)}")
    lines.append(f"- Total BTC fees: {btc(result.fee_btc_total)}")
    lines.append("")

    lines.append("## Monthly Overview (Real Purchases)")
    lines.append("| Month | EUR Spent | BTC Bought | Avg Price (EUR/BTC) | Min Price | Max Price | # Purchases |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for m in sorted(result.monthly.keys()):
        month_num = int(m.split("-")[1])
        month_label = month_abbr(month_num)
        eur = result.monthly[m]["eur"]
        btc_amt = result.monthly[m]["btc"]
        cnt = result.monthly[m]["count"]
        avg = (eur / btc_amt) if btc_amt else Decimal("0")
        min_p = result.monthly[m]["min_price"]
        max_p = result.monthly[m]["max_price"]
        min_p_s = money(min_p) if min_p is not None else ""
        max_p_s = money(max_p) if max_p is not None else ""
        lines.append(
            f"| {month_label} | {money(eur)} | {btc(btc_amt)} | {money(avg)} | {min_p_s} | {max_p_s} | {cnt} |"
        )
    lines.append("")

    lines.append("## Other Transaction Types")
    lines.append(f"- Deposits: {len(result.deposits)} (Total EUR: {money(result.deposit_total)})")
    lines.append(f"- Withdrawals: {len(result.withdrawals)} (Total EUR: {money(result.withdrawal_total)})")
    lines.append(
        f"- Sends: {len(result.sends)} (Net BTC: {btc(result.send_total_btc)}; "
        f"excluding reversals: {btc(result.send_total_btc_excl_rev)})"
    )
    if result.send_reversals:
        lines.append(f"- Send reversals: {len(result.send_reversals)}")
    lines.append("")

    lines.append("## Non-Executed Purchase Events")
    lines.append(f"- Count: {len(result.non_executed)}")
    lines.append(f"- Sum Amount EUR (signed): {money(result.non_exec_amount_eur)}")
    if result.non_exec_by_desc:
        lines.append("- Breakdown by description:")
        for desc, cnt in result.non_exec_by_desc.items():
            label = desc if desc else "(empty)"
            lines.append(f"  - {label}: {cnt}")
    lines.append("")

    if result.inferred_rows:
        lines.append("## Purchases With Derived Cost Basis")
        lines.append("| Date (UTC) | BTC | Price | Cost Basis | Source | Description |")
        lines.append("|---|---:|---:|---:|---|---|")
        for row, cost, source in result.inferred_rows:
            price = row.get("price") or Decimal("0")
            desc = (row.get("Description") or "").strip()
            lines.append(
                f"| {fmt_dt(row.get('dt'))} | {btc(row.get('amount_btc') or Decimal('0'))} | "
                f"{money(price)} | {money(cost)} | {source} | {desc} |"
            )
        lines.append("")

    lines.append("## Data Quality / Checks")
    lines.append(f"- Purchase rows without BTC amount: {len(result.non_executed)}")
    lines.append(f"- Purchase rows with derived cost basis: {len(result.inferred_rows)}")
    lines.append("")

    lines.append("## Deposit Distribution")
    lines.append("| EUR Amount | Count |")
    lines.append("|---:|---:|")
    for amt, cnt in sorted(result.deposit_counts.items()):
        lines.append(f"| {amt:.0f} | {cnt} |")
    lines.append("")

    return "\n".join(lines)


def insert_image_after_h1(md_text: str, image_name: str) -> str:
    lines = md_text.splitlines()
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            insert_idx = i + 1
            break
    lines.insert(insert_idx, f"![Charts]({image_name})")
    lines.insert(insert_idx + 1, "")
    return "\n".join(lines)


def run_pandoc(md_path: Path, pdf_path: Path, engine: str | None = None) -> tuple[bool, str]:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        return False, "pandoc not found"
    pdf_engine = engine or "xelatex"
    if not shutil.which(pdf_engine):
        return False, f"PDF engine not found: {pdf_engine}"
    cmd = [
        pandoc,
        md_path.name,
        "-o",
        pdf_path.name,
        "--pdf-engine",
        pdf_engine,
    ]
    try:
        subprocess.run(cmd, cwd=md_path.parent, check=True)
    except subprocess.CalledProcessError as exc:
        return False, f"pandoc failed: {exc}"
    return True, ""
