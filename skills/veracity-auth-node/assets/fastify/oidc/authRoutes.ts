// Template (Fastify): src/auth/authRoutes.ts
// BFF auth endpoints for Veracity OpenID Connect as a Fastify plugin. Matches the .NET
// AuthEndpoints.cs:
//   GET /auth            (anon)     -> { result: boolean }
//   GET /api/me          (required) -> current user
//   GET /auth/challenge  (anon)     -> redirect to B2C login (?returnUrl=)
//   GET /auth/callback   (anon)     -> code exchange, establishes session
//   GET /signOut         (anon)     -> clears session, redirects to Veracity logout
//
// NOTE: @fastify/cookie + @fastify/session must be registered on the instance BEFORE this
// plugin (see references/oidc.md for the session config + __Host- cookie).

import { randomUUID } from "node:crypto";
import type { FastifyInstance, FastifyPluginAsync } from "fastify";
import "@fastify/cookie";
import { env } from "../config/env.js";
import { getAuthCodeUrl, acquireTokenByCode } from "./msalClient.js";
import { mapClaims } from "./claims.js";
import { isAuthenticated, requireAuth } from "./authPlugin.js";

export const authRoutes: FastifyPluginAsync = async (fastify: FastifyInstance) => {
  // Sign-in status check.
  fastify.get("/auth", async (request) => {
    return { result: isAuthenticated(request) };
  });

  // Current authenticated user.
  fastify.get("/api/me", { preHandler: requireAuth }, async (request) => {
    const user = request.session.user!;
    return {
      id: user.id,
      displayName: user.displayName,
      email: user.email,
      firstName: user.firstName ?? null,
      lastName: user.lastName ?? null,
    };
  });

  // Trigger OIDC login.
  fastify.get<{ Querystring: { returnUrl?: string } }>(
    "/auth/challenge",
    async (request, reply) => {
      const state = randomUUID();
      request.session.authState = state;
      request.session.returnUrl = request.query.returnUrl ?? "/";
      const url = await getAuthCodeUrl(state);
      await reply.redirect(url);
    },
  );

  // OIDC redirect URI — exchange code for tokens and establish the session.
  fastify.get<{ Querystring: { code?: string; state?: string } }>(
    "/auth/callback",
    async (request, reply) => {
      const { code, state } = request.query;
      if (!code || !state || state !== request.session.authState) {
        await reply.code(400).send({ error: "invalid_auth_response" });
        return;
      }

      const result = await acquireTokenByCode(code);
      const claims = (result.idTokenClaims ?? {}) as Record<string, unknown>;
      request.session.user = mapClaims(claims, result.account!);

      const returnUrl = request.session.returnUrl ?? "/";
      request.session.authState = undefined;
      request.session.returnUrl = undefined;
      await reply.redirect(returnUrl);
    },
  );

  // Sign out: clear the local session and redirect to the Veracity logout page.
  fastify.get("/signOut", async (request, reply) => {
    const logoutRedirectUri = env.LOGOUT_REDIRECT_URI ?? "https://www.veracity.com/auth/logout";
    await request.session.destroy();
    await reply.clearCookie("__Host-veracity.session", { path: "/" }).redirect(logoutRedirectUri);
  });
};
