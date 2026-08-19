// Template (Express): src/auth/authMiddleware.ts
// Session-based auth guard for the OIDC BFF pattern.
//   - Unauthenticated requests to /api/*  -> 401 (machine-readable, for API clients)
//   - Other unauthenticated requests       -> redirect to /auth/challenge (browser login)
// Equivalent of the .NET OnRedirectToIdentityProvider "/api" 401 behavior.

import "express-session";
import type { Request, Response, NextFunction } from "express";
import type { SessionUser } from "./claims.js";
import { safeReturnUrl } from "./safeRedirect.js";

export type { SessionUser } from "./claims.js";

declare module "express-session" {
  interface SessionData {
    user?: SessionUser;
    authState?: string;
    returnUrl?: string;
  }
}

export function isAuthenticated(req: Request): boolean {
  return Boolean(req.session?.user);
}

export function requireAuth(req: Request, res: Response, next: NextFunction): void {
  if (isAuthenticated(req)) {
    next();
    return;
  }

  if (req.path.startsWith("/api")) {
    res.status(401).json({ error: "unauthorized" });
    return;
  }

  const returnUrl = encodeURIComponent(safeReturnUrl(req.originalUrl));
  res.redirect(`/auth/challenge?returnUrl=${returnUrl}`);
}
