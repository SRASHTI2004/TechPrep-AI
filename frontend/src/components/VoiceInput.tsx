import { Mic, Square, X } from "lucide-react";
import { useState } from "react";

import { useSpeechRecognition, VOICE_LANGUAGES } from "../hooks/useSpeechRecognition";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";

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
    <div className="relative flex items-center gap-1">
      <Button
        variant={listening ? "destructive" : "ghost"}
        size="icon-sm"
        className={cn("rounded-full", listening && "animate-pulse")}
        onClick={listening ? stop : start}
        disabled={disabled && !listening}
        aria-pressed={listening}
        aria-label={listening ? "Stop voice input" : "Start voice input"}
        title={listening ? "Stop listening" : "Speak your question"}
      >
        {listening ? <Square className="!size-3 fill-current" /> : <Mic />}
      </Button>
      <select
        className="h-7 cursor-pointer rounded-md border-0 bg-transparent px-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
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

      {listening && (
        <p
          className="absolute bottom-full left-0 mb-3 flex w-max max-w-[min(18rem,80vw)] items-center gap-2 rounded-lg border bg-popover px-3 py-2 text-xs text-muted-foreground shadow-lifted"
          role="status"
        >
          <span className="size-2 shrink-0 animate-blink rounded-full bg-destructive" aria-hidden />
          <span>
            Listening… {interim && <em className="text-foreground">{interim}</em>}
          </span>
        </p>
      )}
      {error && (
        <p
          className="absolute bottom-full left-0 mb-3 flex w-max max-w-[min(20rem,80vw)] items-start gap-2 rounded-lg border border-destructive/30 bg-popover px-3 py-2 text-xs text-destructive shadow-lifted"
          role="alert"
        >
          <span>{error}</span>
          <button
            type="button"
            className="rounded p-0.5 text-muted-foreground hover:text-foreground"
            onClick={clearError}
            aria-label="Dismiss"
          >
            <X className="size-3.5" />
          </button>
        </p>
      )}
    </div>
  );
}
