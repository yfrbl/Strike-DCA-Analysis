from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

DATE_FMT = "%b %d %Y %H:%M:%S"
DATE_ONLY_FMT = "%b %d %Y"


def dec(value: str | None) -> Decimal | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return Decimal(value)


def parse_dt(value: str) -> datetime:
    return datetime.strptime(value, DATE_FMT)


def parse_dt_parts(date_str: str | None, time_str: str | None) -> datetime | None:
    if not date_str and not time_str:
        return None
    if date_str and time_str:
        return datetime.strptime(f"{date_str} {time_str}", DATE_FMT)
    if date_str:
        return datetime.strptime(date_str, DATE_ONLY_FMT)
    return None


def fmt_dt(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def q8(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def q0(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def money(value: Decimal) -> str:
    return f"{q0(value):f}"


def percent(value: Decimal) -> str:
    return f"{q2(value):f}%"


def btc(value: Decimal) -> str:
    return f"{q8(value):f}"


def month_abbr(month_num: int) -> str:
    names = {
        1: "Jan.",
        2: "Feb.",
        3: "Mar.",
        4: "Apr.",
        5: "May.",
        6: "Jun.",
        7: "Jul.",
        8: "Aug.",
        9: "Sep.",
        10: "Oct.",
        11: "Nov.",
        12: "Dec.",
    }
    return names.get(month_num, "")
