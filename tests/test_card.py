"""Test della card: selettore dei tastierini.

Le funzioni sono scritte tra i marcatori MULTI-KEYPAD-HELPERS nel file JavaScript e vengono
eseguite con node. Senza node (variabile NODE_BIN o node nel PATH) il test viene saltato.
"""
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "custom_components" / "rfid_access_control" / "www" / "rfid-access-control-card.js"
NODE = os.environ.get("NODE_BIN") or shutil.which("node")


def _helpers_block() -> str:
    text = CARD.read_text(encoding="utf-8")
    start = text.index("// MULTI-KEYPAD-HELPERS-BEGIN")
    end = text.index("// MULTI-KEYPAD-HELPERS-END")
    return text[start:end]


@unittest.skipUnless(NODE, "node non disponibile")
class KeypadSelectorTest(unittest.TestCase):
    def run_js(self, expression: str):
        script = _helpers_block() + f"\nconsole.log(JSON.stringify({expression}));"
        result = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def test_card_file_is_valid_javascript(self):
        result = subprocess.run([NODE, "--check", str(CARD)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_only_keypad_sensors_are_listed_sorted_with_labels(self):
        states = {
            "sensor.rfid_users_portoncino": {"attributes": {
                "device_id": "portoncino", "users": [], "setup_required": False,
                "mqtt_topic": "zigbee2mqtt/portoncino"}},
            "sensor.rfid_users_garage": {"attributes": {
                "device_id": "tastierino_garage", "users": [], "setup_required": True}},
            "sensor.temperatura": {"attributes": {"unit": "C"}},
            "sensor.vecchio": {"attributes": {"device_id": "x"}},
            "light.sala": {"attributes": {}},
        }
        keypads = self.run_js(f"rfidKeypadsFromStates({json.dumps(states)})")
        self.assertEqual(keypads, [
            {"entity": "sensor.rfid_users_garage", "deviceId": "tastierino_garage", "topic": "", "label": "Tastierino garage"},
            {"entity": "sensor.rfid_users_portoncino", "deviceId": "portoncino", "topic": "zigbee2mqtt/portoncino", "label": "Portoncino"},
        ])

    def test_one_keypad_gives_one_entry_and_no_states_gives_none(self):
        states = {"sensor.rfid_users_solo": {"attributes": {
            "device_id": "solo", "users": [], "setup_required": False}}}
        self.assertEqual(len(self.run_js(f"rfidKeypadsFromStates({json.dumps(states)})")), 1)
        self.assertEqual(self.run_js("rfidKeypadsFromStates({})"), [])

    def test_device_id_is_read_from_the_sensor_entity_name(self):
        self.assertEqual(self.run_js("rfidDeviceFromEntity('sensor.rfid_users_garage')"), "garage")
        self.assertEqual(self.run_js("rfidDeviceFromEntity('light.sala')"), "")


if __name__ == "__main__":
    unittest.main()
