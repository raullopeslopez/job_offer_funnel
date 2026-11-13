import type { components } from "../api/schema";
import type { Source } from "../theme";

type Offer = Pick<components["schemas"]["OfferRead"], "watched_company_id" | "job_board_id">;
type JobBoard = Pick<components["schemas"]["JobBoardRead"], "id" | "import_method">;

// How an offer reached the inbox: from a watched company, imported from a job board
// (by its import method), or added by hand.
export function offerSourceKind(offer: Offer, jobBoards: JobBoard[]): Source {
  if (offer.watched_company_id) return "watched";
  const method = jobBoards.find((board) => board.id === offer.job_board_id)?.import_method;
  if (method === "api" || method === "rss" || method === "email") return method;
  return "manual";
}
