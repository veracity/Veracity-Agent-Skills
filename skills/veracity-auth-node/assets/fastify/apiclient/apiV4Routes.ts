// Template (Fastify): src/veracity/apiV4Routes.ts
// BFF proxy endpoints (Fastify plugin) that call the Veracity Platform API V4 (VTM / Graph) on
// behalf of the signed-in user. Mirrors the .NET VeracityV4Endpoints.cs, exposed under the same
// versioned contract the frontend (veracity-auth-ui) expects — `/api/v1/veracity/v4/...`.
//
// Requires an authenticated OIDC BFF session (see references/oidc.md).

import type { FastifyInstance, FastifyPluginAsync, FastifyReply } from "fastify";
import { env } from "../config/env.js";
import { requireAuth } from "../auth/authPlugin.js";
import {
  userApiToken,
  veracityApiFetch,
  parsePolicyRedirect,
} from "./veracityApiHelpers.js";

const BASE = "/api/v1/veracity/v4";

async function forward(reply: FastifyReply, upstream: Response): Promise<void> {
  await reply.code(upstream.status).send(await upstream.json().catch(() => null));
}

export const apiV4Routes: FastifyPluginAsync = async (fastify: FastifyInstance) => {
  // Applications licensed to the current user.
  fastify.get(`${BASE}/me/applications`, { preHandler: requireAuth }, async (request, reply) => {
    const upstream = await veracityApiFetch("v4", "/me/applications", await userApiToken(request));
    await forward(reply, upstream);
  });

  // Tenants the current user belongs to.
  fastify.get(`${BASE}/me/tenants`, { preHandler: requireAuth }, async (request, reply) => {
    const upstream = await veracityApiFetch("v4", "/me/tenants", await userApiToken(request));
    await forward(reply, upstream);
  });

  // Validate policies for the configured service; a 406 means the user must accept a policy
  // or lacks a subscription. The service id is read from configuration (VERACITY_SERVICE_ID),
  // not the request, so callers cannot validate an arbitrary application.
  fastify.get(`${BASE}/policy/validate`, { preHandler: requireAuth }, async (request, reply) => {
    const serviceId = env.VERACITY_SERVICE_ID;
    if (!serviceId) {
      await reply.code(500).send({ error: "VERACITY_SERVICE_ID is not configured." });
      return;
    }
    const returnUrl = `${request.protocol}://${request.host}`;
    const path = `/me/policy-verifications/${encodeURIComponent(
      serviceId,
    )}?return-url=${encodeURIComponent(returnUrl)}`;
    const upstream = await veracityApiFetch("v4", path, await userApiToken(request), "POST");
    if (upstream.status === 406) {
      await reply
        .code(406)
        .send({ compliant: false, redirectUrl: await parsePolicyRedirect(upstream) });
      return;
    }
    // A 403 from the downstream API can carry a redirect URL in its error detail (e.g. the user
    // must accept terms or complete a subscription step). When a redirect URL is present, surface
    // it as a 406 so the client can redirect the user; otherwise it is a genuine authorization
    // failure and is returned as 403.
    if (upstream.status === 403) {
      const redirectUrl = await parsePolicyRedirect(upstream);
      if (redirectUrl) {
        await reply.code(406).send({ compliant: false, redirectUrl });
        return;
      }
      await reply.code(403).send({ compliant: false, redirectUrl: null });
      return;
    }
    await reply
      .code(upstream.ok ? 200 : upstream.status)
      .send({ compliant: upstream.ok, redirectUrl: null });
  });

  // Applications for a specific tenant.
  fastify.get<{ Params: { tenantId: string } }>(
    `${BASE}/tenants/:tenantId/applications`,
    { preHandler: requireAuth },
    async (request, reply) => {
      const upstream = await veracityApiFetch(
        "v4",
        `/tenants/${encodeURIComponent(request.params.tenantId)}/applications`,
        await userApiToken(request),
      );
      await forward(reply, upstream);
    },
  );
};
