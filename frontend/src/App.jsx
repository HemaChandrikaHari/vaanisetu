import { useEffect, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const MAX_RECORDING_SECONDS = 25;

export default function App() {
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
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((response) => {
        if (!response.ok) throw new Error("Backend unavailable");
        return response.json();
      })
      .then(setBackend)
      .catch(() => setBackend({ status: "offline" }));

    fetch(`${API_BASE}/api/languages`)
      .then((response) => response.json())
      .then((data) => {
        setLanguages(data.languages || []);
        setTtsLanguages(data.tts_languages || []);
      })
      .catch(() => setLanguages([]));

    return () => {
      window.clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function startRecording() {
    setNotice("");
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
      const speechResponse = await fetch(`${API_BASE}/api/speech/transcribe?language_code=${encodeURIComponent(languageCode)}`, {
        method: "POST",
        body: form,
      });
      const speechData = await speechResponse.json();
      if (!speechResponse.ok) throw new Error(speechData.detail || "Speech recognition failed.");
      setTranscript(speechData.transcript);

      setNotice("2/3 · Translating the recognised text…");
      const translationResponse = await fetch(`${API_BASE}/api/translation/translate`, {
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
      const ttsResponse = await fetch(`${API_BASE}/api/speech/synthesize`, {
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
      <section className="hero">
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
      </section>
      <footer><span>VaaniSetu · Prototype 0.3.0</span><span>22 languages for recognition and translation · 11 for generated voice</span></footer>
    </main>
  );
}
