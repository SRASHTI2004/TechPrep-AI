// While an answer is still streaming, its Markdown is often cut mid-construct: "**Shard",
// "`arr[", or an open ``` fence. Rendered as-is, those show raw symbols until the closing
// token arrives. This closes (or drops) the dangling opener so the partial text renders
// cleanly. Only used for the in-progress message; final answers are rendered untouched.

const FENCE = /^ {0,3}```/gm;
const FENCED_BLOCK = /```[\s\S]*?```/g;
const INLINE_CODE = /`[^`\n]*`/g;

const count = (text: string, re: RegExp) => (text.match(re) ?? []).length;

export function completeStreamingMarkdown(text: string): string {
  if (count(text, FENCE) % 2 === 1) return `${text}\n\`\`\``;

  const prose = text.replace(FENCED_BLOCK, "");
  if (count(prose, /`/g) % 2 === 1) {
    return text.endsWith("`") ? text.slice(0, -1) : `${text}\``;
  }

  if (count(prose.replace(INLINE_CODE, ""), /\*\*/g) % 2 === 1) {
    const trimmed = text.trimEnd();
    // "…and **" (opener with nothing after it yet): just hide the opener.
    return trimmed.endsWith("**") ? trimmed.slice(0, -2).trimEnd() : `${trimmed}**`;
  }
  return text;
}
