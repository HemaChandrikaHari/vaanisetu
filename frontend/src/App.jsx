import { useEffect, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const MAX_RECORDING_SECONDS = 25;

export default function App() {
  const [backend, setBackend] = useState(null);
  const [languages, setLanguages] = useState([]);
  const [languageCode, setLanguageCode] = useState("te-IN");
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [busy, setBusy] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [notice, setNotice] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
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
      .then((data) => setLanguages(data.languages || []))
      .catch(() => setLanguages([]));

    return () => {
      window.clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function startRecording() {
    setNotice("");
    setTranscript("");
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
    if (backend?.mode !== "live") {
      setNotice("Recording captured locally. Demo mode does not send audio to an AI provider. To transcribe real speech, configure SARVAM_API_KEY and APP_MODE=live in backend/.env.");
      return;
    }
    setBusy(true);
    setNotice("Sending your short audio clip to Sarvam for transcription…");
    const form = new FormData();
    const extension = blob.type.includes("ogg") ? "ogg" : "webm";
    form.append("file", blob, `vaanisetu-recording.${extension}`);
    try {
      const response = await fetch(`${API_BASE}/api/speech/transcribe?language_code=${encodeURIComponent(languageCode)}`, {
        method: "POST",
        body: form,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Transcription failed.");
      setTranscript(data.transcript);
      setNotice(data.transcript ? "Speech recognised successfully." : "No speech was recognised. Try speaking closer to the microphone.");
    } catch (error) {
      setNotice(error.message || "Could not transcribe this recording. Please try again.");
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
        <p className="intro">Start with one voice, one language and one clear transcript. VaaniSetu is being built to connect conversations across India's languages.</p>

        <section className="recorder-card" aria-label="Speech recognition demo">
          <div className="recorder-heading">
            <div><span className="field-label">SPEAKING LANGUAGE</span><h2>Record a short phrase</h2></div>
            <span className={`mode-label ${liveReady ? "live" : ""}`}>{liveReady ? "LIVE AI" : "DEMO MODE"}</span>
          </div>
          <label className="select-label" htmlFor="language">Choose the language you will speak</label>
          <select id="language" value={languageCode} onChange={(event) => setLanguageCode(event.target.value)} disabled={recording || busy}>
            {languages.length ? languages.map((language) => (
              <option key={language.code} value={language.code}>{language.name} ({language.code})</option>
            )) : <><option value="te-IN">Telugu (te-IN)</option><option value="hi-IN">Hindi (hi-IN)</option></>}
          </select>
          <div className={`mic-orb ${recording ? "is-recording" : ""}`}><span className="mic-symbol">🎙</span></div>
          <p className="recording-caption">{recording ? `Listening… ${seconds}s / ${MAX_RECORDING_SECONDS}s` : busy ? "Processing audio…" : "Tap below and speak naturally"}</p>
          {!recording ? (
            <button className="record-button" type="button" onClick={startRecording} disabled={busy || !backendOnline}>
              {busy ? "Processing…" : "Start recording"}
            </button>
          ) : (
            <button className="record-button stop-button" type="button" onClick={stopRecording}>Stop and transcribe</button>
          )}
          {audioUrl && <audio className="audio-preview" controls src={audioUrl}>Your browser does not support audio playback.</audio>}
          {transcript && <div className="transcript-panel" aria-live="polite"><span className="field-label">RECOGNISED SPEECH</span><p lang={languageCode.split("-")[0]}>{transcript}</p></div>}
          {notice && <div className="notice" role="status"><span className="notice-icon">i</span><p>{notice}</p></div>}
        </section>
        <div className="privacy-note"><span>🔒</span><p>Audio is processed in memory by this backend and is not saved to disk by VaaniSetu. In live mode, the clip is sent to Sarvam AI for transcription.</p></div>
      </section>
      <footer><span>VaaniSetu · Prototype 0.2.0</span><span>Building for India's 22 scheduled languages</span></footer>
    </main>
  );
}
