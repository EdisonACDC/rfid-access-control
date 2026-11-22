"""Config flow for RFID Access Control."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_DEVICE_ID, CONF_MQTT_TOPIC, CONF_TAMPER_DELAY, DEFAULT_TAMPER_DELAY

_LOGGER = logging.getLogger(__name__)


class RFIDAccessControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RFID Access Control."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return RFIDAccessControlOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - ask for device ID and MQTT topic."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input.get(CONF_DEVICE_ID, "").strip()
            mqtt_topic = user_input.get(CONF_MQTT_TOPIC, "").strip()

            if not device_id:
                errors["base"] = "no_device_id"
            elif not mqtt_topic:
                errors["base"] = "no_mqtt_topic"
            elif "/" not in mqtt_topic:
                errors[CONF_MQTT_TOPIC] = "invalid_mqtt_topic"
            else:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"RFID Access Control - {device_id}",
                    data={
                        CONF_DEVICE_ID: device_id,
                        CONF_MQTT_TOPIC: mqtt_topic,
                    },
                )

        schema = vol.Schema({
            vol.Required(CONF_DEVICE_ID, default="tastierino_portoncino"): str,
            vol.Required(CONF_MQTT_TOPIC, default="zigbee2mqtt/tastierino_portoncino"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_data)


class RFIDAccessControlOptionsFlow(config_entries.OptionsFlow):
    """Handle options for RFID Access Control (MQTT topic and tamper delay)."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        current_topic = self.config_entry.options.get(
            CONF_MQTT_TOPIC,
            self.config_entry.data.get(CONF_MQTT_TOPIC, ""),
        )
        current_delay = self.config_entry.options.get(CONF_TAMPER_DELAY, DEFAULT_TAMPER_DELAY)

        if user_input is not None:
            mqtt_topic = user_input.get(CONF_MQTT_TOPIC, "").strip()
            delay = int(user_input.get(CONF_TAMPER_DELAY, DEFAULT_TAMPER_DELAY))
            if not mqtt_topic:
                errors[CONF_MQTT_TOPIC] = "no_mqtt_topic"
            elif "/" not in mqtt_topic:
                errors[CONF_MQTT_TOPIC] = "invalid_mqtt_topic"
            else:
                return self.async_create_entry(
                    title="", data={CONF_MQTT_TOPIC: mqtt_topic, CONF_TAMPER_DELAY: delay},
                )

        schema = vol.Schema({
            vol.Required(CONF_MQTT_TOPIC, default=current_topic): str,
            vol.Required(CONF_TAMPER_DELAY, default=current_delay): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=60),
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
