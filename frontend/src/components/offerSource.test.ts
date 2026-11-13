import { describe, expect, it } from "vitest";
import type { Source } from "../theme";
import { offerSourceKind } from "./offerSource";

const jobBoards = [
  { id: "api-board", import_method: "api" as const },
  { id: "rss-board", import_method: "rss" as const },
  { id: "email-board", import_method: "email" as const },
  { id: "none-board", import_method: "none" as const },
];

describe("offerSourceKind", () => {
  it.each<[string, string | null, string | null, Source]>([
    ["a watched company", "company-1", null, "watched"],
    ["a watched company on a job board", "company-1", "api-board", "watched"],
    ["an API job board", null, "api-board", "api"],
    ["an RSS job board", null, "rss-board", "rss"],
    ["an email job board", null, "email-board", "email"],
    ["a job board without import", null, "none-board", "manual"],
    ["an unknown job board", null, "gone-board", "manual"],
    ["no job board", null, null, "manual"],
  ])("is %s → %s", (_case, watchedCompanyId, jobBoardId, kind) => {
    // Arrange
    const offer = { watched_company_id: watchedCompanyId, job_board_id: jobBoardId };

    // Act
    const result = offerSourceKind(offer, jobBoards);

    // Assert
    expect(result).toBe(kind);
  });
});
