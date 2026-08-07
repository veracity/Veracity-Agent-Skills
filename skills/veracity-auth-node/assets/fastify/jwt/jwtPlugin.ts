// Template (Fastify): src/auth/jwtPlugin.ts
// Stateless JWT ****** against the Veracity Azure AD B2C tenant as a Fastify preHandler,
// using the shared framework-agnostic verifier (src/auth/jwtVerifier.ts).
// Equivalent of AddJwtBearer in the .NET veracity-identity-backend skill.
//
// Apply per-route or per-scope, e.g.:
//   fastify.get("/api/v1/thing", { preHandler: requireAuth }, handler);
// or register it as an onRequest/preHandler hook on an encapsulated plugin scope.

import type { FastifyRequest, FastifyReply } from "fastify";
import type { JWTPayload } from "jose";
import { extractBearer, verifyBearerToken } from "./jwtVerifier.js";

declare module "fastify" {
  interface FastifyRequest {
    user?: JWTPayload;
  }
}

export async function requireAuth(
  request: FastifyRequest,
  reply: FastifyReply,
): Promise<void> {
  const token = extractBearer(request.headers.authorization);
  if (!token) {
    await reply.code(401).send({ error: "unauthorized" });
    return;
  }

  try {
    request.user = await verifyBearerToken(token);
  } catch {
    await reply.code(401).send({ error: "unauthorized" });
  }
}
