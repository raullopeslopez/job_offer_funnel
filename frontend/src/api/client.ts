import createClient, { type Middleware } from "openapi-fetch";
import { clearToken, getToken } from "../auth/token";
import type { paths } from "./schema";

const auth: Middleware = {
  onRequest({ request }) {
    const token = getToken();
    if (token && !request.headers.has("Authorization")) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
  onResponse({ response }) {
    // A rejected token sends the user back to the token screen.
    if (response.status === 401) clearToken();
    return response;
  },
};

// Same origin: the Vite proxy (dev) or nginx (`just up`) forwards /api to the API.
export const api = createClient<paths>({
  baseUrl: window.location.origin,
  // Resolve `fetch` on each call, not once at import: lets MSW intercept it in tests.
  fetch: (request) => fetch(request),
});
api.use(auth);
