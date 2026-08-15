import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "registry-server"))

import server as registry_server  # noqa: E402


class RegistryServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_data_file = registry_server.DATA_FILE
        registry_server.DATA_FILE = Path(self.temporary_directory.name) / "mappings.json"
        self.client = TestClient(registry_server.app)

    def tearDown(self) -> None:
        registry_server.DATA_FILE = self.original_data_file
        self.temporary_directory.cleanup()

    def test_health_does_not_require_agent_credentials(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_mapping_round_trip(self) -> None:
        mapping = {
            "id": "servo-1",
            "boardId": "leonardo",
            "partId": "Micro_Servo_SG90",
            "role": "Control",
            "pins": [9],
        }

        write_response = self.client.post("/mappings", json={"mappings": [mapping]})
        read_response = self.client.get("/mappings")

        self.assertEqual(write_response.status_code, 201)
        self.assertEqual(read_response.json()["mappings"], [mapping | {"label": None}])

    def test_rejects_duplicate_component_mappings(self) -> None:
        mappings = [
            {
                "id": "servo-1",
                "boardId": "leonardo",
                "partId": "Micro_Servo_SG90",
                "role": "Control",
                "pins": [9],
            },
            {
                "id": "servo-2",
                "boardId": "leonardo",
                "partId": "Micro_Servo_SG90",
                "role": "Control",
                "pins": [10],
            },
        ]

        response = self.client.post("/mappings", json={"mappings": mappings})

        self.assertEqual(response.status_code, 400)

    def test_generates_arduino_firmware(self) -> None:
        payload = {
            "boardId": "leonardo",
            "mappings": [
                {
                    "id": "buzzer-1",
                    "boardId": "leonardo",
                    "partId": "Piezo_Buzzer",
                    "role": "Buzz",
                    "pins": [6],
                }
            ],
        }

        response = self.client.post("/generate-code", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["fileExtension"], "ino")
        self.assertIn("#define PIEZO_BUZZER_PIN 6", response.json()["code"])
        self.assertIn("#ifdef MICRO_SERVO_SG90_PIN", response.json()["code"])

    def test_generates_raspberry_pi_firmware_for_selected_board(self) -> None:
        payload = {
            "boardId": "pi5",
            "mappings": [
                {
                    "id": "ultrasonic-1",
                    "boardId": "pi5",
                    "partId": "hcsr04",
                    "role": "Distance",
                    "pins": [11, 13],
                },
                {
                    "id": "other-board",
                    "boardId": "leonardo",
                    "partId": "led",
                    "role": "Light",
                    "pins": [9],
                },
            ],
        }

        response = self.client.post("/generate-code", json=payload)

        self.assertEqual(response.status_code, 200)
        generated = response.json()["code"]
        self.assertEqual(response.json()["mappingCount"], 1)
        self.assertIn("GPIO.setmode(GPIO.BOARD)", generated)
        self.assertIn("HCSR04_TRIGGER = 11", generated)
        self.assertIn("HCSR04_ECHO = 13", generated)
        self.assertIn("Hardware controller started for pi5", generated)
        self.assertNotIn("LED_PIN", generated)
        compile(generated, "<generated-pi-code>", "exec")

    def test_mcp_bridge_lists_tools(self) -> None:
        runtime_mappings = REPO_ROOT / "registry-server" / "mappings.json"
        previous_contents = runtime_mappings.read_text() if runtime_mappings.exists() else None
        runtime_mappings.write_text(
            '[{"id":"buzzer-1","boardId":"leonardo",'
            '"partId":"Piezo_Buzzer","role":"Buzz","pins":[6]}]'
        )

        try:
            response = self.client.get("/tools")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                [tool["name"] for tool in response.json()["tools"]],
                ["piezo_beep"],
            )
            self.assertIn(
                "duration",
                response.json()["tools"][0]["input_schema"]["properties"],
            )
            self.assertNotIn(
                "context",
                response.json()["tools"][0]["input_schema"]["properties"],
            )
            self.assertEqual(
                response.json()["tools"][0]["input_schema"]["properties"]["duration"]["maximum"],
                5000,
            )

            invalid_call = self.client.post(
                "/call",
                json={"name": "piezo_beep", "args": {"duration": 0}},
            )
            self.assertEqual(invalid_call.status_code, 422)

            unavailable_call = self.client.post(
                "/call",
                json={"name": "piezo_beep", "args": {"duration": 100}},
            )
            self.assertEqual(unavailable_call.status_code, 422)

            runtime_mappings.write_text(
                '[{"id":"pi-buzzer","boardId":"pi5",'
                '"partId":"Piezo_Buzzer","role":"Buzz","pins":[11]}]'
            )
            pi_tools = self.client.get("/tools")
            self.assertEqual(pi_tools.status_code, 200)
            self.assertEqual(pi_tools.json()["tools"], [])
        finally:
            if previous_contents is None:
                runtime_mappings.unlink(missing_ok=True)
            else:
                runtime_mappings.write_text(previous_contents)

    def test_mcp_bridge_lists_ir_resource(self) -> None:
        runtime_mappings = REPO_ROOT / "registry-server" / "mappings.json"
        previous_contents = runtime_mappings.read_text() if runtime_mappings.exists() else None
        runtime_mappings.write_text(
            '[{"id":"ir-1","boardId":"leonardo",'
            '"partId":"IR_GP2Y0A21YK0F","role":"Distance_Sensor","pins":["A0"]}]'
        )

        async def list_resource_uris() -> list[str]:
            async with registry_server.create_mcp_client() as client:
                resources = await client.list_resources()
            return [str(resource.uri) for resource in resources]

        try:
            self.assertEqual(
                asyncio.run(list_resource_uris()),
                ["sensor://ir/GP2Y0A21YK0F"],
            )
        finally:
            if previous_contents is None:
                runtime_mappings.unlink(missing_ok=True)
            else:
                runtime_mappings.write_text(previous_contents)


if __name__ == "__main__":
    unittest.main()
