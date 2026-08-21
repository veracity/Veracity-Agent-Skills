// Template (NestJS): src/veracity/veracity-v4.controller.ts
// BFF proxy endpoints that call the Veracity Platform API V4 (VTM / Graph) on behalf of the
// signed-in user. Mirrors the .NET VeracityV4Endpoints.cs, exposed under the same versioned
// contract the frontend (veracity-auth-ui) expects — `/api/v1/veracity/v4/...`. Requires an
// authenticated OIDC BFF session (SessionAuthGuard).

import { Controller, Get, Param, Req, Res, UseGuards } from "@nestjs/common";
import type { Request, Response as ExpressResponse } from "express";
import { env } from "../config/env.js";
import { SessionAuthGuard } from "../auth/session-auth.guard.js";
import { VeracityApiService } from "./veracity-api.service.js";

async function forward(res: ExpressResponse, upstream: Response): Promise<void> {
  res.status(upstream.status).json(await upstream.json().catch(() => null));
}

@Controller("api/v1/veracity/v4")
@UseGuards(SessionAuthGuard)
export class VeracityV4Controller {
  constructor(private readonly veracity: VeracityApiService) {}

  // Applications licensed to the current user.
  @Get("me/applications")
  async applications(@Req() req: Request, @Res() res: ExpressResponse): Promise<void> {
    const upstream = await this.veracity.fetch(
      "v4",
      "/me/applications",
      await this.veracity.userApiToken(req),
    );
    await forward(res, upstream);
  }

  // Tenants the current user belongs to.
  @Get("me/tenants")
  async tenants(@Req() req: Request, @Res() res: ExpressResponse): Promise<void> {
    const upstream = await this.veracity.fetch(
      "v4",
      "/me/tenants",
      await this.veracity.userApiToken(req),
    );
    await forward(res, upstream);
  }

  // Validate policies for the configured service; a 406 means the user must accept a policy
  // or lacks a subscription. The service id is read from configuration (VERACITY_SERVICE_ID),
  // not the request, so callers cannot validate an arbitrary application.
  @Get("policy/validate")
  async policy(@Req() req: Request, @Res() res: ExpressResponse): Promise<void> {
    const serviceId = env.VERACITY_SERVICE_ID;
    if (!serviceId) {
      res.status(500).json({ error: "VERACITY_SERVICE_ID is not configured." });
      return;
    }
    const returnUrl = `${req.protocol}://${req.get("host")}`;
    const path = `/me/policy-verifications/${encodeURIComponent(
      serviceId,
    )}?return-url=${encodeURIComponent(returnUrl)}`;
    const upstream = await this.veracity.fetch(
      "v4",
      path,
      await this.veracity.userApiToken(req),
      "POST",
    );
    if (upstream.status === 406) {
      res
        .status(406)
        .json({ compliant: false, redirectUrl: await this.veracity.parsePolicyRedirect(upstream) });
      return;
    }
    // A 403 from the downstream API can carry a redirect URL in its error detail (e.g. the user
    // must accept terms or complete a subscription step). When a redirect URL is present, surface
    // it as a 406 so the client can redirect the user; otherwise it is a genuine authorization
    // failure and is returned as 403.
    if (upstream.status === 403) {
      const redirectUrl = await this.veracity.parsePolicyRedirect(upstream);
      if (redirectUrl) {
        res.status(406).json({ compliant: false, redirectUrl });
        return;
      }
      res.status(403).json({ compliant: false, redirectUrl: null });
      return;
    }
    res.status(upstream.ok ? 200 : upstream.status).json({ compliant: upstream.ok, redirectUrl: null });
  }

  // Applications for a specific tenant.
  @Get("tenants/:tenantId/applications")
  async tenantApplications(
    @Param("tenantId") tenantId: string,
    @Req() req: Request,
    @Res() res: ExpressResponse,
  ): Promise<void> {
    const upstream = await this.veracity.fetch(
      "v4",
      `/tenants/${encodeURIComponent(tenantId)}/applications`,
      await this.veracity.userApiToken(req),
    );
    await forward(res, upstream);
  }
}
