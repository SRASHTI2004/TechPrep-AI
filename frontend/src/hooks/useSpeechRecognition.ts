// Voice input with the browser's Web Speech API (SpeechRecognition).
//
// Supported in Chrome and Edge (prefixed as webkitSpeechRecognition) and Safari; not in
// Firefox. In Chrome the audio is sent to Google's speech service, so it needs internet.
// Nothing is sent to our backend: we only receive the final text and put it in the input box.

import { useCallback, useEffect, useRef, useState } from "react";

// Minimal typings: the Web Speech API is not in TypeScript's DOM lib.
interface SpeechRecognitionAlternativeLike {
  transcript: string;
}
interface SpeechRecognitionResultLike {
  readonly isFinal: boolean;
  readonly length: number;
  [index: number]: SpeechRecognitionAlternativeLike;
}
export interface SpeechRecognitionEventLike {
  readonly resultIndex: number;
  readonly results: { readonly length: number; [index: number]: SpeechRecognitionResultLike };
}
export interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

export function getSpeechRecognition(): SpeechRecognitionCtor | null {
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export const VOICE_LANGUAGES = [
  { code: "en-US", label: "English" },
  { code: "hi-IN", label: "हिन्दी (Hindi)" },
] as const;

const ERROR_MESSAGES: Record<string, string> = {
  "not-allowed": "Microphone permission was denied. Allow it in the browser's site settings.",
  "service-not-allowed": "Microphone permission was denied. Allow it in the browser's site settings.",
  "audio-capture": "No microphone was found.",
  "no-speech": "No speech was heard. Try again.",
  network: "The browser's speech service could not be reached (it needs an internet connection).",
  "language-not-supported": "This language is not supported by your browser's speech service.",
};

export const UNSUPPORTED_MESSAGE =
  "Voice input isn't supported in this browser. Try Chrome, Edge or Safari, or type your question.";

/**
 * `onFinalText` receives each finished phrase. `interim` holds the words being recognised
 * right now (shown as a live preview).
 */
export function useSpeechRecognition(lang: string, onFinalText: (text: string) => void) {
  const Ctor = getSpeechRecognition();
  const supported = Ctor !== null;
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const onFinalRef = useRef(onFinalText);
  onFinalRef.current = onFinalText;

  useEffect(() => () => recognitionRef.current?.abort(), []);

  const start = useCallback(() => {
    setError(null);
    if (!Ctor) {
      setError(UNSUPPORTED_MESSAGE);
      return;
    }
    const recognition = new Ctor();
    recognition.lang = lang;
    recognition.continuous = true; // keep listening until the user clicks again
    recognition.interimResults = true;
    recognition.onstart = () => setListening(true);
    recognition.onend = () => {
      setListening(false);
      setInterim("");
      recognitionRef.current = null;
    };
    recognition.onerror = (event) => {
      if (event.error !== "aborted") {
        setError(ERROR_MESSAGES[event.error] ?? `Voice input error: ${event.error}`);
      }
    };
    recognition.onresult = (event) => {
      let live = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]!;
        const text = result[0]?.transcript ?? "";
        if (result.isFinal) onFinalRef.current(text.trim());
        else live += text;
      }
      setInterim(live);
    };
    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      setError("Could not start voice input. Try again.");
    }
  }, [Ctor, lang]);

  const stop = useCallback(() => recognitionRef.current?.stop(), []);

  return { supported, listening, interim, error, start, stop, clearError: () => setError(null) };
}
