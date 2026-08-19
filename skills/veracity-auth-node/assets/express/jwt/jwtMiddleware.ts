// Template (Express): src/auth/jwtMiddleware.ts
// Stateless JWT ****** against the Veracity Azure AD B2C tenant, using the shared
// framework-agnostic verifier (src/auth/jwtVerifier.ts).
// Equivalent of AddJwtBearer in the .NET veracity-identity-backend skill.

import type { Request, Response, NextFunction } from "express";
import type { JWTPayload } from "jose";
import { extractBearer, verifyBearerToken } from "./jwtVerifier.js";

declare module "express-serve-static-core" {
  interface Request {
    user?: JWTPayload;
  }
}

export async function requireAuth(
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<void> {
  const token = extractBearer(req.headers.authorization);
  if (!token) {
    res.status(401).json({ error: "unauthorized" });
    return;
  }

  try {
    req.user = await verifyBearerToken(token);
    next();
  } catch {
    res.status(401).json({ error: "unauthorized" });
  }
}
