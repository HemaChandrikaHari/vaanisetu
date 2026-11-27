import asyncio
from io import BytesIO
from starlette.datastructures import Headers, UploadFile
from app.config import settings
from app.tts import SpeechSynthesisRequest, synthesize_speech
from app.speech import transcribe_audio
from app.translation import TranslationRequest, translate_text

async def main():
    if settings.app_mode != "live" or not settings.sarvam_api_key:
        raise SystemExit("Live mode or API key is not configured.")
    print("1/3 Generate Telugu test speech...")
    source_audio = await synthesize_speech(SpeechSynthesisRequest(
        text="నమస్కారం, మీరు ఎలా ఉన్నారు? నాకు సహాయం కావాలి.",
        language_code="te-IN",
    ))
    print(f"   Telugu WAV generated: {len(source_audio.body)} bytes")

    print("2/3 Transcribe Telugu audio...")
    upload = UploadFile(
        file=BytesIO(source_audio.body),
        filename="vaanisetu_telugu_test.wav",
        headers=Headers({"content-type": "audio/wav"}),
    )
    stt = await transcribe_audio(file=upload, language_code="te-IN")
    transcript = stt["transcript"]
    print(f"   Transcript: {transcript}")
    if not transcript.strip():
        raise RuntimeError("Speech recognition returned an empty transcript.")

    print("3/3 Translate Telugu to Hindi and synthesize Hindi speech...")
    translated = await translate_text(TranslationRequest(
        text=transcript,
        source_language_code="te-IN",
        target_language_code="hi-IN",
    ))
    hindi_text = translated["translated_text"]
    print(f"   Hindi translation: {hindi_text}")
    hindi_audio = await synthesize_speech(SpeechSynthesisRequest(
        text=hindi_text,
        language_code="hi-IN",
    ))
    print(f"   Hindi WAV generated: {len(hindi_audio.body)} bytes")
    if not hindi_audio.body.startswith(b"RIFF"):
        raise RuntimeError("Hindi output is not a valid WAV file.")
    print("PIPELINE_RESULT=PASS")
    print("Telugu TTS -> Telugu ASR -> Telugu-to-Hindi translation -> Hindi TTS all succeeded.")

asyncio.run(main())
