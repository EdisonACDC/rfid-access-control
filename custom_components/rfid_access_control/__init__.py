"""RFID Access Control integration for Home Assistant - v1.3.0."""
import asyncio
import copy
import json
import logging
import time
from pathlib import Path

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_MQTT_TOPIC,
    CONF_TAMPER_DELAY,
    DEFAULT_TAMPER_DELAY,
    VERSION,
    EVENT_TAMPER_LOCKED,
    SERVICE_SET_OPERATOR_PIN,
    SERVICE_CLEAR_TAMPER_LOCK,
    SERVICE_ADD_USER,
    SERVICE_REMOVE_USER,
    SERVICE_UPDATE_USER,
    SERVICE_ADD_ACTION,
    SERVICE_REMOVE_ACTION,
    SERVICE_VALIDATE_ACCESS,
    SERVICE_LIST_USERS,
    SERVICE_SET_ADMIN_PIN,
    SERVICE_VERIFY_ADMIN_PIN,
    SERVICE_VERIFY_OPERATOR_PIN,
    SERVICE_TEST_ACCESS_CODE,
    SERVICE_SET_INSTALLER_MODE,
    SERVICE_GET_USER_PIN,
    SERVICE_ADD_SOS_ACTION,
    SERVICE_REMOVE_SOS_ACTION,
    SERVICE_COPY_USER,
    SERVICE_DISCOVER_KEYPADS,
    ZIGBEE_DEVICES_TOPIC,
    DISCOVERY_TIMEOUT_SECONDS,
    ATTR_USER_ID,
    ATTR_USER_NAME,
    ATTR_USER_PIN,
    ATTR_USER_RFID,
    ATTR_ACTION_ENTITY,
    ATTR_ACTION_SERVICE,
    ATTR_ACTION_DATA,
    EVENT_ACCESS_GRANTED,
    EVENT_ACCESS_DENIED,
    EVENT_USER_ADDED,
    EVENT_USER_REMOVED,
    EVENT_EMERGENCY,
    KEYPAD_ACTION_EMERGENCY,
    DATA_COORDINATOR,
    DATA_USERS_DB,
    INSTALLER_MODE_MAX_MINUTES,
    DEBOUNCE_SECONDS,
)
from .models import (
    AccessUser,
    AccessAction,
    AccessDatabase,
    PinLockout,
    check_keypad_action,
    check_pin_format,
    check_rfid_format,
    installer_active,
    parse_access_window,
    verify_pin,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]
ATTR_DEVICE_ID = "device_id"

# Card Lovelace: servita dall'integrazione e registrata come risorsa con la versione
CARD_FILE = "rfid-access-control-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILE}"
OLD_CARD_URL = "/local/rfid-access-control-card.js"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({})
}, extra=vol.ALLOW_EXTRA)

# Servizi che rispondono con un valore (verifiche PIN, test codice).
RESPONSE_SERVICES = {
    SERVICE_VERIFY_ADMIN_PIN,
    SERVICE_VERIFY_OPERATOR_PIN,
    SERVICE_TEST_ACCESS_CODE,
    SERVICE_GET_USER_PIN,
    SERVICE_DISCOVER_KEYPADS,
}


def _runtimes(hass: HomeAssistant) -> dict:
    """Runtime data of every configured keypad, keyed by config entry id."""
    return {key: value for key, value in hass.data.get(DOMAIN, {}).items() if isinstance(value, dict) and "db" in value}


def _resolve(hass: HomeAssistant, call: ServiceCall) -> dict:
    """Pick the keypad a service call is about.

    Con un solo tastierino basta il servizio; con più tastierini serve device_id.
    """
    runtimes = _runtimes(hass)
    device_id = str(call.data.get(ATTR_DEVICE_ID, "")).strip()
    if device_id:
        for runtime in runtimes.values():
            if runtime["device_id"] == device_id:
                return runtime
        raise HomeAssistantError(f"Tastierino non configurato: {device_id}")
    if len(runtimes) == 1:
        return next(iter(runtimes.values()))
    if not runtimes:
        raise HomeAssistantError("Nessun tastierino configurato")
    raise HomeAssistantError("Ci sono più tastierini: indica device_id")


def _update_sensor(rt: dict):
    """Refresh the sensor entity after data changes."""
    sensor = rt.get("sensor")
    if sensor:
        try:
            sensor.update_state()
        except Exception as error:
            _LOGGER.debug("Sensor update skipped: %s", error)


async def _save(hass: HomeAssistant, rt: dict):
    await _save_database(hass, rt["store_path"], rt["db"])


def _fire_denied(hass: HomeAssistant, rt: dict, reason: str, **extra):
    hass.bus.async_fire(EVENT_ACCESS_DENIED, {"device_id": rt["device_id"], "reason": reason, **extra})


def _looks_like_rfid(code: str) -> bool:
    return code.startswith("+") or any(c in code.upper() for c in "ABCDEF")


def _find_user(rt: dict, code: str) -> AccessUser | None:
    db = rt["db"]
    if _looks_like_rfid(code):
        return db.find_user_by_credentials(rfid=code) or db.find_user_by_credentials(pin=code)
    return db.find_user_by_credentials(pin=code) or db.find_user_by_credentials(rfid=code)


def _code_hint(code: str) -> str:
    """Last value shown in the sensor: never the full PIN."""
    return code[-4:] if _looks_like_rfid(code) else "***"


async def _execute_user_actions(hass: HomeAssistant, rt: dict, user: AccessUser, keypad_action: str = ""):
    """Record the access and run the actions of the user."""
    user.record_access()
    await _save(hass, rt)
    _update_sensor(rt)

    hass.bus.async_fire(EVENT_ACCESS_GRANTED, {
        ATTR_USER_ID: user.user_id,
        ATTR_USER_NAME: user.user_name,
        "keypad_action": keypad_action,
        ATTR_DEVICE_ID: rt["device_id"],
    })

    executed = await _run_actions(hass, user.actions, keypad_action)
    _LOGGER.info(
        "Access GRANTED: %s | keypad=%s | actions executed=%s/%s",
        user.user_name, keypad_action, executed, len(user.actions),
    )


async def _handle_emergency(hass: HomeAssistant, rt: dict, code: str):
    """Tasto SOS: sempre attivo, anche con tamper o blocco. Il codice serve solo a dire chi è."""
    user = _find_user(rt, code) if code else None
    hass.bus.async_fire(EVENT_EMERGENCY, {
        ATTR_DEVICE_ID: rt["device_id"],
        ATTR_USER_ID: user.user_id if user else "",
        ATTR_USER_NAME: user.user_name if user else "",
    })
    _LOGGER.warning("SOS su '%s' (utente: %s)", rt["device_id"], user.user_name if user else "non riconosciuto")
    executed = await _run_actions(hass, rt["db"].sos_actions, "")
    _LOGGER.info("SOS su '%s': azioni eseguite %s/%s", rt["device_id"], executed, len(rt["db"].sos_actions))


async def _run_actions(hass: HomeAssistant, actions: list, keypad_action: str = "") -> int:
    """Run the given actions, keeping only those for this keypad button. Returns how many ran."""
    executed = 0
    for action in actions:
        if keypad_action and not action.matches_keypad_action(keypad_action):
            continue
        try:
            if action.delay_before_seconds > 0:
                await asyncio.sleep(action.delay_before_seconds)

            domain_svc = action.service.split(".")
            if len(domain_svc) == 2:
                service_data = dict(action.service_data)
                if action.entity_id:
                    service_data["entity_id"] = action.entity_id
                await hass.services.async_call(domain_svc[0], domain_svc[1], service_data)
                executed += 1
            else:
                _LOGGER.error("Formato servizio non valido: %s", action.service)

            if action.delay_after_seconds > 0:
                await asyncio.sleep(action.delay_after_seconds)
        except Exception as error:
            _LOGGER.error("Errore esecuzione azione '%s': %s", action.action_name, error)
    return executed


async def _mqtt_validate(hass: HomeAssistant, rt: dict, code: str, action_type: str):
    """Handle a code typed on the keypad."""
    lockout: PinLockout = rt["lockouts"]["keypad"]
    now = time.time()

    # Antirimbalzo: lo stesso codice dallo stesso tastierino entro pochi secondi
    # è un doppio invio. Viene ignorato: niente azioni e niente conteggio come errore.
    last_code, last_time = rt.get("last_accepted", ("", 0.0))
    if code == last_code and now - last_time < DEBOUNCE_SECONDS:
        _LOGGER.debug("Codice ripetuto su '%s' ignorato (antirimbalzo)", rt["device_id"])
        return
    rt["last_accepted"] = (code, now)
    # Solo le tessere RFID finiscono nel sensore (serve al pulsante "Leggi RFID"): mai i PIN.
    rt["last_code"] = code if _looks_like_rfid(code) else ""
    rt["last_code_time"] = now
    _update_sensor(rt)
    # Stesso evento della 1.2.4, ma con il codice solo per le tessere RFID.
    hass.bus.async_fire("rfid_code_received", {
        "code": rt["last_code"],
        "code_hint": _code_hint(code),
        "action": action_type,
        "device_id": rt["device_id"],
    })

    if lockout.locked(now):
        _fire_denied(hass, rt, "locked_out", seconds_left=lockout.seconds_left(now))
        return

    if rt["keypad_locked_by_tamper"] and not installer_active(rt["installer_until"], now):
        # Con tamper aperto solo il PIN operatore + Arma Tutto riabilita il tastierino.
        if action_type == "arm_all_zones":
            result = verify_pin(lockout, rt["db"].operator_pin, code, now)
            if result["valid"]:
                rt["keypad_locked_by_tamper"] = False
                _update_sensor(rt)
                hass.bus.async_fire("rfid_tamper_unlocked", {"device_id": rt["device_id"]})
                _LOGGER.info("Tamper lock rimosso dal PIN operatore su '%s'", rt["device_id"])
                return
            if result["locked_out"]:
                _fire_denied(hass, rt, "locked_out", seconds_left=result["seconds_left"])
                return
        _fire_denied(hass, rt, "tamper_lock", keypad_action=action_type)
        return

    user = _find_user(rt, code)
    if user:
        lockout.reset()
        await _execute_user_actions(hass, rt, user, keypad_action=action_type)
    else:
        lockout.record_failure(now)
        _fire_denied(hass, rt, "unknown_code", code_type="rfid" if _looks_like_rfid(code) else "pin",
                     code_hint=_code_hint(code), keypad_action=action_type)
        if lockout.locked(now):
            _fire_denied(hass, rt, "locked_out", seconds_left=lockout.seconds_left(now))


def _verified(rt: dict, lockout_name: str, expected: str, given: str) -> dict:
    """Check a PIN with its lockout. Used by the services and by the card."""
    return verify_pin(rt["lockouts"][lockout_name], expected, given)


def _require_valid(result: dict, label: str):
    """Turn a failed PIN check into a HomeAssistantError with a clear message."""
    if result.get("not_set"):
        raise HomeAssistantError(f"Il {label} non è ancora impostato: impostalo prima")
    if result.get("locked_out"):
        raise HomeAssistantError(
            f"Troppi tentativi errati. Riprova tra {result.get('seconds_left', 0)} secondi"
        )
    if not result.get("valid"):
        raise HomeAssistantError(f"{label.capitalize()} non corretto")


async def _set_system_pin(hass: HomeAssistant, rt: dict, call: ServiceCall, which: str):
    """Change the admin or operator PIN. A PIN already set needs the current one."""
    db: AccessDatabase = rt["db"]
    new_pin = str(call.data.get("new_pin", "")).strip()
    error = check_pin_format(new_pin)
    if error:
        raise HomeAssistantError(error)
    other = db.operator_pin if which == "admin" else db.admin_pin
    if new_pin == other:
        raise HomeAssistantError("Il PIN admin e il PIN operatore devono essere diversi")

    current = db.admin_pin if which == "admin" else db.operator_pin
    if current:
        given = str(call.data.get("current_pin", "")).strip()
        _require_valid(_verified(rt, which, current, given), f"PIN {which}")

    if which == "admin":
        db.admin_pin = new_pin
    else:
        db.operator_pin = new_pin
    await _save(hass, rt)
    _update_sensor(rt)
    _LOGGER.info("PIN %s aggiornato per '%s'", which, rt["device_id"])


async def _set_installer_mode(hass: HomeAssistant, rt: dict, call: ServiceCall):
    """Start or stop installer mode (needs the operator PIN)."""
    db: AccessDatabase = rt["db"]
    _require_valid(_verified(rt, "operator", db.operator_pin, str(call.data.get("pin", ""))), "PIN operatore")
    try:
        minutes = int(call.data.get("minutes", 0))
    except (TypeError, ValueError) as error:
        raise HomeAssistantError("I minuti devono essere un numero") from error
    if minutes < 0 or minutes > INSTALLER_MODE_MAX_MINUTES:
        raise HomeAssistantError(f"I minuti devono essere tra 0 e {INSTALLER_MODE_MAX_MINUTES}")

    rt["installer_until"] = time.time() + minutes * 60 if minutes else 0.0
    if rt.get("installer_timer"):
        rt["installer_timer"]()
        rt["installer_timer"] = None
    if minutes:
        rt["installer_timer"] = async_call_later(hass, minutes * 60, lambda _now: _update_sensor(rt))
    hass.bus.async_fire("rfid_installer_mode", {
        "device_id": rt["device_id"],
        "active": bool(minutes),
        "minutes": minutes,
    })
    _update_sensor(rt)
    _LOGGER.info("Modalità installatore su '%s': %s", rt["device_id"], f"{minutes} min" if minutes else "spenta")


def _tamper_delay(rt: dict) -> int:
    """Secondi che il coperchio può restare aperto prima del blocco (opzione del tastierino)."""
    try:
        return max(0, int(rt["entry"].options.get(CONF_TAMPER_DELAY, DEFAULT_TAMPER_DELAY)))
    except (TypeError, ValueError):
        return DEFAULT_TAMPER_DELAY


def _tamper_check(hass: HomeAssistant, rt: dict):
    """Ritardo scaduto: se il coperchio è ancora aperto, il tastierino si blocca."""
    rt["tamper_timer"] = None
    if not rt.get("tamper_active") or rt.get("keypad_locked_by_tamper"):
        return
    if time.time() - rt.get("tamper_since", 0.0) < _tamper_delay(rt):
        return
    rt["keypad_locked_by_tamper"] = True
    _update_sensor(rt)
    hass.bus.async_fire(EVENT_TAMPER_LOCKED, {"device_id": rt["device_id"]})
    _LOGGER.warning("TAMPER su '%s': coperchio aperto oltre il ritardo - tastierino bloccato", rt["device_id"])


async def _options_changed(hass: HomeAssistant, entry: ConfigEntry):
    """Topic o ritardo cambiati nelle opzioni: ricarica il tastierino."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up RFID Access Control component and its services once."""
    hass.data.setdefault(DOMAIN, {})
    _register_services(hass)
    # Un errore nella card non deve impedire all'integrazione di partire.
    try:
        await _register_card(hass)
    except Exception as error:
        _LOGGER.warning(
            "Card non registrata automaticamente (%s). Aggiungi a mano la risorsa %s?v=%s "
            "in Impostazioni → Dashboard → Risorse, tipo Modulo JavaScript.",
            error, CARD_URL, VERSION,
        )
    return True


async def _register_card(hass: HomeAssistant):
    """Serve la card e la registra come risorsa Lovelace: dopo un aggiornamento non serve copiare nulla."""
    http = getattr(hass, "http", None)
    if http is None:
        return
    card_path = str(Path(__file__).parent / "www" / CARD_FILE)
    try:
        from homeassistant.components.http import StaticPathConfig
    except ImportError:  # Home Assistant più vecchio
        http.register_static_path(CARD_URL, card_path, False)
    else:
        await http.async_register_static_paths([StaticPathConfig(CARD_URL, card_path, False)])

    resources = getattr(hass.data.get("lovelace"), "resources", None)
    if resources is None:
        _LOGGER.warning(
            "Lovelace non in modalità dashboard: aggiungi a mano la risorsa %s?v=%s", CARD_URL, VERSION,
        )
        return
    if not resources.loaded:
        await resources.async_load()
    wanted = f"{CARD_URL}?v={VERSION}"
    present = False
    for item in list(resources.async_items()):
        url = str(item.get("url", ""))
        base = url.split("?", 1)[0]
        if base == OLD_CARD_URL:
            # La vecchia copia manuale in /config/www: la sostituisce la risorsa dell'integrazione.
            await resources.async_delete_item(item["id"])
        elif base == CARD_URL:
            present = True
            if url != wanted:
                await resources.async_update_item(item["id"], {"res_type": "module", "url": wanted})
    if not present:
        await resources.async_create_item({"res_type": "module", "url": wanted})
    _LOGGER.info("Card registrata come risorsa Lovelace: %s", wanted)


def _register_services(hass: HomeAssistant):
    """Register each service once; every call is routed to its keypad."""
    handlers = {
        SERVICE_ADD_USER: _svc_add_user,
        SERVICE_REMOVE_USER: _svc_remove_user,
        SERVICE_UPDATE_USER: _svc_update_user,
        SERVICE_ADD_ACTION: _svc_add_action,
        SERVICE_REMOVE_ACTION: _svc_remove_action,
        SERVICE_VALIDATE_ACCESS: _svc_validate_access,
        SERVICE_LIST_USERS: _svc_list_users,
        SERVICE_SET_ADMIN_PIN: _svc_set_admin_pin,
        SERVICE_SET_OPERATOR_PIN: _svc_set_operator_pin,
        SERVICE_CLEAR_TAMPER_LOCK: _svc_clear_tamper_lock,
        SERVICE_VERIFY_ADMIN_PIN: _svc_verify_admin_pin,
        SERVICE_VERIFY_OPERATOR_PIN: _svc_verify_operator_pin,
        SERVICE_TEST_ACCESS_CODE: _svc_test_access_code,
        SERVICE_SET_INSTALLER_MODE: _svc_set_installer_mode,
        SERVICE_GET_USER_PIN: _svc_get_user_pin,
        SERVICE_ADD_SOS_ACTION: _svc_add_sos_action,
        SERVICE_REMOVE_SOS_ACTION: _svc_remove_sos_action,
        SERVICE_COPY_USER: _svc_copy_user,
    }
    # Trova i tastierini Zigbee: non appartiene a nessun tastierino, quindi niente device_id.
    if not hass.services.has_service(DOMAIN, SERVICE_DISCOVER_KEYPADS):
        async def _discover(call: ServiceCall):
            return await _discover_keypads(hass)

        hass.services.async_register(
            DOMAIN, SERVICE_DISCOVER_KEYPADS, _discover, supports_response=SupportsResponse.ONLY,
        )
    for service_name, handler in handlers.items():
        if hass.services.has_service(DOMAIN, service_name):
            continue

        def _make(handler):
            async def _dispatch(call: ServiceCall):
                rt = _resolve(hass, call)
                return await handler(hass, rt, call)
            return _dispatch

        hass.services.async_register(
            DOMAIN,
            service_name,
            _make(handler),
            supports_response=SupportsResponse.ONLY if service_name in RESPONSE_SERVICES else SupportsResponse.NONE,
        )


async def _svc_add_user(hass, rt, call):
    db: AccessDatabase = rt["db"]
    pin = str(call.data.get(ATTR_USER_PIN, "")).strip()
    rfid = str(call.data.get(ATTR_USER_RFID, "")).strip().upper()
    if not pin and not rfid:
        raise HomeAssistantError("Inserisci almeno un PIN o un codice RFID")
    error = (check_pin_format(pin) if pin else "") or check_rfid_format(rfid)
    if error:
        raise HomeAssistantError(error)
    error = db.check_credentials(pin=pin, rfid=rfid)
    if error:
        raise HomeAssistantError(error)
    try:
        window = parse_access_window(
            call.data.get("valid_from", ""), call.data.get("valid_until", ""), call.data.get("max_uses", 0),
        )
    except ValueError as error:
        raise HomeAssistantError(str(error)) from error

    user = AccessUser(
        user_id=str(call.data.get(ATTR_USER_ID, "")),
        user_name=str(call.data.get(ATTR_USER_NAME, "")),
        pin=pin,
        rfid=rfid,
        **window,
    )
    if not user.user_id or not user.user_name:
        raise HomeAssistantError("Nome e identificativo utente sono obbligatori")
    if not db.add_user(user):
        raise HomeAssistantError(f"Utente già esistente: {user.user_id}")
    await _save(hass, rt)
    _update_sensor(rt)
    hass.bus.async_fire(EVENT_USER_ADDED, {ATTR_USER_ID: user.user_id, ATTR_USER_NAME: user.user_name,
                                           ATTR_DEVICE_ID: rt["device_id"]})


async def _svc_remove_user(hass, rt, call):
    user_id = call.data.get(ATTR_USER_ID)
    if not rt["db"].remove_user(user_id):
        raise HomeAssistantError(f"Utente non trovato: {user_id}")
    await _save(hass, rt)
    _update_sensor(rt)
    hass.bus.async_fire(EVENT_USER_REMOVED, {ATTR_USER_ID: user_id, ATTR_DEVICE_ID: rt["device_id"]})


async def _svc_update_user(hass, rt, call):
    db: AccessDatabase = rt["db"]
    user_id = call.data.get(ATTR_USER_ID)
    user = db.get_user(user_id)
    if not user:
        raise HomeAssistantError(f"Utente non trovato: {user_id}")
    pin = str(call.data.get(ATTR_USER_PIN, "") or "").strip()
    rfid = str(call.data.get(ATTR_USER_RFID, "") or "").strip().upper()
    if pin:
        error = check_pin_format(pin) or db.check_credentials(pin=pin, exclude_user_id=user_id)
        if error:
            raise HomeAssistantError(error)
    if rfid:
        error = check_rfid_format(rfid) or db.check_credentials(rfid=rfid, exclude_user_id=user_id)
        if error:
            raise HomeAssistantError(error)
    changes = {"user_name": call.data.get(ATTR_USER_NAME, ""), "pin": pin, "rfid": rfid}
    if "enabled" in call.data:
        changes["enabled"] = call.data["enabled"]
    if any(key in call.data for key in ("valid_from", "valid_until", "max_uses")):
        try:
            changes.update(parse_access_window(
                call.data.get("valid_from", ""), call.data.get("valid_until", ""), call.data.get("max_uses", 0),
            ))
        except ValueError as error:
            raise HomeAssistantError(str(error)) from error
    db.update_user(user_id, changes)
    await _save(hass, rt)
    _update_sensor(rt)


async def _svc_add_action(hass, rt, call):
    user_id = call.data.get(ATTR_USER_ID)
    user = rt["db"].get_user(user_id)
    if not user:
        raise HomeAssistantError(f"Utente non trovato: {user_id}")
    keypad_action = str(call.data.get("keypad_action", "") or "any")
    error = check_keypad_action(keypad_action)
    if error:
        raise HomeAssistantError(error)
    user.actions.append(AccessAction(
        entity_id=call.data.get(ATTR_ACTION_ENTITY, ""),
        service=call.data.get(ATTR_ACTION_SERVICE, ""),
        service_data=call.data.get(ATTR_ACTION_DATA, {}),
        action_name=call.data.get("action_name", ""),
        keypad_action=keypad_action,
        delay_before_seconds=int(call.data.get("delay_before_seconds", 0)),
        delay_after_seconds=int(call.data.get("delay_after_seconds", 0)),
    ))
    await _save(hass, rt)
    _update_sensor(rt)


async def _svc_remove_action(hass, rt, call):
    user_id = call.data.get(ATTR_USER_ID)
    action_name = call.data.get("action_name", "")
    user = rt["db"].get_user(user_id)
    if not user:
        raise HomeAssistantError(f"Utente non trovato: {user_id}")
    before = len(user.actions)
    user.actions = [a for a in user.actions if a.action_name != action_name]
    if len(user.actions) == before:
        raise HomeAssistantError(f"Azione non trovata: {action_name}")
    await _save(hass, rt)
    _update_sensor(rt)


async def _svc_validate_access(hass, rt, call):
    code = str(call.data.get(ATTR_USER_PIN, "") or call.data.get(ATTR_USER_RFID, "")).strip()
    if not code:
        raise HomeAssistantError("Inserisci un PIN o un codice RFID")
    await _mqtt_validate(hass, rt, code, "")


async def _svc_list_users(hass, rt, call):
    rt["last_users"] = [u.user_name for u in rt["db"].get_all_users()]


async def _svc_set_admin_pin(hass, rt, call):
    await _set_system_pin(hass, rt, call, "admin")


async def _svc_set_operator_pin(hass, rt, call):
    await _set_system_pin(hass, rt, call, "operator")


async def _svc_clear_tamper_lock(hass, rt, call):
    db: AccessDatabase = rt["db"]
    _require_valid(_verified(rt, "operator", db.operator_pin, str(call.data.get("pin", ""))), "PIN operatore")
    rt["keypad_locked_by_tamper"] = False
    _update_sensor(rt)
    hass.bus.async_fire("rfid_tamper_unlocked", {"device_id": rt["device_id"], "source": "operator_card"})
    _LOGGER.info("Tamper lock rimosso da menu operatore su '%s'", rt["device_id"])


async def _svc_verify_admin_pin(hass, rt, call):
    return _verification_response(_verified(rt, "admin", rt["db"].admin_pin, str(call.data.get("pin", ""))))


async def _svc_verify_operator_pin(hass, rt, call):
    return _verification_response(_verified(rt, "operator", rt["db"].operator_pin, str(call.data.get("pin", ""))))


def _verification_response(result: dict) -> dict:
    return {
        "valid": bool(result.get("valid")),
        "locked_out": bool(result.get("locked_out")),
        "not_set": bool(result.get("not_set")),
        "seconds_left": int(result.get("seconds_left", 0)),
    }


async def _svc_test_access_code(hass, rt, call):
    """Operator menu: say which user a code belongs to, without running actions."""
    db: AccessDatabase = rt["db"]
    _require_valid(_verified(rt, "operator", db.operator_pin, str(call.data.get("operator_pin", ""))), "PIN operatore")
    code = str(call.data.get("code", "")).strip()
    user = _find_user(rt, code) if code else None
    if not user:
        return {"found": False, "user_name": "", "block_reason": ""}
    return {"found": True, "user_name": user.user_name, "block_reason": user.access_block_reason()}


async def _svc_set_installer_mode(hass, rt, call):
    await _set_installer_mode(hass, rt, call)


async def _svc_get_user_pin(hass, rt, call):
    """Card: show a user's PIN. Needs the admin PIN and counts wrong tries like the other checks."""
    db: AccessDatabase = rt["db"]
    _require_valid(_verified(rt, "admin", db.admin_pin, str(call.data.get("admin_pin", ""))), "PIN admin")
    user_id = call.data.get(ATTR_USER_ID)
    user = db.get_user(user_id)
    if not user:
        raise HomeAssistantError(f"Utente non trovato: {user_id}")
    return {"user_id": user_id, "pin": user.pin}


async def _svc_add_sos_action(hass, rt, call):
    """Global SOS action: runs on the emergency key for everybody, not for one user."""
    db: AccessDatabase = rt["db"]
    action_name = str(call.data.get("action_name", "") or "").strip()
    if not action_name:
        raise HomeAssistantError("Dai un nome all'azione SOS")
    if any(a.action_name == action_name for a in db.sos_actions):
        raise HomeAssistantError(f"Esiste già un'azione SOS con questo nome: {action_name}")
    db.sos_actions.append(AccessAction(
        entity_id=call.data.get(ATTR_ACTION_ENTITY, ""),
        service=call.data.get(ATTR_ACTION_SERVICE, ""),
        service_data=call.data.get(ATTR_ACTION_DATA, {}),
        action_name=action_name,
    ))
    await _save(hass, rt)
    _update_sensor(rt)


async def _svc_remove_sos_action(hass, rt, call):
    db: AccessDatabase = rt["db"]
    action_name = call.data.get("action_name", "")
    before = len(db.sos_actions)
    db.sos_actions = [a for a in db.sos_actions if a.action_name != action_name]
    if len(db.sos_actions) == before:
        raise HomeAssistantError(f"Azione SOS non trovata: {action_name}")
    await _save(hass, rt)
    _update_sensor(rt)


async def _svc_copy_user(hass, rt, call):
    """Copia un utente (PIN, tessera, azioni) su un altro tastierino.

    Si chiede il PIN admin del tastierino di destinazione: il PIN dell'utente non torna mai
    alla card. Le azioni vengono copiate così come sono: le entità possono non esistere lì.
    """
    user_id = call.data.get(ATTR_USER_ID)
    user = rt["db"].get_user(user_id)
    if not user:
        raise HomeAssistantError(f"Utente non trovato: {user_id}")
    target_id = str(call.data.get("target_device_id", "") or "").strip()
    if not target_id:
        raise HomeAssistantError("Indica il tastierino di destinazione")
    if target_id == rt["device_id"]:
        raise HomeAssistantError("Il tastierino di destinazione è quello da cui copi")
    target = next((r for r in _runtimes(hass).values() if r["device_id"] == target_id), None)
    if target is None:
        raise HomeAssistantError(f"Tastierino non configurato: {target_id}")

    target_db: AccessDatabase = target["db"]
    _require_valid(
        _verified(target, "admin", target_db.admin_pin, str(call.data.get("admin_pin", ""))),
        f"PIN admin di {target_id}",
    )
    if target_db.get_user(user_id):
        raise HomeAssistantError(f"Su {target_id} esiste già un utente con questo identificativo")
    error = target_db.check_credentials(pin=user.pin, rfid=user.rfid)
    if error:
        raise HomeAssistantError(f"Su {target_id}: {error}")

    target_db.add_user(AccessUser(
        user_id=user.user_id,
        user_name=user.user_name,
        pin=user.pin,
        rfid=user.rfid,
        actions=[copy.deepcopy(a) for a in user.actions],
        enabled=user.enabled,
        valid_from=user.valid_from,
        valid_until=user.valid_until,
        max_uses=user.max_uses,
    ))
    await _save(hass, target)
    _update_sensor(target)
    hass.bus.async_fire(EVENT_USER_ADDED, {
        ATTR_USER_ID: user.user_id, ATTR_USER_NAME: user.user_name, ATTR_DEVICE_ID: target_id,
    })
    _LOGGER.info("Utente '%s' copiato da '%s' a '%s'", user_id, rt["device_id"], target_id)


def keypads_from_zigbee(items) -> list:
    """Keep the Zigbee devices that are keypads (KEPZB-110 or described as keypad)."""
    keypads = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or item.get("type") == "Coordinator":
            continue
        name = str(item.get("friendly_name") or "").strip()
        definition = item.get("definition") or {}
        model = str(definition.get("model") or "")
        description = str(definition.get("description") or "")
        if not name:
            continue
        if "KEPZB" not in model.upper() and "KEYPAD" not in description.upper() and "TASTIER" not in description.upper():
            continue
        keypads.append({
            "friendly_name": name,
            "model": model,
            "topic": f"zigbee2mqtt/{name}",
        })
    return keypads


async def _discover_keypads(hass: HomeAssistant) -> dict:
    """Read the Zigbee2MQTT device list (retained) and return the keypads found."""
    found: dict = {}
    got_list = asyncio.Event()

    @callback
    def _on_devices(msg):
        try:
            payload = json.loads(msg.payload)
        except (TypeError, ValueError):
            return
        if isinstance(payload, list):
            found["items"] = payload
            got_list.set()

    try:
        unsubscribe = await mqtt.async_subscribe(hass, ZIGBEE_DEVICES_TOPIC, _on_devices, qos=0)
    except Exception as error:
        raise HomeAssistantError(f"MQTT non disponibile: {error}") from error
    try:
        await asyncio.wait_for(got_list.wait(), timeout=DISCOVERY_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        _LOGGER.warning("Nessun elenco da %s: Zigbee2MQTT è acceso?", ZIGBEE_DEVICES_TOPIC)
    finally:
        unsubscribe()
    return {"devices": keypads_from_zigbee(found.get("items", []))}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up RFID Access Control from a config entry."""
    try:
        device_id = entry.data.get(CONF_DEVICE_ID)
        mqtt_topic = entry.options.get(CONF_MQTT_TOPIC) or entry.data.get(CONF_MQTT_TOPIC, "")
        _LOGGER.info("Setting up RFID Access Control v1.3.0 for device: %s", device_id)

        db = AccessDatabase()
        store_path = Path(hass.config.config_dir) / DOMAIN / f"{device_id}.json"
        try:
            if await hass.async_add_executor_job(store_path.exists):
                content = await hass.async_add_executor_job(store_path.read_text)
                db.from_dict(json.loads(content))
                _LOGGER.info("Loaded %s users from storage", len(db.users))
        except Exception as error:
            _LOGGER.error("Failed to load persistent data: %s", error)

        rt = {
            "entry_id": entry.entry_id,
            "device_id": device_id,
            DATA_COORDINATOR: device_id,
            DATA_USERS_DB: db,
            "db": db,
            "store_path": store_path,
            "entry": entry,
            "tamper_active": False,
            "tamper_since": 0.0,
            "tamper_timer": None,
            "keypad_locked_by_tamper": False,
            "installer_until": 0.0,
            "installer_timer": None,
            "last_code": "",
            "last_code_time": 0,
            "lockouts": {"admin": PinLockout(), "operator": PinLockout(), "keypad": PinLockout()},
        }
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = rt
        entry.async_on_unload(entry.add_update_listener(_options_changed))

        @callback
        def _mqtt_message_received(msg):
            """Handle MQTT message from keypad."""
            try:
                payload = json.loads(msg.payload)

                tamper = payload.get("tamper")
                if tamper is not None:
                    was_tamper = rt["tamper_active"]
                    if tamper and not was_tamper:
                        # L'apertura si registra sempre; il blocco scatta solo se resta aperto oltre il ritardo.
                        rt["tamper_active"] = True
                        rt["tamper_since"] = time.time()
                        _update_sensor(rt)
                        hass.bus.async_fire("rfid_tamper_detected", {"device_id": device_id})
                        _LOGGER.warning(
                            "Coperchio aperto su '%s': il tastierino si blocca se resta aperto oltre %s s",
                            device_id, _tamper_delay(rt),
                        )
                        if rt.get("tamper_timer"):
                            rt["tamper_timer"]()
                        rt["tamper_timer"] = async_call_later(
                            hass, _tamper_delay(rt), lambda _now: _tamper_check(hass, rt),
                        )
                    elif not tamper and was_tamper:
                        rt["tamper_active"] = False
                        if rt.get("tamper_timer"):
                            rt["tamper_timer"]()
                            rt["tamper_timer"] = None
                        _update_sensor(rt)
                        if rt["keypad_locked_by_tamper"]:
                            _LOGGER.info(
                                "Coperchio chiuso su '%s' - tastierino ancora bloccato: "
                                "PIN operatore + Arma Tutto per riabilitarlo.", device_id,
                            )
                        else:
                            _LOGGER.info("Coperchio chiuso su '%s' prima del ritardo: nessun blocco", device_id)

                action_code = str(payload.get("action_code", "") or "").strip()
                action_type = str(payload.get("action", "")).lower()
                if action_type == KEYPAD_ACTION_EMERGENCY:
                    # SOS: anche senza codice, e prima di tamper e blocco PIN.
                    hass.async_create_task(_handle_emergency(hass, rt, action_code))
                    return
                if not action_code:
                    return
                hass.async_create_task(_mqtt_validate(hass, rt, action_code, action_type))
            except json.JSONDecodeError:
                _LOGGER.debug("Non-JSON MQTT message on keypad topic: %s", msg.payload)
            except Exception as error:
                _LOGGER.error("Error processing keypad MQTT message: %s", error)

        if mqtt_topic:
            try:
                rt["mqtt_unsubscribe"] = await mqtt.async_subscribe(
                    hass, mqtt_topic, _mqtt_message_received, qos=0
                )
                _LOGGER.info("Subscribed to MQTT topic: %s", mqtt_topic)
            except Exception as error:
                _LOGGER.error("Failed to subscribe to MQTT topic '%s': %s", mqtt_topic, error)

        try:
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        except Exception as error:
            _LOGGER.error("Error forwarding platforms: %s", error)

        _LOGGER.info("RFID Access Control v1.3.0 setup complete for '%s' (MQTT: %s)", device_id, mqtt_topic)
        return True

    except Exception as error:
        _LOGGER.error("Failed to setup RFID Access Control: %s", error)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry. The user file stays on disk."""
    rt = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    unsubscribe = rt.get("mqtt_unsubscribe")
    if unsubscribe:
        unsubscribe()
    if rt.get("tamper_timer"):
        rt["tamper_timer"]()
    if rt.get("installer_timer"):
        rt["installer_timer"]()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _save_database(hass: HomeAssistant, store_path: Path, db: AccessDatabase):
    """Save database to file."""
    try:
        store_path.parent.mkdir(parents=True, exist_ok=True)

        def save():
            store_path.write_text(json.dumps(db.to_dict(), indent=2))

        await hass.async_add_executor_job(save)
    except Exception as error:
        _LOGGER.error("Failed to save database: %s", error)
