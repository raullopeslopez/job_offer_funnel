import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { server } from "./server";
import { matchMedia, resetViewport } from "./viewport";

beforeAll(() => {
  server.listen({ onUnhandledFrame: "error" });
  window.matchMedia = matchMedia;
});
afterEach(() => {
  cleanup();
  server.resetHandlers();
  localStorage.clear();
  resetViewport();
});
afterAll(() => server.close());
