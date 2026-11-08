import type { components } from "./schema";

type Problem = components["schemas"]["ProblemRead"];
type ValidationProblem = components["schemas"]["ValidationProblemRead"];

// Every API error is RFC 9457 problem details; `type` is its stable slug.
export function isProblem(error: unknown, slug: string): boolean {
  return (error as Problem | undefined)?.type === `/problems/${slug}`;
}

/** Field errors of a 422, keyed by body field (`body.url` → `url`, `body.keywords.1` → `keywords`). */
export function fieldErrors(error: unknown): Record<string, string> {
  if (!isProblem(error, "validation-error")) return {};
  const entries = (error as ValidationProblem).errors.map(({ field, message }) => [
    field.replace(/^body\./, "").replace(/\.\d+$/, ""),
    message,
  ]);
  return Object.fromEntries(entries);
}
