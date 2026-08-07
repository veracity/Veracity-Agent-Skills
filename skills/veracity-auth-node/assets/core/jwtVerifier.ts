// Template: src/auth/jwtVerifier.ts
// Framework-agnostic Veracity JWT ****** validation against the Azure AD B2C tenant using
// `jose`. Shared by the Express middleware, Fastify hook, and NestJS guard adapters.
// Equivalent of AddJwtBearer in the .NET veracity-identity-backend skill.
//   - Validates issuer, audience, lifetime, and signature
//   - clockTolerance: 60s (matches the .NET ClockSkew = TimeSpan.FromMinutes(1))

import { createRemoteJWKSet, jwtVerify, type JWTPayload } from "jose";
import { env } from "../config/env.js";

// Authority OIDC metadata; derive issuer + JWKS at first use.
const authority = env.JWT_AUTHORITY!;

let jwks: ReturnType<typeof createRemoteJWKSet> | undefined;
let issuer: string | undefined;

async function getValidationContext(): Promise<{
  jwks: ReturnType<typeof createRemoteJWKSet>;
  issuer: string;
}> {
  if (!jwks || !issuer) {
    const metadataUrl = `${authority.replace(/\/$/, "")}/.well-known/openid-configuration`;
    const res = await fetch(metadataUrl);
    if (!res.ok) {
      throw new Error(`Failed to fetch OIDC metadata: ${res.status}`);
    }
    const metadata = (await res.json()) as { issuer: string; jwks_uri: string };
    issuer = metadata.issuer;
    jwks = createRemoteJWKSet(new URL(metadata.jwks_uri));
  }
  return { jwks, issuer };
}

/** Extract the bearer token from an Authorization header value, or null if absent/malformed. */
export function extractBearer(header: string | undefined | null): string | null {
  if (!header?.startsWith("Bearer ")) {
    return null;
  }
  const token = header.slice("Bearer ".length).trim();
  return token.length > 0 ? token : null;
}

/**
 * Verify a Veracity access token (issuer, audience, lifetime, signature).
 * Resolves the decoded claims on success; throws on any validation failure.
 */
export async function verifyBearerToken(token: string): Promise<JWTPayload> {
  const { jwks: keys, issuer: iss } = await getValidationContext();
  const { payload } = await jwtVerify(token, keys, {
    issuer: iss,
    audience: env.JWT_AUDIENCE!,
    clockTolerance: 60,
  });
  return payload;
}
