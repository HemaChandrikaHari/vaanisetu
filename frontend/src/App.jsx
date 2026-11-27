import { useEffect, useRef, useState } from "react";
import { registerPlugin } from "@capacitor/core";

const CallRedirection = registerPlugin("CallRedirection");

const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const MAX_RECORDING_SECONDS = 25;

export default function App() {
  const [apiBase, setApiBase] = useState(() => localStorage.getItem("vaanisetu_api_base") || DEFAULT_API_BASE);
  const [apiBaseDraft, setApiBaseDraft] = useState(() => localStorage.getItem("vaanisetu_api_base") || DEFAULT_API_BASE);
  const [backend, setBackend] = useState(null);
  const [languages, setLanguages] = useState([]);
  const [ttsLanguages, setTtsLanguages] = useState([]);
  const [languageCode, setLanguageCode] = useState("te-IN");
  const [targetLanguageCode, setTargetLanguageCode] = useState("hi-IN");
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [busy, setBusy] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [translatedText, setTranslatedText] = useState("");
  const [notice, setNotice] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [translatedAudioUrl, setTranslatedAudioUrl] = useState("");
  const [privacyConsent, setPrivacyConsent] = useState(false);
  const [activeTab, setActiveTab] = useState("translate");
  const [callStatus, setCallStatus] = useState(null);
  const [androidCallStatus, setAndroidCallStatus] = useState(null);
  const [androidCallBusy, setAndroidCallBusy] = useState(false);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    fetch(`${apiBase}/health`)
      .then((response) => {
        if (!response.ok) throw new Error("Backend unavailable");
        return response.json();
      })
      .then(setBackend)
      .catch(() => setBackend({ status: "offline" }));

    fetch(`${apiBase}/api/languages`)
      .then((response) => response.json())
      .then((data) => {
        setLanguages(data.languages || []);
        setTtsLanguages(data.tts_languages || []);
      })
      .catch(() => setLanguages([]));

    fetch(`${apiBase}/api/calls/provider-status`)
      .then((response) => response.ok ? response.json() : null)
      .then(setCallStatus)
      .catch(() => setCallStatus(null));

    if (window.Capacitor?.isNativePlatform?.()) {
      CallRedirection.getStatus().then(setAndroidCallStatus).catch(() => setAndroidCallStatus({ supported: false }));
    }

    return () => {
      window.clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, [apiBase]);

  function saveApiBase() {
    try {
      const parsed = new URL(apiBaseDraft.trim());
      if (!["https:", "http:"].includes(parsed.protocol)) throw new Error("Use an HTTP or HTTPS backend URL.");
      if (parsed.protocol === "http:" && !["localhost", "127.0.0.1"].includes(parsed.hostname) && !/^192\.168\./.test(parsed.hostname) && !/^10\./.test(parsed.hostname)) {
        throw new Error("Use HTTPS for public backend servers.");
      }
      const clean = parsed.origin.replace(/\/$/, "");
      localStorage.setItem("vaanisetu_api_base", clean);
      setApiBase(clean);
      setNotice("Backend address saved. Reconnecting…");
    } catch (error) {
      setNotice(error.message || "Enter a valid backend URL.");
    }
  }

  async function startRecording() {
    setNotice("");
    if (liveReady && !privacyConsent) {
      setNotice("Please confirm that you understand your recording and transcript will be sent to Sarvam AI for processing.");
      return;
    }
    setTranscript("");
    setTranslatedText("");
    if (translatedAudioUrl) URL.revokeObjectURL(translatedAudioUrl);
    setTranslatedAudioUrl("");
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setNotice("Your browser does not support microphone recording. Try a recent version of Chrome or Edge over localhost or HTTPS.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const preferredType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType: preferredType });
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data?.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        setAudioUrl((oldUrl) => {
          if (oldUrl) URL.revokeObjectURL(oldUrl);
          return URL.createObjectURL(blob);
        });
        await submitAudio(blob);
      };
      recorder.start(250);
      setRecording(true);
      setSeconds(0);
      timerRef.current = window.setInterval(() => {
        setSeconds((current) => {
          if (current + 1 >= MAX_RECORDING_SECONDS) {
            window.clearInterval(timerRef.current);
            if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
            setRecording(false);
            return MAX_RECORDING_SECONDS;
          }
          return current + 1;
        });
      }, 1000);
    } catch (error) {
      setNotice(error.name === "NotAllowedError"
        ? "Microphone permission was denied. Allow microphone access in your browser and try again."
        : "Could not access the microphone. Check that it is connected and try again.");
    }
  }

  function stopRecording() {
    window.clearInterval(timerRef.current);
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    setRecording(false);
  }

  async function submitAudio(blob) {
    if (backend?.mode !== "live" || !backend?.sarvam_configured) {
      setNotice("Recording captured locally. Demo mode does not send audio to an AI provider. To run real speech → translation → voice, configure SARVAM_API_KEY and APP_MODE=live in backend/.env.");
      return;
    }

    setBusy(true);
    try {
      setNotice("1/3 · Recognising your speech…");
      const form = new FormData();
      const extension = blob.type.includes("ogg") ? "ogg" : "webm";
      form.append("file", blob, `vaanisetu-recording.${extension}`);
      const speechResponse = await fetch(`${apiBase}/api/speech/transcribe?language_code=${encodeURIComponent(languageCode)}`, {
        method: "POST",
        body: form,
      });
      const speechData = await speechResponse.json();
      if (!speechResponse.ok) throw new Error(speechData.detail || "Speech recognition failed.");
      setTranscript(speechData.transcript);

      setNotice("2/3 · Translating the recognised text…");
      const translationResponse = await fetch(`${apiBase}/api/translation/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: speechData.transcript,
          source_language_code: languageCode,
          target_language_code: targetLanguageCode,
        }),
      });
      const translationData = await translationResponse.json();
      if (!translationResponse.ok) throw new Error(translationData.detail || "Translation failed.");
      setTranslatedText(translationData.translated_text);

      setNotice("3/3 · Generating the translated voice…");
      const ttsResponse = await fetch(`${apiBase}/api/speech/synthesize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: translationData.translated_text,
          language_code: targetLanguageCode,
        }),
      });
      if (!ttsResponse.ok) {
        const errorData = await ttsResponse.json();
        throw new Error(errorData.detail || "Speech generation failed.");
      }
      const audioBlob = await ttsResponse.blob();
      setTranslatedAudioUrl(URL.createObjectURL(audioBlob));
      setNotice("Done · Your translated voice is ready.");
    } catch (error) {
      setNotice(error.message || "The voice translation pipeline failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const backendOnline = backend?.status === "ok";
  const liveReady = backend?.mode === "live" && backend?.sarvam_configured;
  const canSwapLanguages = ttsLanguages.some((language) => language.code === languageCode);

  function swapLanguages() {
    if (!canSwapLanguages || recording || busy) return;
    setLanguageCode(targetLanguageCode);
    setTargetLanguageCode(languageCode);
    setTranscript("");
    setTranslatedText("");
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    if (translatedAudioUrl) URL.revokeObjectURL(translatedAudioUrl);
    setAudioUrl("");
    setTranslatedAudioUrl("");
    setNotice("Direction switched. You can now translate the other way.");
  }

  async function requestAndroidCallRole() {
    setAndroidCallBusy(true);
    try {
      const result = await CallRedirection.requestRole();
      const status = await CallRedirection.getStatus();
      setAndroidCallStatus(status);
      setNotice(result?.roleHeld ? "Android call-redirection permission is enabled." : "Android call-redirection permission was not granted.");
    } catch (error) {
      setNotice(error.message || "Could not request Android call-redirection permission.");
    } finally {
      setAndroidCallBusy(false);
    }
  }

  async function saveAndroidCallLanguages() {
    setAndroidCallBusy(true);
    try {
      await CallRedirection.saveLanguageDirection({ sourceLanguage: languageCode, targetLanguage: targetLanguageCode });
      const status = await CallRedirection.getStatus();
      setAndroidCallStatus(status);
      setNotice("Your preferred call language direction has been saved on this Android device.");
    } catch (error) {
      setNotice(error.message || "Could not save the call language direction.");
    } finally {
      setAndroidCallBusy(false);
    }
  }

  return (
    <main className="page-shell">
      <nav className="topbar">
        <a className="brand" href="/" aria-label="VaaniSetu home">
          <span className="brand-mark">వ</span><span>VaaniSetu</span>
        </a>
        <span className="status-pill">
          <span className={`status-dot ${backendOnline ? "connected" : "offline"}`} />
          API {backendOnline ? "connected" : "offline"}
        </span>
      </nav>
      <nav className="mobile-tabs" aria-label="Main navigation">
        <button type="button" className={activeTab === "translate" ? "active" : ""} onClick={() => setActiveTab("translate")}><span>◉</span> Translate</button>
        <button type="button" className={activeTab === "call" ? "active" : ""} onClick={() => setActiveTab("call")}><span>☎</span> Phone call</button>
      </nav>
      {activeTab === "translate" ? <section className="hero">
        <p className="eyebrow">VOICE-FIRST COMMUNICATION</p>
        <h1>Speak freely.<br /><span>Understand each other.</span></h1>
        <p className="intro">Speak in your language. VaaniSetu recognises your words, translates them and speaks them in another Indian language.</p>

        <section className="recorder-card" aria-label="Voice translation prototype">
          <div className="recorder-heading">
            <div><span className="field-label">VOICE TRANSLATION</span><h2>Try a voice translation</h2></div>
            <span className={`mode-label ${liveReady ? "live" : ""}`}>{liveReady ? "LIVE AI" : "DEMO MODE"}</span>
          </div>
          <label className="select-label" htmlFor="language">I will speak in</label>
          <select id="language" value={languageCode} onChange={(event) => setLanguageCode(event.target.value)} disabled={recording || busy}>
            {languages.map((language) => <option key={language.code} value={language.code}>{language.name} ({language.code})</option>)}
          </select>
          <label className="select-label" htmlFor="target-language">Translate and speak in</label>
          <select id="target-language" value={targetLanguageCode} onChange={(event) => setTargetLanguageCode(event.target.value)} disabled={recording || busy}>
            {ttsLanguages.map((language) => <option key={language.code} value={language.code}>{language.name} ({language.code})</option>)}
          </select>
          <button className="swap-button" type="button" onClick={swapLanguages} disabled={!canSwapLanguages || recording || busy}>
            ↕ Swap language direction
          </button>

          {liveReady && <label className="consent-row"><input type="checkbox" checked={privacyConsent} onChange={(event) => setPrivacyConsent(event.target.checked)} disabled={recording || busy} /><span>I understand my voice recording and transcript will be sent to Sarvam AI for processing. VaaniSetu does not save the audio to disk.</span></label>}
          <div className={`mic-orb ${recording ? "is-recording" : ""}`}><span className="mic-symbol">🎙</span></div>
          <p className="recording-caption">{recording ? `Listening… ${seconds}s / ${MAX_RECORDING_SECONDS}s` : busy ? "Processing your voice…" : "Tap below and speak naturally"}</p>
          {!recording ? (
            <button className="record-button" type="button" onClick={startRecording} disabled={busy || !backendOnline}>
              {busy ? "Processing…" : "Start speaking"}
            </button>
          ) : (
            <button className="record-button stop-button" type="button" onClick={stopRecording}>Stop and translate</button>
          )}

          {audioUrl && <audio className="audio-preview" controls src={audioUrl}>Your browser does not support audio playback.</audio>}
          {transcript && <div className="transcript-panel" aria-live="polite"><span className="field-label">ORIGINAL SPEECH</span><p lang={languageCode.split("-")[0]}>{transcript}</p></div>}
          {translatedText && <div className="translation-panel"><span className="field-label">TRANSLATED TEXT</span><p lang={targetLanguageCode.split("-")[0]}>{translatedText}</p></div>}
          {translatedAudioUrl && <div className="voice-result"><span className="field-label">TRANSLATED VOICE</span><audio controls src={translatedAudioUrl}>Your browser does not support audio playback.</audio></div>}
          {notice && <div className="notice" role="status"><span className="notice-icon">i</span><p>{notice}</p></div>}
        </section>
        <div className="privacy-note"><span>🔒</span><p>Audio is processed in memory by this backend and is not saved to disk by VaaniSetu. In live mode, the clip is sent to Sarvam AI for transcription. Translated text is sent to Sarvam for voice generation.</p></div>
      </section> : <section className="hero call-hero">
        <p className="eyebrow">ONE APP. TWO LANGUAGES. NO APP NEEDED FOR THE OTHER PERSON.</p>
        <h1>Make every<br /><span>conversation closer.</span></h1>
        <p className="intro">VaaniSetu is being built to work alongside your existing Android Phone app. The other person will answer a normal phone call and will not need to install VaaniSetu.</p>
        <section className="recorder-card call-card">
          <div className="recorder-heading"><div><span className="field-label">TRANSLATED PHONE CALL</span><h2>Set up your call</h2></div><span className="mode-label">ANDROID INTEGRATION</span></div>
          {window.Capacitor?.isNativePlatform?.() && <section className="android-integration-panel">
            <span className="field-label">ANDROID PHONE APP INTEGRATION</span>
            <p>Allow VaaniSetu to handle outgoing-call routing on this device. Your regular Phone app remains your dialler.</p>
            <label className="select-label" htmlFor="call-source-language">You speak</label>
            <select id="call-source-language" value={languageCode} onChange={(event) => setLanguageCode(event.target.value)} disabled={androidCallBusy}>
              {languages.map((language) => <option key={language.code} value={language.code}>{language.name}</option>)}
            </select>
            <label className="select-label" htmlFor="call-target-language">They speak</label>
            <select id="call-target-language" value={targetLanguageCode} onChange={(event) => setTargetLanguageCode(event.target.value)} disabled={androidCallBusy}>
              {ttsLanguages.map((language) => <option key={language.code} value={language.code}>{language.name}</option>)}
            </select>
            <button type="button" className="swap-button" onClick={saveAndroidCallLanguages} disabled={androidCallBusy || languageCode === targetLanguageCode}>Save call languages</button>
            <div className="call-status-panel">
              <span className={`status-dot ${androidCallStatus?.roleHeld ? "connected" : "offline"}`} />
              <div><strong>{androidCallStatus?.roleHeld ? "Android call-redirection access granted" : "Android call-redirection access not enabled"}</strong>
                <p>{androidCallStatus?.supported === false ? "This feature requires Android 10 or newer." : "This permission lets Android notify VaaniSetu about outgoing calls. It does not replace your Phone app."}</p>
              </div>
            </div>
            <button type="button" className="record-button" onClick={requestAndroidCallRole} disabled={androidCallBusy || androidCallStatus?.roleHeld || androidCallStatus?.supported === false}>
              {androidCallBusy ? "Please wait…" : androidCallStatus?.roleHeld ? "Android access enabled" : "Enable Android call integration"}
            </button>
            <p className="call-footnote">Safety: normal calls still go through unchanged. Automatic translation routing stays off until Exotel confirms the gateway and two-way audio protocol.</p>
          </section>}
          {!window.Capacitor?.isNativePlatform?.() && <div className="call-status-panel"><span className="status-dot offline" /><div><strong>Android app required</strong><p>Install the VaaniSetu Android app to configure Android call-redirection access. The current integration requires Android 10 or newer.</p></div></div>}
          {notice && <div className="notice" role="status"><p>{notice}</p></div>}
          <div className="api-config"><label className="select-label" htmlFor="backend-url">Translation backend URL</label><input id="backend-url" className="phone-input" type="url" inputMode="url" placeholder="https://your-backend.example.com" value={apiBaseDraft} onChange={(event) => setApiBaseDraft(event.target.value)} /><button type="button" className="swap-button" onClick={saveApiBase}>Save backend address</button><p className="call-footnote">Use the deployed HTTPS API address. Do not enter API keys here.</p></div>
          <div className="call-status-panel"><span className="status-dot offline" /><div><strong>Waiting for Exotel technical enablement</strong><p>{callStatus?.note || "No calls are redirected or placed. Exotel gateway routing remains disabled until the two-way audio bridge is verified."}</p></div></div>
          <p className="call-footnote">Your normal Phone app remains in place. This build only requests Android's call-redirection permission and saves your language preference; it does not yet translate cellular calls.</p>
        </section>
      </section>}
      <footer><span>VaaniSetu · Android-ready prototype</span><span>22 languages for recognition and translation · 11 for generated voice</span></footer>
    </main>
  );
}
