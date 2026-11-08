import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { api } from "../api/client";
import { server } from "../test/server";
import { TokenGate } from "./TokenGate";
import { getToken, saveToken } from "./token";

const VALID_TOKEN = "secret";

function feedsRequireToken() {
  server.use(
    http.get("/api/v1/feeds", ({ request }) =>
      request.headers.get("Authorization") === `Bearer ${VALID_TOKEN}`
        ? HttpResponse.json([])
        : HttpResponse.json(
            { type: "/problems/unauthorized", title: "Unauthorized", status: 401 },
            { status: 401 },
          ),
    ),
  );
}

function renderGate() {
  render(
    <TokenGate>
      <p>App content</p>
    </TokenGate>,
  );
}

async function submitToken(token: string) {
  const user = userEvent.setup();
  if (token) await user.type(screen.getByLabelText(/token/i), token);
  await user.click(screen.getByRole("button", { name: "Continue" }));
}

describe("TokenGate", () => {
  it("asks for the token when none is stored", () => {
    // Act
    renderGate();

    // Assert
    expect(screen.getByLabelText(/token/i)).toBeInTheDocument();
    expect(screen.queryByText("App content")).not.toBeInTheDocument();
  });

  it("shows the app and keeps the token when the API accepts it", async () => {
    // Arrange
    feedsRequireToken();
    renderGate();

    // Act
    await submitToken(VALID_TOKEN);

    // Assert
    expect(await screen.findByText("App content")).toBeInTheDocument();
    expect(getToken()).toBe(VALID_TOKEN);
  });

  it.each([
    { token: "", message: "Enter the token" },
    { token: "wrong", message: "Invalid token" },
  ])("rejects the token '$token' with '$message'", async ({ token, message }) => {
    // Arrange
    feedsRequireToken();
    renderGate();

    // Act
    await submitToken(token);

    // Assert
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it("tells when the API cannot be reached", async () => {
    // Arrange
    server.use(http.get("/api/v1/feeds", () => HttpResponse.error()));
    renderGate();

    // Act
    await submitToken(VALID_TOKEN);

    // Assert
    expect(await screen.findByText("Could not reach the API")).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it("asks for the token again when the API rejects the stored one", async () => {
    // Arrange
    feedsRequireToken();
    saveToken("revoked");
    renderGate();

    // Act
    await act(() => api.GET("/api/v1/feeds"));

    // Assert
    expect(screen.getByLabelText(/token/i)).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });
});
