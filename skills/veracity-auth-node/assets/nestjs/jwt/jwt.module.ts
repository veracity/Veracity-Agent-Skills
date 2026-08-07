// Template (NestJS): src/auth/jwt.module.ts
// Provides and exports the JwtAuthGuard so feature modules can apply it via @UseGuards.
// There is no session, controller, or login flow for JWT Bearer (stateless validation only).

import { Module } from "@nestjs/common";
import { JwtAuthGuard } from "./jwt-auth.guard.js";

@Module({
  providers: [JwtAuthGuard],
  exports: [JwtAuthGuard],
})
export class JwtModule {}
