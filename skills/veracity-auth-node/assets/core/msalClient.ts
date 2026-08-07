// Template: src/auth/msalClient.ts
// Framework-agnostic MSAL ConfidentialClientApplication for Veracity Azure AD B2C (OIDC BFF).
// Shared by the Express / Fastify / NestJS OIDC adapters and the Veracity API client.
// Equivalent of Microsoft.Identity.Web's confidential client + token acquisition in .NET.

import {
  ConfidentialClientApplication,
  type Configuration,
  type AuthorizationUrlRequest,
  type AuthorizationCodeRequest,
  type SilentFlowRequest,
  type AuthenticationResult,
  type AccountInfo,
} from "@azure/msal-node";
import { env, b2cAuthority } from "../config/env.js";

const msalConfig: Configuration = {
  auth: {
    clientId: env.CLIENT_ID!,
    authority: b2cAuthority(),
    clientSecret: env.CLIENT_SECRET!,
    knownAuthorities: [new URL(env.B2C_INSTANCE!).host],
  },
  system: {
    loggerOptions: {
      loggerCallback: () => {},
      piiLoggingEnabled: false,
    },
  },
};

export const cca = new ConfidentialClientApplication(msalConfig);

const scopeList = (env.SCOPES ?? "openid profile email offline_access")
  .split(/\s+/)
  .filter(Boolean);

/** Build the authorization-code + PKCE URL to redirect the browser to B2C. */
export function getAuthCodeUrl(state: string): Promise<string> {
  const request: AuthorizationUrlRequest = {
    scopes: scopeList,
    redirectUri: env.REDIRECT_URI!,
    state,
  };
  return cca.getAuthCodeUrl(request);
}

/** Exchange the authorization code returned on the callback for tokens. */
export function acquireTokenByCode(code: string): Promise<AuthenticationResult> {
  const request: AuthorizationCodeRequest = {
    code,
    scopes: scopeList,
    redirectUri: env.REDIRECT_URI!,
  };
  return cca.acquireTokenByCode(request);
}

/**
 * Acquire a token for a downstream API (e.g. the Veracity Platform API) for the
 * already-signed-in user, using the MSAL token cache. Equivalent of .NET
 * ITokenAcquisition.GetAccessTokenForUserAsync.
 */
export async function acquireTokenSilent(
  account: AccountInfo,
  scopes: string[],
): Promise<AuthenticationResult> {
  const request: SilentFlowRequest = { account, scopes };
  const result = await cca.acquireTokenSilent(request);
  if (!result) {
    throw new Error("Silent token acquisition returned no result");
  }
  return result;
}

export { scopeList };
