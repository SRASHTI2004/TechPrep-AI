import { citationNumberFromHref, formatLocation, linkifyCitations } from "./citations";

describe("linkifyCitations", () => {
  const valid = new Set([1, 2, 3]);

  it("links valid citations, including grouped ones", () => {
    expect(linkifyCitations("A [1]. B [2][3]. C [1, 3].", valid)).toBe(
      "A [1](#cite-1). B [2](#cite-2)[3](#cite-3). C [1](#cite-1)[3](#cite-3).",
    );
  });

  it("leaves invalid citation numbers as plain text", () => {
    expect(linkifyCitations("Made up [7].", valid)).toBe("Made up [7].");
  });

  it("never touches code", () => {
    const md = "Use `arr[1]` here [1].\n```py\nx = a[2]\n```";
    expect(linkifyCitations(md, valid)).toBe("Use `arr[1]` here [1](#cite-1).\n```py\nx = a[2]\n```");
  });
});

describe("helpers", () => {
  it("parses cite hrefs", () => {
    expect(citationNumberFromHref("#cite-12")).toBe(12);
    expect(citationNumberFromHref("https://x.y")).toBeNull();
  });

  it("formats page or the last two section levels", () => {
    expect(formatLocation(14, null)).toBe("p. 14");
    expect(formatLocation(null, "Primer > Database > Sharding")).toBe("Database › Sharding");
    expect(formatLocation(null, null)).toBe("");
  });
});
