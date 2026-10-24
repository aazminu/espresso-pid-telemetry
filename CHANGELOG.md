# Changelog — `espresso-pid-telemetry`

All notable engineering changes to `espresso-pid-telemetry` (`espresso_telemetry`) are documented in this file.

## [0.3.0] — 2026-10-24
### Added
- Documented CLI diagnostic usage (`python -m espresso_telemetry --self-test --json`) and deterministic invariant verification workflows in `README.md`.
- Added release history and semantic versioning audit trail in `CHANGELOG.md`.

## [0.2.1] — 2026-10-23
### Added
- Added automated CLI and runtime invariant regression suite in `tests/test_diagnostics_cli.py` covering seed determinism, negative-seed rejection, JSON output schema, and `--self-test` exit codes.

## [0.2.0] — 2026-10-21
### Added
- Added `src/espresso_telemetry/diagnostics.py` (`run_diagnostic_suite`, `validate_runtime_invariants`) and module CLI runner `src/espresso_telemetry/__main__.py`.
- Exported diagnostic helpers in `espresso_telemetry.__all__`.

## [0.1.0] — 2026-10-19
### Added
- Initial architecture and core test suite: Discrete-time PID grouphead temperature controller with anti-windup clamping, Darcy's Law puck hydraulic resistance modeling, and roast RoR/DTR telemetry.
