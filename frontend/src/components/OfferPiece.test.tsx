import { Button, ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import { type Source, theme } from "../theme";
import { OfferPiece } from "./OfferPiece";

const offer = {
  title: "Backend Engineer",
  url: "https://example.com/jobs/1",
  company: "Acme",
  created_at: "2026-11-10T09:00:00Z",
  job_board_name: "Jobicy",
  location: null,
  countries: [],
};
const now = new Date("2026-11-13T12:00:00Z");

function renderThemed(ui: ReactElement) {
  return render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("OfferPiece", () => {
  it("shows the company, its age, the title and a link to the original posting", () => {
    // Arrange / Act
    renderThemed(<OfferPiece offer={offer} sourceKind="api" now={now} />);

    // Assert
    const piece = screen.getByRole("article", { name: "Backend Engineer" });
    expect(piece).toHaveTextContent("3d ago");
    expect(piece).toHaveTextContent("Acme");
    expect(screen.getByRole("heading", { name: "Backend Engineer" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Original posting" })).toHaveAttribute(
      "href",
      "https://example.com/jobs/1",
    );
  });

  it.each<[Source, string]>([
    ["api", "API · Jobicy"],
    ["watched", "Watched company"],
    ["manual", "By hand · Jobicy"],
  ])("tags a %s offer as %j", (kind, tag) => {
    // Arrange / Act
    renderThemed(<OfferPiece offer={offer} sourceKind={kind} now={now} />);

    // Assert
    expect(screen.getByText(tag)).toBeInTheDocument();
  });

  it.each<[string, string | null, string[], string[], string | null]>([
    ["one country as a tag", "Madrid, Spain", ["Spain"], ["Spain"], null],
    [
      "the first country and how many more",
      "Spain, Portugal",
      ["Spain", "Portugal"],
      ["Spain"],
      "+1 country",
    ],
    [
      "the first of many countries",
      "Europe",
      ["Spain", "Portugal", "France"],
      ["Spain"],
      "+2 countries",
    ],
    [
      "the location when it names no known country",
      "San Francisco, CA",
      [],
      ["San Francisco, CA"],
      null,
    ],
    ["no tag without a location", null, [], [], null],
  ])("shows %s", (_name, location, countries, tags, more) => {
    // Arrange / Act
    renderThemed(
      <OfferPiece offer={{ ...offer, location, countries }} sourceKind="api" now={now} />,
    );

    // Assert
    const shown = screen.queryAllByTitle("Country").map((tag) => tag.textContent);
    expect(shown).toEqual(tags);
    const piece = screen.getByRole("article");
    if (more) expect(piece).toHaveTextContent(more);
    else expect(piece).not.toHaveTextContent(/\+\d+ countr/);
  });

  it("renders its actions, strip and footer slots", () => {
    // Arrange / Act
    renderThemed(
      <OfferPiece
        offer={offer}
        sourceKind="api"
        now={now}
        actions={<Button>Promote</Button>}
        strip={<div>Rules here</div>}
        footer={<div>Footer here</div>}
      />,
    );

    // Assert
    expect(screen.getByRole("button", { name: "Promote" })).toBeInTheDocument();
    expect(screen.getByText("Rules here")).toBeInTheDocument();
    expect(screen.getByText("Footer here")).toBeInTheDocument();
  });
});
