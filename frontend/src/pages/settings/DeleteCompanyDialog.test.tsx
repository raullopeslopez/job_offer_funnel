import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import type { Company } from "./CompaniesSection";
import { DeleteCompanyDialog } from "./DeleteCompanyDialog";

const COMPANY: Company = {
  id: "6f1c1d2e-0000-4000-8000-000000000003",
  name: "Acme",
  website: null,
};

function renderDialog() {
  const onDeleted = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <DeleteCompanyDialog company={COMPANY} onClose={() => {}} onDeleted={onDeleted} />
    </QueryClientProvider>,
  );
  return onDeleted;
}

describe("DeleteCompanyDialog", () => {
  it.each([
    ["in-use", 409, "The company has applications and cannot be deleted"],
    ["not-found", 404, "Could not delete the company"],
  ])("explains a %s rejection", async (slug, status, message) => {
    // Arrange
    server.use(
      http.delete(`/api/v1/companies/${COMPANY.id}`, () =>
        HttpResponse.json({ type: `/problems/${slug}`, title: "Rejected", status }, { status }),
      ),
    );
    const onDeleted = renderDialog();
    const user = userEvent.setup();

    // Act
    await user.click(screen.getByRole("button", { name: "Delete" }));

    // Assert
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(onDeleted).not.toHaveBeenCalled();
  });
});
