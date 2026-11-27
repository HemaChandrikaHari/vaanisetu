# VaaniSetu hackathon demo runbook

## Honest product status

The tested milestone is a mobile-friendly, turn-based speech translator:

1. The user records a short utterance in one supported language.
2. Sarvam Saaras v4 transcribes it.
3. Sarvam Translate v1 translates the text.
4. Sarvam Bulbul v4 Flash generates spoken output in a supported target language.
5. The user can reverse the language direction and repeat.

Telugu → Hindi and Hindi → Telugu have been tested successfully in the installed Android app. This is not continuous simultaneous interpretation and is not yet a PSTN phone call. The intended phone-call experience is to keep the user's existing Android Phone app and route selected outgoing calls through VaaniSetu. The Android 10+ call-redirection permission foundation is now implemented, including saving a preferred language direction. The current service still passes every outgoing call through unchanged; Exotel gateway routing and translated two-way call audio are not implemented or enabled yet. Android does not guarantee a universal "Call with VaaniSetu" button in every OEM dialler.

## Pre-demo checklist

- [ ] Open the installed VaaniSetu Android app.
- [ ] Confirm the backend URL is `https://vaanisetu-api.onrender.com`.
- [ ] Confirm the backend health endpoint is available: `https://vaanisetu-api.onrender.com/health`.
- [ ] Confirm the response says `status: ok`, `mode: live`, and `sarvam_configured: true`. Never show or share API keys.
- [ ] Grant microphone permission when Android asks.
- [ ] Read and accept the disclosure that audio and transcript text are sent to Sarvam for processing.
- [ ] Test Telugu → Hindi with a short, clear sentence.
- [ ] Test Hindi → Telugu using the direction swap control.
- [ ] Confirm the transcript, translated text, and generated speech are all correct and audible.
- [ ] Keep each utterance short (about 5–10 seconds) and pause between turns.
- [ ] Use a quiet room and headphones where possible. Have a mobile hotspot or backup network available.

## Suggested test phrases

**Telugu → Hindi**

`నమస్కారం, మీరు ఎలా ఉన్నారు? నాకు సహాయం కావాలి.`

**Hindi → Telugu**

`नमस्ते, आप कैसे हैं? मुझे स्टेशन जाने का रास्ता बताइए।`

Also try one unscripted phrase in each direction so the demo is not limited to memorised examples.

## What to measure during testing

Record at least five turns per direction:

| Metric | How to record |
|---|---|
| Recognition | Did the transcript preserve the spoken meaning? |
| Translation | Is the translated sentence natural and correct? |
| Speech output | Is the voice understandable and complete? |
| Turn latency | Seconds from pressing stop to translated audio becoming playable |
| Reliability | Successful turns divided by total attempts |

Do not invent accuracy or latency percentages. Report only measured results and note the test conditions (device, network, room noise, phrase length).

## Suggested 60-second presentation

"VaaniSetu aims to remove language barriers in everyday conversations across India. A Telugu speaker should be able to call a Hindi speaker, speak naturally in Telugu, and have the other person hear Hindi; replies should come back in Telugu. The recipient should not need to install an app. We have already built and tested the core Telugu–Hindi speech pipeline on Android using Sarvam speech recognition, translation, and text-to-speech. The next milestone is the telephony bridge. We are working with Exotel to confirm the account-specific two-leg calling and bidirectional audio-streaming interface before enabling real calls."

## Privacy, safety and limitations

- In live mode, microphone audio is sent to the VaaniSetu backend and then to Sarvam for processing. Do not claim the audio stays only on the phone.
- The current app processes short turns; it is not continuous full-duplex interpretation. Expect a pause while transcription, translation and speech generation complete.
- Do not use the prototype for emergency, medical, legal, financial, or other high-stakes communication.
- Get clear consent before processing another person's speech.
- Keep Exotel outbound calling disabled. The ExoML two-leg controller, account-specific AgentStream codec/protocol validation, public WSS deployment, and real-call tests are still pending.
- Do not describe the current build as an ordinary cellular-call translator. The intended call flow must be initiated inside VaaniSetu.
