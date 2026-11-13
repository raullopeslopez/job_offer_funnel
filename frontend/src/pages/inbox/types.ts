import type { components } from "../../api/schema";

export type Offer = components["schemas"]["OfferRead"];
export type OfferStatus = components["schemas"]["OfferStatus"];
/** A tab of the inbox: a status, or the pending offers that fit no search profile. */
export type OfferView = OfferStatus | "filtered";
