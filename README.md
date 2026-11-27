# VaaniSetu

**Speak your language. Let everyone understand you.**

VaaniSetu is a voice-first, bidirectional translation prototype for conversations across Indian languages. The long-term target is all 22 scheduled Indian languages, plus Indian English; the first complete voice path is Telugu → Hindi.

## Project status

### Implemented
- React + Vite frontend and Python + FastAPI backend.
- Capacitor Android project wrapping the mobile interface, plus an installable PWA manifest and static app-shell cache.
- Mobile Translate / Phone call navigation and a phone-call setup screen for configuring language direction and Android call-redirection permission.
- Android microphone permission declaration and configurable backend URL for installed builds.
- Android 10+ call-redirection service registration, permission request, and native bridge for saving preferred call-language direction; outgoing calls are still passed through unchanged pending Exotel gateway verification.
- Demo/live configuration scaffolding.
- Browser microphone recording (up to 25 seconds per turn).
- Server-side Sarvam Saaras v4 speech-to-text integration.
- Sarvam Translate v1 text translation integration.
- Sarvam Bulbul v4 Flash text-to-speech integration.
- Language selector populated from 22 scheduled Indian languages plus Indian English.
- Separate output-language selector restricted to the current 11-language Bulbul TTS coverage.
- Original transcript, translated text and generated audio playback.
- Uploaded audio is processed in memory by this app and is not written to disk.
- Live-mode microphone capture requires an explicit acknowledgement that audio and transcript data are sent to Sarvam AI for processing.
- Automated backend API tests for health, language coverage, consent validation, phone-number validation, and safe call blocking.

### Not implemented yet
- Two-participant conversation rooms.
- WebRTC / continuous streaming.
- Full cellular phone-call translation, including Exotel two-leg call routing and bidirectional translated audio injection.
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

### Run backend checks

```bash
cd backend
python -m unittest discover -s tests -v
```

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

## Backend deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for the Render Blueprint deployment steps. The deployed API enables the existing short-turn Sarvam translation pipeline to be reached from the Android app. Keep Exotel outbound calling disabled: the production two-person PSTN media bridge is not yet implemented or verified.

## Phone-call integration (in progress)

The first PSTN provider being evaluated is Exotel India. Its Voice V1
"Connect Two Numbers" API can call the VaaniSetu user's number first, then
call the recipient, and bridge the two legs. However, the simple Connect Voice
AI endpoint is designed for a bot talking to one caller; VaaniSetu needs two
human participants and separate audio directions. The intended production
design therefore uses Exotel's ExoML programmable legs: keep each participant
on a distinct call leg, stream each leg to its own authenticated WebSocket
session, and inject translated audio into the opposite leg. The exact two-leg
call/bridge sequence and AgentStream controls must be verified with Exotel's
technical team and against the account before enabling real calls.

The Android app now registers `VaaniSetuCallRedirectionService` and exposes a
native permission/status bridge. The user can save their preferred source and
target languages in advance. This is not a universal OEM dialler menu item;
the current service always passes outgoing calls through unchanged until the
Exotel gateway adapter is verified and implemented.

Backend scaffolding is present:
- `GET /api/calls/provider-status` reports provider configuration without exposing credentials.
- `POST /api/calls/start` validates Indian E.164 numbers, language direction,
  and explicit consent, but remains safety-blocked and places no call.
- `backend/app/media_bridge.py` contains an isolated media-relay prototype and
  provider-neutral PCM turn segmentation. The Exotel wire protocol, codec,
  outbound-audio injection shape, and two-leg orchestration are not verified.
  The WebSocket route refuses connections unless
  `EXOTEL_AGENTSTREAM_PROTOCOL_VERIFIED=true` is explicitly set after account-
  specific documentation review and live protocol tests. It is not enabled in
  the deployed environment.
- The media WebSocket route is `/api/calls/media/{role}`. It is not yet wired
  to ExoML leg creation, bridge membership, or public TLS hosting.
- Exotel credentials and the media token are read only from backend environment
  variables. No secrets belong in the frontend or Git.
- Outbound calling remains deliberately blocked. No PSTN call can be placed
  by this build.

Required backend environment variables (keep values in `backend/.env` only):
`EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`, `EXOTEL_ACCOUNT_SID`,
`EXOTEL_CALLER_ID`, `EXOTEL_STREAM_URL`, and `EXOTEL_MEDIA_TOKEN`.
Keep `EXOTEL_AGENTSTREAM_PROTOCOL_VERIFIED=false` until Exotel confirms the
account-specific protocol and incoming/outgoing audio tests pass. Keep
`ENABLE_OUTBOUND_CALLS=false` until the live media bridge, consent
disclosure, abuse protection, and call-cost limits are ready.

The critical next engineering task is to keep each participant's audio
separate, translate each direction independently, and inject translated
audio only into the opposite participant's call leg. A single mixed call
recording is not sufficient for reliable bidirectional translation.

## Hackathon demo

See [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md) for startup steps, test utterances, and an accurate description of what the current prototype does and does not demonstrate. See [ANDROID_SETUP.md](ANDROID_SETUP.md) for Android build and installation instructions.

GitHub Actions runs backend API tests, a frontend production build, and an Android debug APK build on pushes and pull requests to `main`. The Android APK is uploaded as the `vaanisetu-android-debug` workflow artifact when the build succeeds.

## Planned milestones

1. Repository and application foundation.
2. Microphone capture and speech recognition.
3. Telugu ↔ Hindi translation and voice generation.
4. Two-participant browser conversation.
5. Streaming, noise, accent, mixed-language and latency testing.
6. Deployment and demo hardening.

## License

No license has been selected yet.
