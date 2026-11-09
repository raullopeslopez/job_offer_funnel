import { ThemeProvider } from "@mui/material";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { theme } from "../theme";
import { CompanyAvatar, domainOf, LOGO_URL, toneForName } from "./CompanyAvatar";

const renderAvatar = (ui: React.ReactElement) =>
  render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);

describe("CompanyAvatar", () => {
  it("shows the uppercase initial without a domain", () => {
    // Arrange / Act
    const { container } = renderAvatar(<CompanyAvatar name="acme" />);

    // Assert
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(container.querySelector("img")).toBeNull();
  });

  it("shows the logo with a domain", () => {
    // Arrange / Act
    const { container } = renderAvatar(<CompanyAvatar name="Acme" domain="acme.com" />);

    // Assert
    expect(container.querySelector("img")).toHaveAttribute("src", LOGO_URL("acme.com"));
  });

  it("falls back to the initial when the image fails", () => {
    // Arrange
    const { container } = renderAvatar(<CompanyAvatar name="Acme" domain="acme.com" />);

    // Act
    fireEvent.error(container.querySelector("img") as HTMLImageElement);

    // Assert
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(container.querySelector("img")).toBeNull();
  });

  it("gives the same tone to the same name", () => {
    // Arrange / Act
    const first = toneForName("Globex");
    const second = toneForName("Globex");

    // Assert
    expect(first).toBe(second);
  });
});

describe("domainOf", () => {
  it.each([
    ["https://www.acme.com/jobs", "acme.com"],
    ["http://acme.io", "acme.io"],
    ["acme.com/careers", "acme.com"],
    ["", null],
    [null, null],
    [undefined, null],
  ])("domainOf(%j) is %j", (website, expected) => {
    // Arrange / Act
    const result = domainOf(website);

    // Assert
    expect(result).toBe(expected);
  });
});
