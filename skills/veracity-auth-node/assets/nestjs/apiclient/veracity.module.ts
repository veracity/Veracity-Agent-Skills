// Template (NestJS): src/veracity/veracity.module.ts
// Wires the Veracity API client service + V3/V4 proxy controllers into a Nest module.
// Import VeracityModule into your AppModule (after AuthModule). Include only the controllers
// for the API version(s) you generated.

import { Module } from "@nestjs/common";
import { AuthModule } from "../auth/auth.module.js";
import { VeracityApiService } from "./veracity-api.service.js";
import { VeracityV3Controller } from "./veracity-v3.controller.js";
import { VeracityV4Controller } from "./veracity-v4.controller.js";

@Module({
  imports: [AuthModule],
  controllers: [VeracityV3Controller, VeracityV4Controller],
  providers: [VeracityApiService],
})
export class VeracityModule {}
