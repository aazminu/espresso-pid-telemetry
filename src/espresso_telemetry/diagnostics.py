"""Deterministic runtime diagnostics and invariant verification for `espresso_telemetry`."""

from __future__ import annotations

import time
from typing import Any

from .extraction import simulate_boiler_pid, compute_puck_resistance_curve

def _domain_probe(seed: int) -> dict:
    sim = simulate_boiler_pid(
        setpoint_c=93.0, initial_temp_c=93.0, duration_sec=28.0, dt_sec=0.5, cold_water_flow_ml_s=2.0
    )
    r_curve = compute_puck_resistance_curve([2.0, 9.0, 9.0, 6.0], [1.0, 1.5, 2.0, 2.0])
    return {
        "min_temp_c": round(sim.min_temp_c, 3),
        "max_temp_c": round(sim.max_temp_c, 3),
        "rmse_c": round(sim.rmse_c, 4),
        "peak_resistance": round(max(r_curve), 2),
        "invariants_ok": (sim.min_temp_c > 92.4 and sim.max_temp_c <= 93.2 and sim.rmse_c < 0.25 and max(r_curve) == 6.0),
    }


def run_diagnostic_suite(seed: int = 42) -> dict[str, Any]:
    """Execute deterministic domain probe for `espresso-pid-telemetry` and return structured metrics."""
    if not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    t0 = time.perf_counter()
    metrics = _domain_probe(seed)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    return {
        "repository": "espresso-pid-telemetry",
        "package": "espresso_telemetry",
        "seed": seed,
        "elapsed_ms": elapsed_ms,
        "metrics": metrics,
        "status": "ok" if metrics.get("invariants_ok", False) else "failed",
    }


def validate_runtime_invariants(seed: int = 42) -> dict[str, Any]:
    """Validate deterministic reproducibility and domain invariants for `espresso_telemetry`."""
    run_a = run_diagnostic_suite(seed=seed)
    run_b = run_diagnostic_suite(seed=seed)
    reproducible = run_a["metrics"] == run_b["metrics"]
    passed = bool(run_a["metrics"].get("invariants_ok", False)) and reproducible
    return {
        "repository": "espresso-pid-telemetry",
        "package": "espresso_telemetry",
        "seed": seed,
        "reproducible": reproducible,
        "passed": passed,
        "metrics": run_a["metrics"],
    }
