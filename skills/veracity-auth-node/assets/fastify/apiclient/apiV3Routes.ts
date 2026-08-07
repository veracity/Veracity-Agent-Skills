// Template (Fastify): src/veracity/apiV3Routes.ts
// BFF proxy endpoints (Fastify plugin) that call the Veracity Platform API V3 on behalf of the
// signed-in user. Mirrors the .NET VeracityV3Endpoints.cs, exposed under the same versioned
// contract the frontend (veracity-auth-ui) expects — `/api/v1/veracity/v3/...`.
//
// Requires an authenticated OIDC BFF session (see references/oidc.md).

import type { FastifyInstance, FastifyPluginAsync, FastifyReply } from "fastify";
import { requireAuth } from "../auth/authPlugin.js";
import {
  userApiToken,
  veracityApiFetch,
  parsePolicyRedirect,
} from "./veracityApiHelpers.js";

const BASE = "/api/v1/veracity/v3";

async function forward(reply: FastifyReply, upstream: Response): Promise<void> {
  await reply.code(upstream.status).send(await upstream.json().catch(() => null));
}

export const apiV3Routes: FastifyPluginAsync = async (fastify: FastifyInstance) => {
  // Services the current user can access.
  fastify.get(`${BASE}/services`, { preHandler: requireAuth }, async (request, reply) => {
    const upstream = await veracityApiFetch("v3", "/my/services", await userApiToken(request));
    await forward(reply, upstream);
  });

  // Notification count for the current user.
  fastify.get(
    `${BASE}/notifications/count`,
    { preHandler: requireAuth },
    async (request, reply) => {
      const upstream = await veracityApiFetch(
        "v3",
        "/my/messages/count",
        await userApiToken(request),
      );
      await forward(reply, upstream);
    },
  );

  // Validate Veracity policies; a 406 means the user must accept a policy.
  fastify.get(`${BASE}/policy/validate`, { preHandler: requireAuth }, async (request, reply) => {
    const upstream = await veracityApiFetch(
      "v3",
      "/my/policies/validate()",
      await userApiToken(request),
    );
    if (upstream.status === 406) {
      await reply
        .code(406)
        .send({ compliant: false, redirectUrl: await parsePolicyRedirect(upstream) });
      return;
    }
    await reply
      .code(upstream.ok ? 200 : upstream.status)
      .send({ compliant: upstream.ok, redirectUrl: null });
  });
};
