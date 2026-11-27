import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.firebase_auth import require_firebase_user
from app.exotel_client import ExotelClient


class ExotelOrchestrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        app.dependency_overrides[require_firebase_user] = lambda: {"uid": "test-user"}

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(require_firebase_user, None)

    def test_leg_sid_parser_handles_documented_nested_response_shapes(self):
        self.assertEqual(
            ExotelClient._find_sid({"leg": {"leg_sid": "LGSID123"}}),
            "LGSID123",
        )
        self.assertEqual(
            ExotelClient._find_sid({"data": [{"Sid": "LGSID456"}]}),
            "LGSID456",
        )
        self.assertIsNone(ExotelClient._find_sid({"status": "created"}))

    def test_provider_status_reports_event_transport_as_unverified(self):
        response = self.client.get("/api/calls/provider-status")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["leg_event_endpoint_verified"])
        self.assertFalse(body["agentstream_protocol_verified"])
        self.assertFalse(body["outbound_calls_enabled"])
        self.assertFalse(body["media_bridge_ready"])
        self.assertIn("gRPC", body["note"])
        self.assertNotIn("api_token", body)
        self.assertNotIn("api_key", body)

    def test_event_endpoint_is_closed_until_exotel_confirms_transport(self):
        response = self.client.post(
            "/api/calls/exotel/events?session_id=abcdefghijklmnop&role=caller&source_language=te-IN&target_language=hi-IN",
            json={
                "event_name": "leg_answered",
                "data": {"leg_sid": "LGSID123"},
            },
        )
        self.assertEqual(response.status_code, 503)

    def test_start_call_stays_blocked_without_live_pstn_verification(self):
        response = self.client.post("/api/calls/start", json={
            "caller_number": "+919876543210",
            "recipient_number": "+919876543211",
            "source_language": "te-IN",
            "target_language": "hi-IN",
            "consent_confirmed": True,
        })
        self.assertEqual(response.status_code, 503)
        self.assertIn("No call has been placed", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
