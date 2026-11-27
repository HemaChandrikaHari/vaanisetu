# VaaniSetu hackathon demo runbook

## What the current demo proves

- A user can speak into a browser microphone for a short turn.
- Sarvam Saaras v4 recognises the selected source language.
- Sarvam Translate v1 translates the recognised text.
- Sarvam Bulbul v4 Flash generates speech in a supported target language.
- The user can reverse the language direction using the swap control.

The current demo is a one-person, turn-based browser prototype. It is **not yet a live phone call** and does not connect a second participant. Do not describe it as real-time or as an ordinary cellular-call translator.

## Before the demo

1. Start the FastAPI backend from `backend` on port 8001 (or update the frontend API URL to match).
2. Start the Vite frontend from `frontend`.
3. Check `/health` and `/api/languages`.
4. Confirm the backend reports live mode and a configured Sarvam key. Never display or share the key.
5. Test Telugu → Hindi with a short, quiet utterance.
6. Use the swap control and test Hindi → Telugu.
7. Confirm that translated audio plays and the transcript and translation are legible.
8. Use headphones or a quiet room; keep each utterance under 10 seconds for a smoother demo.

## Suggested demo utterances

- Telugu: `నమస్కారం, మీరు ఎలా ఉన్నారు? నాకు సహాయం కావాలి.`
- Hindi: `नमस्ते, आप कैसे हैं? मुझे स्टेशन जाने का रास्ता बताइए।`

Speak naturally and allow a short pause after each sentence.

## Safety and honesty

- Live-mode use requires acknowledgement that audio and transcript are sent to Sarvam AI for processing.
- Do not claim audio is never transmitted: it is sent to Sarvam in live mode.
- VaaniSetu does not currently persist uploaded audio to disk.
- Do not use the prototype for emergency, medical, legal, or other high-stakes conversations.
- Do not enable Exotel outbound calls. The ExoML call controller, public WSS deployment, and provider-approved two-leg audio flow are not complete.
- A recipient-side phone app is not required by the intended architecture, but the PSTN bridge is still pending provider enablement and validation.
