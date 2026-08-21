// Template (Express): src/veracity/apiV4Routes.ts
// BFF proxy endpoints that call the Veracity Platform API V4 (VTM / Graph) on behalf of the
// signed-in user. Mirrors the .NET VeracityV4Endpoints.cs, exposed under the same versioned
// contract the frontend (veracity-auth-ui) expects — `/api/v1/veracity/v4/...`:
//   GET /api/v1/veracity/v4/me/applications              -> applications licensed to the user
//   GET /api/v1/veracity/v4/me/tenants                   -> tenants the current user belongs to
//   GET /api/v1/veracity/v4/policy/validate              -> policy compliance for the configured service
//   GET /api/v1/veracity/v4/tenants/{tenantId}/applications -> applications for a tenant
//
// These require an authenticated OIDC BFF session (see references/oidc.md). The user's
// Veracity API token is obtained via MSAL acquireTokenSilent for VERACITY_API_SCOPE.

import type { Express, Request, Response } from "express";
import { env } from "../config/env.js";
import { requireAuth } from "../auth/authMiddleware.js";
import {
  userApiToken,
  veracityApiFetch,
  parsePolicyRedirect,
} from "./veracityApiMiddleware.js";

const BASE = "/api/v1/veracity/v4";

export function registerApiV4Routes(app: Express): void {
  // Applications licensed to the current user.
  app.get(`${BASE}/me/applications`, requireAuth, async (req: Request, res: Response) => {
    const upstream = await veracityApiFetch("v4", "/me/applications", await userApiToken(req));
    res.status(upstream.status).json(await upstream.json().catch(() => null));
  });

  // Tenants the current user belongs to.
  app.get(`${BASE}/me/tenants`, requireAuth, async (req: Request, res: Response) => {
    const upstream = await veracityApiFetch("v4", "/me/tenants", await userApiToken(req));
    res.status(upstream.status).json(await upstream.json().catch(() => null));
  });

  // Validate policies for the configured service; a 406 means the user must accept a policy
  // or lacks a subscription. The service (application) id is read from configuration
  // (VERACITY_SERVICE_ID) — the Veracity service this app is connected to — not from the
  // request, so callers cannot validate an arbitrary application.
  app.get(`${BASE}/policy/validate`, requireAuth, async (req: Request, res: Response) => {
    const serviceId = env.VERACITY_SERVICE_ID;
    if (!serviceId) {
      res.status(500).json({ error: "VERACITY_SERVICE_ID is not configured." });
      return;
    }
    const returnUrl = `${req.protocol}://${req.get("host")}`;
    const path = `/me/policy-verifications/${encodeURIComponent(
      serviceId,
    )}?return-url=${encodeURIComponent(returnUrl)}`;
    const upstream = await veracityApiFetch("v4", path, await userApiToken(req), "POST");
    if (upstream.status === 406) {
      res.status(406).json({ compliant: false, redirectUrl: await parsePolicyRedirect(upstream) });
      return;
    }
    // A 403 from the downstream API can carry a redirect URL in its error detail (e.g. the user
    // must accept terms or complete a subscription step). When a redirect URL is present, surface
    // it as a 406 so the client can redirect the user; otherwise it is a genuine authorization
    // failure and is returned as 403.
    if (upstream.status === 403) {
      const redirectUrl = await parsePolicyRedirect(upstream);
      if (redirectUrl) {
        res.status(406).json({ compliant: false, redirectUrl });
        return;
      }
      res.status(403).json({ compliant: false, redirectUrl: null });
      return;
    }
    res.status(upstream.ok ? 200 : upstream.status).json({ compliant: upstream.ok, redirectUrl: null });
  });

  // Applications for a specific tenant.
  app.get(
    `${BASE}/tenants/:tenantId/applications`,
    requireAuth,
    async (req: Request, res: Response) => {
      const upstream = await veracityApiFetch(
        "v4",
        `/tenants/${encodeURIComponent(String(req.params.tenantId))}/applications`,
        await userApiToken(req),
      );
      res.status(upstream.status).json(await upstream.json().catch(() => null));
    },
  );
}
