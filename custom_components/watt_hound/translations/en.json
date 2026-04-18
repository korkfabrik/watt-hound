{
  "config": {
    "step": {
      "user": {
        "title": "WattHound – Power Sensor",
        "description": "Select the power sensor that measures your total house consumption (e.g. Shelly 3EM, Tibber Pulse, SML reader). The sensor state must be numeric and in Watts.",
        "data": {
          "power_sensor": "Power sensor entity"
        }
      },
      "timing": {
        "title": "WattHound – Timing",
        "description": "Adjust delays to match your meter's reporting interval.\n\n**Measure delay**: How long to wait after a switch event before reading the power sensor. Set this higher than your meter's reporting interval (e.g. Shelly 3EM ≈ 2 s → use 4 s).\n\n**Clean window**: If any *other* device switches within this window, the measurement is marked dirty and discarded.\n\n**Min samples**: How many clean measurements are required before showing a value.\n\n**Max samples**: Rolling window size for the estimator.",
        "data": {
          "measure_delay": "Measure delay (seconds)",
          "clean_window": "Clean window (seconds)",
          "min_samples": "Minimum clean samples",
          "max_samples": "Maximum stored samples"
        }
      },
      "tracking": {
        "title": "WattHound – What to track",
        "description": "Choose which entity domains to learn power for. Exclude any entities you don't want tracked (e.g. devices with their own power meter).",
        "data": {
          "track_lights": "Track light entities",
          "track_switches": "Track switch entities",
          "excluded_entities": "Excluded entities"
        }
      }
    },
    "error": {
      "sensor_not_found": "Sensor entity not found in Home Assistant.",
      "sensor_unavailable": "Sensor is currently unavailable. Check your device.",
      "sensor_not_numeric": "Sensor value is not a number. Only numeric power sensors are supported.",
      "must_be_positive": "Value must be greater than zero.",
      "window_smaller_than_delay": "Clean window should be at least as large as the measure delay."
    },
    "abort": {
      "already_configured": "WattHound is already configured."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "WattHound – Settings",
        "data": {
          "measure_delay": "Measure delay (seconds)",
          "clean_window": "Clean window (seconds)",
          "min_samples": "Minimum clean samples",
          "max_samples": "Maximum stored samples",
          "track_lights": "Track light entities",
          "track_switches": "Track switch entities",
          "excluded_entities": "Excluded entities"
        }
      }
    }
  }
}
