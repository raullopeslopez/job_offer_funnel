import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import type { Company } from "./CompaniesSection";
import { CompanyDialog } from "./CompanyDialog";

const COMPANY: Company = {
  id: "6f1c1d2e-0000-4000-8000-000000000002",
  name: "Acme",
  website: "https://acme.example",
};

function renderDialog(company: Company | null = null) {
  const onSaved = vi.fn();
  render(<CompanyDialog company={company} onClose={() => {}} onSaved={onSaved} />);
  return onSaved;
}

describe("CompanyDialog", () => {
  it("creates a company without a website", async () => {
    // Arrange
    let body: unknown;
    server.use(
      http.post("/api/v1/companies", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...COMPANY, website: null }, { status: 201 });
      }),
    );
    const onSaved = renderDialog();
    const user = userEvent.setup();

    // Act
    await user.type(screen.getByLabelText("Name"), "Acme");
    await user.click(screen.getByRole("button", { name: "Create" }));

    // Assert
    expect(onSaved).toHaveBeenCalled();
    expect(body).toEqual({ name: "Acme", website: null });
  });

  it.each([
    ["Name", "body.name"],
    ["Website", "body.website"],
  ])("shows the error of %s next to its field", async (label, field) => {
    // Arrange
    server.use(
      http.post("/api/v1/companies", () =>
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

  it("says when the company already exists", async () => {
    // Arrange
    server.use(
      http.patch(`/api/v1/companies/${COMPANY.id}`, () =>
        HttpResponse.json(
          { type: "/problems/already-exists", title: "Already exists", status: 409 },
          { status: 409 },
        ),
      ),
    );
    renderDialog(COMPANY);
    const user = userEvent.setup();

    // Act
    await user.click(screen.getByRole("button", { name: "Save" }));

    // Assert
    expect(await screen.findByText("The company already exists")).toBeInTheDocument();
  });

  it("edits a company, sending a cleared website as null", async () => {
    // Arrange
    let body: unknown;
    server.use(
      http.patch(`/api/v1/companies/${COMPANY.id}`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...COMPANY, website: null });
      }),
    );
    const onSaved = renderDialog(COMPANY);
    const user = userEvent.setup();

    // Act
    await user.clear(screen.getByLabelText("Website"));
    await user.click(screen.getByRole("button", { name: "Save" }));

    // Assert
    expect(onSaved).toHaveBeenCalled();
    expect(body).toEqual({ name: "Acme", website: null });
  });
});
