"""Discrete PID boiler temperature control, Darcy puck resistance & channeling detection, and TDS Extraction Yield."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


class DiscretePIDController:
    """Discrete-time PID controller with anti-windup integral clamping and derivative-on-measurement."""

    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        setpoint: float = 93.0,
        output_min: float = 0.0,
        output_max: float = 100.0,
        integral_limit: float = 50.0,
    ) -> None:
        if output_min >= output_max:
            raise ValueError("output_min must be strictly less than output_max.")
        if integral_limit <= 0.0:
            raise ValueError("integral_limit must be strictly positive.")
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.setpoint = float(setpoint)
        self.output_min = float(output_min)
        self.output_max = float(output_max)
        self.integral_limit = float(integral_limit)
        self.integral = 0.0
        self._prev_measurement: float | None = None

    def reset(self) -> None:
        """Reset accumulated integral state and previous measurement."""
        self.integral = 0.0
        self._prev_measurement = None

    def update(self, measurement: float, dt: float) -> float:
        """Compute clamped control duty cycle for current `measurement` over step `dt` (seconds)."""
        if dt <= 0.0:
            raise ValueError("dt must be strictly positive.")
        error = self.setpoint - float(measurement)
        self.integral += error * dt
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))

        if self._prev_measurement is None:
            d_meas = 0.0
        else:
            d_meas = (float(measurement) - self._prev_measurement) / dt
        self._prev_measurement = float(measurement)

        raw_out = self.kp * error + self.ki * self.integral - self.kd * d_meas
        return max(self.output_min, min(self.output_max, raw_out))


@dataclass(frozen=True)
class BoilerSimulationResult:
    """Time-series telemetry of a simulated espresso boiler under PID control."""

    timestamps_sec: tuple[float, ...]
    temperatures_c: tuple[float, ...]
    heater_duty_pct: tuple[float, ...]
    min_temp_c: float
    max_temp_c: float
    final_temp_c: float
    rmse_c: float


def simulate_boiler_pid(
    setpoint_c: float = 93.0,
    initial_temp_c: float = 93.0,
    duration_sec: float = 30.0,
    dt_sec: float = 0.5,
    kp: float = 65.0,
    ki: float = 22.0,
    kd: float = 8.0,
    cold_water_flow_ml_s: float = 2.0,
    inlet_water_temp_c: float = 65.0,
) -> BoilerSimulationResult:
    """Simulate espresso grouphead/boiler thermal trajectory under PID control during extraction.

    Models a 600 mL saturated brass/stainless brew boiler fed by a pre-heated heat-exchanger
    inlet (`inlet_water_temp_c = 65.0 C`) with heater capacity of +1.10 C/s at 100% duty.
    """
    if duration_sec <= 0.0 or dt_sec <= 0.0:
        raise ValueError("duration_sec and dt_sec must be strictly positive.")

    pid = DiscretePIDController(kp=kp, ki=ki, kd=kd, setpoint=setpoint_c)
    boiler_volume_ml = 600.0
    max_heating_rate_c_per_s = 1.10
    ambient_loss_coeff = 0.0015
    ambient_temp_c = 25.0

    steps = int(round(duration_sec / dt_sec)) + 1
    timestamps: list[float] = []
    temps: list[float] = []
    duties: list[float] = []

    curr_temp = float(initial_temp_c)
    for i in range(steps):
        t = i * dt_sec
        duty = pid.update(curr_temp, dt_sec)
        timestamps.append(t)
        temps.append(curr_temp)
        duties.append(duty)

        q_heater = (duty / 100.0) * max_heating_rate_c_per_s
        q_inlet = (max(0.0, cold_water_flow_ml_s) / boiler_volume_ml) * (inlet_water_temp_c - curr_temp)
        q_ambient = -ambient_loss_coeff * (curr_temp - ambient_temp_c)
        curr_temp += (q_heater + q_inlet + q_ambient) * dt_sec

    sq_err = sum((temp - setpoint_c) ** 2 for temp in temps) / len(temps)
    return BoilerSimulationResult(
        timestamps_sec=tuple(timestamps),
        temperatures_c=tuple(temps),
        heater_duty_pct=tuple(duties),
        min_temp_c=min(temps),
        max_temp_c=max(temps),
        final_temp_c=temps[-1],
        rmse_c=math.sqrt(sq_err),
    )


@dataclass(frozen=True)
class ChannelingAnalysis:
    """Darcy porous-media puck resistance telemetry and channeling diagnostic."""

    resistances_bar_s_ml: tuple[float, ...]
    mean_pressurized_resistance: float
    peak_resistance: float
    max_resistance_drop_rate: float
    channeling_detected: bool
    channeling_timestamps_sec: tuple[float, ...]


def compute_puck_resistance_curve(
    pressure_bar: Sequence[float],
    flow_ml_s: Sequence[float],
    min_flow_floor: float = 0.05,
) -> list[float]:
    """Compute instantaneous Darcy puck resistance R_puck(t) = Delta_P(t) / Q(t).

    Args:
        pressure_bar: Gauge pressure sequence in bar.
        flow_ml_s: Volumetric flow rate sequence in mL/s.
        min_flow_floor: Lower bound clamp on flow rate (mL/s) to avoid division by zero during pre-wetting.

    Returns:
        List of puck resistance values in bar * s / mL.
    """
    if len(pressure_bar) != len(flow_ml_s) or not pressure_bar:
        raise ValueError("pressure_bar and flow_ml_s must be non-empty sequences of equal length.")
    if min_flow_floor <= 0.0:
        raise ValueError("min_flow_floor must be strictly positive.")

    resistances: list[float] = []
    for p, q in zip(pressure_bar, flow_ml_s):
        if p < 0.0:
            raise ValueError("Pressure values must be non-negative.")
        eff_q = max(float(min_flow_floor), float(q))
        resistances.append(float(p) / eff_q)
    return resistances


def detect_puck_channeling(
    timestamps_sec: Sequence[float],
    pressure_bar: Sequence[float],
    flow_ml_s: Sequence[float],
    preinfusion_cutoff_sec: float = 6.0,
    drop_rate_threshold: float = -0.85,
) -> ChannelingAnalysis:
    """Detect hydraulic channeling events from pressure and flow extraction telemetry.

    Flags timestamps after `preinfusion_cutoff_sec` (while pressure >= 4.0 bar) where
    the rate of change `dR_puck/dt` drops below `drop_rate_threshold` (bar*s/mL per second)
    while flow is simultaneously accelerating (`dQ/dt > 0.15 mL/s^2`).
    """
    n = len(timestamps_sec)
    if n < 2 or len(pressure_bar) != n or len(flow_ml_s) != n:
        raise ValueError("timestamps_sec, pressure_bar, and flow_ml_s must have matching length >= 2.")

    resistances = compute_puck_resistance_curve(pressure_bar, flow_ml_s)
    pressurized_r = [
        r for t, p, r in zip(timestamps_sec, pressure_bar, resistances) if t >= preinfusion_cutoff_sec and p >= 4.0
    ]
    mean_r = sum(pressurized_r) / len(pressurized_r) if pressurized_r else sum(resistances) / n

    channel_times: list[float] = []
    min_dr_dt = 0.0

    for i in range(1, n):
        dt = float(timestamps_sec[i]) - float(timestamps_sec[i - 1])
        if dt <= 0.0:
            raise ValueError("timestamps_sec must be strictly increasing.")
        if timestamps_sec[i] < preinfusion_cutoff_sec or pressure_bar[i] < 4.0:
            continue

        dr_dt = (resistances[i] - resistances[i - 1]) / dt
        dq_dt = (float(flow_ml_s[i]) - float(flow_ml_s[i - 1])) / dt
        if dr_dt < min_dr_dt:
            min_dr_dt = dr_dt

        if dr_dt <= drop_rate_threshold and dq_dt > 0.15:
            channel_times.append(float(timestamps_sec[i]))

    return ChannelingAnalysis(
        resistances_bar_s_ml=tuple(resistances),
        mean_pressurized_resistance=mean_r,
        peak_resistance=max(resistances),
        max_resistance_drop_rate=min_dr_dt,
        channeling_detected=len(channel_times) > 0,
        channeling_timestamps_sec=tuple(channel_times),
    )


@dataclass(frozen=True)
class ExtractionReport:
    """Refractometry Extraction Yield (EY%) and SCA Gold Cup classification."""

    tds_percent: float
    beverage_mass_g: float
    dry_dose_g: float
    brew_ratio: float
    extraction_yield_pct: float
    classification: str
    is_balanced_gold_cup: bool


def compute_extraction_yield(
    tds_percent: float,
    beverage_mass_g: float,
    dry_dose_g: float,
) -> float:
    """Compute Percentage Extraction Yield: EY% = (TDS% * M_bev) / M_dose."""
    if tds_percent <= 0.0 or beverage_mass_g <= 0.0 or dry_dose_g <= 0.0:
        raise ValueError("tds_percent, beverage_mass_g, and dry_dose_g must be strictly positive.")
    return (float(tds_percent) * float(beverage_mass_g)) / float(dry_dose_g)


def classify_extraction_profile(
    tds_percent: float,
    beverage_mass_g: float,
    dry_dose_g: float,
    min_ideal_ey: float = 18.0,
    max_ideal_ey: float = 22.0,
) -> ExtractionReport:
    """Evaluate brew ratio, Extraction Yield (EY%), and sensory extraction window."""
    ey = compute_extraction_yield(tds_percent, beverage_mass_g, dry_dose_g)
    ratio = float(beverage_mass_g) / float(dry_dose_g)

    if ey < min_ideal_ey:
        classification = "UNDER_EXTRACTED"
        balanced = False
    elif ey > max_ideal_ey:
        classification = "OVER_EXTRACTED"
        balanced = False
    else:
        classification = "BALANCED_GOLD_CUP"
        balanced = True

    return ExtractionReport(
        tds_percent=float(tds_percent),
        beverage_mass_g=float(beverage_mass_g),
        dry_dose_g=float(dry_dose_g),
        brew_ratio=ratio,
        extraction_yield_pct=ey,
        classification=classification,
        is_balanced_gold_cup=balanced,
    )
