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
      { discard_reason: "title_word" as const, discard_word: "Senior" },
      "A word in the title: Senior",
    ],
    [{ discard_reason: "none" as const, discard_word: null }, "No reason"],
    [{ discard_reason: null, discard_word: null }, "—"],
  ])("says %o as %s", (offer, expected) => {
    // Act
    const text = discardReasonText(offer);

    // Assert
    expect(text).toBe(expected);
  });
});
