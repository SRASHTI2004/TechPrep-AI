import { readSse, SseParser } from "./sse";

describe("SseParser", () => {
  it("parses events split across arbitrary chunk boundaries", () => {
    const p = new SseParser();
    const stream = 'event: meta\ndata: {"a":1}\n\nevent: token\ndata: {"text":"Hel"}\n\nevent: tok';
    const first = p.feed(stream.slice(0, 13));
    const rest = p.feed(stream.slice(13));
    expect(first).toEqual([]);
    expect(rest).toEqual([
      { event: "meta", data: '{"a":1}' },
      { event: "token", data: '{"text":"Hel"}' },
    ]);
    expect(p.feed('en\ndata: {"text":"lo"}\n\n')).toEqual([
      { event: "token", data: '{"text":"lo"}' },
    ]);
  });

  it("handles CRLF, comments and multi-line data", () => {
    const p = new SseParser();
    expect(p.feed(": keep-alive\r\n\r\nevent: done\r\ndata: line1\r\ndata: line2\r\n\r\n")).toEqual([
      { event: "done", data: "line1\nline2" },
    ]);
  });
});

describe("readSse", () => {
  it("reads events from a streamed Response body", async () => {
    const enc = new TextEncoder();
    const body = new ReadableStream({
      start(c) {
        c.enqueue(enc.encode("event: token\ndata: {\"text\":\"a\"}\n"));
        c.enqueue(enc.encode("\nevent: done\ndata: {}\n\n"));
        c.close();
      },
    });
    const events = [];
    for await (const ev of readSse(new Response(body))) events.push(ev.event);
    expect(events).toEqual(["token", "done"]);
  });
});
