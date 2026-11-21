import { describe, expect, it } from "vitest";
import { discardReasonText, titleWords } from "./discardReasons";

describe("titleWords", () => {
  it.each([
    ["Senior Backend Engineer", ["Senior", "Backend", "Engineer"]],
    ["Python Developer (Django)", ["Python", "Developer", "Django"]],
    ["Senior C++ Developer, Remote", ["Senior", "C++", "Developer", "Remote"]],
    ["Engineer - Engineer", ["Engineer"]],
  ])("splits %s into its words", (title, expected) => {
    // Act
    const words = titleWords(title);

    // Assert
    expect(words).toEqual(expected);
  });
});

describe("discardReasonText", () => {
  it.each([
    [
      { discard_reason: "title_word" as const, discard_word: "Senior", triager_discard: null },
      "A word in the title: Senior",
    ],
    [{ discard_reason: "none" as const, discard_word: null, triager_discard: null }, "No reason"],
    [{ discard_reason: null, discard_word: null, triager_discard: null }, "—"],
    [
      {
        discard_reason: "contract" as const,
        discard_word: null,
        triager_discard: "discarded" as const,
      },
      "Discarded by AI · Contract",
    ],
    [
      {
        discard_reason: "stack" as const,
        discard_word: null,
        triager_discard: "restored" as const,
      },
      "Stack",
    ],
  ])("says %o as %s", (offer, expected) => {
    // Act
    const text = discardReasonText(offer);

    // Assert
    expect(text).toBe(expected);
  });
});
