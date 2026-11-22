"""Constants for RFID Access Control."""

DOMAIN = "rfid_access_control"

# Device model identifiers (Zigbee)
SUPPORTED_MODELS = {
    "KEPZB-110": {
        "name": "KEPLERO Keypad",
        "manufacturer": "Frient A/S",
        "device_type": "ZHAPresence",
    }
}

# Configuration keys
CONF_DEVICE_ID = "device_id"
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_USERS = "users"
CONF_KEYPAD_ATTRIBUTE = "keypad_attribute"
# Opzione: secondi che il coperchio può restare aperto prima che il tastierino si blocchi
CONF_TAMPER_DELAY = "tamper_delay"
DEFAULT_TAMPER_DELAY = 3

# Versione dell'integrazione: serve anche per il numero di versione della risorsa Lovelace
VERSION = "1.3.0"

# User attributes
ATTR_USER_ID = "user_id"
ATTR_USER_NAME = "user_name"
ATTR_USER_PIN = "user_pin"
ATTR_USER_RFID = "user_rfid"
ATTR_USER_ACTIONS = "user_actions"
ATTR_ACTION_ENTITY = "action_entity"
ATTR_ACTION_SERVICE = "action_service"
ATTR_ACTION_DATA = "action_data"

# Services
SERVICE_ADD_USER = "add_user"
SERVICE_REMOVE_USER = "remove_user"
SERVICE_UPDATE_USER = "update_user"
SERVICE_ADD_ACTION = "add_action"
SERVICE_REMOVE_ACTION = "remove_action"
SERVICE_VALIDATE_ACCESS = "validate_access"
SERVICE_LIST_USERS = "list_users"
SERVICE_SET_ADMIN_PIN = "set_admin_pin"
SERVICE_SET_OPERATOR_PIN = "set_operator_pin"
SERVICE_CLEAR_TAMPER_LOCK = "clear_tamper_lock"
SERVICE_VERIFY_ADMIN_PIN = "verify_admin_pin"
SERVICE_VERIFY_OPERATOR_PIN = "verify_operator_pin"
SERVICE_TEST_ACCESS_CODE = "test_access_code"
SERVICE_SET_INSTALLER_MODE = "set_installer_mode"
SERVICE_GET_USER_PIN = "get_user_pin"
SERVICE_ADD_SOS_ACTION = "add_sos_action"
SERVICE_REMOVE_SOS_ACTION = "remove_sos_action"
SERVICE_COPY_USER = "copy_user"
SERVICE_DISCOVER_KEYPADS = "discover_keypads"

# Elenco dispositivi Zigbee2MQTT (retained): da qui si trovano i tastierini da aggiungere
ZIGBEE_DEVICES_TOPIC = "zigbee2mqtt/bridge/devices"
DISCOVERY_TIMEOUT_SECONDS = 3

# Installatore: durata massima della modalità (minuti)
INSTALLER_MODE_MAX_MINUTES = 60

# Antirimbalzo: stesso codice dallo stesso tastierino entro questi secondi = doppio invio
DEBOUNCE_SECONDS = 2

# Sicurezza PIN: dopo troppi codici errati il controllo si blocca per un po'
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 60

# PIN di esempio delle versioni precedenti: non devono mai essere accettati
LEGACY_DEFAULT_PINS = {"11061988", "0000"}

# Events
EVENT_ACCESS_GRANTED = "rfid_access_granted"
EVENT_ACCESS_DENIED = "rfid_access_denied"
EVENT_USER_ADDED = "rfid_user_added"
EVENT_USER_REMOVED = "rfid_user_removed"
# Tasto SOS del tastierino (Zigbee2MQTT: action "emergency")
EVENT_EMERGENCY = "rfid_emergency"
KEYPAD_ACTION_EMERGENCY = "emergency"

# Data keys
DATA_COORDINATOR = "coordinator"
DATA_USERS_DB = "users_db"

# Validation
MIN_PIN_LENGTH = 4
MAX_PIN_LENGTH = 8
MIN_RFID_LENGTH = 8
MAX_USERS = 100

# Keypad events mapping
KEYPAD_EVENTS = {
    "rfid": "rfid_detected",
    "pin": "pin_entered",
    "access_granted": "access_granted",
    "access_denied": "access_denied",
}

# Ritardo coperchio: il tastierino si blocca solo se il coperchio resta aperto oltre il ritardo
EVENT_TAMPER_LOCKED = "rfid_tamper_locked"
