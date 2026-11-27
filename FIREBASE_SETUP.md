# Firebase Authentication setup

VaaniSetu uses Firebase Authentication for Android phone-number sign-in and an email/password identity linked to the same account. The Android app obtains Firebase ID tokens; FastAPI verifies those tokens with Firebase Admin before allowing speech transcription, translation, TTS, or call initiation.

## Firebase project configuration

Project: `vaanisetu-e395b`
Android package: `com.vaanisetu.app`

In Firebase Console → Project settings → General → Your apps → Android app, confirm these debug fingerprints are registered:

- SHA-1: `A8:AD:7A:C8:4A:F8:EA:96:69:E6:71:A3:6D:4F:ED:9F:69:74:5E:50`
- SHA-256: `7E:E7:DD:8E:93:20:F8:1E:F5:41:34:7E:80:2C:77:B6:94:74:DC:3F:E0:B4:65:92:C6:28:D8:61:67:1D:16:49`

Both fingerprints were visible in the Firebase Android app settings during setup. The Android `google-services.json` belongs at `frontend/android/app/google-services.json` and is intentionally excluded from Git.

In Authentication → Sign-in method, enable:

- Phone
- Email/Password

Both were confirmed enabled in the Firebase Console on 27 November 2026. New Firebase projects currently show a 10-SMS-per-day quota; do not add billing without approval.

## Test phone numbers (no real SMS)

Before testing on a physical device without consuming SMS quota, open Authentication → Sign-in method → Phone → Phone numbers for testing. Add a dedicated test number and a fixed six-digit test code. Use only a number you control and never use a real user's number as a test credential. Firebase test numbers do not send SMS and are intended for development only. Remove or rotate them before production.

## Firebase Admin service account for the API

The backend requires the service account JSON as the secret environment variable `FIREBASE_SERVICE_ACCOUNT_JSON`. Generate a private key from Firebase Console → Project settings → Service accounts → Generate new private key. Store the downloaded JSON securely. Do not commit it, put it in the Android app, paste it into source code, or send it in chat.

For local development, set `FIREBASE_SERVICE_ACCOUNT_JSON` in `backend/.env` to the complete JSON object on one line. For Render, add the same variable as a secret in the `vaanisetu-api` service Environment settings. The Render blueprint declares this variable with `sync: false`; it must be populated privately in the Render dashboard.

After setting the secret, redeploy the Render service and check `/health`. The health endpoint intentionally does not expose credential contents. A protected endpoint without a bearer token should return HTTP 401. A protected endpoint with a valid Firebase ID token should proceed to its application logic.

## Security behavior

- `/health`, `/`, `/api/languages`, and `/api/calls/provider-status` remain public read-only diagnostics.
- Speech transcription, translation, speech synthesis, and call initiation require `Authorization: Bearer <Firebase ID token>`.
- Exotel's HTTPS event callback uses its separate HTTP Basic credential gate.
- Exotel's media WebSocket uses its separate high-entropy media token gate.
- Outbound PSTN calling remains disabled until Exotel confirms account-specific event/media protocol and a real end-to-end test passes.

## Release checklist

- [ ] Add India (+91) to the Firebase Phone Authentication SMS region allowlist if the console requires an explicit region policy.
- [ ] Add a development test phone number and fixed test code.
- [ ] Keep Firebase service-account JSON private and set `FIREBASE_SERVICE_ACCOUNT_JSON` in Render.
- [ ] Deploy the latest `main` commit and verify valid/invalid token behavior.
- [ ] Install the current debug APK and test phone sign-in and email linking using the Firebase test number.
- [ ] Test a real SMS only after confirming the quota and any billing requirements. Never enable billing automatically.
- [ ] Before production, add per-user rate limits and usage limits for paid Sarvam requests.
