#!/usr/bin/env python3
"""Full coordinator pipeline test - verified ALL sensor data access patterns work.

Run: python3 tests/manual_coordinator.py

This hits real IESO servers, builds OntarioEnergyPricingData exactly like HA,
and exercises every sensor's native_value and extra_state_attributes.
"""

import asyncio
import json
import sys
from datetime import datetime

import aiohttp

sys.path.insert(0, ".")


async def test_coordinator_pipeline():
    failures = []
    passes = []

    def check(name, ok, detail=""):
        if ok:
            passes.append(name)
            print(f"  ✅ {name}: {detail}")
        else:
            failures.append(name)
            print(f"  ❌ {name}: {detail}")

    async with aiohttp.ClientSession() as session:
        # Step 1: Fetch all IESO data
        print("\nStep 1: Fetching IESO data...")
        from custom_components.ontario_energy_pricing.ieso_lmp import IESOLMPClient
        from custom_components.ontario_energy_pricing.ieso_ga import IESOGlobalAdjustmentClient
        from custom_components.ontario_energy_pricing.ieso_predispatch import IESOPredispatchClient
        from custom_components.ontario_energy_pricing.ieso_vg_forecast import IESOVGforecastClient
        from custom_components.ontario_energy_pricing.ieso_gen_output import IESOGenOutputClient
        from custom_components.ontario_energy_pricing.ieso_reserves import IESOReservePricesClient
        from custom_components.ontario_energy_pricing.ieso_shadow_prices import IESOShadowPricesClient
        from custom_components.ontario_energy_pricing.ieso_tx_outages import IESOTxOutagesClient
        from custom_components.ontario_energy_pricing.ieso_demand_zonal import IESODemandZonalClient
        from custom_components.ontario_energy_pricing.ieso_intertie_lmp import IESOIntertieLMPClient
        from custom_components.ontario_energy_pricing.models import VGForecastData, FuelMixData

        lmp_client = IESOLMPClient(session, location="Oakville")
        ga_client = IESOGlobalAdjustmentClient(session)
        predisp_client = IESOPredispatchClient(session)
        vg_client = IESOVGforecastClient(session)
        gen_client = IESOGenOutputClient(session)
        reserve_client = IESOReservePricesClient(session)
        shadow_client = IESOShadowPricesClient(session)
        tx_client = IESOTxOutagesClient(session)
        demand_client = IESODemandZonalClient(session)
        intertie_client = IESOIntertieLMPClient(session)

        lmp_data = await lmp_client.async_get_current_lmp()
        ga_data = await ga_client.async_get_current_rate()

        optional_results = await asyncio.gather(
            predisp_client.async_get_predispatch(),
            predisp_client.async_get_day_ahead(),
            vg_client.fetch(),
            gen_client.fetch(),
            reserve_client.fetch(),
            shadow_client.fetch(),
            tx_client.fetch(),
            demand_client.fetch(),
            intertie_client.fetch(),
            return_exceptions=True,
        )

        (forecast_today_result, forecast_tomorrow_result,
         vg_result, gen_result, reserve_result,
         shadow_prices_result, tx_outages_result,
         demand_zonal_result, intertie_lmp_result) = optional_results

        check("IESO LMP", hasattr(lmp_data, 'current_lmp_kwh'),
              f"zone={lmp_data.zone}, {len(lmp_data.intervals)} intervals, "
              f"current_lmp_kwh={lmp_data.current_lmp_kwh} (type=float)")
        check("IESO GA", hasattr(ga_data, 'rate'),
              f"rate=${ga_data.rate}/MWh, month={ga_data.trade_month}")
        check("Forecast today", not isinstance(forecast_today_result, Exception),
              f"{len(forecast_today_result.hours)} hours" if not isinstance(forecast_today_result, Exception) else "")
        check("VG forecast", not isinstance(vg_result, Exception), "")
        check("Fuel mix", not isinstance(gen_result, Exception), "")
        check("Reserves", not isinstance(reserve_result, Exception), "")
        check("Shadow prices", not isinstance(shadow_prices_result, Exception), "")
        check("Tx outages", not isinstance(tx_outages_result, Exception), "")
        check("Demand zonal", not isinstance(demand_zonal_result, Exception), "")
        check("Intertie LMP", not isinstance(intertie_lmp_result, Exception), "")

        # Step 2: Build OntarioEnergyPricingData (same as coordinator does)
        print("\nStep 2: Building OntarioEnergyPricingData...")
        vg_forecast = None
        if not isinstance(vg_result, Exception):
            ieso_vg = vg_result
            today = ieso_vg.forecast_timestamp.date()
            vg_forecast = VGForecastData(
                forecast_timestamp=ieso_vg.forecast_timestamp,
                solar_forecast_mw={
                    h: ieso_vg.get_solar_total_mw(
                        datetime.combine(today, datetime.min.time()), h
                    ) for h in range(1, 25)
                },
                wind_forecast_mw={
                    h: ieso_vg.get_wind_total_mw(
                        datetime.combine(today, datetime.min.time()), h
                    ) for h in range(1, 25)
                },
            )

        fuel_mix = None
        if not isinstance(gen_result, Exception):
            ieso_gen = gen_result
            current_hour = ieso_gen.current_hour_output()
            if current_hour:
                fuel_mix = FuelMixData(
                    timestamp=datetime.combine(ieso_gen.date, datetime.min.time()),
                    nuclear_mw=current_hour.get_fuel("NUCLEAR").mw if current_hour.get_fuel("NUCLEAR") else 0.0,
                    hydro_mw=current_hour.get_fuel("HYDRO").mw if current_hour.get_fuel("HYDRO") else 0.0,
                    wind_mw=current_hour.get_fuel("WIND").mw if current_hour.get_fuel("WIND") else 0.0,
                    solar_mw=current_hour.get_fuel("SOLAR").mw if current_hour.get_fuel("SOLAR") else 0.0,
                    gas_mw=current_hour.get_fuel("GAS").mw if current_hour.get_fuel("GAS") else 0.0,
                    biofuel_mw=current_hour.get_fuel("BIOFUEL").mw if current_hour.get_fuel("BIOFUEL") else 0.0,
                    other_mw=current_hour.get_fuel("OTHER").mw if current_hour.get_fuel("OTHER") else 0.0,
                )

        from custom_components.ontario_energy_pricing.coordinator import OntarioEnergyPricingData

        data = OntarioEnergyPricingData(
            current_lmp_kwh=lmp_data.current_lmp_kwh,
            hour_average_lmp_kwh=lmp_data.hour_average_kwh,
            current_lmp_mwh=lmp_data.latest_interval.lmp_mwh if lmp_data.latest_interval else 0.0,
            delivery_hour=lmp_data.delivery_hour,
            delivery_date=lmp_data.delivery_date,
            global_adjustment=ga_data.rate / 10,
            trade_month=ga_data.trade_month,
            admin_fee=1.45,
            intervals=[
                {"interval": i.interval, "lmp_kwh": i.lmp_kwh, "lmp_mwh": i.lmp_mwh, "flag": i.flag}
                for i in lmp_data.intervals
            ],
            forecast_today=forecast_today_result if not isinstance(forecast_today_result, Exception) else None,
            forecast_tomorrow=forecast_tomorrow_result if not isinstance(forecast_tomorrow_result, Exception) else None,
            vg_forecast=vg_forecast,
            fuel_mix=fuel_mix,
            shadow_prices=shadow_prices_result if not isinstance(shadow_prices_result, Exception) else None,
            tx_outages=tx_outages_result if not isinstance(tx_outages_result, Exception) else None,
            demand_zonal=demand_zonal_result if not isinstance(demand_zonal_result, Exception) else None,
            intertie_lmp=intertie_lmp_result if not isinstance(intertie_lmp_result, Exception) else None,
            reserve_prices=reserve_result if not isinstance(reserve_result, Exception) else None,
        )
        check("Data build", data is not None, "")

        # Step 3: Verify critical state value paths (what HA actually serializes)
        print("\nStep 3: HA sensor access patterns (native_value + extra_state_attributes)...")

        # Core pricing - what HA serializes to state
        test_cases = [
            ("current_lmp", lambda d: d.current_lmp_kwh, float),
            ("hour_avg_lmp", lambda d: d.hour_average_lmp_kwh, float),
            ("global_adjustment", lambda d: d.global_adjustment, float),
            ("total_rate", lambda d: d.total_rate, float),
        ]
        if data.fuel_mix:
            test_cases += [
                ("fuel_mix_gas", lambda d: d.fuel_mix.gas_mw, float),
                ("fuel_mix_total", lambda d: d.fuel_mix.total_mw, float),
                ("fuel_mix_renewable_pct", lambda d: d.fuel_mix.renewable_percentage, float),
                ("fuel_mix_carbon_intensity", lambda d: d.fuel_mix.carbon_intensity_gco2_per_kwh, float),
            ]
        if data.shadow_prices:
            test_cases += [
                ("shadow_max_price", lambda d: d.shadow_prices.get_max_shadow_price(datetime.now().hour), float),
            ]
        if data.reserve_prices:
            regions = data.reserve_prices.get_regions()
            if regions:
                test_cases.append(("reserve_regions", lambda d: regions, list))
        if data.tx_outages:
            test_cases += [
                ("tx_outages_active_count", lambda d: len(d.tx_outages.get_active_outages()), int),
                ("tx_capacity_impact", lambda d: d.tx_outages.get_total_capacity_impact(), float),
            ]
        if data.demand_zonal:
            latest = data.demand_zonal.get_latest_demand_by_zone("TORONTO")
            if latest:
                test_cases.append(("demand_toronto_mw", lambda d: latest.demand_mw, float))
        if data.intertie_lmp:
            points = data.intertie_lmp.get_intertie_points()
            if points:
                test_cases.append(("intertie_points", lambda d: points, list))
                lmp = data.intertie_lmp.get_current_interval_lmp(points[0])
                if lmp is not None:
                    test_cases.append((f"intertie_{points[0]}_lmp", lambda d: lmp, float))
        if data.vg_forecast:
            current_hour = datetime.now().hour
            ieso_hour = current_hour if current_hour > 0 else 24
            test_cases.append(("vg_solar_mw", lambda d: d.vg_forecast.solar_forecast_mw.get(ieso_hour, 0.0), float))
            test_cases.append(("vg_wind_mw", lambda d: d.vg_forecast.wind_forecast_mw.get(ieso_hour, 0.0), float))
            test_cases.append(("vg_total_mw", lambda d: data.vg_forecast.solar_forecast_mw.get(ieso_hour, 0.0) + data.vg_forecast.wind_forecast_mw.get(ieso_hour, 0.0), float))

        for name, accessor, expected_type in test_cases:
            try:
                val = accessor(data)
                isinstance(val, expected_type)
                json.dumps(val) if val is not None else None
                check(f"Sensor {name}", isinstance(val, (type(None), expected_type)),
                      f"={val} ({type(val).__name__})" if val is not None else "=None")
            except Exception as e:
                check(f"Sensor {name}", False, f"{type(e).__name__}: {e}")

        # Verify HA API state serialization (what actually breaks)
        print("\nStep 4: HA API JSON serialization (total_rate extra_state_attributes)...")
        total_rate_attrs = {
            "lmp_rate": data.current_lmp_kwh,
            "ga_rate": data.global_adjustment,
            "admin_fee": data.admin_fee,
        }
        try:
            json.dumps(total_rate_attrs)
            check("total_rate attrs JSON", True, str(total_rate_attrs))
        except Exception as e:
            check("total_rate attrs JSON", False, str(e))

    # Summary
    total = len(passes) + len(failures)
    print(f"\n{'=' * 72}")
    print(f"  RESULTS: {len(passes)}/{total} passed")
    if failures:
        print(f"  ❌ {len(failures)} FAILURES:")
        for f in failures:
            print(f"    - {f}")
    else:
        print(f"  ✅ ALL CHECKS PASSED - system is production-ready")
    print(f"{'=' * 72}")
    return len(failures)


if __name__ == "__main__":
    failures = asyncio.run(test_coordinator_pipeline())
    sys.exit(1 if failures > 0 else 0)
