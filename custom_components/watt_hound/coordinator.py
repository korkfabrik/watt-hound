"""
WattHound coordinator.

Listens for state_changed events on light/switch entities, waits
`measure_delay` seconds, reads the power sensor delta, marks the
measurement clean or dirty based on the `clean_window`, and updates
the per-device DeviceStats.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store

from .const import (
    CONF_POWER_SENSOR,
    CONF_MEASURE_DELAY,
    CONF_CLEAN_WINDOW,
    CONF_MIN_SAMPLES,
    CONF_MAX_SAMPLES,
    CONF_TRACK_LIGHTS,
    CONF_TRACK_SWITCHES,
    CONF_EXCLUDED_ENTITIES,
    DEFAULT_MEASURE_DELAY,
    DEFAULT_CLEAN_WINDOW,
    DEFAULT_MIN_SAMPLES,
    DEFAULT_MAX_SAMPLES,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .statistics import DeviceStats

_LOGGER = logging.getLogger(__name__)

# Pending event: entity_id → (timestamp, power_before, event_type)
PendingEvent = tuple[datetime, float, str]


class PowerLearnerCoordinator:
    """Central coordinator for one config entry."""

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        self.hass = hass
        self._config = config
        self._stats: dict[str, DeviceStats] = {}
        self._pending: dict[str, PendingEvent] = {}
        self._recent_events: list[tuple[datetime, str]] = []  # (ts, entity_id)
        self._listeners: list = []
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._update_callbacks: list = []

    # ------------------------------------------------------------------
    # Properties from config
    # ------------------------------------------------------------------

    @property
    def power_sensor(self) -> str:
        return self._config[CONF_POWER_SENSOR]

    @property
    def measure_delay(self) -> float:
        return self._config.get(CONF_MEASURE_DELAY, DEFAULT_MEASURE_DELAY)

    @property
    def clean_window(self) -> float:
        return self._config.get(CONF_CLEAN_WINDOW, DEFAULT_CLEAN_WINDOW)

    @property
    def min_samples(self) -> int:
        return self._config.get(CONF_MIN_SAMPLES, DEFAULT_MIN_SAMPLES)

    @property
    def max_samples(self) -> int:
        return self._config.get(CONF_MAX_SAMPLES, DEFAULT_MAX_SAMPLES)

    @property
    def excluded_entities(self) -> list[str]:
        return self._config.get(CONF_EXCLUDED_ENTITIES, [])

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """Load stored data and start listening."""
        await self._async_load()

        domains: list[str] = []
        if self._config.get(CONF_TRACK_LIGHTS, True):
            domains.append("light")
        if self._config.get(CONF_TRACK_SWITCHES, True):
            domains.append("switch")

        if not domains:
            _LOGGER.warning("WattHound: no domains to track (lights and switches both disabled)")
            return

        @callback
        def _handle_state_change(event: Event) -> None:
            self.hass.async_create_task(self._async_handle_event(event))

        for domain in domains:
            self._listeners.append(
                async_track_state_change_event(
                    self.hass,
                    self.hass.states.async_entity_ids(domain),
                    _handle_state_change,
                )
            )

        _LOGGER.debug("WattHound coordinator started, tracking: %s", domains)

    async def async_unload(self) -> None:
        """Stop listening."""
        for unsub in self._listeners:
            unsub()
        self._listeners.clear()
        await self._async_save()

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    async def _async_handle_event(self, event: Event) -> None:
        entity_id: str = event.data.get("entity_id", "")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")

        if entity_id in self.excluded_entities:
            return
        if old_state is None or new_state is None:
            return

        old = old_state.state
        new = new_state.state

        # Determine if this is an ON or OFF transition
        if old == "off" and new == "on":
            event_type = "on"
        elif old == "on" and new == "off":
            event_type = "off"
        else:
            return  # unavailable / unknown transitions → ignore

        now = datetime.now()
        power_before = self._read_power()
        if power_before is None:
            _LOGGER.debug("Power sensor unavailable, skipping %s", entity_id)
            return

        # Register in recent-events list (for dirty detection)
        self._recent_events.append((now, entity_id))
        self._prune_recent_events(now)

        # Store as pending; wait measure_delay before sampling
        self._pending[entity_id] = (now, power_before, event_type)
        _LOGGER.debug(
            "Pending: %s %s  power_before=%.1fW  delay=%.1fs",
            entity_id, event_type, power_before, self.measure_delay,
        )

        await asyncio.sleep(self.measure_delay)
        await self._async_finalise(entity_id, now)

    async def _async_finalise(self, entity_id: str, trigger_ts: datetime) -> None:
        """Read power after delay and decide clean/dirty."""
        pending = self._pending.pop(entity_id, None)
        if pending is None:
            return  # was already handled or cancelled

        ts_orig, power_before, event_type = pending

        # Stale check: if a newer event already replaced this one, ignore
        if ts_orig != trigger_ts:
            return

        power_after = self._read_power()
        if power_after is None:
            return

        delta = power_after - power_before
        if event_type == "off":
            delta = -delta  # we want a positive "how much did it draw"

        # Dirty detection: were there other switch events in the clean window
        # around the original trigger_ts?
        is_dirty = self._is_dirty(entity_id, ts_orig)

        stats = self._get_or_create_stats(entity_id)

        if is_dirty:
            stats.add_dirty()
            _LOGGER.debug("%s: dirty event (overlapping switches), skipping", entity_id)
        else:
            # Basic sanity: delta should be positive and not absurdly large
            if delta < 0.5:
                _LOGGER.debug(
                    "%s: delta %.1fW too small to be meaningful, discarding", entity_id, delta
                )
            elif delta > 20000:
                _LOGGER.debug(
                    "%s: delta %.1fW unrealistically large, discarding", entity_id, delta
                )
            else:
                stats.add_measurement(delta, event_type, trigger_ts)
                _LOGGER.debug(
                    "%s: clean %s  delta=%.1fW  samples=%d  confidence=%.2f",
                    entity_id, event_type, delta,
                    stats.sample_count, stats.confidence(self.min_samples),
                )

        await self._async_save()
        self._notify_listeners()

    # ------------------------------------------------------------------
    # Dirty detection
    # ------------------------------------------------------------------

    def _is_dirty(self, entity_id: str, ts: datetime) -> bool:
        """True if any *other* entity switched within clean_window of ts."""
        window = timedelta(seconds=self.clean_window)
        for evt_ts, evt_entity in self._recent_events:
            if evt_entity == entity_id:
                continue
            if abs((evt_ts - ts).total_seconds()) <= self.clean_window:
                return True
        return False

    def _prune_recent_events(self, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self.clean_window * 2)
        self._recent_events = [
            (t, e) for t, e in self._recent_events if t > cutoff
        ]

    # ------------------------------------------------------------------
    # Power sensor reading
    # ------------------------------------------------------------------

    def _read_power(self) -> Optional[float]:
        state = self.hass.states.get(self.power_sensor)
        if state is None or state.state in ("unavailable", "unknown", ""):
            return None
        try:
            return float(state.state)
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Stats management
    # ------------------------------------------------------------------

    def _get_or_create_stats(self, entity_id: str) -> DeviceStats:
        if entity_id not in self._stats:
            self._stats[entity_id] = DeviceStats(
                entity_id=entity_id,
                max_samples=self.max_samples,
            )
        return self._stats[entity_id]

    def get_stats(self, entity_id: str) -> Optional[DeviceStats]:
        return self._stats.get(entity_id)

    def all_tracked_entities(self) -> list[str]:
        domains: list[str] = []
        if self._config.get(CONF_TRACK_LIGHTS, True):
            domains.append("light")
        if self._config.get(CONF_TRACK_SWITCHES, True):
            domains.append("switch")
        entities = []
        for domain in domains:
            entities.extend(self.hass.states.async_entity_ids(domain))
        return [e for e in entities if e not in self.excluded_entities]

    # ------------------------------------------------------------------
    # Update callbacks (for sensors to refresh)
    # ------------------------------------------------------------------

    def register_update_callback(self, cb) -> None:
        self._update_callbacks.append(cb)

    def unregister_update_callback(self, cb) -> None:
        self._update_callbacks.discard(cb) if hasattr(self._update_callbacks, "discard") else None
        try:
            self._update_callbacks.remove(cb)
        except ValueError:
            pass

    def _notify_listeners(self) -> None:
        for cb in list(self._update_callbacks):
            try:
                cb()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _async_load(self) -> None:
        data = await self._store.async_load()
        if data and "devices" in data:
            for item in data["devices"]:
                try:
                    stats = DeviceStats.from_dict(item)
                    stats.max_samples = self.max_samples
                    self._stats[stats.entity_id] = stats
                except Exception as exc:
                    _LOGGER.warning("Could not restore stats for %s: %s", item, exc)
        _LOGGER.debug("Loaded %d device stats from storage", len(self._stats))

    async def _async_save(self) -> None:
        data = {"devices": [s.to_dict() for s in self._stats.values()]}
        await self._store.async_save(data)
