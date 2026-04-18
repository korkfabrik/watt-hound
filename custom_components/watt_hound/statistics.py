"""
Bayesian-inspired power estimator for a single device.

Strategy:
  - Maintain a rolling window of clean ON-delta and OFF-delta measurements.
  - Reject outliers using a ±2 sigma filter once enough samples exist.
  - Report the trimmed mean as the estimated power.
  - Confidence rises from 0 → 1 as the sample count approaches min_samples
    and variance falls below a threshold.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class DeviceStats:
    entity_id: str
    on_deltas: list[float] = field(default_factory=list)
    off_deltas: list[float] = field(default_factory=list)
    dirty_count: int = 0
    last_clean_ts: Optional[str] = None  # ISO string for serialisation
    max_samples: int = 30

    # ------------------------------------------------------------------
    # Core update
    # ------------------------------------------------------------------

    def add_measurement(self, delta_w: float, event_type: str, ts: datetime) -> None:
        """Add a clean measurement.  event_type is 'on' or 'off'."""
        target = self.on_deltas if event_type == "on" else self.off_deltas
        target.append(abs(delta_w))
        # Trim to rolling window
        if len(target) > self.max_samples:
            target.pop(0)
        self.last_clean_ts = ts.isoformat()

    def add_dirty(self) -> None:
        self.dirty_count += 1

    # ------------------------------------------------------------------
    # Derived statistics
    # ------------------------------------------------------------------

    @property
    def sample_count(self) -> int:
        return len(self.on_deltas) + len(self.off_deltas)

    def _trimmed_mean(self, values: list[float]) -> Optional[float]:
        """Median-absolute-deviation filter, then mean of survivors.

        Using the median as the centre point makes this robust against
        single large outliers (unlike mean ± 2σ which shifts with the outlier).
        Threshold: 3 × MAD (equivalent to ~2σ for normally distributed data).
        """
        if not values:
            return None
        if len(values) < 3:
            return sum(values) / len(values)
        med = statistics.median(values)
        mad = statistics.median([abs(v - med) for v in values])
        if mad == 0:
            return med
        filtered = [v for v in values if abs(v - med) <= 3 * mad]
        return statistics.mean(filtered) if filtered else med

    def _variance_confidence(self, values: list[float]) -> float:
        """0 → 1 confidence based on coefficient of variation."""
        if len(values) < 2:
            return 0.0
        mean = statistics.mean(values)
        if mean == 0:
            return 0.0
        cv = statistics.stdev(values) / mean   # coefficient of variation
        # cv=0 → perfect, cv≥1 → very noisy
        return max(0.0, 1.0 - min(cv, 1.0))

    def estimated_power(self, min_samples: int = 3) -> Optional[float]:
        """Best estimate of device power in Watts, or None if not ready."""
        on_est = self._trimmed_mean(self.on_deltas)
        off_est = self._trimmed_mean(self.off_deltas)

        # Need at least one side to have min_samples
        on_n = len(self.on_deltas)
        off_n = len(self.off_deltas)
        if on_n + off_n < min_samples:
            return None

        candidates = [v for v in [on_est, off_est] if v is not None]
        if not candidates:
            return None

        # Weighted blend: give more weight to the side with more samples
        if on_est is not None and off_est is not None:
            total = on_n + off_n
            blended = (on_est * on_n + off_est * off_n) / total
            return round(blended, 1)
        return round(candidates[0], 1)

    def confidence(self, min_samples: int = 3) -> float:
        """0.0 – 1.0 confidence score."""
        n = self.sample_count
        if n == 0:
            return 0.0
        # Part 1: sample count ramp (0 → 1 over min_samples … min_samples*3)
        count_conf = min(n / (min_samples * 3), 1.0)
        # Part 2: variance stability
        all_values = self.on_deltas + self.off_deltas
        var_conf = self._variance_confidence(all_values) if len(all_values) >= 2 else 0.0
        # Combined
        return round(0.4 * count_conf + 0.6 * var_conf, 3)

    # ------------------------------------------------------------------
    # Serialisation (for HA Storage)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "on_deltas": self.on_deltas,
            "off_deltas": self.off_deltas,
            "dirty_count": self.dirty_count,
            "last_clean_ts": self.last_clean_ts,
            "max_samples": self.max_samples,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceStats":
        obj = cls(entity_id=data["entity_id"])
        obj.on_deltas = data.get("on_deltas", [])
        obj.off_deltas = data.get("off_deltas", [])
        obj.dirty_count = data.get("dirty_count", 0)
        obj.last_clean_ts = data.get("last_clean_ts")
        obj.max_samples = data.get("max_samples", 30)
        return obj
