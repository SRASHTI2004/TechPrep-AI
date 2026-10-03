import { completeStreamingMarkdown } from "./markdown";

describe("completeStreamingMarkdown", () => {
  it("leaves complete markdown alone", () => {
    const text = "**Sharding** splits data. Use `arr[1]`.\n\n```py\nx = 1\n```";
    expect(completeStreamingMarkdown(text)).toBe(text);
  });

  it("closes an unfinished bold run", () => {
    expect(completeStreamingMarkdown("Use **consistent hash")).toBe("Use **consistent hash**");
    expect(completeStreamingMarkdown("Use **consistent ")).toBe("Use **consistent**");
  });

  it("hides a bold opener that has no text yet", () => {
    expect(completeStreamingMarkdown("Two kinds: **")).toBe("Two kinds:");
  });

  it("closes inline code and code fences", () => {
    expect(completeStreamingMarkdown("Call `get(")).toBe("Call `get(`");
    expect(completeStreamingMarkdown("Example:\n```py\nx = 1")).toBe("Example:\n```py\nx = 1\n```");
  });

  it("ignores ** inside code", () => {
    expect(completeStreamingMarkdown("Power: `2 ** 8` is 256")).toBe("Power: `2 ** 8` is 256");
  });
});
