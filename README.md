# WattHound

A Home Assistant custom integration that **automatically learns the power consumption** of your lights and switches by watching a whole-house power meter and correlating it with switch events.

No manual configuration per device. No fixed profiles. It learns from your actual wiring.

---

## How it works

1. When a light or switch changes state, the integration records the power reading from your meter.
2. After a configurable delay (default 4 s), it reads the power again and computes the delta.
3. If no other devices switched within the **clean window**, the measurement is stored as a clean sample.
4. A Bayesian-inspired rolling estimator computes the best estimate from the clean samples.
5. Once enough clean samples exist, a virtual power sensor becomes available for the Energy Dashboard.

### Dirty detection

If two devices switch within the clean window of each other, both measurements are marked **dirty** and discarded. This prevents overlap contamination. Over time, every device will accumulate enough clean measurements.

---

## Supported meters

Any Home Assistant sensor entity with a numeric power reading in Watts works:

| Meter | Notes |
|---|---|
| Shelly 3EM | Reports every ~2 s → use measure delay ≥ 4 s |
| Shelly EM | Same as above |
| Tibber Pulse | Depends on firmware/reporting interval |
| SML Lesekopf (HICHI, etc.) | Usually 1–2 s → delay 3–4 s |
| Tasmota PZEM | ~1 s → delay 2–3 s |
| Any numeric sensor | Set delay > reporting interval |

---

## Installation

### Via HACS (recommended)

1. In HACS → Integrations → ⋮ → Custom repositories
2. Add this repository URL, category: Integration
3. Install **WattHound**
4. Restart Home Assistant

### Manual

Copy `custom_components/watt_hound` into your HA config directory and restart.

---

## Configuration

Go to **Settings → Devices & Services → Add Integration → WattHound**.

The setup wizard has three steps:

**Step 1 – Power sensor**
Select the entity that provides your total house consumption in Watts.

**Step 2 – Timing**

| Parameter | Default | Description |
|---|---|---|
| Measure delay | 4 s | Wait time after switch event before reading the meter |
| Clean window | 6 s | No other switch events allowed in this time window |
| Min samples | 3 | Minimum clean measurements before showing a value |
| Max samples | 30 | Rolling window size |

**Step 3 – Tracking**
Choose to track lights, switches, or both. Exclude devices with their own power meters.

Settings can be changed later via the integration's **Configure** button.

---

## Entities

For each tracked device, one sensor is created:

- **State**: Estimated power in W (`unknown` until min_samples reached)
- **Attributes**:
  - `confidence` – 0.0 to 1.0, rises with more consistent measurements
  - `sample_count` – total clean samples collected
  - `on_delta_avg` – average measured delta on turn-on
  - `off_delta_avg` – average measured delta on turn-off
  - `dirty_count` – number of discarded dirty measurements
  - `last_clean_measurement` – timestamp of last good sample

---

## Energy Dashboard

The virtual sensors report `device_class: power` and `state_class: measurement`. To add them to the Energy Dashboard, wrap them in an integration (Riemann sum) sensor:

```yaml
sensor:
  - platform: integration
    name: "Wohnzimmer Decke Energy"
    source: sensor.wohnzimmer_decke_learned_power
    unit_prefix: k
    method: left
```

Then add the resulting `kWh` sensor under **Settings → Energy → Individual devices**.

---

## Tips

- **First few days**: Many measurements will be dirty. This is normal. Confidence rises as your devices get isolated switch events.
- **Dimmer devices**: Each brightness level is treated as a separate on-event. Average converges toward typical-use brightness over time.
- **Devices with own meters**: Exclude them in step 3. There's no benefit in learning what you already know.
- **Standby loads**: The delta measures the difference between whatever state the device was in before and after. If a TV draws 5 W in standby, the "on" delta will reflect the step from 5 W to active power.

---

## License

MIT
