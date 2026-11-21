// Shared by playwright.config.ts and the steps.
export const E2E_TOKEN = "e2e-token";

// Each worker has its own API (with its own database) and its own Vite proxying to it:
// worker `i` (Playwright's parallelIndex) uses the ports 8001 + i and 5174 + i.
export const apiPort = (worker: number) => 8001 + worker;
export const webPort = (worker: number) => 5174 + worker;
export const apiUrl = (worker: number) => `http://127.0.0.1:${apiPort(worker)}`;
export const webUrl = (worker: number) => `http://127.0.0.1:${webPort(worker)}`;
