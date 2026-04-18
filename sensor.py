"""
Config flow for WattHound.

Step 1 – sensor:   pick the main power sensor + optional label
Step 2 – timing:   measure_delay, clean_window, min_samples, max_samples
Step 3 – tracking: track lights, track switches, excluded entities
"""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

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
)


class PowerLearnerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict = {}

    # ------------------------------------------------------------------
    # Step 1: Power sensor selection
    # ------------------------------------------------------------------

    async def async_step_user(self, user_input=None):
        errors: dict = {}

        if user_input is not None:
            sensor_id = user_input[CONF_POWER_SENSOR]
            state = self.hass.states.get(sensor_id)
            if state is None:
                errors[CONF_POWER_SENSOR] = "sensor_not_found"
            elif state.state in ("unavailable", "unknown"):
                errors[CONF_POWER_SENSOR] = "sensor_unavailable"
            else:
                # Try to parse as float
                try:
                    float(state.state)
                except ValueError:
                    errors[CONF_POWER_SENSOR] = "sensor_not_numeric"

            if not errors:
                self._data.update(user_input)
                return await self.async_step_timing()

        schema = vol.Schema(
            {
                vol.Required(CONF_POWER_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "example": "sensor.shelly3em_channel_a_power"
            },
        )

    # ------------------------------------------------------------------
    # Step 2: Timing parameters
    # ------------------------------------------------------------------

    async def async_step_timing(self, user_input=None):
        errors: dict = {}

        if user_input is not None:
            delay = user_input[CONF_MEASURE_DELAY]
            window = user_input[CONF_CLEAN_WINDOW]

            if delay <= 0:
                errors[CONF_MEASURE_DELAY] = "must_be_positive"
            if window <= 0:
                errors[CONF_CLEAN_WINDOW] = "must_be_positive"
            if window < delay:
                errors[CONF_CLEAN_WINDOW] = "window_smaller_than_delay"

            if not errors:
                self._data.update(user_input)
                return await self.async_step_tracking()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MEASURE_DELAY, default=DEFAULT_MEASURE_DELAY
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=30, step=0.5, unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_CLEAN_WINDOW, default=DEFAULT_CLEAN_WINDOW
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=2, max=60, step=1, unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_MIN_SAMPLES, default=DEFAULT_MIN_SAMPLES
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=20, step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_MAX_SAMPLES, default=DEFAULT_MAX_SAMPLES
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=100, step=5,
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="timing",
            data_schema=schema,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Step 3: What to track
    # ------------------------------------------------------------------

    async def async_step_tracking(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title=f"WattHound ({self._data[CONF_POWER_SENSOR]})",
                data=self._data,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_TRACK_LIGHTS, default=True): bool,
                vol.Required(CONF_TRACK_SWITCHES, default=True): bool,
                vol.Optional(CONF_EXCLUDED_ENTITIES, default=[]): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["light", "switch"],
                        multiple=True,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="tracking",
            data_schema=schema,
        )

    # ------------------------------------------------------------------
    # Options flow (lets users adjust settings after setup)
    # ------------------------------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PowerLearnerOptionsFlow(config_entry)


class PowerLearnerOptionsFlow(config_entries.OptionsFlow):
    """Allow editing settings after initial setup."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.data

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MEASURE_DELAY,
                    default=current.get(CONF_MEASURE_DELAY, DEFAULT_MEASURE_DELAY),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=30, step=0.5, unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_CLEAN_WINDOW,
                    default=current.get(CONF_CLEAN_WINDOW, DEFAULT_CLEAN_WINDOW),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=2, max=60, step=1, unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_MIN_SAMPLES,
                    default=current.get(CONF_MIN_SAMPLES, DEFAULT_MIN_SAMPLES),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=20, step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_MAX_SAMPLES,
                    default=current.get(CONF_MAX_SAMPLES, DEFAULT_MAX_SAMPLES),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=100, step=5,
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_TRACK_LIGHTS,
                    default=current.get(CONF_TRACK_LIGHTS, True),
                ): bool,
                vol.Required(
                    CONF_TRACK_SWITCHES,
                    default=current.get(CONF_TRACK_SWITCHES, True),
                ): bool,
                vol.Optional(
                    CONF_EXCLUDED_ENTITIES,
                    default=current.get(CONF_EXCLUDED_ENTITIES, []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["light", "switch"],
                        multiple=True,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
