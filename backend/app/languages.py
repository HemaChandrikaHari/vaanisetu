"""Language capabilities exposed by Sarvam's current model APIs.

ASR, translation, and TTS do not have identical language coverage.
"""
SUPPORTED_LANGUAGES = [
    {"code": "as-IN", "name": "Assamese"}, {"code": "bn-IN", "name": "Bengali"},
    {"code": "brx-IN", "name": "Bodo"}, {"code": "doi-IN", "name": "Dogri"},
    {"code": "gu-IN", "name": "Gujarati"}, {"code": "hi-IN", "name": "Hindi"},
    {"code": "kn-IN", "name": "Kannada"}, {"code": "ks-IN", "name": "Kashmiri"},
    {"code": "kok-IN", "name": "Konkani"}, {"code": "mai-IN", "name": "Maithili"},
    {"code": "ml-IN", "name": "Malayalam"}, {"code": "mni-IN", "name": "Manipuri (Meitei)"},
    {"code": "mr-IN", "name": "Marathi"}, {"code": "ne-IN", "name": "Nepali"},
    {"code": "od-IN", "name": "Odia"}, {"code": "pa-IN", "name": "Punjabi"},
    {"code": "sa-IN", "name": "Sanskrit"}, {"code": "sat-IN", "name": "Santali"},
    {"code": "sd-IN", "name": "Sindhi"}, {"code": "ta-IN", "name": "Tamil"},
    {"code": "te-IN", "name": "Telugu"}, {"code": "ur-IN", "name": "Urdu"},
]
LANGUAGE_CODES = {language["code"] for language in SUPPORTED_LANGUAGES}

# Bulbul TTS supports a smaller set than Saaras ASR / Sarvam Translate.
TTS_LANGUAGES = [
    {"code": "bn-IN", "name": "Bengali"}, {"code": "en-IN", "name": "English (India)"},
    {"code": "gu-IN", "name": "Gujarati"}, {"code": "hi-IN", "name": "Hindi"},
    {"code": "kn-IN", "name": "Kannada"}, {"code": "ml-IN", "name": "Malayalam"},
    {"code": "mr-IN", "name": "Marathi"}, {"code": "od-IN", "name": "Odia"},
    {"code": "pa-IN", "name": "Punjabi"}, {"code": "ta-IN", "name": "Tamil"},
    {"code": "te-IN", "name": "Telugu"},
]
TTS_LANGUAGE_CODES = {language["code"] for language in TTS_LANGUAGES}
