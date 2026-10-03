import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { SpeechRecognitionEventLike } from "../hooks/useSpeechRecognition";
import { UNSUPPORTED_MESSAGE } from "../hooks/useSpeechRecognition";
import VoiceInput from "./VoiceInput";

class FakeRecognition {
  static last: FakeRecognition | null = null;
  lang = "";
  continuous = false;
  interimResults = false;
  onstart: (() => void) | null = null;
  onend: (() => void) | null = null;
  onerror: ((e: { error: string }) => void) | null = null;
  onresult: ((e: SpeechRecognitionEventLike) => void) | null = null;
  start = vi.fn(() => this.onstart?.());
  stop = vi.fn(() => this.onend?.());
  abort = vi.fn();
  constructor() {
    FakeRecognition.last = this;
  }
}

function result(transcript: string, isFinal: boolean): SpeechRecognitionEventLike {
  const r = Object.assign([{ transcript }], { isFinal });
  return { resultIndex: 0, results: Object.assign([r], { length: 1 }) };
}

afterEach(() => vi.unstubAllGlobals());

describe("VoiceInput", () => {
  it("explains when the browser has no speech recognition", async () => {
    render(<VoiceInput onText={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Start voice input" }));
    expect(screen.getByRole("alert")).toHaveTextContent(UNSUPPORTED_MESSAGE);
  });

  it("listens, shows the indicator and returns final text in the chosen language", async () => {
    vi.stubGlobal("webkitSpeechRecognition", FakeRecognition);
    const onText = vi.fn();
    render(<VoiceInput onText={onText} />);

    await userEvent.selectOptions(screen.getByLabelText("Voice input language"), "hi-IN");
    await userEvent.click(screen.getByRole("button", { name: "Start voice input" }));
    const rec = FakeRecognition.last!;
    expect(rec.lang).toBe("hi-IN");
    expect(screen.getByRole("status")).toHaveTextContent("Listening");

    act(() => rec.onresult?.(result("what is shard", false)));
    expect(screen.getByRole("status")).toHaveTextContent("what is shard");
    act(() => rec.onresult?.(result(" what is sharding ", true)));
    expect(onText).toHaveBeenCalledWith("what is sharding");

    await userEvent.click(screen.getByRole("button", { name: "Stop voice input" }));
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("shows a readable message when microphone permission is denied", async () => {
    vi.stubGlobal("webkitSpeechRecognition", FakeRecognition);
    render(<VoiceInput onText={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Start voice input" }));
    act(() => FakeRecognition.last!.onerror?.({ error: "not-allowed" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/permission was denied/);
  });
});
