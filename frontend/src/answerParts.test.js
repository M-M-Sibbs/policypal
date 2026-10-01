import { describe, expect, it } from "vitest";
import { locationLabel, splitAnswer } from "./answerParts.js";

describe("splitAnswer", () => {
  it("separates text and valid citation markers", () => {
    expect(splitAnswer("Five days [1][2]. More [9].", [1, 2])).toEqual([
      { type: "text", value: "Five days " },
      { type: "cite", id: 1 },
      { type: "cite", id: 2 },
      { type: "text", value: ". More " },
      { type: "text", value: "." },
    ]);
  });

  it("keeps markup as plain text", () => {
    const parts = splitAnswer("<img src=x onerror=alert(1)> [1]", [1]);
    expect(parts[0]).toEqual({ type: "text", value: "<img src=x onerror=alert(1)> " });
  });
});

describe("locationLabel", () => {
  it("shows pages for PDFs and sections otherwise", () => {
    expect(locationLabel({ section: "Receipts", page_start: 3, page_end: 3 })).toBe("Receipts · page 3");
    expect(locationLabel({ section: "Receipts", page_start: 3, page_end: 4 })).toBe("Receipts · pages 3–4");
    expect(locationLabel({ section: "Carry-over", page_start: null, page_end: null })).toBe("Carry-over");
  });
});
