import { setupServer } from "msw/node";

// Simulated API for component tests. Each test registers its handlers with `server.use`.
export const server = setupServer();
