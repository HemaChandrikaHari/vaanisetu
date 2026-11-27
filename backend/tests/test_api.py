import unittest

from fastapi.testclient import TestClient

from app.main import app


class VaaniSetuApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_does_not_expose_secrets(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("sarvam_configured", body)
        self.assertNotIn("api_key", body)
        self.assertNotIn("api_token", body)

    def test_language_registry_has_separate_tts_coverage(self):
        response = self.client.get("/api/languages")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["languages"]), 23)
        self.assertEqual(len(body["tts_languages"]), 11)
        self.assertIn({"code": "te-IN", "name": "Telugu"}, body["languages"])
        self.assertIn({"code": "hi-IN", "name": "Hindi"}, body["tts_languages"])

    def test_call_requires_explicit_consent(self):
        response = self.client.post("/api/calls/start", json={
            "caller_number": "+919876543210",
            "recipient_number": "+919876543211",
            "source_language": "te-IN",
            "target_language": "hi-IN",
            "consent_confirmed": False,
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("agreed", response.json()["detail"])

    def test_call_rejects_invalid_indian_mobile_number(self):
        response = self.client.post("/api/calls/start", json={
            "caller_number": "9876543210",
            "recipient_number": "+919876543211",
            "source_language": "te-IN",
            "target_language": "hi-IN",
            "consent_confirmed": True,
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("+91", response.json()["detail"])

    def test_call_is_safely_blocked_until_media_bridge_is_ready(self):
        response = self.client.post("/api/calls/start", json={
            "caller_number": "+919876543210",
            "recipient_number": "+919876543211",
            "source_language": "te-IN",
            "target_language": "hi-IN",
            "consent_confirmed": True,
        })
        self.assertEqual(response.status_code, 503)
        self.assertIn("No call has been placed", response.json()["detail"])

    def test_provider_status_never_claims_call_readiness(self):
        response = self.client.get("/api/calls/provider-status")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["media_bridge_ready"])
        self.assertFalse(body["outbound_calls_enabled"])


if __name__ == "__main__":
    unittest.main()
