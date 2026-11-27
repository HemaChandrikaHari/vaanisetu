# VaaniSetu Android app

VaaniSetu now has a Capacitor Android project wrapping the React interface. It includes a mobile Translate / Phone call tab bar, microphone permission declaration, PWA manifest and offline app-shell caching.

## Important current limitations

- The Android app is a native Android shell around the web UI, not a native Kotlin rewrite.
- The Translate tab uses the existing short-turn Sarvam pipeline.
- The Phone call tab is intentionally disabled until Exotel ExoML call orchestration and the public bidirectional media bridge are verified.
- An installed Android app cannot use `localhost` to reach the backend running on your PC. Configure a reachable backend URL in Phone call → Backend server URL. Use HTTPS for a public server.
- The app does not contain Sarvam or Exotel API keys. Provider credentials remain on the backend only.

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
