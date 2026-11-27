# Firebase Authentication Setup — VaaniSetu

This project uses the Capawesome Capacitor Firebase Authentication plugin (Capacitor 8) for native Android phone-number sign-in and email/password account linking.

## 1. Create a Firebase project

1. Open https://console.firebase.google.com/
2. Sign in with an account you control.
3. Select **Create a project** and name it **VaaniSetu**.
4. Google Analytics is not required for authentication; you can leave it off.

## 2. Register the Android app

In the Firebase project overview, choose **Add app** → Android.

- Android package name: `com.vaanisetu.app`
- App nickname: `VaaniSetu Android`

Add these debug signing certificate fingerprints under the Android app settings:

- SHA-1: `A8:AD:7A:C8:4A:F8:EA:96:69:E6:71:A3:6D:4F:ED:9F:69:74:5E:50`
- SHA-256: `7E:E7:DD:8E:93:20:F8:1E:F5:41:34:7E:80:2C:77:B6:94:74:DC:3F:E0:B4:65:92:C6:28:D8:61:67:1D:16:49`

These are for the current local debug signing key. A separate release/Play App Signing fingerprint will be needed before public Play Store distribution.

## 3. Add the Firebase Android configuration file

1. Download `google-services.json` from the Firebase Android app setup screen.
2. Place it at:

```
frontend/android/app/google-services.json
```

Do not rename the file or put it in the frontend root. Do not paste its contents into chat.

## 4. Enable authentication providers

In Firebase Console → **Authentication** → **Get started** → **Sign-in method**:

- Enable **Phone**.
- Enable **Email/Password**.

Then open Authentication → **Settings** → **SMS region policy** and allow **India**. New Firebase projects may block all SMS regions until you explicitly configure this policy.

For development, you can configure Firebase test phone numbers and fixed test codes in the Phone provider settings. Use those before sending real SMS messages.

## 5. Rebuild and test

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

Test a Firebase test phone number first. Then test a real phone number only after checking the current Firebase SMS limits and pricing.

## Current implementation notes

- Phone number is the primary verified sign-in method.
- Email/password is linked to the same Firebase user after phone verification.
- The recipient of a translated call does not need a VaaniSetu account.
- The Firebase Android config file is intentionally not committed to the repository.
- Backend endpoints are not yet enforcing Firebase ID-token authentication. That server-side authorization layer is a separate hardening task before public launch.
