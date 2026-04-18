"""
WattHound – sensor platform.

Creates one sensor per tracked light/switch entity.
The sensor exposes:
  - state: estimated power in W (or None until enough samples)
  - attributes: confidence, sample count, on/off deltas, dirty count
"""
from __future__ import annotations

import logging
from typing import Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ATTR_CONFIDENCE,
    ATTR_SAMPLE_COUNT,
    ATTR_ON_DELTA_AVG,
    ATTR_OFF_DELTA_AVG,
    ATTR_DIRTY_COUNT,
    ATTR_LAST_CLEAN,
)
from .coordinator import PowerLearnerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PowerLearnerCoordinator = hass.data[DOMAIN][entry.entry_id]

    tracked = coordinator.all_tracked_entities()
    entities = [PowerLearnerSensor(coordinator, entity_id) for entity_id in tracked]
    async_add_entities(entities, update_before_add=True)
    _LOGGER.debug("WattHound: created %d sensor entities", len(entities))


class PowerLearnerSensor(SensorEntity):
    """Virtual power sensor for a single light or switch."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "W"
    _attr_icon = "mdi:lightning-bolt-circle"
    _attr_should_poll = False

    def __init__(self, coordinator: PowerLearnerCoordinator, tracked_entity_id: str) -> None:
        self._coordinator = coordinator
        self._tracked_entity_id = tracked_entity_id

        # Build a human-readable name from the entity_id
        # e.g. light.wohnzimmer_decke  →  "Wohnzimmer Decke (Learned Power)"
        domain, name_raw = tracked_entity_id.split(".", 1)
        friendly = name_raw.replace("_", " ").title()
        self._attr_name = f"{friendly} Learned Power"
        self._attr_unique_id = f"{DOMAIN}_{tracked_entity_id}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, tracked_entity_id)},
            name=self._attr_name,
            manufacturer="WattHound",
            model="Virtual Power Sensor",
        )

    async def async_added_to_hass(self) -> None:
        @callback
        def _on_update() -> None:
            self._handle_coordinator_update()

        self._coordinator.register_update_callback(_on_update)
        self._remove_cb = _on_update

    async def async_will_remove_from_hass(self) -> None:
        self._coordinator.unregister_update_callback(self._remove_cb)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> Optional[float]:
        stats = self._coordinator.get_stats(self._tracked_entity_id)
        if stats is None:
            return None
        return stats.estimated_power(self._coordinator.min_samples)

    @property
    def extra_state_attributes(self) -> dict:
        stats = self._coordinator.get_stats(self._tracked_entity_id)
        if stats is None:
            return {
                ATTR_CONFIDENCE: 0.0,
                ATTR_SAMPLE_COUNT: 0,
                ATTR_ON_DELTA_AVG: None,
                ATTR_OFF_DELTA_AVG: None,
                ATTR_DIRTY_COUNT: 0,
                ATTR_LAST_CLEAN: None,
                "tracked_entity": self._tracked_entity_id,
            }

        on_avg = stats._trimmed_mean(stats.on_deltas)
        off_avg = stats._trimmed_mean(stats.off_deltas)

        return {
            ATTR_CONFIDENCE: stats.confidence(self._coordinator.min_samples),
            ATTR_SAMPLE_COUNT: stats.sample_count,
            ATTR_ON_DELTA_AVG: round(on_avg, 1) if on_avg is not None else None,
            ATTR_OFF_DELTA_AVG: round(off_avg, 1) if off_avg is not None else None,
            ATTR_DIRTY_COUNT: stats.dirty_count,
            ATTR_LAST_CLEAN: stats.last_clean_ts,
            "tracked_entity": self._tracked_entity_id,
        }

    @property
    def available(self) -> bool:
        # Sensor is always "available" (shows None until enough data)
        power_state = self.hass.states.get(self._coordinator.power_sensor)
        return power_state is not None and power_state.state not in ("unavailable", "unknown")
