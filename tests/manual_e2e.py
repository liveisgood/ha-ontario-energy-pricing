#!/usr/bin/env python3
"""End-to-end manual test: fetches REAL IESO data and processes it through our code.

Run: python3 tests/manual_e2e.py

This script actually hits IESO public servers - requires internet.
Tests that every component can fetch, parse, and produce valid data.
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime

import aiohttp

sys.path.insert(0, ".")


async def test_ieso_lmp():
    """Test the real-time zonal LMP feed."""
    from custom_components.ontario_energy_pricing.ieso_lmp import IESOLMPClient

    async with aiohttp.ClientSession() as session:
        client = IESOLMPClient(session, location="Oakville")
        data = await client.async_get_current_lmp()

        print(f"  Zone: {data.zone}")
        print(f"  Delivery: {data.delivery_date} hour {data.delivery_hour}")
        print(f"  Intervals: {len(data.intervals)}")
        print(f"  Current LMP: {data.current_lmp_kwh} ¢/kWh  (type={type(data.current_lmp_kwh).__name__})")
        print(f"  Hour Avg: {data.hour_average_kwh} ¢/kWh  (type={type(data.hour_average_kwh).__name__})")
        print(f"  Latest Interval: {data.latest_interval}")

        assert isinstance(data.current_lmp_kwh, float), f"Expected float, got {type(data.current_lmp_kwh)}"
        assert isinstance(data.hour_average_kwh, float), f"Expected float, got {type(data.hour_average_kwh)}"
        assert isinstance(data.hour_average_mwh, float)
        assert data.delivery_date is not None
        assert len(data.intervals) > 0

        # Verify JSON serialization (this is what HA does)
        test_attrs = {
            "lmp_rate": data.current_lmp_kwh,
        }
        json.dumps(test_attrs)
        print(f"  ✓ JSON serialization OK")

        return data


async def test_ieso_ga():
    """Test the Global Adjustment feed."""
    from custom_components.ontario_energy_pricing.ieso_ga import IESOGlobalAdjustmentClient

    async with aiohttp.ClientSession() as session:
        client = IESOGlobalAdjustmentClient(session)
        data = await client.async_get_current_rate()

        print(f"  Rate: {data.rate} $/MWh = {data.rate/10} ¢/kWh  (type={type(data.rate).__name__})")
        print(f"  Trade Month: {data.trade_month}")

        assert isinstance(data.rate, (int, float))
        assert data.trade_month is not None
        json.dumps({"ga_rate": data.rate})
        print(f"  ✓ JSON serialization OK")

        return data


async def test_ieso_forecast():
    """Test the predispatch forecast feed."""
    from custom_components.ontario_energy_pricing.ieso_predispatch import IESOPredispatchClient

    async with aiohttp.ClientSession() as session:
        client = IESOPredispatchClient(session)
        data = await client.async_get_predispatch()

        print(f"  Delivery: {data.delivery_date}")
        print(f"  Hours: {len(data.hours)}")
        print(f"  Avg Price: {data.average_price_kwh} ¢/kWh  (type={type(data.average_price_kwh).__name__})")

        assert hasattr(data, 'hours')
        assert len(data.hours) > 0
        assert isinstance(data.average_price_kwh, float)

        # Test cheapest_hours logic
        cheapest = data.cheapest_hours(3)
        print(f"  Cheapest 3 hours: {sorted(cheapest)}")
        assert len(cheapest) == 3

        # Test is_in_cheapest_hours(current_hour, num_hours)
        result = data.is_in_cheapest_hours(3, 3)
        print(f"  Hour 3 is in cheapest 3: {result}")

        json.dumps({"avg_price_kwh": data.average_price_kwh})
        print(f"  ✓ JSON serialization OK")

        return data


async def test_ieso_fuel_mix():
    """Test the fuel mix (generation output) feed."""
    from custom_components.ontario_energy_pricing.ieso_gen_output import IESOGenOutputClient

    async with aiohttp.ClientSession() as session:
        client = IESOGenOutputClient(session)
        data = await client.fetch()

        print(f"  Date: {data.date}")
        print(f"  Hours: {len(data.hours)}")
        current = data.current_hour_output()
        if current:
            nuclear = current.get_fuel("NUCLEAR")
            print(f"  Nuclear: {nuclear.mw if nuclear else 0} MW")
            gas = current.get_fuel("GAS")
            print(f"  Gas: {gas.mw if gas else 0} MW")
            wind = current.get_fuel("WIND")
            print(f"  Wind: {wind.mw if wind else 0} MW")

        return data


async def test_ieso_vg_forecast():
    """Test the variable generation forecast feed."""
    from custom_components.ontario_energy_pricing.ieso_vg_forecast import IESOVGforecastClient

    async with aiohttp.ClientSession() as session:
        client = IESOVGforecastClient(session)
        data = await client.fetch()

        print(f"  Forecast Timestamp: {data.forecast_timestamp}")
        for hour in [1, 6, 12, 18]:
            solar = data.get_solar_total_mw(datetime.now(), hour)
            wind = data.get_wind_total_mw(datetime.now(), hour)
            print(f"  Hour {hour}: solar={solar:.0f} MW, wind={wind:.0f} MW")

        return data


async def test_ieso_shadow_prices():
    """Test the shadow prices feed."""
    from custom_components.ontario_energy_pricing.ieso_shadow_prices import IESOShadowPricesClient

    async with aiohttp.ClientSession() as session:
        client = IESOShadowPricesClient(session)
        data = await client.fetch()

        print(f"  Delivery: {data.delivery_date}")
        print(f"  Constraints: {len(data.constraints)}")
        max_price = data.get_max_shadow_price(datetime.now().hour)
        print(f"  Max shadow price: ${max_price:.2f}/MWh  (type={type(max_price).__name__})")

        assert isinstance(max_price, float)
        assert len(data.constraints) > 0

        json.dumps({"max_shadow_price": max_price})
        print(f"  ✓ JSON serialization OK")

        return data


async def test_ieso_tx_outages():
    """Test the transmission outages feed."""
    from custom_components.ontario_energy_pricing.ieso_tx_outages import IESOTxOutagesClient

    async with aiohttp.ClientSession() as session:
        client = IESOTxOutagesClient(session)
        data = await client.fetch()

        total_capacity = data.get_total_capacity_impact()
        active = data.get_active_outages()
        print(f"  Delivery: {data.delivery_date}")
        print(f"  Total outages: {len(data.outages)}")
        print(f"  Active outages: {len(active)}")
        print(f"  Total capacity impact: {total_capacity:.1f} MW  (type={type(total_capacity).__name__})")

        assert isinstance(total_capacity, (int, float))
        assert len(data.outages) >= len(active)

        json.dumps({"total_capacity": total_capacity})
        print(f"  ✓ JSON serialization OK")

        return data


async def test_ieso_demand_zonal():
    """Test the demand zonal feed."""
    from custom_components.ontario_energy_pricing.ieso_demand_zonal import IESODemandZonalClient

    async with aiohttp.ClientSession() as session:
        client = IESODemandZonalClient(session)
        data = await client.fetch()

        print(f"  Zones: {data.get_zones()}")
        latest = data.get_latest_demand_by_zone("TORONTO")
        if latest:
            print(f"  Toronto demand: {latest.demand_mw} MW  (type={type(latest.demand_mw).__name__})")
            assert isinstance(latest.demand_mw, (int, float)), f"Expected float, got {type(latest.demand_mw)}"

        total_latest = data.get_latest_demand_by_zone("ONTARIO")
        if total_latest:
            print(f"  Ontario total: {total_latest.demand_mw} MW")

        json.dumps({"demand_mw": latest.demand_mw if latest else 0})
        print(f"  ✓ JSON serialization OK")

        return data, latest


async def test_ieso_intertie_lmp():
    """Test the intertie LMP feed."""
    from custom_components.ontario_energy_pricing.ieso_intertie_lmp import IESOIntertieLMPClient

    async with aiohttp.ClientSession() as session:
        client = IESOIntertieLMPClient(session)
        data = await client.fetch()

        print(f"  Delivery: {data.delivery_date}")
        points = data.get_intertie_points()
        print(f"  Intertie points: {points}")
        for pt in points:
            lmp = data.get_current_interval_lmp(pt)
            if lmp is not None:
                print(f"    {pt}: ${lmp:.2f}/MWh  (type={type(lmp).__name__})")
                assert isinstance(lmp, float)

        json.dumps({"points": points})
        print(f"  ✓ JSON serialization OK")

        return data


async def test_ieso_reserve_prices():
    """Test the reserve prices feed."""
    from custom_components.ontario_energy_pricing.ieso_reserves import IESOReservePricesClient

    async with aiohttp.ClientSession() as session:
        client = IESOReservePricesClient(session)
        data = await client.fetch()

        print(f"  Delivery: {data.delivery_date}")
        regions = data.get_regions()
        print(f"  Regions: {regions}")
        for region in regions:
            types = data.get_reserve_types(region)
            print(f"    {region} types: {types}")
            for rt in types:
                price = data.get_reserve_price(region, rt, 1, 1)
                if price is not None:
                    print(f"      {rt}: ${price:.2f}/MWh  (type={type(price).__name__})")
                    assert isinstance(price, float), f"Expected float, got {type(price)}"

        json.dumps({"regions": regions})
        print(f"  ✓ JSON serialization OK")

        return data


async def run_all():
    """Run all end-to-end tests."""
    failures = 0
    total = 0

    tests = [
        ("IESO LMP (Real-time Zonal)", test_ieso_lmp),
        ("IESO Global Adjustment", test_ieso_ga),
        ("IESO Predispatch Forecast", test_ieso_forecast),
        ("IESO Fuel Mix", test_ieso_fuel_mix),
        ("IESO VG Forecast", test_ieso_vg_forecast),
        ("IESO Shadow Prices", test_ieso_shadow_prices),
        ("IESO Transmission Outages", test_ieso_tx_outages),
        ("IESO Demand Zonal", test_ieso_demand_zonal),
        ("IESO Intertie LMP", test_ieso_intertie_lmp),
        ("IESO Reserve Prices", test_ieso_reserve_prices),
    ]

    print("=" * 72)
    print("  ONTARIO ENERGY PRICING - End-to-End Test Suite")
    print("  Fetches REAL data from IESO public servers")
    print(f"  Started: {datetime.now().isoformat()}")
    print("=" * 72)

    for name, test_fn in tests:
        total += 1
        print(f"\n{'─' * 72}")
        print(f"  [{total}] {name}")
        print(f"{'─' * 72}")
        try:
            await test_fn()
            print(f"  ✅ PASS")
        except Exception as e:
            print(f"  ❌ FAIL: {e}")
            traceback.print_exc()
            failures += 1

    print(f"\n{'=' * 72}")
    print(f"  RESULTS: {total - failures}/{total} passed")
    if failures:
        print(f"  ❌ {failures} FAILURES - check above for details")
    else:
        print(f"  ✅ ALL PASSED")
    print(f"{'=' * 72}")

    return failures


if __name__ == "__main__":
    failures = asyncio.run(run_all())
    sys.exit(1 if failures > 0 else 0)
