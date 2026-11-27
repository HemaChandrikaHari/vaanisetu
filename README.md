# VaaniSetu

**Speak your language. Let everyone understand you.**

VaaniSetu is a voice-first, bidirectional translation prototype for conversations across Indian languages. The first target flow is Telugu ↔ Hindi.

## Project status

This repository contains the initial application foundation. The current milestone provides:
- A React + Vite frontend scaffold.
- A Python + FastAPI backend with a health endpoint.
- Demo/live configuration scaffolding.
- Environment-variable based secret handling.

**Speech recognition, translation, text-to-speech and two-person audio are not implemented yet.** They will be added in subsequent milestones. The app does not currently translate live speech.

## Architecture

```text
Browser microphone
      |
      v
React frontend  <---- HTTP / future WebSocket ---->  FastAPI backend
                                                        |
                                                        v
                                                AI provider adapters
                                                - Sarvam ASR
                                                - Sarvam Translate
                                                - Sarvam TTS
```

For the first working speech milestone, we will process short speech turns. Streaming and WebRTC will follow after the basic speech pipeline is validated.

## Requirements

- Node.js 20+
- Python 3.10+
- Git

## Run locally

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

The backend health endpoint is available at http://localhost:8000/health and API docs at http://localhost:8000/docs.

### 2. Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite prints the local frontend URL (usually http://localhost:5173).

## Configuration

The backend reads its configuration from environment variables. Copy `.env.example` to `.env` inside `backend/`.

- `APP_MODE=demo` starts without provider credentials.
- `APP_MODE=live` is reserved for real Sarvam API calls once the provider adapter is implemented.
- `SARVAM_API_KEY` must remain on the backend and must never be exposed through a `VITE_*` variable.

Never commit `.env`, API keys, access tokens or other secrets.

## Languages

Initial language pair:
- Telugu (`te-IN`)
- Hindi (`hi-IN`)

## Planned milestones

1. Repository and application foundation.
2. Microphone capture and speech recognition.
3. Telugu ↔ Hindi translation.
4. Translated speech generation.
5. Two-participant browser conversation.
6. Noise, accent, mixed-language and latency testing.

## Privacy and safety

The prototype should obtain clear consent before capturing or processing speech. Audio should not be permanently stored by default. Do not use this prototype for emergency or high-stakes medical communication.

## License

No license has been selected yet.
