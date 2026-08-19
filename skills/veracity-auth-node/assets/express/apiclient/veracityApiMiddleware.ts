// Template (Express): src/veracity/veracityApiMiddleware.ts
// Express-specific glue over the shared Veracity API client core (veracityApiClient.ts).
// Re-exports the raw-fetch helpers and adds `userApiToken(req)` which reads the signed-in
// user's MSAL account from the session and acquires a Veracity API token for them.

import type { Request } from "express";
import {
  acquireUserApiToken,
  veracityApiFetch,
  parsePolicyRedirect,
  createVeracityClient,
  type ApiVersion,
  type GetAccessToken,
} from "./veracityApiClient.js";

export { veracityApiFetch, parsePolicyRedirect, createVeracityClient };
export type { ApiVersion, GetAccessToken };

/** Acquire a Veracity API token for the signed-in user on this request. */
export function userApiToken(req: Request): Promise<string> {
  const account = req.session.user?.account;
  if (!account) {
    throw new Error("No authenticated user on request.");
  }
  return acquireUserApiToken(account);
}
