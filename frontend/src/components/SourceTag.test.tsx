import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { type Source, theme } from "../theme";
import { SourceTag } from "./SourceTag";

describe("SourceTag", () => {
  it.each<[Source, string | undefined, string]>([
    ["api", "Jobicy", "API · Jobicy"],
    ["rss", "Evenbreak", "RSS · Evenbreak"],
    ["email", "LinkedIn", "Email · LinkedIn"],
    ["watched", "Ignored", "Watched company"],
    ["manual", "Indeed", "By hand · Indeed"],
    ["manual", undefined, "By hand"],
  ])("shows %s with name %j as %j, with a hidden icon", (kind, name, text) => {
    // Arrange / Act
    const { container } = render(
      <ThemeProvider theme={theme}>
        <SourceTag kind={kind} name={name} />
      </ThemeProvider>,
    );

    // Assert
    expect(screen.getByText(text)).toBeInTheDocument();
    expect(container.querySelector("svg[aria-hidden='true']")).not.toBeNull();
  });
});
