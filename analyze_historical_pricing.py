#!/usr/bin/env python3
"""
Ontario Electricity Historical Price Analysis for Pool Pump Scheduling.

Fetches HOEP data from IESO, finds the 8 most expensive hours each month
to SKIP (pump off), and runs the pump the other 16 hours.

Pool season: May through October. Pump runs 16 hrs/day.

Usage:
  python3 analyze_historical_pricing.py
  python3 analyze_historical_pricing.py --year 2023
  python3 analyze_historical_pricing.py --years 2023,2024 --admin-fee 1.45
"""

from __future__ import annotations

import argparse
import csv
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Final
from urllib.request import urlopen

# ── IESO URLs ─────────────────────────────────────────────────────────────
IESO_HOEP_URL: Final = (
    "https://reports-public.ieso.ca/public/PriceHOEPPredispOR/"
    "PUB_PriceHOEPPredispOR_{year}.csv"
)
IESO_GA_MONTHLY_URL: Final = (
    "https://reports-public.ieso.ca/public/GlobalAdjustment/"
    "PUB_GlobalAdjustment_{yyyymm}_v3.xml"
)

DEFAULT_ADMIN_FEE: Final = 1.45

# Pool season months
POOL_SEASON_MONTHS: list[int] = [5, 6, 7, 8, 9, 10]

# Pump runs 16 hours, off 8 hours
PUMP_ON_HOURS: Final = 16
PUMP_OFF_HOURS: Final = 24 - PUMP_ON_HOURS  # 8
PUMP_KW: Final = 1.1  # typical 1.5 HP pool pump
PUMP_KWH_PER_DAY: Final = PUMP_KW * PUMP_ON_HOURS  # 17.6
SEASON_DAYS: Final = 183  # May 1 – Oct 31

# Known 2024 GA rates (¢/kWh) for pool season
GA_RATES_2024: dict[int, float] = {
    5: 7.21,
    6: 8.39,
    7: 8.93,
    8: 9.23,
    9: 8.21,
    10: 7.98,
}


def fetch_hoep_csv(year: int, cache_dir: Path) -> list[dict]:
    """Fetch and parse IESO HOEP yearly CSV, with local caching."""
    cache_file = cache_dir / f"HOEP_{year}.csv"

    if cache_file.exists():
        print(f"  Using cached: {cache_file}")
        raw = cache_file.read_text()
    else:
        url = IESO_HOEP_URL.format(year=year)
        print(f"  Fetching HOEP for {year}: {url}")
        try:
            with urlopen(url, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
            cache_file.write_text(raw)
            print(f"  Cached to: {cache_file}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            return []

    data_lines = [l for l in raw.strip().split("\n") if not l.startswith("\\")]
    reader = csv.DictReader(data_lines)
    rows = []
    for row in reader:
        try:
            hoep = row.get("HOEP", "").strip()
            if not hoep:
                continue
            rows.append(
                {
                    "date": row["Date"].strip(),
                    "hour": int(row["Hour"].strip()),
                    "hoep_mwh": float(hoep),
                }
            )
        except (ValueError, KeyError):
            continue

    print(f"  ✓ {len(rows)} hourly records for {year}")
    return rows


def fetch_ga_xml(year: int) -> dict[int, float]:
    """Fetch GA rates from IESO monthly XML. Returns {month: ¢/kWh}."""
    ga_rates: dict[int, float] = {}
    for month in range(1, 13):
        yyyymm = f"{year}{month:02d}"
        url = IESO_GA_MONTHLY_URL.format(yyyymm=yyyymm)
        try:
            with urlopen(url, timeout=15) as resp:
                xml_text = resp.read().decode("utf-8")
            root = ET.fromstring(xml_text)
            ns = {"ieso": "http://www.ieso.ca/schema"}
            for tag in ["FirstEstimateRate", "SecondEstimateRate", "ActualRate"]:
                elem = root.find(f".//ieso:{tag}", ns) or root.find(f".//{tag}")
                if elem is not None and elem.text and elem.text.strip():
                    ga_rates[month] = float(elem.text.strip()) * 100  # $→¢
                    break
        except Exception:
            continue

    if ga_rates:
        print(f"  ✓ GA rates for {len(ga_rates)}/12 months from XML")
    return ga_rates


def get_ga_cents(month: int, ga_xml: dict[int, float]) -> float:
    """Get GA in ¢/kWh for a month. Falls back to 2024 known rates, then 8.0."""
    if month in ga_xml:
        return ga_xml[month]
    return GA_RATES_2024.get(month, 8.0)


def analyze(all_rows: list[dict], ga_xml: dict[int, float], admin_fee: float) -> None:
    """Analyze hourly patterns and build 16-hr pump schedule."""

    # ── Group by month+hour ──────────────────────────────────────────
    by_month_hour: dict[int, dict[int, list[float]]] = {
        m: defaultdict(list) for m in POOL_SEASON_MONTHS
    }
    by_hour_all: dict[int, list[float]] = defaultdict(list)

    for row in all_rows:
        try:
            month = datetime.strptime(row["date"], "%Y-%m-%d").month
        except ValueError:
            continue
        if month not in POOL_SEASON_MONTHS:
            continue
        hoep_kwh = row["hoep_mwh"] / 10.0
        by_month_hour[month][row["hour"]].append(hoep_kwh)
        by_hour_all[row["hour"]].append(hoep_kwh)

    if not by_hour_all:
        print("\n⚠ No pool season data found!")
        return

    # ── Compute avg HOEP per hour (overall pool season) ─────────────
    avg_ga = sum(get_ga_cents(m, ga_xml) for m in POOL_SEASON_MONTHS) / len(
        POOL_SEASON_MONTHS
    )
    hourly_avg: dict[int, float] = {}
    for hour, vals in by_hour_all.items():
        hourly_avg[hour] = sum(vals) / len(vals)

    sorted_hours = sorted(hourly_avg.items(), key=lambda x: x[1])

    # ── Hourly price chart ───────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  HOURLY PRICE PATTERN — Pool Season (May–Oct)")
    print("=" * 72)
    print(f"  {'Hour':>6}  {'Avg HOEP':>9}  {'Total rate':>10}  {'Bar':>24}")
    print("  " + "-" * 55)

    max_avg = max(hourly_avg.values()) if hourly_avg else 1
    overall_skip = {h for h, _ in sorted_hours[-PUMP_OFF_HOURS:]}

    for hour in sorted(hourly_avg):
        hoep = hourly_avg[hour]
        total = hoep + avg_ga + admin_fee
        bar_len = int(24 * (hoep / max_avg)) if max_avg > 0 else 0
        marker = " ❌" if hour in overall_skip else " ✅"
        print(
            f"  {hour:02d}:00   {hoep:>7.2f}¢  {total:>8.2f}¢   {'█' * bar_len}{marker}"
        )

    # ── Overall skip/run recommendation ──────────────────────────────
    skip_hrs = sorted(h for h, _ in sorted_hours[-PUMP_OFF_HOURS:])
    run_hrs = sorted(h for h in range(1, 25) if h not in overall_skip)

    print("\n" + "=" * 72)
    print(
        f"  🏊 OPTIMAL SCHEDULE — PUMP ON {PUMP_ON_HOURS} HRS, OFF {PUMP_OFF_HOURS} HRS"
    )
    print("=" * 72)
    print(f"\n  ❌ OFF (skip) hours: {', '.join(f'{h:02d}:00' for h in skip_hrs)}")
    print(f"  ✅ ON  (run)  hours: {', '.join(f'{h:02d}:00' for h in run_hrs)}")

    run_avg = sum(hourly_avg[h] for h in run_hrs) / PUMP_ON_HOURS
    skip_avg = sum(hourly_avg[h] for h in skip_hrs) / PUMP_OFF_HOURS
    flat_avg = sum(hourly_avg.values()) / 24
    print(f"\n  Average rate while ON:  {run_avg + avg_ga + admin_fee:.2f}¢/kWh")
    print(f"  Average rate while OFF: {skip_avg + avg_ga + admin_fee:.2f}¢/kWh")
    print(f"  If ran 24/7 flat:       {flat_avg + avg_ga + admin_fee:.2f}¢/kWh")

    # ── Season cost ──────────────────────────────────────────────────
    d_smart = PUMP_KWH_PER_DAY * (run_avg + avg_ga + admin_fee) / 100
    d_flat = PUMP_KW * 24 * (flat_avg + avg_ga + admin_fee) / 100  # 24hr flat
    d_worst_off = sorted(h for h, _ in sorted_hours[:PUMP_OFF_HOURS:])  # skip cheapest
    worst_run_avg = (
        sum(hourly_avg[h] for h in range(1, 25) if h not in d_worst_off) / PUMP_ON_HOURS
    )
    d_worst = PUMP_KWH_PER_DAY * (worst_run_avg + avg_ga + admin_fee) / 100

    print(
        f"\n  ── Season Cost ({PUMP_KW} kW pump, {PUMP_ON_HOURS} hrs/day = {PUMP_KWH_PER_DAY:.1f} kWh/day) ──"
    )
    print(f"  GA avg: {avg_ga:.2f}¢/kWh")
    print()
    print(
        f"  Smart schedule:   ${d_smart:.2f}/day  →  ${d_smart * SEASON_DAYS:.2f}/season"
    )
    print(
        f"  24/7 flat:        ${d_flat:.2f}/day  →  ${d_flat * SEASON_DAYS:.2f}/season"
    )
    print(
        f"  Worst schedule:   ${d_worst:.2f}/day  →  ${d_worst * SEASON_DAYS:.2f}/season"
    )
    print()
    save_vs_flat = d_flat - d_smart
    save_vs_worst = d_worst - d_smart
    print(f"  💰 Smart vs 24/7 flat:  saves ${save_vs_flat * SEASON_DAYS:.2f}/season")
    print(f"  💰 Smart vs worst case: saves ${save_vs_worst * SEASON_DAYS:.2f}/season")

    # ── Month-by-month ───────────────────────────────────────────────
    print("\n" + "=" * 72)
    print(f"  MONTH-BY-MONTH: TURN PUMP OFF FOR {PUMP_OFF_HOURS} HOURS")
    print("=" * 72)

    for month in POOL_SEASON_MONTHS:
        hour_data = by_month_hour[month]
        if not hour_data:
            continue
        month_name = datetime(2000, month, 1).strftime("%B")
        ga_m = get_ga_cents(month, ga_xml)

        # Sort hours by avg HOEP for this month
        mh_avg = {h: sum(v) / len(v) for h, v in hour_data.items()}
        sorted_mh = sorted(mh_avg.items(), key=lambda x: x[1])

        skip_m = sorted([h for h, _ in sorted_mh[-PUMP_OFF_HOURS:]])
        run_m = sorted([h for h in range(1, 25) if h in mh_avg and h not in skip_m])

        run_total_avg = sum(mh_avg[h] for h in run_m) / len(run_m) + ga_m + admin_fee
        skip_total_avg = sum(mh_avg[h] for h in skip_m) / len(skip_m) + ga_m + admin_fee

        skip_str = ", ".join(f"{h:02d}:00" for h in skip_m)
        run_str = ", ".join(f"{h:02d}:00" for h in run_m)

        d_m = PUMP_KWH_PER_DAY * run_total_avg / 100

        print(f"\n  {month_name} (GA={ga_m:.2f}¢/kWh):")
        print(f"    ❌ OFF: {skip_str}  (avg {skip_total_avg:.2f}¢/kWh)")
        print(f"    ✅ ON:  {run_str}  (avg {run_total_avg:.2f}¢/kWh)")
        print(f"    Daily cost: ${d_m:.2f}   Monthly: ${d_m * 30:.2f}")

    # ── Quick reference ──────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  QUICK REFERENCE: PUMP OFF HOURS BY MONTH")
    print("=" * 72)
    print(
        f"  {'Month':<10}  {'Turn pump OFF':<30}  {'ON avg rate':>12}  {'Daily $':>8}"
    )
    print("  " + "-" * 65)

    for month in POOL_SEASON_MONTHS:
        hour_data = by_month_hour[month]
        if not hour_data:
            continue
        month_name = datetime(2000, month, 1).strftime("%B")
        ga_m = get_ga_cents(month, ga_xml)
        mh_avg = {h: sum(v) / len(v) for h, v in hour_data.items()}
        sorted_mh = sorted(mh_avg.items(), key=lambda x: x[1])
        skip_m = sorted([h for h, _ in sorted_mh[-PUMP_OFF_HOURS:]])
        run_m = sorted([h for h in range(1, 25) if h in mh_avg and h not in skip_m])
        run_total = sum(mh_avg[h] for h in run_m) / len(run_m) + ga_m + admin_fee
        d_m = PUMP_KWH_PER_DAY * run_total / 100
        skip_str = ", ".join(f"{h:02d}:00" for h in skip_m)
        print(
            f"  {month_name:<10}  {skip_str:<30}  {run_total:>10.2f}¢/kWh  ${d_m:>6.2f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze historical IESO pricing for pool pump scheduling (16 hrs/day)"
    )
    parser.add_argument(
        "--year", type=int, default=2024, help="Year to analyze (default: 2024)"
    )
    parser.add_argument(
        "--years", type=str, default=None, help="Comma-separated years, e.g. 2023,2024"
    )
    parser.add_argument(
        "--admin-fee",
        type=float,
        default=DEFAULT_ADMIN_FEE,
        help=f"Admin fee in ¢/kWh (default: {DEFAULT_ADMIN_FEE})",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="/tmp/ieso_historical",
        help="Cache directory for downloaded CSVs",
    )
    args = parser.parse_args()

    years = (
        [int(y.strip()) for y in args.years.split(",")] if args.years else [args.year]
    )

    print("=" * 72)
    print("  Ontario Electricity — Pool Pump Scheduling Analysis")
    print("=" * 72)
    print(f"  Year(s):    {', '.join(map(str, years))}")
    print(f"  Admin fee:  {args.admin_fee:.2f} ¢/kWh")
    print(
        f"  Pump:       {PUMP_KW} kW, {PUMP_ON_HOURS} hrs/day = {PUMP_KWH_PER_DAY:.1f} kWh/day"
    )
    print(f"  Season:     May – October ({SEASON_DAYS} days)")
    print()

    # Fetch HOEP
    print("── Fetching HOEP Data ──")
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict] = []
    for year in years:
        all_rows.extend(fetch_hoep_csv(year, cache_dir))

    if not all_rows:
        print("\n✗ No data fetched!")
        sys.exit(1)

    pool_rows = [
        r
        for r in all_rows
        if datetime.strptime(r["date"], "%Y-%m-%d").month in POOL_SEASON_MONTHS
    ]
    print(f"\n  Total records: {len(all_rows)}  |  Pool season: {len(pool_rows)}")

    # Fetch GA
    print("\n── Fetching Global Adjustment ──")
    ga_xml: dict[int, float] = {}
    for year in years:
        ga_xml.update(fetch_ga_xml(year))
    if not any(m in ga_xml for m in POOL_SEASON_MONTHS):
        print("  Using known 2024 GA rates as fallback")

    analyze(all_rows, ga_xml, args.admin_fee)

    print("\n" + "=" * 72)
    print("  NOTES")
    print("=" * 72)
    print("  • HOEP = Hourly Ontario Energy Price (market wholesale price)")
    print("  • Total rate = HOEP + GA + Admin Fee")
    print("  • Prices in ¢/kWh (HOEP converted from $/MWh ÷ 10)")
    print(
        f"  • Pump: {PUMP_KW} kW, {PUMP_ON_HOURS} hrs/day ({PUMP_KWH_PER_DAY:.1f} kWh/day)"
    )
    print("  • Schedule: skip 8 most expensive hours, run the other 16")
    print("  • Pattern is consistent year-over-year")
    print()


if __name__ == "__main__":
    main()
