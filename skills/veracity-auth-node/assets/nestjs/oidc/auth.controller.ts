// Template (NestJS): src/auth/auth.controller.ts
// BFF auth endpoints for Veracity OpenID Connect. Matches the .NET AuthEndpoints.cs:
//   GET /auth            (anon)     -> { result: boolean }
//   GET /api/me          (required) -> current user
//   GET /auth/challenge  (anon)     -> redirect to B2C login (?returnUrl=)
//   GET /auth/callback   (anon)     -> code exchange, establishes session
//   GET /signOut         (anon)     -> clears session, redirects to Veracity logout
//
// These routes must be reachable at the root (not under a global `/api` prefix). If the app
// calls `app.setGlobalPrefix('api')`, exclude these paths or register this controller so
// `/auth`, `/auth/callback` and `/signOut` stay at the origin root.
//
// NOTE: express-session must be registered in main.ts BEFORE the app handles requests
// (see references/oidc.md for the session config + __Host- cookie).

import { randomUUID } from "node:crypto";
import { Controller, Get, Query, Req, Res, UseGuards } from "@nestjs/common";
import type { Request, Response } from "express";
import { env } from "../config/env.js";
import { mapClaims } from "./claims.js";
import { MsalService } from "./msal.service.js";
import { SessionAuthGuard } from "./session-auth.guard.js";
import "./session.types.js";

@Controller()
export class AuthController {
  constructor(private readonly msal: MsalService) {}

  // Sign-in status check.
  @Get("auth")
  status(@Req() req: Request): { result: boolean } {
    return { result: Boolean(req.session?.user) };
  }

  // Current authenticated user.
  @Get("api/me")
  @UseGuards(SessionAuthGuard)
  me(@Req() req: Request) {
    const user = req.session.user!;
    return {
      id: user.id,
      displayName: user.displayName,
      email: user.email,
      firstName: user.firstName ?? null,
      lastName: user.lastName ?? null,
    };
  }

  // Trigger OIDC login.
  @Get("auth/challenge")
  async challenge(
    @Req() req: Request,
    @Res() res: Response,
    @Query("returnUrl") returnUrl?: string,
  ): Promise<void> {
    const state = randomUUID();
    req.session.authState = state;
    req.session.returnUrl = returnUrl ?? "/";
    const url = await this.msal.getAuthCodeUrl(state);
    res.redirect(url);
  }

  // OIDC redirect URI — exchange code for tokens and establish the session.
  @Get("auth/callback")
  async callback(
    @Req() req: Request,
    @Res() res: Response,
    @Query("code") code?: string,
    @Query("state") state?: string,
  ): Promise<void> {
    if (!code || !state || state !== req.session.authState) {
      res.status(400).json({ error: "invalid_auth_response" });
      return;
    }

    const result = await this.msal.acquireTokenByCode(code);
    const claims = (result.idTokenClaims ?? {}) as Record<string, unknown>;
    req.session.user = mapClaims(claims, result.account!);

    const returnUrl = req.session.returnUrl ?? "/";
    delete req.session.authState;
    delete req.session.returnUrl;
    res.redirect(returnUrl);
  }

  // Sign out: clear the local session and redirect to the Veracity logout page.
  @Get("signOut")
  signOut(@Req() req: Request, @Res() res: Response): void {
    const logoutRedirectUri = env.LOGOUT_REDIRECT_URI ?? "https://www.veracity.com/auth/logout";
    req.session.destroy(() => {
      res.clearCookie("__Host-veracity.session", { path: "/" });
      res.redirect(logoutRedirectUri);
    });
  }
}
