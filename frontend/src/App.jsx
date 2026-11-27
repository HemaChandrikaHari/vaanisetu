import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [mode, setMode] = useState("demo");
  const [apiStatus, setApiStatus] = useState("checking");

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((response) => {
        if (!response.ok) throw new Error("Backend unavailable");
        return response.json();
      })
      .then(() => setApiStatus("connected"))
      .catch(() => setApiStatus("offline"));
  }, []);

  return (
    <main className="page-shell">
      <nav className="topbar">
        <a className="brand" href="/" aria-label="VaaniSetu home">
          <span className="brand-mark">ವ</span>
          <span>VaaniSetu</span>
        </a>
        <span className="status-pill">
          <span className={`status-dot ${apiStatus}`} />
          API {apiStatus}
        </span>
      </nav>

      <section className="hero">
        <p className="eyebrow">VOICE-FIRST COMMUNICATION</p>
        <h1>Speak freely.<br /><span>Understand each other.</span></h1>
        <p className="intro">
          A voice translation experience for conversations across Indian
          languages. Start with Telugu and Hindi.
        </p>

        <div className="language-card">
          <div className="language-side">
            <span className="field-label">YOUR LANGUAGE</span>
            <strong>తెలుగు</strong>
            <span className="language-name">Telugu</span>
          </div>
          <div className="swap-mark" aria-hidden="true">⇄</div>
          <div className="language-side align-right">
            <span className="field-label">OTHER LANGUAGE</span>
            <strong>हिन्दी</strong>
            <span className="language-name">Hindi</span>
          </div>
        </div>

        <div className="mode-card">
          <div>
            <strong>Prototype mode</strong>
            <p>Demo works without a key. Live AI will use your server-side Sarvam key.</p>
          </div>
          <div className="mode-switch" role="group" aria-label="Prototype mode">
            <button
              className={mode === "demo" ? "selected" : ""}
              onClick={() => setMode("demo")}
              type="button"
            >Demo</button>
            <button
              className={mode === "live" ? "selected" : ""}
              onClick={() => setMode("live")}
              type="button"
            >Live AI</button>
          </div>
        </div>

        <div className="notice" role="status">
          <span className="notice-icon">i</span>
          <p>
            Foundation milestone: microphone capture and translation are not
            connected yet. The next milestone adds speech recognition.
          </p>
        </div>
      </section>

      <footer>
        <span>VaaniSetu · Prototype 0.1.0</span>
        <span>Telugu ↔ Hindi</span>
      </footer>
    </main>
  );
}
