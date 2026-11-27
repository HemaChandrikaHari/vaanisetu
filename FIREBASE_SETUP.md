# Firebase Authentication Setup — VaaniSetu

This project uses the Capawesome Capacitor Firebase Authentication plugin (Capacitor 8) for email/password sign-in with mandatory email verification. The registration form also collects a mobile number as contact information; it is not SMS-verified.

## 1. Firebase project

Project ID: `vaanisetu-e395b`

## 2. Android app registration

- Android package name: `com.vaanisetu.app`
- App nickname: `VaaniSetu Android`

The following debug signing fingerprints are registered in Firebase Android app settings:

- SHA-1: `A8:AD:7A:C8:4A:F8:EA:96:69:E6:71:A3:6D:4F:ED:9F:69:74:5E:50`
- SHA-256: `7E:E7:DD:8E:93:20:F8:1E:F5:41:34:7E:80:2C:77:B6:94:74:DC:3F:E0:B4:65:92:C6:28:D8:61:67:1D:16:49`

These are for the current local debug signing key. A separate release/Play App Signing fingerprint will be needed before public Play Store distribution.

## 3. Firebase Android configuration file

The `google-services.json` file is placed at:

```
frontend/android/app/google-services.json
```

Do not rename the file or put it in the frontend root. It is intentionally excluded from Git. Do not paste its contents into chat.

## 4. Authentication providers

In Firebase Console > Authentication > Sign-in method, enable **Email/Password**. The app creates an email/password account and sends Firebase's built-in email verification link. The user must verify the address before protected VaaniSetu APIs will accept the Firebase ID token.

Phone Authentication is no longer used by the current app flow. Do not enable Firebase billing for SMS on behalf of this project. The mobile number field is collected as contact information only and is not proof of phone ownership. In this version it is stored locally on the device; cloud profile storage can be added separately if cross-device access is required.

## 5. Firebase Admin service account for backend verification

The backend uses Firebase Admin to verify the ID tokens sent by the Android app. It requires the complete service-account JSON as the secret environment variable `FIREBASE_SERVICE_ACCOUNT_JSON`.

Generate a private key from Firebase Console > Project settings > Service accounts > Generate new private key. Store the downloaded JSON securely. Do not commit it, put it in the Android app, paste it into source code, or send it in chat.

For local development, set `FIREBASE_SERVICE_ACCOUNT_JSON` in `backend/.env` to the complete JSON object on one line. For Render, add the same variable as a private secret in the `vaanisetu-api` service Environment settings. The Render blueprint declares this variable with `sync: false`; it must be populated privately in the Render dashboard.

After setting the secret, redeploy the Render service. The `/health` endpoint intentionally does not expose credential contents. A protected endpoint without a bearer token should return HTTP 401. A protected endpoint with a valid Firebase ID token should proceed to its application logic only when the token has `email_verified: true`; unverified email accounts receive HTTP 403.

## 6. Rebuild and test

From the `frontend` directory:

```powershell
npm.cmd run build
npx.cmd cap sync android
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.13.10002-hotspot'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
.\android\gradlew.bat -p android assembleDebug
```

The debug APK is generated at:

```
frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

Create a new account with an email address, open the Firebase verification email, return to the app and tap ?I've verified my email?. Confirm that an unverified account cannot access protected APIs and that a verified account can. No SMS should be sent.

## Security behavior

- Email/password is the sign-in method.
- Email verification is mandatory before access to the app and protected APIs.
- Mobile number is collected as contact information only; it is not SMS-verified.
- The recipient of a translated call does not need a VaaniSetu account.
- Speech transcription, translation, speech synthesis, and call initiation require `Authorization: Bearer <Firebase ID token>`.
- `/health`, `/`, `/api/languages`, and `/api/calls/provider-status` remain public read-only diagnostics.
- Exotel's HTTPS event callback uses its separate HTTP Basic credential gate.
- Exotel's media WebSocket uses its separate high-entropy media token gate.
- Outbound PSTN calling remains disabled until Exotel confirms account-specific event/media protocol and a real end-to-end test passes.

## Release checklist

- [ ] Confirm Email/Password is enabled in Firebase Authentication.
- [ ] Test email verification and protected API rejection for unverified accounts.
- [ ] Keep Firebase service-account JSON private and set `FIREBASE_SERVICE_ACCOUNT_JSON` in Render.
- [ ] Deploy the latest `main` commit and verify valid/invalid token behavior.
- [ ] Install the current debug APK and test registration, email verification, sign-in, and sign-out.
- [ ] Confirm no SMS is sent and Firebase billing remains disabled.
- [ ] Add per-user rate limits and usage limits for paid Sarvam requests before public launch.
