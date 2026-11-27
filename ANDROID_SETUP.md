# VaaniSetu Android app

VaaniSetu now has a Capacitor Android project wrapping the React interface. It includes a mobile Translate / Phone call tab bar, microphone permission declaration, PWA manifest and offline app-shell caching.

## Important current limitations

- The Android app is a Capacitor shell around the web UI, with a small native Kotlin/Java integration layer.
- The Translate tab uses the existing short-turn Sarvam pipeline.
- Android 10+ call-redirection role support is now registered. The app can request the Android call-redirection role and save the preferred source/target languages.
- The redirection service deliberately passes every outgoing call through unchanged. It does not yet route calls to Exotel because ExoML two-leg orchestration and the bidirectional media protocol are not verified.
- Android does not provide a universal "Call with VaaniSetu" chooser button inside every manufacturer's Phone app. The current milestone is the Android call-redirection role foundation, not a finished OEM dialler add-on.
- An installed Android app cannot use `localhost` to reach the backend running on your PC. Configure a reachable backend URL in Phone call → Backend server URL. Use HTTPS for a public server.
- The app does not contain Sarvam or Exotel API keys. Provider credentials remain on the backend only.

## Android call-redirection foundation

1. Install the VaaniSetu APK on Android 10 or newer.
2. Open VaaniSetu → Phone call.
3. Choose the language you speak and the language the other person speaks, then save the direction.
4. Tap **Enable Android call integration** and approve the Android call-redirection permission prompt.
5. Confirm the app reports that Android call-redirection access is granted.
6. Place an ordinary outgoing call and verify it behaves normally. This build must not reroute any call.

The system may invoke VaaniSetu for outgoing-call routing decisions after the role is granted. The current service intentionally calls `placeCallUnmodified()` in all cases. The actual gateway routing must not be enabled until Exotel confirms the account permissions, call-leg workflow, audio codec, WebSocket event format, and translated-audio injection method. The Android API also has a short response deadline, so language selection is saved in advance rather than shown as a blocking prompt during call placement.

This integration does not replace the default Phone app. OEM Phone apps differ, so a dedicated per-call "Call with VaaniSetu" menu item is not guaranteed by Android's call-redirection role.

## Android build prerequisites

- Node.js 22 or newer
- JDK 21
- Android SDK Platform 36
- Android SDK Build Tools 34 or newer
- Android SDK Command-line Tools

Set `JAVA_HOME` to the JDK 21 folder and `ANDROID_HOME` to your Android SDK folder. Accept Android SDK licences before building.

## Build and open the Android project

From the `frontend` directory:

```powershell
npm ci
npm run android:sync
npm run android:open
```

In Android Studio, wait for Gradle sync, connect an Android device with USB debugging enabled or start an emulator, then run the `app` configuration.

To build a debug APK from PowerShell:

```powershell
cd android
.\gradlew.bat assembleDebug
```

The APK is generated at:

`frontend/android/app/build/outputs/apk/debug/app-debug.apk`

## Backend URL configuration

For an installed app, deploy the FastAPI backend to a public HTTPS host, then open the Phone call tab and save the backend URL. The backend must allow the Capacitor origin `https://localhost` (already included in this project) and your web origin if using the PWA.

For local USB/Wi-Fi testing only, the phone and PC must share a network, the backend must bind to `0.0.0.0`, Windows Firewall must allow the backend port, and the app must use the PC's LAN IP. Avoid exposing the development server to public networks.

## Install as a web app

When hosted over HTTPS, open the VaaniSetu site in Chrome on Android and choose **Install app** / **Add to Home screen**. The PWA caches its static app shell and same-origin app assets; API requests and audio are not cached.
