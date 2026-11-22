"""Sensor platform for RFID Access Control."""
import logging
import time
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_USERS_DB, CONF_MQTT_TOPIC
from .models import installer_active

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RFID Access Control sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    device_id = data.get("coordinator", "rfid")
    db = data.get(DATA_USERS_DB)

    sensor = RFIDAccessControlUsersSensor(hass, entry, device_id, db)
    data["sensor"] = sensor
    async_add_entities([sensor])


class RFIDAccessControlUsersSensor(SensorEntity):
    """Sensor that exposes the users of one keypad and its status.

    I PIN (utenti, admin, operatore) non vengono mai esposti come attributi.
    """

    def __init__(self, hass, entry, device_id, db):
        """Initialize the sensor. Name and unique_id are the ones used since 1.2.4."""
        self._hass_obj = hass
        self._entry = entry
        self._device_id = device_id
        self._db = db
        self._attr_name = f"RFID Users {device_id}"
        self._attr_unique_id = f"rfid_access_control_{device_id}_users"
        self._attr_icon = "mdi:account-group"

    def _get_entry_data(self):
        """Get the integration data dict."""
        try:
            return self._hass_obj.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
        except Exception:
            return {}

    @property
    def native_value(self):
        """Return number of users."""
        return len(self._db.users)

    @property
    def extra_state_attributes(self):
        """Return user list (without PINs) and keypad status."""
        users_list = []
        for user in self._db.get_all_users():
            users_list.append({
                "user_id": user.user_id,
                "user_name": user.user_name,
                "enabled": user.enabled,
                "has_pin": bool(user.pin),
                "has_rfid": bool(user.rfid),
                "rfid": user.rfid,
                "created_at": user.created_at,
                "last_access": user.last_access,
                "access_count": user.access_count,
                "valid_from": user.valid_from,
                "valid_until": user.valid_until,
                "max_uses": user.max_uses,
                "uses": user.uses,
                "access_status": user.access_block_reason() or "active",
                "actions": [
                    {
                        "action_name": a.action_name,
                        "entity_id": a.entity_id,
                        "service": a.service,
                        "keypad_action": a.keypad_action,
                        "delay_before_seconds": a.delay_before_seconds,
                        "delay_after_seconds": a.delay_after_seconds,
                    }
                    for a in user.actions
                ],
            })

        data = self._get_entry_data()
        now = time.time()
        installer_until = data.get("installer_until", 0.0) or 0.0
        keypad_lockout = data.get("lockouts", {}).get("keypad")
        return {
            "users": users_list,
            "sos_actions": [
                {"action_name": a.action_name, "entity_id": a.entity_id, "service": a.service}
                for a in self._db.sos_actions
            ],
            "device_id": self._device_id,
            # Topic MQTT del tastierino: serve alla card per segnare i tastierini già aggiunti.
            "mqtt_topic": self._entry.options.get(CONF_MQTT_TOPIC, self._entry.data.get(CONF_MQTT_TOPIC, "")),
            "last_code": data.get("last_code", ""),
            "last_code_time": data.get("last_code_time", 0),
            "tamper_active": data.get("tamper_active", False),
            "keypad_locked_by_tamper": data.get("keypad_locked_by_tamper", False),
            "installer_active": installer_active(installer_until, now),
            "installer_until": (
                datetime.fromtimestamp(installer_until).astimezone().isoformat(timespec="seconds")
                if installer_active(installer_until, now) else None
            ),
            "setup_required": not self._db.pins_configured(),
            "admin_pin_set": bool(self._db.admin_pin),
            "operator_pin_set": bool(self._db.operator_pin),
            "locked_out": bool(keypad_lockout and keypad_lockout.locked(now)),
            "lockout_seconds_left": keypad_lockout.seconds_left(now) if keypad_lockout else 0,
        }

    def update_state(self):
        """Force state update after user changes."""
        self.async_write_ha_state()
