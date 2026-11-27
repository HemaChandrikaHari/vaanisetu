# VaaniSetu

**Speak your language. Let everyone understand you.**

VaaniSetu is a voice-first, bidirectional translation prototype for conversations across Indian languages. The long-term target is all 22 scheduled Indian languages; the first complete voice path is Telugu → Hindi.

## Project status

### Implemented
- React + Vite frontend and Python + FastAPI backend.
- Demo/live configuration scaffolding.
- Browser microphone recording (up to 25 seconds per turn).
- Server-side Sarvam Saaras v4 speech-to-text integration.
- Sarvam Translate v1 text translation integration.
- Sarvam Bulbul v4 Flash text-to-speech integration.
- Language selector populated from a 22-language speech/translation registry.
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

## Language capability note

Saaras v4 speech recognition and Sarvam Translate v1 support all 22 scheduled Indian languages. Bulbul TTS currently supports 11 languages: Bengali, English (India), Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Punjabi, Tamil and Telugu. The UI therefore allows all supported source languages but only offers currently supported TTS target languages.

## Privacy and safety

The application does not persist uploaded audio to disk. In live mode, the audio clip and text are transmitted to Sarvam AI for processing, subject to that provider's terms and privacy practices. Obtain clear consent before recording or processing another person's speech. Do not use this prototype for emergency or high-stakes medical communication.

## Planned milestones

1. Repository and application foundation.
2. Microphone capture and speech recognition.
3. Telugu ↔ Hindi translation and voice generation.
4. Two-participant browser conversation.
5. Streaming, noise, accent, mixed-language and latency testing.
6. Deployment and demo hardening.

## License

No license has been selected yet.
