// Template (NestJS): src/auth/session-auth.guard.ts
// Session-based auth guard for the OIDC BFF pattern. Unauthenticated requests are rejected
// with 401 (UnauthorizedException) — the machine-readable contract the SPA relies on.
//
// The browser "redirect to /auth/challenge" behavior (used by the Express/Fastify adapters
// for server-rendered navigation) is intentionally NOT done here: a NestJS BFF serves a SPA
// that performs a full-page navigation to `/auth/challenge` itself (see the frontend contract
// in references/oidc.md). Throwing a clean 401 keeps guard semantics correct and avoids
// double-sending a response. Apply with `@UseGuards(SessionAuthGuard)`.

import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from "@nestjs/common";
import type { Request } from "express";

@Injectable()
export class SessionAuthGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const req = context.switchToHttp().getRequest<Request>();
    if (req.session?.user) {
      return true;
    }
    throw new UnauthorizedException("unauthorized");
  }
}
