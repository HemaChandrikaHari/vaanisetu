const STORAGE_KEY = "vaanisetu_local_conversation_history";
const MAX_ENTRIES = 100;

export function saveHistoryEntry(entry) {
  try {
    const current = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    const next = [{
      id: globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      createdAt: new Date().toISOString(),
      ...entry,
    }, ...current].slice(0, MAX_ENTRIES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    window.dispatchEvent(new CustomEvent("vaanisetu-history-updated"));
  } catch {
    // History is best-effort; never interrupt a successful translation.
  }
}

export function readHistory() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export function deleteHistoryEntry(id) {
  const next = readHistory().filter((entry) => entry.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  window.dispatchEvent(new CustomEvent("vaanisetu-history-updated"));
}

export function clearHistory() {
  localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new CustomEvent("vaanisetu-history-updated"));
}

export function exportHistoryText(entries) {
  return entries.map((entry) => [
    new Date(entry.createdAt).toLocaleString(),
    `${entry.sourceLanguage} → ${entry.targetLanguage}`,
    `Original: ${entry.originalText}`,
    `Translation: ${entry.translatedText}`,
    "—".repeat(32),
  ].join("\n")).join("\n\n");
}
