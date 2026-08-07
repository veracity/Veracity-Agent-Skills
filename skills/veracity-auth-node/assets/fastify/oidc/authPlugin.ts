// Template (Fastify): src/auth/authPlugin.ts
// Session-based auth guard for the OIDC BFF pattern on Fastify.
//   - Unauthenticated requests to /api/*  -> 401 (machine-readable, for API clients)
//   - Other unauthenticated requests       -> redirect to /auth/challenge (browser login)
// Equivalent of the .NET OnRedirectToIdentityProvider "/api" 401 behavior.
//
// Session state lives on `request.session` (from @fastify/session + @fastify/cookie); see
// references/oidc.md for the session/cookie registration (__Host- cookie).

import type { FastifyRequest, FastifyReply } from "fastify";
import "@fastify/session";
import type { SessionUser } from "./claims.js";

export type { SessionUser } from "./claims.js";

declare module "fastify" {
  interface Session {
    user?: SessionUser;
    authState?: string;
    returnUrl?: string;
  }
}

export function isAuthenticated(request: FastifyRequest): boolean {
  return Boolean(request.session?.user);
}

/** Fastify preHandler that enforces an authenticated session. */
export async function requireAuth(
  request: FastifyRequest,
  reply: FastifyReply,
): Promise<void> {
  if (isAuthenticated(request)) {
    return;
  }

  if (request.url.startsWith("/api")) {
    await reply.code(401).send({ error: "unauthorized" });
    return;
  }

  const returnUrl = encodeURIComponent(request.url);
  await reply.redirect(`/auth/challenge?returnUrl=${returnUrl}`);
}
