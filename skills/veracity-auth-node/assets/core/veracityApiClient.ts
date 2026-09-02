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
  // The Veracity Platform API (V3/V4) sits behind Azure API Management, which requires an
  // Ocp-Apim-Subscription-Key on every call *in addition* to the bearer token. When the key is
  // missing, APIM rejects the request with 401 — which the BFF proxy surfaces as an opaque
  // 502 Bad Gateway (upstreamStatus 401). Fail fast here with an actionable message instead, so a
  // forgotten key is diagnosed at the call site rather than as a confusing gateway error.
  if (!env.VERACITY_SUBSCRIPTION_KEY) {
    throw new Error(
      "VERACITY_SUBSCRIPTION_KEY is not set. The Veracity Platform API (V3/V4) is behind Azure " +
        "API Management and requires an Ocp-Apim-Subscription-Key header; without it the API " +
        "returns 401. Set VERACITY_SUBSCRIPTION_KEY in .env.local — get the key from the " +
        "Developer Portal (https://developer.veracity.com) -> your app resource -> Settings.",
    );
  }
  headers.set("Ocp-Apim-Subscription-Key", env.VERACITY_SUBSCRIPTION_KEY);
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
 * Allow-list of outbound origins for the Veracity API, derived from the configured base URLs.
 * Any resolved request URL whose origin is not in this set is refused (CWE-918 SSRF guard).
 */
function allowedApiOrigins(): Set<string> {
  const origins = new Set<string>();
  for (const base of [env.VERACITY_API_V3_BASE_URL, env.VERACITY_API_V4_BASE_URL]) {
    if (base) {
      origins.add(new URL(base).origin);
    }
  }
  return origins;
}

/**
 * Resolve a caller-supplied **relative** API `path` against the configured Veracity base URL for
 * `version` and validate the result against the allow-list of Veracity origins. Rejects absolute
 * URLs, protocol-relative authorities (`//host`), and anything that resolves off the expected
 * origin, so an upstream-influenced value cannot redirect the server-side request (CWE-918 SSRF).
 */
export function resolveVeracityApiUrl(version: ApiVersion, path: string): URL {
  // Reject anything that is not a plain, single-slash root-relative path. Blocking `//host`,
  // backslashes (`/\host`, normalized to `//` by the URL parser for special schemes), control
  // characters, and any embedded scheme means `path` can only ever be a relative path — it can
  // never carry an authority that redirects the request off-origin (CWE-918).
  if (
    typeof path !== "string" ||
    !path.startsWith("/") ||
    path.startsWith("//") ||
    path.startsWith("/\\") ||
    path.includes("\\") ||
    path.includes("://") ||
    // eslint-disable-next-line no-control-regex
    /[\u0000-\u001f\u007f]/.test(path)
  ) {
    throw new Error(
      `Invalid Veracity API path (must be a relative path starting with a single "/"): ${path}`,
    );
  }
  const base = baseUrlFor(version);
  // Append the validated relative `path` to the trusted base. Because `path` is guaranteed to be a
  // plain root-relative path (no authority, no scheme, no backslashes), the resulting origin is
  // ALWAYS the base's origin and can never be influenced by the caller.
  const url = new URL(`${base}${path}`);
  // Defense-in-depth: re-assert the origin against the configured allow-list at the point the URL
  // is built, so the ONLY thing that can ever reach fetch() is a configured Veracity origin.
  if (url.origin !== new URL(base).origin || !allowedApiOrigins().has(url.origin)) {
    throw new Error(`Refusing to call a non-allow-listed Veracity API origin: ${url.origin}`);
  }
  return url;
}

/**
 * Raw fetch against the Veracity API (used by the BFF proxy endpoints, which simply forward
 * the upstream response). Adds the ****** + subscription key. The path is relative to the
 * version base URL (e.g. "/my/services") and is validated against the Veracity origin allow-list
 * before the request is issued (CWE-918 SSRF guard).
 */
export function veracityApiFetch(
  version: ApiVersion,
  path: string,
  token: string,
  method: "GET" | "POST" = "GET",
): Promise<Response> {
  const url = resolveVeracityApiUrl(version, path);
  // Inline SSRF guard at the sink: even though resolveVeracityApiUrl already validated the origin,
  // re-assert it here so the neutralization is visible in the same function as the fetch() call.
  if (!allowedApiOrigins().has(url.origin)) {
    throw new Error(`Refusing to fetch non-allow-listed Veracity API origin: ${url.origin}`);
  }
  const headers = new Headers();
  withAuthHeaders(headers, token);
  headers.set("Accept", "application/json");
  return fetch(url, { method, headers });
}

/**
 * Coerce a candidate redirect value to a well-formed absolute `https:` URL, or `null`.
 * The value here comes from the Veracity policy-validation response, which is trusted
 * upstream content (reached server-side through the origin allow-list in
 * `resolveVeracityApiUrl`, authenticated + subscription-keyed). This is therefore only a
 * minimal sanity net — not host validation — ensuring a malformed or non-`https` value can
 * never flow through to a client-side redirect.
 */
function sanitizePolicyRedirect(candidate: unknown): string | null {
  if (typeof candidate !== "string" || candidate.trim() === "") {
    return null;
  }
  try {
    const url = new URL(candidate.trim());
    return url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

/**
 * Parse the redirect URL from a Veracity policy-validation 406 response. The body/headers
 * carry the URL the user must visit to accept a policy or add a subscription. The value is
 * trusted upstream content (see `sanitizePolicyRedirect`) but is still constrained to a
 * well-formed absolute `https:` URL before it is surfaced to the client.
 */
export async function parsePolicyRedirect(response: Response): Promise<string | null> {
  const location = response.headers.get("location");
  if (location) {
    return sanitizePolicyRedirect(location);
  }
  try {
    const body = (await response.clone().json()) as { url?: string; redirectUrl?: string };
    return sanitizePolicyRedirect(body.url ?? body.redirectUrl ?? null);
  } catch {
    return null;
  }
}
