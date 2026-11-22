"""Data models for RFID Access Control.

Questo modulo non dipende da Home Assistant: la logica di accesso è testabile da sola.
"""
import hmac
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List

from .const import (
    LEGACY_DEFAULT_PINS,
    LOCKOUT_SECONDS,
    MAX_FAILED_ATTEMPTS,
    MAX_PIN_LENGTH,
    MIN_PIN_LENGTH,
    MIN_RFID_LENGTH,
)


KEYPAD_ACTIONS = [
    "any",
    "arm_all_zones",
    "arm_day_zones",
    "arm_night_zones",
    "disarm",
]


def check_keypad_action(value: str) -> str:
    """Return an error message for an unknown keypad button choice, or an empty string."""
    if value not in KEYPAD_ACTIONS:
        return "Tasto del tastierino non valido: usa any, disarm, arm_all_zones, arm_day_zones o arm_night_zones"
    return ""


def parse_datetime(value: str) -> datetime | None:
    """Parse an ISO date/time saved in local time. Empty values return None."""
    if not value:
        return None
    return datetime.fromisoformat(value)


def parse_access_window(valid_from: str, valid_until: str, max_uses: Any) -> Dict[str, Any]:
    """Validate the temporary access fields and return them normalized.

    Dates are naive local ISO strings (minutes precision). max_uses 0 means unlimited.
    """
    start = parse_datetime(str(valid_from or "").strip())
    end = parse_datetime(str(valid_until or "").strip())
    if start and end and end <= start:
        raise ValueError("La data di fine deve essere dopo la data di inizio")
    try:
        uses = int(max_uses or 0)
    except (TypeError, ValueError) as error:
        raise ValueError("Il numero di accessi deve essere un numero intero") from error
    if uses < 0 or uses > 999:
        raise ValueError("Il numero di accessi deve essere tra 0 e 999")
    return {
        "valid_from": start.replace(second=0, microsecond=0).isoformat(timespec="minutes") if start else "",
        "valid_until": end.replace(second=0, microsecond=0).isoformat(timespec="minutes") if end else "",
        "max_uses": uses,
    }


def check_pin_format(pin: str) -> str:
    """Return an error message for a bad PIN, or an empty string."""
    if not pin.isdigit():
        return "Il PIN deve contenere solo cifre"
    if len(pin) < MIN_PIN_LENGTH or len(pin) > MAX_PIN_LENGTH:
        return f"Il PIN deve avere tra {MIN_PIN_LENGTH} e {MAX_PIN_LENGTH} cifre"
    if pin in LEGACY_DEFAULT_PINS:
        return "Scegli un PIN diverso dai valori di esempio"
    return ""


def check_rfid_format(rfid: str) -> str:
    """Return an error message for a bad RFID code, or an empty string."""
    if rfid and len(rfid) < MIN_RFID_LENGTH:
        return f"Il codice RFID deve avere almeno {MIN_RFID_LENGTH} caratteri"
    return ""


@dataclass
class AccessAction:
    """Represents an action to perform on access."""

    entity_id: str
    service: str
    service_data: Dict[str, Any] = field(default_factory=dict)
    action_name: str = ""
    keypad_action: str = "any"
    delay_before_seconds: int = 0
    delay_after_seconds: int = 0

    def matches_keypad_action(self, keypad_action: str) -> bool:
        """Check if this action should run for the given keypad action."""
        if not self.keypad_action or self.keypad_action == "any":
            return True
        return self.keypad_action.lower() == keypad_action.lower()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessAction":
        """Create from dictionary — backward compatible with old delay_seconds."""
        old_delay = int(data.get("delay_seconds", 0))
        return cls(
            entity_id=data.get("entity_id", ""),
            service=data.get("service", ""),
            service_data=data.get("service_data", {}),
            action_name=data.get("action_name", ""),
            keypad_action=data.get("keypad_action", "any"),
            delay_before_seconds=int(data.get("delay_before_seconds", old_delay)),
            delay_after_seconds=int(data.get("delay_after_seconds", 0)),
        )


@dataclass
class AccessUser:
    """Represents an access control user (one keypad each)."""

    user_id: str
    user_name: str
    pin: str
    rfid: str
    actions: List[AccessAction] = field(default_factory=list)
    enabled: bool = True
    created_at: str = ""
    last_access: str = ""
    access_count: int = 0
    # Accesso temporaneo: date locali ISO (vuote = sempre valido), 0 accessi = illimitati.
    valid_from: str = ""
    valid_until: str = ""
    max_uses: int = 0
    uses: int = 0

    def __post_init__(self):
        """Post initialization."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def access_block_reason(self, now: datetime | None = None) -> str:
        """Return why this user cannot access right now, or an empty string."""
        now = now or datetime.now()
        if not self.enabled:
            return "disabled"
        start = parse_datetime(self.valid_from)
        if start and now < start:
            return "not_yet_valid"
        end = parse_datetime(self.valid_until)
        if end and now > end:
            return "expired"
        if self.max_uses and self.uses >= self.max_uses:
            return "uses_exhausted"
        return ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["actions"] = [a.to_dict() for a in self.actions]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessUser":
        """Create from dictionary (old 1.2.4 files have no temporary fields)."""
        actions = [
            AccessAction.from_dict(a) for a in data.get("actions", [])
        ]
        return cls(
            user_id=data.get("user_id", ""),
            user_name=data.get("user_name", ""),
            pin=data.get("pin", ""),
            rfid=data.get("rfid", ""),
            actions=actions,
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", ""),
            last_access=data.get("last_access", ""),
            access_count=data.get("access_count", 0),
            valid_from=data.get("valid_from", ""),
            valid_until=data.get("valid_until", ""),
            max_uses=int(data.get("max_uses", 0) or 0),
            uses=int(data.get("uses", 0) or 0),
        )

    def validate_credentials(self, pin: str = "", rfid: str = "", now: datetime | None = None) -> bool:
        """Validate user credentials, including the temporary access window."""
        if self.access_block_reason(now):
            return False
        if pin and rfid:
            return self._pin_matches(pin) and self._rfid_matches(rfid)
        if pin:
            return self._pin_matches(pin)
        if rfid:
            return self._rfid_matches(rfid)
        return False

    def _pin_matches(self, pin: str) -> bool:
        return bool(self.pin) and hmac.compare_digest(self.pin, pin)

    def _rfid_matches(self, rfid: str) -> bool:
        return bool(self.rfid) and self.rfid.upper().strip() == rfid.upper().strip()

    def record_access(self):
        """Record successful access."""
        self.last_access = datetime.now().isoformat()
        self.access_count += 1
        self.uses += 1


class PinLockout:
    """Counts wrong codes and blocks checks for LOCKOUT_SECONDS after too many."""

    def __init__(self):
        """Start unlocked with no failures."""
        self.failed = 0
        self.until = 0.0

    def locked(self, now: float | None = None) -> bool:
        """True while the lockout lasts."""
        return (time.time() if now is None else now) < self.until

    def seconds_left(self, now: float | None = None) -> int:
        """Seconds until the lockout ends (0 when unlocked)."""
        return max(0, round(self.until - (time.time() if now is None else now)))

    def record_failure(self, now: float | None = None):
        """Count a wrong code; lock after MAX_FAILED_ATTEMPTS."""
        now = time.time() if now is None else now
        self.failed += 1
        if self.failed >= MAX_FAILED_ATTEMPTS:
            self.until = now + LOCKOUT_SECONDS
            self.failed = 0

    def reset(self):
        """A correct code clears the counter."""
        self.failed = 0
        self.until = 0.0


def verify_pin(lockout: PinLockout, expected: str, given: str, now: float | None = None) -> Dict[str, Any]:
    """Compare a code with the saved one, applying the lockout."""
    now = time.time() if now is None else now
    if lockout.locked(now):
        return {"valid": False, "locked_out": True, "seconds_left": lockout.seconds_left(now)}
    if not expected:
        return {"valid": False, "locked_out": False, "not_set": True, "seconds_left": 0}
    valid = bool(given) and hmac.compare_digest(str(expected), str(given))
    if valid:
        lockout.reset()
    else:
        lockout.record_failure(now)
    return {"valid": valid, "locked_out": lockout.locked(now), "seconds_left": lockout.seconds_left(now)}


def installer_active(until: float, now: float | None = None) -> bool:
    """True while installer mode runs (until is a unix timestamp, 0 = off)."""
    return bool(until) and (time.time() if now is None else now) < until


class AccessDatabase:
    """Manages the users of one keypad and its PINs."""

    def __init__(self):
        """Initialize database. PINs stay empty until the admin sets them."""
        self.users: Dict[str, AccessUser] = {}
        self.admin_pin: str = ""
        self.operator_pin: str = ""
        # Azioni globali del tasto SOS (non legate a un utente).
        self.sos_actions: List[AccessAction] = []

    def pins_configured(self) -> bool:
        """True when both admin and operator PINs are set."""
        return bool(self.admin_pin and self.operator_pin)

    def check_credentials(self, pin: str = "", rfid: str = "", exclude_user_id: str = "") -> str:
        """Return an error if the code clashes with another user or a system PIN, else ''."""
        if pin and pin in (self.admin_pin, self.operator_pin):
            return "Questo PIN coincide con un PIN di sistema"
        for other in self.users.values():
            if other.user_id == exclude_user_id:
                continue
            if pin and other.pin == pin:
                return "Questo PIN è già usato da un altro utente"
            if rfid and other.rfid and other.rfid.upper().strip() == rfid.upper().strip():
                return "Questo codice RFID è già usato da un altro utente"
        return ""

    def add_user(self, user: AccessUser) -> bool:
        """Add a new user."""
        if user.user_id in self.users:
            return False
        self.users[user.user_id] = user
        return True

    def remove_user(self, user_id: str) -> bool:
        """Remove a user."""
        if user_id not in self.users:
            return False
        del self.users[user_id]
        return True

    def get_user(self, user_id: str) -> AccessUser | None:
        """Get user by ID."""
        return self.users.get(user_id)

    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Update user. An empty PIN or RFID means 'keep the current value'."""
        if user_id not in self.users:
            return False
        user = self.users[user_id]
        if user_data.get("user_name"):
            user.user_name = user_data["user_name"]
        if user_data.get("pin"):
            user.pin = user_data["pin"]
        if user_data.get("rfid"):
            user.rfid = user_data["rfid"]
        if "enabled" in user_data:
            user.enabled = bool(user_data["enabled"])
        for key in ("valid_from", "valid_until", "max_uses"):
            if key in user_data:
                setattr(user, key, user_data[key])
        return True

    def find_user_by_credentials(self, pin: str = "", rfid: str = "", now: datetime | None = None) -> AccessUser | None:
        """Find the user matching the code (PIN or RFID)."""
        for user in self.users.values():
            if user.validate_credentials(pin=pin, rfid=rfid, now=now):
                return user
        return None

    def get_all_users(self) -> List[AccessUser]:
        """Get all users."""
        return list(self.users.values())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, same format as version 1.2.4."""
        data = {
            "_admin_pin": self.admin_pin,
            "_operator_pin": self.operator_pin,
            "users": {
                user_id: user.to_dict()
                for user_id, user in self.users.items()
            },
        }
        # Il campo SOS c'è solo se usato: senza azioni SOS il file resta com'era nella 1.2.4.
        if self.sos_actions:
            data["_sos_actions"] = [a.to_dict() for a in self.sos_actions]
        return data

    def from_dict(self, data: Dict[str, Any]):
        """Load from dictionary: 1.2.4 files, flat legacy files and new files.

        I PIN di esempio (0000, 11061988) salvati dalle versioni precedenti diventano
        "non impostati": il pannello chiede di sceglierne di nuovi.
        """
        self.admin_pin = self._clean_pin(data.get("_admin_pin", ""))
        self.operator_pin = self._clean_pin(data.get("_operator_pin", ""))
        self.sos_actions = [AccessAction.from_dict(a) for a in data.get("_sos_actions", [])]
        if "users" in data and isinstance(data["users"], dict):
            users = data["users"]
        else:
            users = {k: v for k, v in data.items() if not k.startswith("_")}
        self.users = {
            user_id: AccessUser.from_dict(user_data)
            for user_id, user_data in users.items()
        }

    @staticmethod
    def _clean_pin(value: Any) -> str:
        pin = str(value or "")
        return "" if pin in LEGACY_DEFAULT_PINS else pin
