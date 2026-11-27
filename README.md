# VaaniSetu

**Speak your language. Let everyone understand you.**

VaaniSetu is a voice-first, bidirectional translation prototype for conversations across Indian languages. The long-term target is all 22 scheduled Indian languages, plus Indian English; the first complete voice path is Telugu → Hindi.

## Project status

### Implemented
- React + Vite frontend and Python + FastAPI backend.
- Demo/live configuration scaffolding.
- Browser microphone recording (up to 25 seconds per turn).
- Server-side Sarvam Saaras v4 speech-to-text integration.
- Sarvam Translate v1 text translation integration.
- Sarvam Bulbul v4 Flash text-to-speech integration.
- Language selector populated from 22 scheduled Indian languages plus Indian English.
- Separate output-language selector restricted to the current 11-language Bulbul TTS coverage.
- Original transcript, translated text and generated audio playback.
- Uploaded audio is processed in memory by this app and is not written to disk.

### Not implemented yet
- Two-participant conversation rooms.
- WebRTC / continuous streaming.
- Cellular phone-call integration.
- Advanced noise suppression, interruption handling and live partial transcripts.

## Current end-to-end flow

```text
Browser microphone
  -> React frontend
  -> FastAPI backend
  -> Sarvam Saaras v4 (speech -> source-language text)
  -> Sarvam Translate v1 (source text -> target text)
  -> Sarvam Bulbul v4 Flash (target text -> WAV audio)
  -> Browser plays translated voice
```

The first version uses short speech turns. The UI caps recordings at 25 seconds. Streaming will follow after the short-turn pipeline is validated.

## Requirements

- Node.js 20+
- Python 3.10+
- Git

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Health: http://localhost:8000/health  
API docs: http://localhost:8000/docs  
Language registry: http://localhost:8000/api/languages

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite prints the local frontend URL (usually http://localhost:5173).

## Demo mode and live AI mode

The app starts in demo mode without credentials. In demo mode, the microphone can record and preview a short clip locally, but audio is not sent to Sarvam. No transcript or translation is fabricated.

To enable real voice translation, create a Sarvam API key in the Sarvam dashboard, then edit `backend/.env`:

```env
APP_MODE=live
SARVAM_API_KEY=your_key_here
FRONTEND_ORIGINS=http://localhost:5173
```

Restart the backend after changing environment variables. The browser sends audio to the VaaniSetu backend; the backend calls Sarvam. The API key is never sent to the browser.

## API endpoints

- `GET /` — service status.
- `GET /health` — backend mode and provider configuration status.
- `GET /api/languages` — language lists and model capability information.
- `POST /api/speech/transcribe?language_code=te-IN` — transcribe a short audio upload using Saaras v4.
- `POST /api/translation/translate` — translate source text using Sarvam Translate v1.
- `POST /api/speech/synthesize` — generate WAV speech using Bulbul v4 Flash.
- `GET /api/calls/provider-status` — check Exotel configuration and calling readiness.
- `POST /api/calls/start` — validated, consent-gated Exotel call request (currently safety-blocked until the media bridge is ready).

## Language capability note

Saaras v4 speech recognition and Sarvam Translate v1 support all 22 scheduled Indian languages plus Indian English. Bulbul TTS currently supports 11 languages: Bengali, English (India), Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Punjabi, Tamil and Telugu. The UI therefore allows all 22 scheduled Indian languages plus Indian English as source languages, but only offers currently supported TTS target languages.

## Privacy and safety

The application does not persist uploaded audio to disk. In live mode, the audio clip and text are transmitted to Sarvam AI for processing, subject to that provider's terms and privacy practices. Obtain clear consent before recording or processing another person's speech. Do not use this prototype for emergency or high-stakes medical communication.

## Phone-call integration (in progress)

The first PSTN provider being evaluated is Exotel India. Its Voice V1
"Connect Two Numbers" API can call the VaaniSetu user's number first, then
call the recipient, and bridge the two legs. However, the simple Connect Voice
AI endpoint is designed for a bot talking to one caller; VaaniSetu needs two
human participants and separate audio directions. The intended production
design therefore uses Exotel's ExoML programmable legs: keep each participant
on a distinct call leg, stream each leg to its own authenticated WebSocket
session, and inject translated audio into the opposite leg. Exotel documents
per-leg `StartStream`, `JoinBridge`, and bidirectional AgentStream controls.
The exact two-leg call/bridge sequence must be verified against an Exotel
account before enabling real calls.

Backend scaffolding is present:
- `GET /api/calls/provider-status` reports provider configuration without exposing credentials.
- `POST /api/calls/start` validates Indian E.164 numbers, language direction,
  and explicit consent, but remains safety-blocked and places no call.
- `backend/app/media_bridge.py` now contains a prototype Exotel AgentStream
  WebSocket receiver, short-turn silence segmentation, Sarvam ASR → translation
  → TTS processing, and translated-audio relay to the opposite participant
  stream. It expects separate `caller` and `recipient` streams to share a
  `session_id` supplied by the future call controller and uses a private media token.
- The media WebSocket route is `/api/calls/media/{role}`. It is not yet wired
  to ExoML leg creation, bridge membership, or public TLS hosting.
- Exotel credentials and the media token are read only from backend environment
  variables. No secrets belong in the frontend or Git.
- Outbound calling remains deliberately blocked. No PSTN call can be placed
  by this build.

Required backend environment variables (keep values in `backend/.env` only):
`EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`, `EXOTEL_ACCOUNT_SID`,
`EXOTEL_CALLER_ID`, `EXOTEL_STREAM_URL`, and `EXOTEL_MEDIA_TOKEN`.
Keep `ENABLE_OUTBOUND_CALLS=false` until the live media bridge, consent
disclosure, abuse protection, and call-cost limits are ready.

The critical next engineering task is to keep each participant's audio
separate, translate each direction independently, and inject translated
audio only into the opposite participant's call leg. A single mixed call
recording is not sufficient for reliable bidirectional translation.

## Planned milestones

1. Repository and application foundation.
2. Microphone capture and speech recognition.
3. Telugu ↔ Hindi translation and voice generation.
4. Two-participant browser conversation.
5. Streaming, noise, accent, mixed-language and latency testing.
6. Deployment and demo hardening.

## License

No license has been selected yet.
