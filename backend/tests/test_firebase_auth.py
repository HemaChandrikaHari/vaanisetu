import unittest
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.firebase_auth import require_firebase_user

class FirebaseAuthVerificationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.credentials = HTTPAuthorizationCredentials(scheme='Bearer', credentials='test-token')

    @patch('app.firebase_auth._firebase_app', return_value=object())
    @patch('firebase_admin.auth.verify_id_token')
    async def test_verified_email_is_accepted(self, verify_token, _firebase_app):
        expected = {'uid': 'verified-user', 'email_verified': True}
        verify_token.return_value = expected
        self.assertEqual(await self._run(), expected)

    @patch('app.firebase_auth._firebase_app', return_value=object())
    @patch('firebase_admin.auth.verify_id_token')
    async def test_unverified_email_is_rejected(self, verify_token, _firebase_app):
        verify_token.return_value = {'uid': 'unverified-user', 'email_verified': False}
        with self.assertRaises(HTTPException) as caught:
            await self._run()
        self.assertEqual(caught.exception.status_code, 403)
        self.assertIn('verify your email', caught.exception.detail)

    @patch('app.firebase_auth._firebase_app', return_value=object())
    @patch('firebase_admin.auth.verify_id_token')
    async def test_missing_email_verified_claim_is_rejected(self, verify_token, _firebase_app):
        verify_token.return_value = {'uid': 'legacy-user'}
        with self.assertRaises(HTTPException) as caught:
            await self._run()
        self.assertEqual(caught.exception.status_code, 403)

    async def test_missing_bearer_token_is_rejected(self):
        with self.assertRaises(HTTPException) as caught:
            await require_firebase_user(credentials=None)
        self.assertEqual(caught.exception.status_code, 401)

    @patch('app.firebase_auth._firebase_app', return_value=object())
    @patch('firebase_admin.auth.verify_id_token', side_effect=Exception('invalid token'))
    async def test_invalid_token_is_rejected(self, _verify_token, _firebase_app):
        with self.assertRaises(HTTPException) as caught:
            await self._run()
        self.assertEqual(caught.exception.status_code, 401)

    @patch('app.firebase_auth._firebase_app', side_effect=RuntimeError('missing config'))
    async def test_missing_server_firebase_config_is_unavailable(self, _firebase_app):
        with self.assertRaises(HTTPException) as caught:
            await self._run()
        self.assertEqual(caught.exception.status_code, 503)
    async def _run(self):
        return await require_firebase_user(credentials=self.credentials)

if __name__ == '__main__':
    unittest.main()

