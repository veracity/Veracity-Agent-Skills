// Template (Express): src/veracity/apiV3Routes.ts
// BFF proxy endpoints that call the Veracity Platform API V3 on behalf of the signed-in user.
// Mirrors the .NET VeracityV3Endpoints.cs, exposed under the same versioned contract the
// frontend (veracity-auth-ui) expects — `/api/v1/veracity/v3/...`:
//   GET /api/v1/veracity/v3/services            -> services the current user can access
//   GET /api/v1/veracity/v3/notifications/count -> notification count for the current user
//   GET /api/v1/veracity/v3/policy/validate     -> policy compliance; on 406 -> { compliant, redirectUrl }
//
// These require an authenticated OIDC BFF session (see references/oidc.md). The user's
// Veracity API token is obtained via MSAL acquireTokenSilent for VERACITY_API_SCOPE.

import type { Express, Request, Response } from "express";
import { requireAuth } from "../auth/authMiddleware.js";
import {
  userApiToken,
  veracityApiFetch,
  parsePolicyRedirect,
} from "./veracityApiMiddleware.js";

const BASE = "/api/v1/veracity/v3";

export function registerApiV3Routes(app: Express): void {
  // Services the current user can access.
  app.get(`${BASE}/services`, requireAuth, async (req: Request, res: Response) => {
    const upstream = await veracityApiFetch("v3", "/my/services", await userApiToken(req));
    res.status(upstream.status).json(await upstream.json().catch(() => null));
  });

  // Notification count for the current user.
  app.get(`${BASE}/notifications/count`, requireAuth, async (req: Request, res: Response) => {
    const upstream = await veracityApiFetch("v3", "/my/messages/count", await userApiToken(req));
    res.status(upstream.status).json(await upstream.json().catch(() => null));
  });

  // Validate Veracity policies; a 406 means the user must accept a policy.
  app.get(`${BASE}/policy/validate`, requireAuth, async (req: Request, res: Response) => {
    // `returnUrl` is where Veracity sends the user back after they accept an outstanding policy
    // (mirrors the .NET SDK `my.ValidatePolicies(returnUrl)` and the V4 `return-url` param).
    const returnUrl = `${req.protocol}://${req.get("host")}`;
    const upstream = await veracityApiFetch(
      "v3",
      `/my/policies/validate()?returnUrl=${encodeURIComponent(returnUrl)}`,
      await userApiToken(req),
    );
    if (upstream.status === 406) {
      res.status(406).json({ compliant: false, redirectUrl: await parsePolicyRedirect(upstream) });
      return;
    }
    res.status(upstream.ok ? 200 : upstream.status).json({ compliant: upstream.ok, redirectUrl: null });
  });
}
