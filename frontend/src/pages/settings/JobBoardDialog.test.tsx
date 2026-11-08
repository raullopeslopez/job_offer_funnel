import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import { JobBoardDialog } from "./JobBoardDialog";
import type { JobBoard } from "./JobBoardsSection";

const JOB_BOARD: JobBoard = {
  id: "6f1c1d2e-0000-4000-8000-000000000004",
  name: "LinkedIn",
  search_url_template: "https://www.linkedin.com/jobs/search/?keywords={query}",
  syntax: "boolean",
};

function renderDialog(jobBoard: JobBoard | null = null) {
  const onSaved = vi.fn();
  render(<JobBoardDialog jobBoard={jobBoard} onClose={() => {}} onSaved={onSaved} />);
  return onSaved;
}

describe("JobBoardDialog", () => {
  it("creates a job board with the chosen syntax", async () => {
    // Arrange
    let body: unknown;
    server.use(
      http.post("/api/v1/job-boards", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(JOB_BOARD, { status: 201 });
      }),
    );
    const onSaved = renderDialog();
    const user = userEvent.setup();

    // Act
    await user.type(screen.getByLabelText("Name"), "LinkedIn");
    await user.type(
      screen.getByLabelText("Search URL template"),
      "https://jobs.example/search?q={{query}",
    );
    await user.click(screen.getByRole("combobox", { name: "Syntax" }));
    await user.click(screen.getByRole("option", { name: "boolean" }));
    await user.click(screen.getByRole("button", { name: "Create" }));

    // Assert
    expect(onSaved).toHaveBeenCalled();
    expect(body).toEqual({
      name: "LinkedIn",
      search_url_template: "https://jobs.example/search?q={query}",
      syntax: "boolean",
    });
  });

  it.each([
    ["Name", "body.name"],
    ["Search URL template", "body.search_url_template"],
  ])("shows the error of %s next to its field", async (label, field) => {
    // Arrange
    server.use(
      http.post("/api/v1/job-boards", () =>
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

  it("says when the job board already exists", async () => {
    // Arrange
    server.use(
      http.patch(`/api/v1/job-boards/${JOB_BOARD.id}`, () =>
        HttpResponse.json(
          { type: "/problems/already-exists", title: "Already exists", status: 409 },
          { status: 409 },
        ),
      ),
    );
    renderDialog(JOB_BOARD);
    const user = userEvent.setup();

    // Act
    await user.click(screen.getByRole("button", { name: "Save" }));

    // Assert
    expect(await screen.findByText("The job board already exists")).toBeInTheDocument();
  });
});
