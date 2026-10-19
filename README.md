# espresso-pid-telemetry

Specialty coffee **espresso extraction** and **drum/fluid-bed roast telemetry** analytics library in pure Python. Designed for analyzing 9-bar pressure/flow transducer curves, discrete boiler PID thermal stability under brew-water influx, optical refractometry Extraction Yield ($EY\%$), and bean-probe Rate-of-Rise ($RoR$) / Development Time Ratio ($DTR\%$) curves.

## Core Models & Physics

### 1. Discrete PID Boiler Thermal Control

Simulates a brass/stainless espresso boiler thermal mass with anti-windup integral clamping and derivative-on-measurement damping during cold-water intrashot flow disturbances:

$$u(t_k) = \text{clip}\!\left(K_p e_k + K_i \sum_{j=0}^{k} e_j \Delta t - K_d \frac{T_k - T_{k-1}}{\Delta t},\; u_{\min},\; u_{\max}\right)$$

### 2. Darcy's Law Porous-Media Puck Resistance & Channeling Detection

Models compacted espresso coffee pucks as a deformable porous bed where instantaneous hydraulic resistance $R_{\text{puck}}(t)$ relates head-space gauge pressure $\Delta P(t)$ ($\text{bar}$) to volumetric flow rate $Q(t)$ ($\text{mL/s}$):

$$R_{\text{puck}}(t) = \frac{\Delta P(t)}{Q(t)} \quad \left[\frac{\text{bar}\cdot\text{s}}{\text{mL}}\right]$$

During steady pressurized extraction ($t \ge t_{\text{preinfusion}}$), gradual solubles dissolution yields a smooth, monotonic resistance decay. Localized **puck channeling** (pinholes or sidewall bypass) manifests as an abrupt negative spike in $\frac{d R_{\text{puck}}}{dt}$ accompanied by an uncommanded flow surge.

### 3. Refractometry Extraction Yield ($EY\%$)

Given measured Total Dissolved Solids ($\text{TDS}\%$), beverage mass/volume $V_{\text{bev}}$ ($\text{g}$), and dry ground coffee dose $M_{\text{dose}}$ ($\text{g}$):

$$EY\% = \frac{\text{TDS}\% \times V_{\text{bev}}}{M_{\text{dose}}}$$

Evaluates whether a shot lands within the specialty **Gold Cup / Balanced Extraction window** ($18.0\% \le EY\% \le 22.0\%$).

### 4. Roast Rate-of-Rise ($RoR$) & Development Time Ratio ($DTR\%$)

Computes bean-probe thermal velocity in $^\circ\text{C}/\text{min}$, identifies the post-charge **Turning Point**, partitions the roast into **Drying**, **Maillard**, and **Development** phases, computes **Development Time Ratio**:

$$\text{DTR}\% = \frac{t_{\text{drop}} - t_{\text{first\_crack}}}{t_{\text{drop}} - t_{\text{charge}}} \times 100\%$$

and flags post-crack **RoR Crash** and late-roast **RoR Flick** anomalies.

## Quickstart

```python
from espresso_telemetry import (
    classify_extraction_profile,
    detect_puck_channeling,
    simulate_boiler_pid,
    analyze_roast_curve,
)

# 1. Refractometry & SCA Extraction Yield
shot = classify_extraction_profile(tds_percent=10.2, beverage_mass_g=38.0, dry_dose_g=19.0)
print(f"Brew Ratio: 1:{shot.brew_ratio:.1f}, EY: {shot.extraction_yield_pct:.2f}% ({shot.classification})")

# 2. Simulate 93.0 C Boiler PID during a 28-second 2.0 mL/s espresso pull
sim = simulate_boiler_pid(setpoint_c=93.0, initial_temp_c=93.0, duration_sec=28.0, cold_water_flow_ml_s=2.0)
print(f"Min intrashot temp: {sim.min_temp_c:.2f} C, RMSE: {sim.rmse_c:.3f} C")
```

## Running Tests

```bash
pytest
```

## License

MIT © [Abdullah Azmi](https://abdullahazmi.com)
