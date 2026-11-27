import { useEffect, useState } from "react";
import { clearHistory, deleteHistoryEntry, exportHistoryText, readHistory } from "./historyStore.js";

export default function ConversationHistory() {
  const [entries, setEntries] = useState(readHistory);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    const refresh = () => setEntries(readHistory());
    window.addEventListener("vaanisetu-history-updated", refresh);
    return () => window.removeEventListener("vaanisetu-history-updated", refresh);
  }, []);

  function exportText() {
    if (!entries.length) return;
    const blob = new Blob([exportHistoryText(entries)], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "vaanisetu-conversation-history.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  return <section className="hero history-hero">
    <p className="eyebrow">PRIVATE ON THIS DEVICE</p>
    <h1>Your conversation<br /><span>history.</span></h1>
    <p className="intro">Completed translation turns are saved on this device only. Audio recordings are not saved in history.</p>
    <section className="recorder-card">
      <div className="recorder-heading">
        <div><span className="field-label">LOCAL HISTORY</span><h2>{entries.length} saved {entries.length === 1 ? "turn" : "turns"}</h2></div>
        <span className="mode-label">ON DEVICE</span>
      </div>
      {entries.length > 0 && <div className="history-actions">
        <button className="swap-button" type="button" onClick={exportText}>Export TXT</button>
        <button className="swap-button danger-button" type="button" onClick={() => { if (window.confirm("Delete all VaaniSetu history stored on this device?")) { clearHistory(); setSelected(null); } }}>Delete all</button>
      </div>}
      {!entries.length && <div className="history-empty"><span>◷</span><strong>No saved conversations yet</strong><p>Your completed speech translations will appear here.</p></div>}
      <div className="history-list">
        {entries.map((entry) => <article className={selected?.id === entry.id ? "history-entry selected" : "history-entry"} key={entry.id}>
          <button type="button" className="history-entry-main" onClick={() => setSelected(selected?.id === entry.id ? null : entry)}>
            <span className="history-date">{new Date(entry.createdAt).toLocaleString()}</span>
            <strong>{entry.sourceLanguage} → {entry.targetLanguage}</strong>
            <span>{entry.originalText}</span>
            <small>{entry.translatedText}</small>
          </button>
          <button type="button" className="history-delete" aria-label="Delete this history item" onClick={() => { deleteHistoryEntry(entry.id); if (selected?.id === entry.id) setSelected(null); }}>×</button>
          {selected?.id === entry.id && <div className="history-detail">
            <span className="field-label">ORIGINAL SPEECH · {entry.sourceLanguage}</span><p>{entry.originalText}</p>
            <span className="field-label">TRANSLATION · {entry.targetLanguage}</span><p>{entry.translatedText}</p>
          </div>}
        </article>)}
      </div>
      <p className="history-privacy">Privacy: this history stays in this app's local browser storage. It is not synced to another phone or uploaded to VaaniSetu's server. Clearing app data may erase it.</p>
    </section>
  </section>;
}
