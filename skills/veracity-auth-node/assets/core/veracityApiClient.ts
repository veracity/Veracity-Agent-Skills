// Template: src/veracity/veracityApiClient.ts
// Framework-agnostic Veracity Platform API client core. Shared by the Express routes,
// Fastify plugins, and NestJS controllers. Equivalent of the .NET VeracityApiAuthHandler
// (DelegatingHandler) that attaches the ****** + Ocp-Apim-Subscription-Key, plus the
// raw-fetch helpers the BFF proxy endpoints use.
//
// The generated openapi-fetch types come from `npm run veracity:gen`:
//   import type { paths as V3Paths } from "./generated/apiV3.js";
//   import type { paths as V4Paths } from "./generated/apiV4.js";
// Remove the version (V3 or V4) you did not generate.

import createClient, { type Middleware } from "openapi-fetch";
import type { AccountInfo } from "@azure/msal-node";
import { env } from "../config/env.js";
import { acquireTokenSilent } from "../auth/msalClient.js";
// import type { paths as V3Paths } from "./generated/apiV3.js";
// import type { paths as V4Paths } from "./generated/apiV4.js";

export type ApiVersion = "v3" | "v4";

/** Async function that returns a Veracity API access token for the current user. */
export type GetAccessToken = () => Promise<string>;

function baseUrlFor(version: ApiVersion): string {
  const url = version === "v3" ? env.VERACITY_API_V3_BASE_URL : env.VERACITY_API_V4_BASE_URL;
  if (!url) {
    throw new Error(`Missing base URL for Veracity API ${version}`);
  }
  return url.replace(/\/$/, "");
}

/**
 * Acquire a Veracity API access token for the signed-in user's MSAL account, using the
 * VERACITY_API_SCOPE. Framework adapters read the account from their session/request and
 * call this. Equivalent of .NET ITokenAcquisition.GetAccessTokenForUserAsync.
 */
export async function acquireUserApiToken(account: AccountInfo): Promise<string> {
  const scope = env.VERACITY_API_SCOPE;
  if (!scope) {
    throw new Error("VERACITY_API_SCOPE is not configured.");
  }
  const result = await acquireTokenSilent(account, [scope]);
  return result.accessToken;
}

function withAuthHeaders(headers: Headers, token: string): void {
  headers.set("Authorization", `Bearer ${token}`);
  if (env.VERACITY_SUBSCRIPTION_KEY) {
    headers.set("Ocp-Apim-Subscription-Key", env.VERACITY_SUBSCRIPTION_KEY);
  }
}

function authMiddleware(getAccessToken: GetAccessToken): Middleware {
  return {
    async onRequest({ request }) {
      withAuthHeaders(request.headers, await getAccessToken());
      return request;
    },
  };
}

/**
 * Build a typed openapi-fetch client for the requested Veracity API version.
 * Pass the generated `paths` type as the type parameter, e.g.:
 *   createVeracityClient<V3Paths>("v3", getAccessToken)
 */
export function createVeracityClient<Paths extends object>(
  version: ApiVersion,
  getAccessToken: GetAccessToken,
) {
  const client = createClient<Paths>({ baseUrl: baseUrlFor(version) });
  client.use(authMiddleware(getAccessToken));
  return client;
}

/**
 * Raw fetch against the Veracity API (used by the BFF proxy endpoints, which simply forward
 * the upstream response). Adds the ****** + subscription key. The path is relative to the
 * version base URL (e.g. "/my/services").
 */
export function veracityApiFetch(
  version: ApiVersion,
  path: string,
  token: string,
  method: "GET" | "POST" = "GET",
): Promise<Response> {
  const headers = new Headers();
  withAuthHeaders(headers, token);
  headers.set("Accept", "application/json");
  return fetch(`${baseUrlFor(version)}${path}`, { method, headers });
}

/**
 * Parse the redirect URL from a Veracity policy-validation 406 response. The body/headers
 * carry the URL the user must visit to accept a policy or add a subscription.
 */
export async function parsePolicyRedirect(response: Response): Promise<string | null> {
  const location = response.headers.get("location");
  if (location) {
    return location;
  }
  try {
    const body = (await response.clone().json()) as { url?: string; redirectUrl?: string };
    return body.url ?? body.redirectUrl ?? null;
  } catch {
    return null;
  }
}
