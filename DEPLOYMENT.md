## Deploy the API for Android testing

A Render Blueprint is included in `render.yaml`. To deploy:

1. Sign in to Render and choose **New → Blueprint**.
2. Connect `HemaChandrikaHari/vaanisetu` and select the `main` branch.
3. Review the `vaanisetu-api` service. Keep outbound calls disabled.
4. When prompted, enter the Sarvam API key as the secret value for `SARVAM_API_KEY`. Never commit it to GitHub or put it in the Android app.
5. Deploy. Wait for the service health check to pass at `/health`.
6. Copy the service's HTTPS URL into VaaniSetu → Phone call → Backend URL on the Android app. The translation tab uses the same backend URL.

The free service is intended for hackathon testing and may sleep when idle, causing a cold start. Do not use a sleeping free instance for production calling. The Exotel PSTN bridge is still incomplete and outbound calls remain disabled; this deployment only makes the existing short-turn Sarvam translation API reachable from the phone.
