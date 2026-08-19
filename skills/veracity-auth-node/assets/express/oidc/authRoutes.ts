// Template (Express): src/auth/authRoutes.ts
// BFF auth endpoints for Veracity OpenID Connect. Matches the .NET AuthEndpoints.cs:
//   GET /auth            (anon)     -> { result: boolean }
//   GET /api/me          (required) -> current user
//   GET /auth/challenge  (anon)     -> redirect to B2C login (?returnUrl=)
//   GET /auth/callback   (anon)     -> code exchange, establishes session
//   GET /signOut         (anon)     -> clears session, redirects to Veracity logout
//
// NOTE: express-session middleware must be registered on the app BEFORE calling
// registerAuthRoutes (see references/oidc.md for the session config + __Host- cookie).

import { randomUUID } from "node:crypto";
import type { Express, Request, Response } from "express";
import { env } from "../config/env.js";
import { getAuthCodeUrl, acquireTokenByCode } from "./msalClient.js";
import { mapClaims } from "./claims.js";
import { isAuthenticated, requireAuth } from "./authMiddleware.js";
import { safeReturnUrl } from "./safeRedirect.js";

export function registerAuthRoutes(app: Express): void {
  // Sign-in status check.
  app.get("/auth", (req: Request, res: Response) => {
    res.json({ result: isAuthenticated(req) });
  });

  // Current authenticated user.
  app.get("/api/me", requireAuth, (req: Request, res: Response) => {
    const user = req.session.user!;
    res.json({
      id: user.id,
      displayName: user.displayName,
      email: user.email,
      firstName: user.firstName ?? null,
      lastName: user.lastName ?? null,
    });
  });

  // Trigger OIDC login.
  app.get("/auth/challenge", async (req: Request, res: Response) => {
    const state = randomUUID();
    req.session.authState = state;
    req.session.returnUrl = safeReturnUrl(req.query.returnUrl);
    const url = await getAuthCodeUrl(state);
    res.redirect(url);
  });

  // OIDC redirect URI — exchange code for tokens and establish the session.
  app.get("/auth/callback", async (req: Request, res: Response) => {
    const code = req.query.code as string | undefined;
    const state = req.query.state as string | undefined;
    if (!code || !state || state !== req.session.authState) {
      res.status(400).json({ error: "invalid_auth_response" });
      return;
    }

    const result = await acquireTokenByCode(code);
    const claims = (result.idTokenClaims ?? {}) as Record<string, unknown>;
    req.session.user = mapClaims(claims, result.account!);

    const returnUrl = safeReturnUrl(req.session.returnUrl);
    delete req.session.authState;
    delete req.session.returnUrl;
    res.redirect(returnUrl);
  });

  // Sign out: clear the local session and redirect to the Veracity logout page.
  app.get("/signOut", (req: Request, res: Response) => {
    const logoutRedirectUri = env.LOGOUT_REDIRECT_URI ?? "https://www.veracity.com/auth/logout";
    req.session.destroy(() => {
      res.clearCookie("__Host-veracity.session", { path: "/" });
      res.redirect(logoutRedirectUri);
    });
  });
}
