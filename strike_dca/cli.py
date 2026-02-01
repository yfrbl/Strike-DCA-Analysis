from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from .analysis import analyze
from .charts import generate_charts
from .io import load_rows
from .report import build_markdown, insert_image_after_h1, run_pandoc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Strike BTC DCA history.")
    parser.add_argument("input", help="Input CSV/TXT export file")
    parser.add_argument("output", nargs="?", default=None, help="Output markdown filename")
    parser.add_argument("--current-price-eur", default=None, help="Current BTC price in EUR")
    parser.add_argument("--current-price-date", default=None, help="Date for current BTC price (YYYY-MM-DD)")
    parser.add_argument("--fx-rate", default=None, help="FX reference: 1 EUR = X USD")
    parser.add_argument("--fx-date", default=None, help="FX reference date (YYYY-MM-DD)")
    parser.add_argument("--no-charts", action="store_true", help="Skip chart generation")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation")
    parser.add_argument("--pdf-engine", default=None, help="Pandoc PDF engine (default: xelatex)")
    parser.add_argument("--report-dir", default=None, help="Override Report directory path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)

    report_dir = Path(args.report_dir) if args.report_dir else (input_path.parent / "Report")
    report_dir.mkdir(parents=True, exist_ok=True)

    output_name = Path(args.output).name if args.output else f"{input_path.stem}-analysis.md"
    output_path = report_dir / output_name
    chart_path = report_dir / f"{input_path.stem}-charts.png"
    pdf_path = report_dir / f"{input_path.stem}-analysis.pdf"

    rows = load_rows(input_path)
    result = analyze(rows)

    current_price = Decimal(str(args.current_price_eur)) if args.current_price_eur else None

    markdown = build_markdown(
        result,
        current_price_eur=current_price,
        current_price_date=args.current_price_date,
        fx_rate=args.fx_rate,
        fx_date=args.fx_date,
    )
    output_path.write_text(markdown, encoding="utf-8")

    if not args.no_charts:
        try:
            generate_charts(input_path, chart_path)
        except Exception as exc:
            print(f"Chart generation failed: {exc}")

    if not args.no_pdf:
        if chart_path.exists():
            combined_md = report_dir / f"{input_path.stem}-combined.md"
            combined_md.write_text(
                insert_image_after_h1(output_path.read_text(), chart_path.name),
                encoding="utf-8",
            )
            ok, msg = run_pandoc(combined_md, pdf_path, engine=args.pdf_engine)
            if not ok:
                print(f"PDF generation failed: {msg}")
        else:
            print("PDF generation skipped: chart image not found.")

    print(f"Wrote {output_path}")
    if chart_path.exists():
        print(f"Wrote {chart_path}")
    if pdf_path.exists():
        print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
