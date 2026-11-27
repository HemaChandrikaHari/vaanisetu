# VaaniSetu

**Speak your language. Let everyone understand you.**

VaaniSetu is a voice-first, bidirectional translation prototype for conversations across Indian languages. The long-term target is all 22 scheduled Indian languages; the initial end-to-end pair is Telugu ↔ Hindi.

## Project status

### Implemented
- React + Vite frontend and Python + FastAPI backend.
- Demo/live configuration scaffolding.
- Browser microphone recording (up to 25 seconds per turn).
- Server-side Sarvam Saaras v4 speech-to-text integration.
- Language selector populated from a 22-language registry.
- Audio preview and transcript display.
- Uploaded audio is processed in memory by this app and is not written to disk.

### Not implemented yet
- Text translation.
- Text-to-speech.
- Two-participant conversation rooms.
- WebRTC / continuous streaming.
- Cellular phone-call integration.

## Architecture

```text
Browser microphone -> React -> FastAPI -> Sarvam Saaras v4 -> transcript
```

The first speech milestone uses short turns. Sarvam's synchronous speech-to-text REST API accepts clips up to 30 seconds; the UI caps recordings at 25 seconds. Streaming will follow after short-turn processing is validated.

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

The app starts in demo mode without credentials. In demo mode, the microphone can record and preview a short clip locally, but audio is not sent to Sarvam. No transcript is fabricated or presented as AI output.

To enable real transcription, create a Sarvam API key in the Sarvam dashboard, then edit `backend/.env`:

```env
APP_MODE=live
SARVAM_API_KEY=your_key_here
FRONTEND_ORIGINS=http://localhost:5173
```

Restart the backend after changing environment variables. The browser sends audio to the VaaniSetu backend; the backend calls Sarvam. The API key is never sent to the browser.

## API endpoints

- `GET /` — service status.
- `GET /health` — backend mode and provider configuration status.
- `GET /api/languages` — supported speech/translation language codes.
- `POST /api/speech/transcribe?language_code=te-IN` — transcribe a short audio upload using Saaras v4.

## Language capability note

The language registry reflects Sarvam's current Saaras v4 speech recognition and Sarvam Translate v1 language lists. Text-to-speech has a different supported-language set; do not assume all 22 languages are available for generated voice until validated separately.

## Privacy and safety

The application does not persist uploaded audio to disk. In live mode, the audio clip is transmitted to Sarvam AI for transcription, subject to that provider's terms and privacy practices. Obtain clear consent before recording or processing another person's speech. Do not use this prototype for emergency or high-stakes medical communication.

## Planned milestones

1. Repository and application foundation.
2. Microphone capture and speech recognition.
3. Telugu ↔ Hindi translation.
4. Translated speech generation.
5. Two-participant browser conversation.
6. Noise, accent, mixed-language and latency testing.

## License

No license has been selected yet.
