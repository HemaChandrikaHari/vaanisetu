import asyncio
from io import BytesIO

from starlette.datastructures import Headers, UploadFile

from app.config import settings
from app.speech import transcribe_audio
from app.translation import TranslationRequest, translate_text
from app.tts import SpeechSynthesisRequest, synthesize_speech


async def main():
    if settings.app_mode != "live" or not settings.sarvam_api_key:
        raise SystemExit("Live mode or API key is not configured.")

    print("1/3 Generate Hindi test speech...")
    source_audio = await synthesize_speech(
        SpeechSynthesisRequest(
            text="नमस्ते, आप कैसे हैं? मुझे स्टेशन जाने का रास्ता बताइए।",
            language_code="hi-IN",
        )
    )
    print(f"   Hindi WAV generated: {len(source_audio.body)} bytes")

    print("2/3 Transcribe Hindi audio...")
    upload = UploadFile(
        file=BytesIO(source_audio.body),
        filename="vaanisetu_hindi_test.wav",
        headers=Headers({"content-type": "audio/wav"}),
    )
    stt = await transcribe_audio(file=upload, language_code="hi-IN")
    transcript = stt["transcript"]
    print(f"   Transcript: {transcript}")
    if not transcript.strip():
        raise RuntimeError("Speech recognition returned an empty transcript.")

    print("3/3 Translate Hindi to Telugu and synthesize Telugu speech...")
    translated = await translate_text(
        TranslationRequest(
            text=transcript,
            source_language_code="hi-IN",
            target_language_code="te-IN",
        )
    )
    telugu_text = translated["translated_text"]
    print(f"   Telugu translation: {telugu_text}")
    telugu_audio = await synthesize_speech(
        SpeechSynthesisRequest(text=telugu_text, language_code="te-IN")
    )
    print(f"   Telugu WAV generated: {len(telugu_audio.body)} bytes")
    if not telugu_audio.body.startswith(b"RIFF"):
        raise RuntimeError("Telugu output is not a valid WAV file.")

    print("PIPELINE_RESULT=PASS")
    print("Hindi TTS -> Hindi ASR -> Hindi-to-Telugu translation -> Telugu TTS all succeeded.")


if __name__ == "__main__":
    asyncio.run(main())
