from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from .io import infer_cost_basis, is_purchase_type, load_rows
from .utils import month_abbr


def generate_charts(input_path: Path | str, output_path: Path | str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "matplotlib is required for chart generation. Install via Homebrew: brew install python-matplotlib"
        ) from exc

    input_path = Path(input_path)
    output_path = Path(output_path)

    rows = [r for r in load_rows(input_path) if r.get("dt") is not None]
    rows.sort(key=lambda r: r["dt"])

    purchases = [r for r in rows if is_purchase_type(r) and r.get("amount_btc") is not None]

    monthly = defaultdict(lambda: {"eur": Decimal("0"), "btc": Decimal("0")})
    for r in purchases:
        m = r["dt"].strftime("%Y-%m")
        cost, _ = infer_cost_basis(r)
        monthly[m]["eur"] += cost
        monthly[m]["btc"] += r.get("amount_btc") or Decimal("0")

    months = sorted(monthly.keys())
    month_labels = [month_abbr(int(m.split("-")[1])) for m in months]
    eur_vals = [float(monthly[m]["eur"]) for m in months]
    btc_vals = [float(monthly[m]["btc"]) for m in months]
    avg_price_vals = [
        float((monthly[m]["eur"] / monthly[m]["btc"]) if monthly[m]["btc"] else Decimal("0"))
        for m in months
    ]

    fig, axs = plt.subplots(2, 2, figsize=(12, 8))

    ax = axs[0, 0]
    ax.plot(month_labels, avg_price_vals, marker="o", color="blue", linewidth=2)
    ax.set_title("Average purchase price per Bitcoin (EUR)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Price (EUR)")
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis="x", rotation=45)

    ax = axs[0, 1]
    ax.bar(month_labels, btc_vals, color="#f4a62a")
    ax.set_title("Bitcoin bought per month")
    ax.set_xlabel("Month")
    ax.set_ylabel("BTC amount")
    ax.grid(True, axis="y", alpha=0.3)
    ax.tick_params(axis="x", rotation=45)

    ax = axs[1, 0]
    ax.bar(month_labels, eur_vals, color="#1f7a1f")
    ax.set_title("EUR spent per month")
    ax.set_xlabel("Month")
    ax.set_ylabel("EUR amount")
    ax.grid(True, axis="y", alpha=0.3)
    ax.tick_params(axis="x", rotation=45)

    ax = axs[1, 1]
    ax.bar(month_labels, btc_vals, color="#f4a62a", alpha=0.4)
    ax.set_title("Price vs. purchase volume")
    ax.set_xlabel("Month")
    ax.set_ylabel("BTC amount", color="#f4a62a")
    ax.tick_params(axis="x", rotation=45)
    ax2 = ax.twinx()
    ax2.plot(month_labels, avg_price_vals, marker="o", color="blue", linewidth=2)
    ax2.set_ylabel("Price (EUR)", color="blue")
    ax.grid(True, axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Strike DCA charts.")
    parser.add_argument("input", help="Input CSV/TXT export file")
    parser.add_argument("output", nargs="?", default=None, help="Output PNG path")
    parser.add_argument("--chart", action="store_true", help="Generate charts")
    return parser.parse_args()


def cli_main() -> None:
    args = parse_args()
    if not args.chart:
        print("Nothing to do. Re-run with --chart to generate charts.")
        return

    input_path = Path(args.input)
    report_dir = input_path.parent / "Report"
    report_dir.mkdir(parents=True, exist_ok=True)
    if args.output:
        out_name = Path(args.output).name
    else:
        out_name = f"{input_path.stem}-charts.png"
    output_path = report_dir / out_name

    generate_charts(input_path, output_path)
    print(f"Wrote {output_path}")
