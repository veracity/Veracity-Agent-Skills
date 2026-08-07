// Template (NestJS): src/auth/jwt-auth.guard.ts
// Stateless JWT ****** guard against the Veracity Azure AD B2C tenant, using the shared
// framework-agnostic verifier (src/auth/jwtVerifier.ts). Equivalent of AddJwtBearer in the
// .NET veracity-identity-backend skill. Apply with `@UseGuards(JwtAuthGuard)`.
//
// NOTE (module system): uses ESM-style `.js` import specifiers. Drop the extension if your
// NestJS project compiles to CommonJS (the Nest default).

import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from "@nestjs/common";
import type { Request } from "express";
import type { JWTPayload } from "jose";
import { extractBearer, verifyBearerToken } from "./jwtVerifier.js";

declare module "express-serve-static-core" {
  interface Request {
    user?: JWTPayload;
  }
}

@Injectable()
export class JwtAuthGuard implements CanActivate {
  async canActivate(context: ExecutionContext): Promise<boolean> {
    const req = context.switchToHttp().getRequest<Request>();
    const token = extractBearer(req.headers.authorization);
    if (!token) {
      throw new UnauthorizedException("unauthorized");
    }

    try {
      req.user = await verifyBearerToken(token);
      return true;
    } catch {
      throw new UnauthorizedException("unauthorized");
    }
  }
}
