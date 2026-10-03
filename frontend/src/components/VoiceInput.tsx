import { useState } from "react";

import { useSpeechRecognition, VOICE_LANGUAGES } from "../hooks/useSpeechRecognition";

const LANG_KEY = "techprep.voiceLang";

function savedLanguage(): string {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved && VOICE_LANGUAGES.some((l) => l.code === saved)) return saved;
  } catch {
    /* storage blocked: use the default */
  }
  return "en-US";
}

interface Props {
  /** Called with each recognised phrase; the page appends it to the question box. */
  onText: (text: string) => void;
  disabled?: boolean;
}

/** Mic button + language picker + listening indicator for the chat composer. */
export default function VoiceInput({ onText, disabled }: Props) {
  const [lang, setLang] = useState(savedLanguage);
  const { listening, interim, error, start, stop, clearError } = useSpeechRecognition(lang, onText);

  return (
    <div className="voice">
      <div className="voice-controls">
        <button
          type="button"
          className={`secondary mic${listening ? " listening" : ""}`}
          onClick={listening ? stop : start}
          disabled={disabled && !listening}
          aria-pressed={listening}
          aria-label={listening ? "Stop voice input" : "Start voice input"}
          title={listening ? "Stop listening" : "Speak your question"}
        >
          {listening ? "■" : "🎤"}
        </button>
        <select
          className="voice-lang"
          value={lang}
          aria-label="Voice input language"
          disabled={listening}
          onChange={(e) => {
            setLang(e.target.value);
            try {
              localStorage.setItem(LANG_KEY, e.target.value);
            } catch {
              /* not persisted: fine */
            }
          }}
        >
          {VOICE_LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.code === "en-US" ? "EN" : "HI"}
            </option>
          ))}
        </select>
      </div>
      {listening && (
        <p className="voice-status" role="status">
          <span className="rec-dot" aria-hidden /> Listening… {interim && <em>{interim}</em>}
        </p>
      )}
      {error && (
        <p className="voice-status error" role="alert">
          {error}{" "}
          <button type="button" className="ghost" onClick={clearError} aria-label="Dismiss">
            ×
          </button>
        </p>
      )}
    </div>
  );
}
