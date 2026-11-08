import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import { ProfileDialog } from "./ProfileDialog";
import type { Profile } from "./ProfilesGrid";

const PROFILE: Profile = {
  id: "6f1c1d2e-0000-4000-8000-000000000001",
  name: "Backend",
  titles: ["Backend Engineer"],
  keywords: ["Python"],
  excluded_keywords: [],
  location: "Madrid",
  work_modes: ["remote"],
};

function renderDialog(profile: Profile | null = null) {
  const onSaved = vi.fn();
  render(<ProfileDialog profile={profile} onClose={() => {}} onSaved={onSaved} />);
  return onSaved;
}

describe("ProfileDialog", () => {
  it("creates a profile from the comma-separated lists", async () => {
    // Arrange
    let body: unknown;
    server.use(
      http.post("/api/v1/search-profiles", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...PROFILE }, { status: 201 });
      }),
    );
    const onSaved = renderDialog();
    const user = userEvent.setup();

    // Act
    await user.type(screen.getByLabelText("Name"), "Backend");
    await user.type(screen.getByLabelText("Titles"), "Backend Engineer, Python Developer");
    await user.click(screen.getByRole("button", { name: "Create" }));

    // Assert
    expect(onSaved).toHaveBeenCalled();
    expect(body).toEqual({
      name: "Backend",
      titles: ["Backend Engineer", " Python Developer"],
      keywords: [],
      excluded_keywords: [],
      location: null,
      work_modes: [],
    });
  });

  it.each([
    ["titles", "Titles", "body.titles"],
    ["an item of keywords", "Keywords", "body.keywords.1"],
  ])("shows the error of %s next to its field", async (_, label, field) => {
    // Arrange
    server.use(
      http.post("/api/v1/search-profiles", () =>
        HttpResponse.json(
          {
            type: "/problems/validation-error",
            title: "Invalid request",
            status: 422,
            errors: [{ field, message: "Invalid value" }],
          },
          { status: 422 },
        ),
      ),
    );
    const onSaved = renderDialog();
    const user = userEvent.setup();

    // Act
    await user.click(screen.getByRole("button", { name: "Create" }));

    // Assert
    expect(await screen.findByLabelText(label)).toHaveAttribute("aria-invalid", "true");
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("says when the profile already exists", async () => {
    // Arrange
    server.use(
      http.post("/api/v1/search-profiles", () =>
        HttpResponse.json(
          { type: "/problems/already-exists", title: "Already exists", status: 409 },
          { status: 409 },
        ),
      ),
    );
    renderDialog();
    const user = userEvent.setup();

    // Act
    await user.click(screen.getByRole("button", { name: "Create" }));

    // Assert
    expect(await screen.findByText("The search profile already exists")).toBeInTheDocument();
  });

  it("edits a profile, sending a cleared location as null", async () => {
    // Arrange
    let body: unknown;
    server.use(
      http.patch(`/api/v1/search-profiles/${PROFILE.id}`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...PROFILE, location: null });
      }),
    );
    const onSaved = renderDialog(PROFILE);
    const user = userEvent.setup();

    // Act
    await user.clear(screen.getByLabelText("Location"));
    await user.click(screen.getByRole("button", { name: "Save" }));

    // Assert
    expect(onSaved).toHaveBeenCalled();
    expect(body).toEqual({
      name: "Backend",
      titles: ["Backend Engineer"],
      keywords: ["Python"],
      excluded_keywords: [],
      location: null,
      work_modes: ["remote"],
    });
  });
});
