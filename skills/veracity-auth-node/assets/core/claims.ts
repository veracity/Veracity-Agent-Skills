// Template: src/auth/claims.ts
// Framework-agnostic user model + ID-token claim mapping shared by the Express / Fastify /
// NestJS OIDC adapters. Keeps the shape of the session user in one place.

import type { AccountInfo } from "@azure/msal-node";

// Shape stored in the session after a successful sign-in.
export interface SessionUser {
  account: AccountInfo;
  id: string;
  displayName: string;
  email: string;
  firstName?: string;
  lastName?: string;
}

/** Map raw B2C ID-token claims + the MSAL account into the SessionUser shape. */
export function mapClaims(
  claims: Record<string, unknown>,
  account: AccountInfo,
): SessionUser {
  const emails = claims["emails"];
  const email =
    (Array.isArray(emails) ? (emails[0] as string) : (claims["email"] as string)) ?? "";
  return {
    account,
    id: (claims["sub"] as string) ?? (claims["oid"] as string) ?? account.homeAccountId,
    displayName: (claims["name"] as string) ?? "",
    email,
    firstName: claims["given_name"] as string | undefined,
    lastName: claims["family_name"] as string | undefined,
  };
}
