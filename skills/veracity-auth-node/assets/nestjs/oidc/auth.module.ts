// Template (NestJS): src/auth/auth.module.ts
// Wires the Veracity OIDC BFF pieces into a Nest module: the MSAL service, the session guard,
// and the auth controller. Import AuthModule into your AppModule.
//
// express-session itself is configured in main.ts (see references/oidc.md), not here, because
// it is applied to the underlying Express instance before requests are handled.

import { Module } from "@nestjs/common";
import { AuthController } from "./auth.controller.js";
import { MsalService } from "./msal.service.js";
import { SessionAuthGuard } from "./session-auth.guard.js";

@Module({
  controllers: [AuthController],
  providers: [MsalService, SessionAuthGuard],
  exports: [MsalService, SessionAuthGuard],
})
export class AuthModule {}
