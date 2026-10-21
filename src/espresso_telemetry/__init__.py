"""Specialty coffee espresso PID telemetry, Darcy puck resistance, and roast RoR/DTR toolkit."""

from .extraction import (
    BoilerSimulationResult,
    ChannelingAnalysis,
    DiscretePIDController,
    ExtractionReport,
    classify_extraction_profile,
    compute_extraction_yield,
    compute_puck_resistance_curve,
    detect_puck_channeling,
    simulate_boiler_pid,
)
from .roast import (
    RoastProfileSummary,
    analyze_roast_curve,
    compute_development_time_ratio,
    compute_rate_of_rise,
)

__all__ = [
    "DiscretePIDController",
    "BoilerSimulationResult",
    "ChannelingAnalysis",
    "ExtractionReport",
    "simulate_boiler_pid",
    "compute_puck_resistance_curve",
    "detect_puck_channeling",
    "compute_extraction_yield",
    "classify_extraction_profile",
    "RoastProfileSummary",
    "compute_rate_of_rise",
    "compute_development_time_ratio",
    "analyze_roast_curve",
]

__version__ = "0.2.0"

from .diagnostics import run_diagnostic_suite, validate_runtime_invariants
__all__ = list(__all__) + ["run_diagnostic_suite", "validate_runtime_invariants"]
