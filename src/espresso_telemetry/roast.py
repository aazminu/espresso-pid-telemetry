"""Coffee roast bean-probe Rate-of-Rise (RoR) and Development Time Ratio (DTR) curve profiler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class RoastProfileSummary:
    """Comprehensive specialty coffee roast telemetry summary."""

    charge_temp_c: float
    turning_point_sec: float
    turning_point_temp_c: float
    drying_end_sec: float
    first_crack_sec: float
    drop_sec: float
    drop_temp_c: float
    drying_phase_pct: float
    maillard_phase_pct: float
    development_time_ratio_pct: float
    ror_c_per_min: tuple[float, ...]
    ror_crash_detected: bool
    ror_flick_detected: bool


def compute_rate_of_rise(
    timestamps_sec: Sequence[float],
    bean_temps_c: Sequence[float],
    smoothing_window: int = 1,
) -> list[float]:
    """Compute Bean Probe Rate-of-Rise (RoR) in degrees Celsius per minute (C/min).

    Args:
        timestamps_sec: Strictly increasing sample timestamps in seconds.
        bean_temps_c: Bean probe temperature readings in Celsius.
        smoothing_window: Moving-average window width (>= 1) applied to raw RoR values.

    Returns:
        List of RoR values (in C/min) of length `len(timestamps_sec) - 1`.
    """
    n = len(timestamps_sec)
    if n < 2 or len(bean_temps_c) != n:
        raise ValueError("timestamps_sec and bean_temps_c must have matching length >= 2.")
    if smoothing_window < 1:
        raise ValueError("smoothing_window must be >= 1.")

    raw_ror: list[float] = []
    for i in range(1, n):
        dt = float(timestamps_sec[i]) - float(timestamps_sec[i - 1])
        if dt <= 0.0:
            raise ValueError("timestamps_sec must be strictly increasing.")
        dtemp = float(bean_temps_c[i]) - float(bean_temps_c[i - 1])
        raw_ror.append((dtemp / dt) * 60.0)

    if smoothing_window == 1:
        return raw_ror

    smoothed: list[float] = []
    for i in range(len(raw_ror)):
        start = max(0, i - smoothing_window + 1)
        window = raw_ror[start : i + 1]
        smoothed.append(sum(window) / len(window))
    return smoothed


def compute_development_time_ratio(
    first_crack_sec: float,
    drop_sec: float,
    charge_sec: float = 0.0,
) -> float:
    """Compute Development Time Ratio: DTR% = ((t_drop - t_fc) / (t_drop - t_charge)) * 100."""
    if drop_sec <= charge_sec:
        raise ValueError("drop_sec must be strictly greater than charge_sec.")
    if not (charge_sec <= first_crack_sec <= drop_sec):
        raise ValueError("first_crack_sec must lie between charge_sec and drop_sec.")
    total_roast_sec = float(drop_sec) - float(charge_sec)
    dev_sec = float(drop_sec) - float(first_crack_sec)
    return (dev_sec / total_roast_sec) * 100.0


def analyze_roast_curve(
    timestamps_sec: Sequence[float],
    bean_temps_c: Sequence[float],
    first_crack_sec: float,
    drying_end_temp_c: float = 150.0,
    smoothing_window: int = 1,
) -> RoastProfileSummary:
    """Profile a complete coffee roast curve, computing phase percentages and RoR crash/flick."""
    ror = compute_rate_of_rise(timestamps_sec, bean_temps_c, smoothing_window=smoothing_window)
    charge_sec = float(timestamps_sec[0])
    drop_sec = float(timestamps_sec[-1])
    total_sec = drop_sec - charge_sec

    dtr_pct = compute_development_time_ratio(first_crack_sec, drop_sec, charge_sec=charge_sec)

    # Locate Turning Point (minimum bean temperature after charge)
    tp_idx = min(range(len(bean_temps_c)), key=lambda idx: bean_temps_c[idx])
    tp_sec = float(timestamps_sec[tp_idx])
    tp_temp = float(bean_temps_c[tp_idx])

    # Locate Dry End (first sample after Turning Point reaching drying_end_temp_c)
    dry_end_sec = first_crack_sec
    for idx in range(tp_idx, len(bean_temps_c)):
        if bean_temps_c[idx] >= drying_end_temp_c:
            dry_end_sec = min(float(timestamps_sec[idx]), first_crack_sec)
            break

    drying_pct = ((dry_end_sec - charge_sec) / total_sec) * 100.0
    maillard_pct = ((first_crack_sec - dry_end_sec) / total_sec) * 100.0

    # Detect RoR Crash (sharp drop of > 5.0 C/min between consecutive intervals near/after first crack)
    # and RoR Flick (late-roast upward RoR rebound of > 1.5 C/min after first crack)
    ror_crash = False
    ror_flick = False
    for i in range(1, len(ror)):
        sample_t = float(timestamps_sec[i + 1])
        if sample_t >= first_crack_sec - 15.0:
            delta_ror = ror[i] - ror[i - 1]
            if delta_ror <= -5.0:
                ror_crash = True
            if sample_t > first_crack_sec and delta_ror >= 1.5:
                ror_flick = True

    return RoastProfileSummary(
        charge_temp_c=float(bean_temps_c[0]),
        turning_point_sec=tp_sec,
        turning_point_temp_c=tp_temp,
        drying_end_sec=dry_end_sec,
        first_crack_sec=float(first_crack_sec),
        drop_sec=drop_sec,
        drop_temp_c=float(bean_temps_c[-1]),
        drying_phase_pct=drying_pct,
        maillard_phase_pct=maillard_pct,
        development_time_ratio_pct=dtr_pct,
        ror_c_per_min=tuple(ror),
        ror_crash_detected=ror_crash,
        ror_flick_detected=ror_flick,
    )
