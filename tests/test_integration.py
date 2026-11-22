"""Test dei servizi e del tastierino con un Home Assistant finto.

Home Assistant non serve: i moduli `homeassistant.*` e `voluptuous` vengono
sostituiti da stub minimi prima di caricare il pacchetto.
"""
import asyncio
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "custom_components" / "rfid_access_control"


def _install_stubs():
    def module(name, **attrs):
        mod = types.ModuleType(name)
        mod.__dict__.update(attrs)
        sys.modules[name] = mod
        return mod

    class HomeAssistantError(Exception):
        pass

    class SupportsResponse:
        ONLY = "only"
        NONE = "none"

    class _Anything:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            return _Anything()

        def __getattr__(self, name):
            return _Anything()

    def callback(func):
        return func

    async def async_subscribe(hass, topic, handler, qos=0):
        hass.subscriptions[topic] = handler
        return lambda: hass.subscriptions.pop(topic, None)

    module("homeassistant")
    module("homeassistant.components")
    module("homeassistant.components.mqtt", async_subscribe=async_subscribe)
    module("homeassistant.config_entries", ConfigEntry=_Anything)
    module("homeassistant.core", HomeAssistant=_Anything, ServiceCall=_Anything,
           SupportsResponse=SupportsResponse, callback=callback)
    module("homeassistant.exceptions", HomeAssistantError=HomeAssistantError)
    module("homeassistant.helpers")
    module("homeassistant.helpers.event",
           async_call_later=lambda hass, seconds, action: (lambda: None))
    module("homeassistant.helpers.typing", ConfigType=dict)
    module("voluptuous", Schema=_Anything, ALLOW_EXTRA=None)


_install_stubs()
spec = importlib.util.spec_from_file_location(
    "rfid_pkg", PKG_DIR / "__init__.py", submodule_search_locations=[str(PKG_DIR)]
)
integ = importlib.util.module_from_spec(spec)
sys.modules["rfid_pkg"] = integ
spec.loader.exec_module(integ)
HomeAssistantError = sys.modules["homeassistant.exceptions"].HomeAssistantError


class _Services:
    def __init__(self, hass):
        self.hass = hass
        self.handlers = {}
        self.calls = []

    def has_service(self, domain, name):
        return (domain, name) in self.handlers

    def async_register(self, domain, name, handler, supports_response=None):
        self.handlers[(domain, name)] = handler

    async def async_call(self, domain, service, data=None, **kwargs):
        data = dict(data or {})
        if domain == "rfid_access_control":
            call = types.SimpleNamespace(data=data)
            return await self.handlers[(domain, service)](call)
        self.calls.append((f"{domain}.{service}", data))


class FakeHass:
    def __init__(self, config_dir):
        self.config = types.SimpleNamespace(config_dir=str(config_dir))
        self.data = {}
        self.events = []
        self.subscriptions = {}
        self.pending = []
        self.services = _Services(self)
        self.bus = types.SimpleNamespace(async_fire=lambda name, data: self.events.append((name, data)))
        self.config_entries = types.SimpleNamespace(
            async_forward_entry_setups=self._noop,
            async_unload_platforms=self._true,
        )

    async def _noop(self, *args, **kwargs):
        return None

    async def _true(self, *args, **kwargs):
        return True

    async def async_add_executor_job(self, func, *args):
        return func(*args)

    def async_create_task(self, coro):
        self.pending.append(coro)

    async def flush(self):
        while self.pending:
            await self.pending.pop(0)

    def denied_reasons(self):
        return [data.get("reason") for name, data in self.events if name == "rfid_access_denied"]


class FakeEntry:
    def __init__(self, device_id):
        self.entry_id = f"entry_{device_id}"
        self.data = {"device_id": device_id, "mqtt_topic": f"zigbee2mqtt/{device_id}"}
        self.options = {}

    def add_update_listener(self, listener):
        return lambda: None

    def async_on_unload(self, func):
        pass


def keypad_message(hass, device_id, payload):
    handler = hass.subscriptions[f"zigbee2mqtt/{device_id}"]
    handler(types.SimpleNamespace(payload=json.dumps(payload)))


class IntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hass = FakeHass(self.tmp.name)
        self.entry = FakeEntry("porta")
        await integ.async_setup(self.hass, {})
        self.assertTrue(await integ.async_setup_entry(self.hass, self.entry))

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def call(self, service, **data):
        return await self.hass.services.async_call("rfid_access_control", service, data)

    def rt(self, entry=None):
        return self.hass.data["rfid_access_control"][(entry or self.entry).entry_id]

    async def set_pins(self, admin="2468", operator="1357"):
        await self.call("set_admin_pin", new_pin=admin)
        await self.call("set_operator_pin", new_pin=operator)

    async def test_first_run_needs_pins_and_refuses_example_values(self):
        self.assertFalse(self.rt()["db"].pins_configured())
        with self.assertRaises(HomeAssistantError):
            await self.call("set_admin_pin", new_pin="0000")
        result = await self.call("verify_admin_pin", pin="11061988")
        self.assertFalse(result["valid"])
        self.assertTrue(result["not_set"])

    async def test_changing_a_pin_needs_the_current_one(self):
        await self.set_pins()
        with self.assertRaises(HomeAssistantError):
            await self.call("set_admin_pin", new_pin="1111")
        with self.assertRaises(HomeAssistantError):
            await self.call("set_admin_pin", new_pin="1111", current_pin="9999")
        await self.call("set_admin_pin", new_pin="1111", current_pin="2468")
        self.assertEqual(self.rt()["db"].admin_pin, "1111")

    async def test_admin_and_operator_pins_must_differ(self):
        await self.call("set_admin_pin", new_pin="2468")
        with self.assertRaises(HomeAssistantError):
            await self.call("set_operator_pin", new_pin="2468")

    async def test_wrong_operator_pin_locks_out_after_five_tries(self):
        await self.set_pins()
        for _ in range(5):
            last = await self.call("verify_operator_pin", pin="0000")
        self.assertTrue(last["locked_out"])
        blocked = await self.call("verify_operator_pin", pin="1357")
        self.assertFalse(blocked["valid"], "il PIN giusto non passa durante il blocco")

    async def test_user_pins_cannot_repeat_or_use_examples(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        with self.assertRaises(HomeAssistantError):
            await self.call("add_user", user_id="luca", user_name="Luca", user_pin="1234")
        with self.assertRaises(HomeAssistantError):
            await self.call("add_user", user_id="anna", user_name="Anna", user_pin="0000")
        with self.assertRaises(HomeAssistantError):
            await self.call("add_user", user_id="carlo", user_name="Carlo", user_pin="1357")

    async def test_update_without_pin_keeps_the_pin(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        await self.call("update_user", user_id="mario", user_name="Mario Rossi", user_pin="", user_rfid="")
        user = self.rt()["db"].get_user("mario")
        self.assertEqual((user.user_name, user.pin), ("Mario Rossi", "1234"))

    async def test_tamper_blocks_users_until_operator_pin(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        await self.call("add_action", user_id="mario", action_name="Luce",
                        action_entity="light.sala", action_service="light.turn_on")

        keypad_message(self.hass, "porta", {"tamper": True})
        self.assertFalse(self.rt()["keypad_locked_by_tamper"], "il blocco arriva solo dopo il ritardo")
        await self.expire_tamper_delay()
        self.assertTrue(self.rt()["keypad_locked_by_tamper"])
        keypad_message(self.hass, "porta", {"action": "arm_all_zones", "action_code": "1234"})
        await self.hass.flush()
        self.assertIn("tamper_lock", self.hass.denied_reasons())
        self.assertEqual(self.hass.services.calls, [])

        keypad_message(self.hass, "porta", {"action": "arm_all_zones", "action_code": "1357"})
        await self.hass.flush()
        self.assertFalse(self.rt()["keypad_locked_by_tamper"])

    async def expire_tamper_delay(self):
        """Il coperchio è aperto da più del ritardo: simula lo scadere del timer."""
        rt = self.rt()
        rt["tamper_since"] -= 3600
        integ._tamper_check(self.hass, rt)

    async def test_tamper_delay_defaults_to_three_seconds(self):
        self.assertEqual(integ._tamper_delay(self.rt()), 3)

    async def test_card_error_does_not_stop_the_integration(self):
        failing = mock.AsyncMock(side_effect=RuntimeError("risorsa non valida"))
        with mock.patch.object(integ, "_register_card", failing):
            with self.assertLogs("rfid_pkg", level="WARNING") as logs:
                self.assertTrue(await integ.async_setup(self.hass, {}))
        self.assertEqual(failing.await_count, 1)
        self.assertTrue(any(
            "/rfid_access_control/rfid-access-control-card.js?v=1.3.0" in line for line in logs.output
        ))
        # L'integrazione è comunque operativa: i servizi rispondono.
        await self.set_pins()
        self.assertTrue(self.rt()["db"].pins_configured())

    async def test_short_cover_opening_is_logged_but_does_not_lock(self):
        with self.assertLogs("rfid_pkg", level="WARNING") as logs:
            keypad_message(self.hass, "porta", {"tamper": True})
        self.assertTrue(any("Coperchio aperto" in line for line in logs.output))
        keypad_message(self.hass, "porta", {"tamper": False})
        await self.expire_tamper_delay()
        self.assertFalse(self.rt()["tamper_active"])
        self.assertFalse(self.rt()["keypad_locked_by_tamper"], "chiuso prima del ritardo: nessun blocco")
        self.assertIn(("rfid_tamper_detected", {"device_id": "porta"}), self.hass.events)
        self.assertNotIn("rfid_tamper_locked", [name for name, _ in self.hass.events])

    async def test_zero_delay_option_locks_as_soon_as_the_timer_runs(self):
        self.entry.options = {"tamper_delay": 0}
        keypad_message(self.hass, "porta", {"tamper": True})
        integ._tamper_check(self.hass, self.rt())
        self.assertTrue(self.rt()["keypad_locked_by_tamper"])
        self.assertIn(("rfid_tamper_locked", {"device_id": "porta"}), self.hass.events)

    async def test_installer_mode_works_with_cover_open(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        await self.call("add_action", user_id="mario", action_name="Luce",
                        action_entity="light.sala", action_service="light.turn_on")
        keypad_message(self.hass, "porta", {"tamper": True})

        with self.assertRaises(HomeAssistantError):
            await self.call("set_installer_mode", pin="1357", minutes=61)
        with self.assertRaises(HomeAssistantError):
            await self.call("set_installer_mode", pin="0000", minutes=15)
        await self.call("set_installer_mode", pin="1357", minutes=15)

        keypad_message(self.hass, "porta", {"action": "disarm", "action_code": "1234"})
        await self.hass.flush()
        self.assertEqual(self.hass.services.calls, [("light.turn_on", {"entity_id": "light.sala"})])

        await self.call("set_installer_mode", pin="1357", minutes=0)
        self.assertEqual(self.rt()["installer_until"], 0.0)

    async def test_removing_keypad_keeps_its_file(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        store = self.rt()["store_path"]
        self.assertTrue(store.exists())
        self.assertTrue(await integ.async_unload_entry(self.hass, self.entry))
        self.assertTrue(store.exists(), "rimuovere il tastierino non cancella gli utenti")

    async def test_two_keypads_need_device_id_and_stay_separate(self):
        second = FakeEntry("ingresso")
        self.assertTrue(await integ.async_setup_entry(self.hass, second))
        await self.call("set_admin_pin", device_id="porta", new_pin="2468")
        await self.call("set_operator_pin", device_id="porta", new_pin="1357")
        with self.assertRaises(HomeAssistantError):
            await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        await self.call("add_user", device_id="ingresso", user_id="mario", user_name="Mario", user_pin="1234")
        self.assertIn("mario", self.rt(second)["db"].users)
        self.assertNotIn("mario", self.rt()["db"].users)

    async def test_repeated_code_within_two_seconds_is_ignored(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        await self.call("add_action", user_id="mario", action_name="Luce",
                        action_entity="light.sala", action_service="light.turn_on")

        keypad_message(self.hass, "porta", {"action": "disarm", "action_code": "1234"})
        keypad_message(self.hass, "porta", {"action": "disarm", "action_code": "1234"})
        await self.hass.flush()
        self.assertEqual(len(self.hass.services.calls), 1, "il doppio invio non esegue azioni")
        self.assertEqual(self.rt()["lockouts"]["keypad"].failed, 0, "il doppio invio non conta come errore")

        keypad_message(self.hass, "porta", {"action": "disarm", "action_code": "9999"})
        keypad_message(self.hass, "porta", {"action": "disarm", "action_code": "1234"})
        await self.hass.flush()
        self.assertEqual(len(self.hass.services.calls), 2, "un codice diverso non viene ignorato")

    async def test_test_access_code_needs_operator_pin_and_hides_pins(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        with self.assertRaises(HomeAssistantError):
            await self.call("test_access_code", operator_pin="0000", code="1234")
        result = await self.call("test_access_code", operator_pin="1357", code="1234")
        self.assertEqual(result, {"found": True, "user_name": "Mario", "block_reason": ""})

    async def press(self, action, code="1234"):
        """Un tasto con un codice. L'antirimbalzo viene azzerato: ogni prova è una pressione nuova."""
        self.rt()["last_accepted"] = ("", 0.0)
        keypad_message(self.hass, "porta", {"action": action, "action_code": code})
        await self.hass.flush()

    async def test_keypad_button_decides_which_action_runs(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        await self.call("add_action", user_id="mario", action_name="Apri", action_entity="lock.porta",
                        action_service="lock.unlock", keypad_action="disarm")
        await self.call("add_action", user_id="mario", action_name="Notte", action_entity="alarm.casa",
                        action_service="alarm.arm_night", keypad_action="arm_night_zones")

        await self.press("arm_night_zones")
        self.assertEqual(self.hass.services.calls, [("alarm.arm_night", {"entity_id": "alarm.casa"})])
        await self.press("disarm")
        self.assertEqual(self.hass.services.calls[1], ("lock.unlock", {"entity_id": "lock.porta"}))
        await self.press("arm_day_zones")
        self.assertEqual(len(self.hass.services.calls), 2, "il tasto casa non attiva le azioni degli altri tasti")

    async def test_invalid_keypad_button_is_refused(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        with self.assertRaises(HomeAssistantError):
            await self.call("add_action", user_id="mario", action_name="X", action_entity="light.sala",
                            action_service="light.turn_on", keypad_action="emergency")

    async def test_sos_fires_without_code_and_runs_only_global_actions(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        await self.call("add_action", user_id="mario", action_name="Luce", action_entity="light.sala",
                        action_service="light.turn_on")
        await self.call("add_sos_action", action_name="Sirena", action_entity="siren.cortile",
                        action_service="siren.turn_on")
        self.assertEqual(len(self.rt()["db"].sos_actions), 1)

        keypad_message(self.hass, "porta", {"action": "emergency"})
        await self.hass.flush()
        self.assertEqual(self.hass.services.calls, [("siren.turn_on", {"entity_id": "siren.cortile"})])
        self.assertIn(("rfid_emergency", {"device_id": "porta", "user_id": "", "user_name": ""}), self.hass.events)

    async def test_sos_with_code_names_the_user_even_when_tamper_locked(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        keypad_message(self.hass, "porta", {"tamper": True})
        await self.expire_tamper_delay()
        keypad_message(self.hass, "porta", {"action": "emergency", "action_code": "1234"})
        await self.hass.flush()
        emergencies = [data for name, data in self.hass.events if name == "rfid_emergency"]
        self.assertEqual(emergencies, [{"device_id": "porta", "user_id": "mario", "user_name": "Mario"}])
        self.assertTrue(self.rt()["keypad_locked_by_tamper"], "il SOS non sblocca il tastierino")

    async def test_remove_sos_action(self):
        await self.set_pins()
        await self.call("add_sos_action", action_name="Sirena", action_entity="siren.cortile",
                        action_service="siren.turn_on")
        with self.assertRaises(HomeAssistantError):
            await self.call("add_sos_action", action_name="Sirena", action_entity="siren.x",
                            action_service="siren.turn_on")
        await self.call("remove_sos_action", action_name="Sirena")
        self.assertEqual(self.rt()["db"].sos_actions, [])
        with self.assertRaises(HomeAssistantError):
            await self.call("remove_sos_action", action_name="Sirena")

    async def test_get_user_pin_needs_admin_pin_not_operator_pin(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        with self.assertRaises(HomeAssistantError):
            await self.call("get_user_pin", admin_pin="1357", user_id="mario")
        result = await self.call("get_user_pin", admin_pin="2468", user_id="mario")
        self.assertEqual(result, {"user_id": "mario", "pin": "1234"})

    async def test_get_user_pin_locks_out_after_five_wrong_admin_pins(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        for _ in range(5):
            with self.assertRaises(HomeAssistantError):
                await self.call("get_user_pin", admin_pin="0000", user_id="mario")
        with self.assertRaises(HomeAssistantError) as ctx:
            await self.call("get_user_pin", admin_pin="2468", user_id="mario")
        self.assertIn("Troppi tentativi", str(ctx.exception))

    async def test_remove_user_deletes_it_on_disk(self):
        await self.set_pins()
        await self.call("add_user", user_id="mario", user_name="Mario", user_pin="1234")
        await self.call("remove_user", user_id="mario")
        self.assertIsNone(self.rt()["db"].get_user("mario"))
        saved = json.loads(self.rt()["store_path"].read_text())
        self.assertNotIn("mario", saved["users"])

    async def add_second_keypad(self):
        self.second = FakeEntry("ingresso")
        self.assertTrue(await integ.async_setup_entry(self.hass, self.second))
        await self.call("set_admin_pin", device_id="ingresso", new_pin="3579")
        await self.call("set_operator_pin", device_id="ingresso", new_pin="9753")

    async def test_device_id_is_optional_with_one_keypad_but_checked_when_given(self):
        await self.set_pins()
        await self.call("add_user", device_id="porta", user_id="mario", user_name="Mario", user_pin="1234")
        self.assertIn("mario", self.rt()["db"].users)
        with self.assertRaises(HomeAssistantError) as ctx:
            await self.call("add_user", device_id="nope", user_id="luca", user_name="Luca", user_pin="5555")
        self.assertIn("non configurato", str(ctx.exception))

    async def test_copy_user_to_second_keypad_needs_its_admin_pin(self):
        await self.set_pins()
        await self.add_second_keypad()
        await self.call("add_user", device_id="porta", user_id="mario", user_name="Mario", user_pin="1234")
        await self.call("add_action", device_id="porta", user_id="mario", action_name="Apri",
                        action_entity="lock.porta", action_service="lock.unlock", keypad_action="disarm")

        # Il PIN admin di porta non vale per ingresso.
        with self.assertRaises(HomeAssistantError):
            await self.call("copy_user", device_id="porta", user_id="mario",
                            target_device_id="ingresso", admin_pin="2468")
        await self.call("copy_user", device_id="porta", user_id="mario",
                        target_device_id="ingresso", admin_pin="3579")

        copied = self.rt(self.second)["db"].get_user("mario")
        self.assertEqual((copied.user_name, copied.pin), ("Mario", "1234"))
        self.assertEqual([(a.entity_id, a.keypad_action) for a in copied.actions], [("lock.porta", "disarm")])

        # Le azioni sono copie: cambiarle su ingresso non tocca porta.
        copied.actions[0].entity_id = "lock.altro"
        self.assertEqual(self.rt()["db"].get_user("mario").actions[0].entity_id, "lock.porta")

        with self.assertRaises(HomeAssistantError):
            await self.call("copy_user", device_id="porta", user_id="mario",
                            target_device_id="ingresso", admin_pin="3579")

    async def test_copy_user_refuses_a_pin_already_used_on_the_target(self):
        await self.set_pins()
        await self.add_second_keypad()
        await self.call("add_user", device_id="porta", user_id="mario", user_name="Mario", user_pin="1234")
        await self.call("add_user", device_id="ingresso", user_id="luca", user_name="Luca", user_pin="1234")
        with self.assertRaises(HomeAssistantError) as ctx:
            await self.call("copy_user", device_id="porta", user_id="mario",
                            target_device_id="ingresso", admin_pin="3579")
        self.assertIn("già usato", str(ctx.exception))
        self.assertNotIn("mario", self.rt(self.second)["db"].users)

    async def test_copy_user_to_the_same_keypad_is_refused(self):
        await self.set_pins()
        await self.add_second_keypad()
        await self.call("add_user", device_id="porta", user_id="mario", user_name="Mario", user_pin="1234")
        with self.assertRaises(HomeAssistantError):
            await self.call("copy_user", device_id="porta", user_id="mario",
                            target_device_id="porta", admin_pin="2468")

    async def test_discover_keypads_lists_only_keypads(self):
        task = asyncio.ensure_future(self.hass.services.async_call("rfid_access_control", "discover_keypads", {}))
        await asyncio.sleep(0)
        devices = [
            {"friendly_name": "portoncino", "type": "EndDevice",
             "definition": {"model": "KEPZB-110", "description": "Keypad"}},
            {"friendly_name": "lampada", "type": "EndDevice",
             "definition": {"model": "E14", "description": "Lampadina"}},
            {"friendly_name": "Coordinator", "type": "Coordinator", "definition": {"model": "ZZ"}},
        ]
        self.hass.subscriptions["zigbee2mqtt/bridge/devices"](types.SimpleNamespace(payload=json.dumps(devices)))
        result = await task
        self.assertEqual(result["devices"], [
            {"friendly_name": "portoncino", "model": "KEPZB-110", "topic": "zigbee2mqtt/portoncino"},
        ])


if __name__ == "__main__":
    unittest.main()
