"""Unit and integration test suite for espresso-pid-telemetry."""

from __future__ import annotations

import pytest

from espresso_telemetry import (
    DiscretePIDController,
    analyze_roast_curve,
    classify_extraction_profile,
    compute_development_time_ratio,
    compute_extraction_yield,
    compute_puck_resistance_curve,
    compute_rate_of_rise,
    detect_puck_channeling,
    simulate_boiler_pid,
)


def test_pid_controller_proportional_response_and_clamping() -> None:
    pid = DiscretePIDController(kp=25.0, ki=0.0, kd=0.0, setpoint=93.0, output_min=0.0, output_max=100.0)
    # 2.0 C below setpoint -> P = 50%
    assert pid.update(91.0, dt=0.5) == pytest.approx(50.0)
    # 6.0 C below setpoint -> unclamped 150%, clamped to 100%
    assert pid.update(87.0, dt=0.5) == pytest.approx(100.0)
    # Above setpoint -> clamped to 0%
    assert pid.update(95.0, dt=0.5) == pytest.approx(0.0)


def test_pid_controller_anti_windup_integral_limit() -> None:
    pid = DiscretePIDController(kp=0.0, ki=2.0, kd=0.0, setpoint=93.0, integral_limit=10.0)
    for _ in range(20):
        out = pid.update(80.0, dt=1.0)
    assert pid.integral == pytest.approx(10.0)
    assert out == pytest.approx(20.0)


def test_pid_controller_derivative_on_measurement_damping() -> None:
    pid = DiscretePIDController(kp=10.0, ki=0.0, kd=5.0, setpoint=93.0)
    # Step 1: prev_measurement is None, d_meas = 0 -> out = 10 * (93 - 90) = 30
    assert pid.update(90.0, dt=1.0) == pytest.approx(30.0)
    # Step 2: temp rises rapidly to 92.0 (d_meas = +2.0 C/s) -> out = 10*(1) - 5*(2.0) = 0.0
    assert pid.update(92.0, dt=1.0) == pytest.approx(0.0)


def test_simulate_boiler_pid_maintains_intrashot_stability() -> None:
    sim = simulate_boiler_pid(
        setpoint_c=93.0,
        initial_temp_c=93.0,
        duration_sec=28.0,
        dt_sec=0.5,
        cold_water_flow_ml_s=2.0,
    )
    # Boiler temperature stays within 0.6 C of 93.0 C throughout a 28s pull
    assert sim.min_temp_c > 92.4
    assert sim.max_temp_c <= 93.2
    assert sim.rmse_c < 0.25


def test_compute_puck_resistance_curve_darcy_ratio() -> None:
    pressures = [2.0, 9.0, 9.0, 6.0]
    flows = [1.0, 1.5, 2.0, 2.0]
    r = compute_puck_resistance_curve(pressures, flows)
    assert r == pytest.approx([2.0, 6.0, 4.5, 3.0])


def test_compute_puck_resistance_clamps_zero_flow_floor() -> None:
    r = compute_puck_resistance_curve([1.5], [0.0], min_flow_floor=0.1)
    assert r == pytest.approx([15.0])


def test_detect_puck_channeling_clean_declining_lever_shot() -> None:
    timestamps = [0.0, 3.0, 6.0, 10.0, 15.0, 20.0, 25.0, 30.0]
    pressures = [2.0, 3.5, 9.0, 8.8, 8.4, 7.8, 7.0, 6.2]
    flows = [0.8, 1.0, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]
    analysis = detect_puck_channeling(timestamps, pressures, flows)
    assert analysis.channeling_detected is False
    assert analysis.channeling_timestamps_sec == ()


def test_detect_puck_channeling_flags_sudden_puck_erosion_spike() -> None:
    timestamps = [0.0, 3.0, 6.0, 10.0, 12.0, 14.0, 18.0, 22.0]
    pressures = [2.0, 4.0, 9.0, 9.0, 8.2, 8.5, 8.5, 8.0]
    # At t=12.0s, flow suddenly surges from 1.4 mL/s to 3.2 mL/s due to a channel
    flows = [0.8, 1.0, 1.3, 1.4, 3.2, 3.3, 3.4, 3.5]
    analysis = detect_puck_channeling(timestamps, pressures, flows)
    assert analysis.channeling_detected is True
    assert 12.0 in analysis.channeling_timestamps_sec
    assert analysis.max_resistance_drop_rate < -1.5


def test_compute_extraction_yield_exact_formula() -> None:
    # 10.0% TDS * 38.0g beverage / 19.0g dose = 20.0% EY
    assert compute_extraction_yield(10.0, 38.0, 19.0) == pytest.approx(20.0)


def test_classify_extraction_profile_gold_cup_vs_under_and_over() -> None:
    balanced = classify_extraction_profile(tds_percent=10.0, beverage_mass_g=38.0, dry_dose_g=19.0)
    assert balanced.is_balanced_gold_cup is True
    assert balanced.classification == "BALANCED_GOLD_CUP"
    assert balanced.brew_ratio == pytest.approx(2.0)

    under = classify_extraction_profile(tds_percent=8.0, beverage_mass_g=36.0, dry_dose_g=20.0)
    assert under.extraction_yield_pct == pytest.approx(14.4)
    assert under.classification == "UNDER_EXTRACTED"

    over = classify_extraction_profile(tds_percent=11.5, beverage_mass_g=42.0, dry_dose_g=20.0)
    assert over.extraction_yield_pct == pytest.approx(24.15)
    assert over.classification == "OVER_EXTRACTED"


def test_compute_rate_of_rise_converts_to_celsius_per_minute() -> None:
    # +3.0 C over 15 seconds = +12.0 C/min; +2.0 C over 15 seconds = +8.0 C/min
    ts = [60.0, 75.0, 90.0]
    temps = [120.0, 123.0, 125.0]
    assert compute_rate_of_rise(ts, temps) == pytest.approx([12.0, 8.0])


def test_compute_development_time_ratio_dtr() -> None:
    # First crack at 450s (7:30), drop at 540s (9:00) -> 90s / 540s = 16.6667% DTR
    assert compute_development_time_ratio(first_crack_sec=450.0, drop_sec=540.0) == pytest.approx(16.6666667)


def test_analyze_roast_curve_smooth_declining_ror_profile() -> None:
    ts = [0.0, 45.0, 180.0, 270.0, 360.0, 450.0, 500.0, 540.0]
    temps = [200.0, 92.0, 132.0, 152.0, 175.0, 196.0, 205.5, 211.5]
    summary = analyze_roast_curve(ts, temps, first_crack_sec=450.0)
    assert summary.turning_point_sec == 45.0
    assert summary.turning_point_temp_c == 92.0
    assert summary.drying_end_sec == 270.0
    assert summary.drying_phase_pct == pytest.approx(50.0)
    assert summary.maillard_phase_pct == pytest.approx(33.333333, rel=1e-4)
    assert summary.development_time_ratio_pct == pytest.approx(16.666667, rel=1e-4)
    assert summary.ror_crash_detected is False
    assert summary.ror_flick_detected is False


def test_analyze_roast_curve_detects_post_crack_ror_crash_and_flick() -> None:
    ts = [0.0, 45.0, 240.0, 420.0, 450.0, 480.0, 510.0, 540.0]
    # At 450s (FC): RoR was (196-189)*2 = 14 C/min
    # 450->480s: temp barely rises 196->197.5 (RoR = 3.0 C/min -> delta = -11.0 C/min -> CRASH)
    # 480->510s: RoR rebounds 197.5->201.5 (RoR = 8.0 C/min -> delta = +5.0 C/min -> FLICK)
    temps = [195.0, 95.0, 150.0, 189.0, 196.0, 197.5, 201.5, 205.0]
    summary = analyze_roast_curve(ts, temps, first_crack_sec=450.0)
    assert summary.ror_crash_detected is True
    assert summary.ror_flick_detected is True


def test_input_validation_errors_across_modules() -> None:
    with pytest.raises(ValueError, match="strictly positive"):
        compute_extraction_yield(0.0, 36.0, 18.0)
    with pytest.raises(ValueError, match="between charge_sec and drop_sec"):
        compute_development_time_ratio(first_crack_sec=600.0, drop_sec=540.0)
    with pytest.raises(ValueError, match="strictly increasing"):
        compute_rate_of_rise([0.0, 10.0, 10.0], [100.0, 110.0, 120.0])
