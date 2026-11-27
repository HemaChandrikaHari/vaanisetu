import unittest
from unittest.mock import patch

from app import telephony
from app.exotel_client import ExotelApiError


class FakeExotelClient:
    def __init__(self):
        self.hangups = []

    async def start_stream(self, leg_sid, stream_url):
        raise ExotelApiError('simulated stream start failure')

    async def hangup_leg(self, leg_sid):
        self.hangups.append(leg_sid)


class ExotelFailClosedCleanupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        telephony.CALL_SESSIONS.clear()

    def tearDown(self):
        telephony.CALL_SESSIONS.clear()

    @patch('app.telephony.ExotelClient')
    async def test_stream_failure_hangs_up_both_answered_legs(self, client_class):
        client = FakeExotelClient()
        client_class.return_value = client
        telephony.CALL_SESSIONS['session-cleanup-123456'] = {
            'roles': {
                'caller': {'leg_sid': 'caller-leg'},
                'recipient': {'leg_sid': 'recipient-leg'},
            },
            'ended': False,
            'creating': False,
            'cleanup_pending': False,
        }

        with self.assertRaises(ExotelApiError):
            await telephony._process_exotel_event(
                'session-cleanup-123456', 'caller', 'te-IN', 'hi-IN',
                'leg_answered', 'caller-leg'
            )

        self.assertCountEqual(client.hangups, ['caller-leg', 'recipient-leg'])
        self.assertNotIn('session-cleanup-123456', telephony.CALL_SESSIONS)

    @patch('app.telephony.ExotelClient')
    async def test_late_answer_after_session_end_is_hung_up_without_stream(self, client_class):
        client = FakeExotelClient()
        client_class.return_value = client
        telephony.CALL_SESSIONS['session-ended-123456'] = {
            'roles': {
                'caller': {'leg_sid': 'caller-leg'},
                'recipient': {'leg_sid': None},
            },
            'ended': True,
            'creating': False,
            'cleanup_pending': False,
        }

        await telephony._process_exotel_event(
            'session-ended-123456', 'recipient', 'te-IN', 'hi-IN',
            'leg_answered', 'late-recipient-leg'
        )

        self.assertEqual(client.hangups, ['late-recipient-leg'])
        self.assertNotIn('session-ended-123456', telephony.CALL_SESSIONS)


if __name__ == '__main__':
    unittest.main()
