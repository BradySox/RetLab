import { hasContent } from "./EventsFeed";

describe("hasContent", () => {
  it("skips a rule of hyphens", () => {
    expect(hasContent("-".repeat(40))).toBe(false);
  });

  it("skips an empty or missing body", () => {
    expect(hasContent("")).toBe(false);
    expect(hasContent("   ")).toBe(false);
    expect(hasContent(null)).toBe(false);
    expect(hasContent(undefined)).toBe(false);
  });

  it("keeps a body with words or numbers", () => {
    expect(hasContent("Enemy convoy destroyed")).toBe(true);
    expect(hasContent("-- 3 --")).toBe(true);
  });
});
