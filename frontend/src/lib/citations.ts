// Turn "[1]" / "[2][3]" / "[1, 4]" in an answer into markdown links "#cite-N" that
// AnswerMarkdown renders as clickable chips. Only *valid* source numbers become links;
// anything else stays plain text. Code (```fenced``` or `inline`) is never touched,
// so `arr[1]` inside code stays as it is.

const CITATION = /\[(\d{1,2}(?:\s*,\s*\d{1,2})*)\]/g;
const CODE = /(```[\s\S]*?(?:```|$)|`[^`\n]*`)/g;

export function linkifyCitations(markdown: string, validNumbers: Set<number>): string {
  return markdown
    .split(CODE)
    .map((part, i) => {
      if (i % 2 === 1) return part; // odd indices are the captured code segments
      return part.replace(CITATION, (match, group: string) => {
        const nums = group.split(",").map((s) => Number(s.trim()));
        if (!nums.every((n) => validNumbers.has(n))) return match;
        return nums.map((n) => `[${n}](#cite-${n})`).join("");
      });
    })
    .join("");
}

export function citationNumberFromHref(href: string | undefined): number | null {
  const m = href?.match(/^#cite-(\d+)$/);
  return m ? Number(m[1]) : null;
}

export function formatLocation(page: number | null, section: string | null): string {
  if (page) return `p. ${page}`;
  if (!section) return "";
  const parts = section.split(" > ");
  return parts.slice(-2).join(" › ");
}
