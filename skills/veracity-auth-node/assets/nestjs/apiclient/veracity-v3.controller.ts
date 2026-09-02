// Template (NestJS): src/veracity/veracity-v3.controller.ts
// BFF proxy endpoints that call the Veracity Platform API V3 on behalf of the signed-in user.
// Mirrors the .NET VeracityV3Endpoints.cs, exposed under the same versioned contract the
// frontend (veracity-auth-ui) expects — `/api/v1/veracity/v3/...`. Requires an authenticated
// OIDC BFF session (SessionAuthGuard).

import { Controller, Get, Req, Res, UseGuards } from "@nestjs/common";
import type { Request, Response as ExpressResponse } from "express";
import { SessionAuthGuard } from "../auth/session-auth.guard.js";
import { VeracityApiService } from "./veracity-api.service.js";

async function forward(res: ExpressResponse, upstream: Response): Promise<void> {
  res.status(upstream.status).json(await upstream.json().catch(() => null));
}

@Controller("api/v1/veracity/v3")
@UseGuards(SessionAuthGuard)
export class VeracityV3Controller {
  constructor(private readonly veracity: VeracityApiService) {}

  // Services the current user can access.
  @Get("services")
  async services(@Req() req: Request, @Res() res: ExpressResponse): Promise<void> {
    const upstream = await this.veracity.fetch(
      "v3",
      "/my/services",
      await this.veracity.userApiToken(req),
    );
    await forward(res, upstream);
  }

  // Notification count for the current user.
  @Get("notifications/count")
  async notifications(@Req() req: Request, @Res() res: ExpressResponse): Promise<void> {
    const upstream = await this.veracity.fetch(
      "v3",
      "/my/messages/count",
      await this.veracity.userApiToken(req),
    );
    await forward(res, upstream);
  }

  // Validate Veracity policies; a 406 means the user must accept a policy.
  @Get("policy/validate")
  async policy(@Req() req: Request, @Res() res: ExpressResponse): Promise<void> {
    // `returnUrl` is where Veracity sends the user back after they accept an outstanding policy
    // (mirrors the .NET SDK `my.ValidatePolicies(returnUrl)` and the V4 `return-url` param).
    const returnUrl = `${req.protocol}://${req.get("host")}`;
    const upstream = await this.veracity.fetch(
      "v3",
      `/my/policies/validate()?returnUrl=${encodeURIComponent(returnUrl)}`,
      await this.veracity.userApiToken(req),
    );
    if (upstream.status === 406) {
      res
        .status(406)
        .json({ compliant: false, redirectUrl: await this.veracity.parsePolicyRedirect(upstream) });
      return;
    }
    res.status(upstream.ok ? 200 : upstream.status).json({ compliant: upstream.ok, redirectUrl: null });
  }
}
