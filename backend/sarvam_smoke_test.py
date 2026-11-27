"""Minimal live Sarvam chat-completions smoke test.

Run from the backend directory:
    python sarvam_smoke_test.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sarvamai import SarvamAI


load_dotenv(Path(__file__).resolve().parent / ".env")

api_key = os.environ.get("SARVAM_API_KEY")
if not api_key:
    raise SystemExit("SARVAM_API_KEY is missing. Add it to backend/.env.")

client = SarvamAI(api_subscription_key=api_key)

response = client.chat.completions_v2(
    model="sarvam-105b-conversations",
    messages=[
        {
            "role": "user",
            "content": "Reply with one short sentence confirming that the Sarvam API connection works.",
        }
    ],
    max_tokens=100,
)

print(response.choices[0].message.content)
