import { type APIRequestContext, expect } from "@playwright/test";
import type { components } from "../../src/api/schema";
import { API_URL, E2E_TOKEN } from "./env";

type Schemas = components["schemas"];

// Given steps prepare the data through the real API, as a client would.
export class Api {
  // Ids of what the scenario created, by the name the spec gives it.
  private readonly companyIds = new Map<string, string>();
  readonly applicationIds = new Map<string, string>();
  lastApplicationId = "";

  constructor(private readonly request: APIRequestContext) {}

  async reset(): Promise<void> {
    const response = await this.request.post(`${API_URL}/e2e/reset`);
    expect(response.ok()).toBe(true);
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const response = await this.request.post(`${API_URL}/api/v1${path}`, {
      headers: { Authorization: `Bearer ${E2E_TOKEN}` },
      data: body,
    });
    expect(response.ok(), await response.text()).toBe(true);
    return (await response.json()) as T;
  }

  addJobBoard(
    name: string,
    syntax: Schemas["Syntax"] = "keywords",
    template = "https://jobs.example/search?q={query}",
  ): Promise<Schemas["JobBoardRead"]> {
    return this.post("/job-boards", { name, search_url_template: template, syntax });
  }

  addSearchProfile(
    name: string,
    fields: Partial<Schemas["SearchProfileCreate"]> = {},
  ): Promise<Schemas["SearchProfileRead"]> {
    return this.post("/search-profiles", { name, titles: ["Backend Engineer"], ...fields });
  }

  addOffer(
    company: string,
    title: string,
    url = "https://jobs.example/1",
  ): Promise<Schemas["OfferRead"]> {
    return this.post("/offers", { company, title, url });
  }

  discard(offerId: string): Promise<Schemas["OfferRead"]> {
    return this.post(`/offers/${offerId}/discard`, {});
  }

  promote(offerId: string): Promise<Schemas["OfferRead"]> {
    return this.post(`/offers/${offerId}/promotion`, {});
  }

  async addCompany(name: string, website?: string): Promise<Schemas["CompanyRead"]> {
    const company = await this.post<Schemas["CompanyRead"]>("/companies", { name, website });
    this.companyIds.set(name, company.id);
    return company;
  }

  async addApplication(
    company: string,
    role: string,
    fields: Partial<Schemas["ApplicationCreate"]> = {},
  ): Promise<Schemas["ApplicationRead"]> {
    const application = await this.post<Schemas["ApplicationRead"]>("/applications", {
      company_id: this.companyIds.get(company),
      role,
      channel: "portal",
      ...fields,
    });
    this.applicationIds.set(role, application.id);
    this.lastApplicationId = application.id;
    return application;
  }

  transition(
    applicationId: string,
    body: Schemas["TransitionCreate"],
  ): Promise<Schemas["TransitionRead"]> {
    return this.post(`/applications/${applicationId}/transitions`, body);
  }
}
