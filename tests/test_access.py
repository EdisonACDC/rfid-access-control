"""Test della logica di accesso (senza Home Assistant).

Il pacchetto viene caricato come `rfid_pkg` senza eseguire __init__.py,
che dipende da Home Assistant. Così i test girano con la sola libreria standard.
"""
import importlib.util
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "custom_components" / "rfid_access_control"

pkg = types.ModuleType("rfid_pkg")
pkg.__path__ = [str(PKG_DIR)]
sys.modules["rfid_pkg"] = pkg
models = importlib.import_module("rfid_pkg.models")
const = importlib.import_module("rfid_pkg.const")


def legacy_124_file(users=None, admin="11061988", operator="0000"):
    """File nel formato della 1.2.4 (lo stesso di db.to_dict() di allora)."""
    return {
        "_admin_pin": admin,
        "_operator_pin": operator,
        "users": users if users is not None else {
            "mario_001": {
                "user_id": "mario_001", "user_name": "Mario", "pin": "1234", "rfid": "04A12B3C1D",
                "actions": [{"entity_id": "light.sala", "service": "light.turn_on", "service_data": {},
                             "action_name": "Luce", "keypad_action": "any"}],
                "enabled": True, "created_at": "2026-01-01T10:00:00", "last_access": "",
                "access_count": 3,
            },
        },
    }


class MigrationTest(unittest.TestCase):
    def test_1_2_4_file_keeps_users_pins_and_actions(self):
        db = models.AccessDatabase()
        db.from_dict(legacy_124_file(admin="2468", operator="1357"))
        user = db.get_user("mario_001")
        self.assertIsNotNone(user)
        self.assertEqual(user.pin, "1234")
        self.assertEqual(user.rfid, "04A12B3C1D")
        self.assertEqual(user.access_count, 3)
        self.assertEqual(user.actions[0].action_name, "Luce")
        self.assertEqual((db.admin_pin, db.operator_pin), ("2468", "1357"))
        self.assertTrue(db.pins_configured())

    def test_1_2_4_default_pins_become_not_set(self):
        db = models.AccessDatabase()
        db.from_dict(legacy_124_file())
        self.assertEqual(db.admin_pin, "")
        self.assertEqual(db.operator_pin, "")
        self.assertFalse(db.pins_configured())
        self.assertEqual(len(db.users), 1)

    def test_round_trip_keeps_1_2_4_layout(self):
        db = models.AccessDatabase()
        db.from_dict(legacy_124_file(admin="2468", operator="1357"))
        data = db.to_dict()
        self.assertEqual(set(data), {"_admin_pin", "_operator_pin", "users"})
        self.assertEqual(data["users"]["mario_001"]["pin"], "1234")

    def test_flat_legacy_file_is_still_read(self):
        db = models.AccessDatabase()
        db.from_dict({"mario_001": legacy_124_file()["users"]["mario_001"]})
        self.assertIn("mario_001", db.users)


class PinRulesTest(unittest.TestCase):
    def test_example_pins_are_refused(self):
        self.assertTrue(models.check_pin_format("0000"))
        self.assertTrue(models.check_pin_format("11061988"))

    def test_pin_must_be_digits_in_range(self):
        self.assertTrue(models.check_pin_format("12a4"))
        self.assertTrue(models.check_pin_format("123"))
        self.assertTrue(models.check_pin_format("123456789"))
        self.assertEqual(models.check_pin_format("4321"), "")

    def test_user_pin_cannot_clash_with_system_pin_or_other_user(self):
        db = models.AccessDatabase()
        db.admin_pin, db.operator_pin = "2468", "1357"
        db.add_user(models.AccessUser("a", "A", pin="1111", rfid=""))
        self.assertTrue(db.check_credentials(pin="2468"))
        self.assertTrue(db.check_credentials(pin="1357"))
        self.assertTrue(db.check_credentials(pin="1111"))
        self.assertEqual(db.check_credentials(pin="1111", exclude_user_id="a"), "")
        self.assertEqual(db.check_credentials(pin="9999"), "")

    def test_rfid_duplicate_is_refused(self):
        db = models.AccessDatabase()
        db.add_user(models.AccessUser("a", "A", pin="", rfid="04A12B3C1D"))
        self.assertTrue(db.check_credentials(rfid="04a12b3c1d"))


class LockoutTest(unittest.TestCase):
    def test_five_wrong_codes_lock_then_release(self):
        lock = models.PinLockout()
        now = 1000.0
        for _ in range(const.MAX_FAILED_ATTEMPTS):
            result = models.verify_pin(lock, "1357", "0000", now=now)
        self.assertFalse(result["valid"])
        self.assertTrue(result["locked_out"])
        during = models.verify_pin(lock, "1357", "1357", now=now + 1)
        self.assertFalse(during["valid"], "il PIN giusto non passa durante il blocco")
        after = models.verify_pin(lock, "1357", "1357", now=now + const.LOCKOUT_SECONDS + 1)
        self.assertTrue(after["valid"])
        self.assertFalse(lock.locked(now + const.LOCKOUT_SECONDS + 1))

    def test_correct_code_resets_failures(self):
        lock = models.PinLockout()
        for _ in range(3):
            models.verify_pin(lock, "1357", "0000", now=1.0)
        self.assertTrue(models.verify_pin(lock, "1357", "1357", now=2.0)["valid"])
        self.assertEqual(lock.failed, 0)

    def test_unset_pin_is_reported_not_accepted(self):
        result = models.verify_pin(models.PinLockout(), "", "")
        self.assertFalse(result["valid"])
        self.assertTrue(result["not_set"])


class TemporaryAccessTest(unittest.TestCase):
    def setUp(self):
        self.user = models.AccessUser("ospite", "Ospite", pin="5555", rfid="")

    def test_always_valid_without_window(self):
        self.assertEqual(self.user.access_block_reason(datetime(2030, 1, 1)), "")
        self.assertTrue(self.user.validate_credentials(pin="5555"))

    def test_window_start_and_end(self):
        self.user.valid_from = "2026-12-24T18:00"
        self.user.valid_until = "2026-12-26T23:59"
        self.assertEqual(self.user.access_block_reason(datetime(2026, 12, 24, 17, 0)), "not_yet_valid")
        self.assertEqual(self.user.access_block_reason(datetime(2026, 12, 25, 12, 0)), "")
        self.assertEqual(self.user.access_block_reason(datetime(2026, 12, 27, 8, 0)), "expired")
        self.assertFalse(self.user.validate_credentials(pin="5555", now=datetime(2026, 12, 27, 8, 0)))

    def test_max_uses_counts_accesses(self):
        self.user.max_uses = 2
        self.user.record_access()
        self.assertEqual(self.user.access_block_reason(), "")
        self.user.record_access()
        self.assertEqual(self.user.access_block_reason(), "uses_exhausted")
        self.assertEqual(self.user.access_count, 2)

    def test_disabled_user_is_blocked(self):
        self.user.enabled = False
        self.assertEqual(self.user.access_block_reason(), "disabled")

    def test_window_is_normalized_and_checked(self):
        window = models.parse_access_window("2026-12-24T18:00:45", "2026-12-26T23:59", "3")
        self.assertEqual(window, {"valid_from": "2026-12-24T18:00", "valid_until": "2026-12-26T23:59", "max_uses": 3})
        with self.assertRaises(ValueError):
            models.parse_access_window("2026-12-26T10:00", "2026-12-25T10:00", 0)
        with self.assertRaises(ValueError):
            models.parse_access_window("", "", -1)


class InstallerModeTest(unittest.TestCase):
    def test_active_until_deadline(self):
        self.assertTrue(models.installer_active(1000.0 + 60, now=1000.0))
        self.assertFalse(models.installer_active(1000.0 + 60, now=1000.0 + 61))
        self.assertFalse(models.installer_active(0.0, now=1000.0))


class UpdateUserTest(unittest.TestCase):
    def test_empty_pin_keeps_current_value(self):
        db = models.AccessDatabase()
        db.add_user(models.AccessUser("a", "A", pin="1111", rfid="04A12B3C1D"))
        db.update_user("a", {"user_name": "", "pin": "", "rfid": ""})
        self.assertEqual(db.get_user("a").pin, "1111")
        self.assertEqual(db.get_user("a").user_name, "A")


if __name__ == "__main__":
    unittest.main()
