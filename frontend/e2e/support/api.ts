import { type APIRequestContext, expect } from "@playwright/test";
import type { components } from "../../src/api/schema";
import { API_URL, E2E_TOKEN } from "./env";

type Schemas = components["schemas"];

// Given steps prepare the data through the real API, as a client would.
export class Api {
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

  addJobBoard(name: string): Promise<Schemas["JobBoardRead"]> {
    return this.post("/job-boards", {
      name,
      search_url_template: "https://jobs.example/search?q={query}",
      syntax: "keywords",
    });
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
}
