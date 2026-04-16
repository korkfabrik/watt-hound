# WattHound – Roadmap

## v0.2 – Phase-aware measurement
- Config Flow: optional L1 / L2 / L3 sensor inputs
- Auto-detect which phase a device lives on from its first clean measurement
- Phase-scoped dirty detection: two devices on *different* phases switching simultaneously are both treated as clean
- Measure delta per phase instead of total house power → less noise from unrelated phases
- Store phase assignment per device in persistent storage

## v0.3 – Energy Dashboard integration
- Automatically create a Riemann sum (integration) sensor for each learned device
- Sensors get `device_class: energy` and `state_class: total_increasing`
- No manual YAML required to appear in the Energy Dashboard

## v0.4 – Dimmer / brightness awareness
- Track brightness level at time of switch event
- Store separate power estimates per brightness bucket (e.g. 0–25%, 25–50%, 50–75%, 75–100%)
- Reported power scales with current brightness state

## v0.5 – PowerCalc seed values
- On first setup, check if PowerCalc is installed
- If a PowerCalc estimate exists for a device, use it as the Bayesian prior (starting value before real measurements exist)
- Speeds up cold-start significantly for known devices (Philips Hue, IKEA, etc.)

## v0.6 – Validation layer
- For devices that *do* have their own power sensor (e.g. Shelly plug), compare WattHound's estimate against real readings
- Surface accuracy score in sensor attributes
- Use validated devices to calibrate the measurement timing for that specific installation

## v0.7 – History Bootstrap
- On first start (or via a "Learn from history" button in the UI), query HA's recorder history for the last X days
- Correlate all past switch events with surrounding power sensor values
- Run the same clean/dirty detection logic retroactively
- Pre-warm the Bayesian estimator → devices have 50+ samples from day one instead of starting cold
- Configurable lookback window (default: 30 days)

## v0.8 – WattHound Analyst (MCP)
- Separate standalone MCP server (~100 lines Python) that exposes HA history data as a tool
- Claude reads weeks of switch events + power time series and analyses them freely
- Can detect patterns that fixed algorithms miss: inrush currents, dimmer stages, devices that always switch together, appliance aging
- Outputs structured JSON that can be imported directly into WattHound's learned storage
- Runs on-demand or on a schedule (e.g. weekly deep analysis)

## Backlog / Ideas
- Service call to manually reset learned values for a specific device
- Dashboard card (Lovelace) showing confidence + sample progress per device
- Anomaly detection: alert if a device's power draw suddenly changes significantly (e.g. appliance aging)
- MQTT publishing of learned values for external use
