// Template (NestJS): src/veracity/veracity-api.service.ts
// Injectable wrapper over the framework-agnostic Veracity API client core
// (veracityApiClient.ts). Reads the signed-in user's MSAL account from the session and
// acquires a Veracity API token for them; exposes the raw upstream fetch + policy-redirect
// helpers the controllers forward.

import { Injectable } from "@nestjs/common";
import type { Request } from "express";
import {
  acquireUserApiToken,
  veracityApiFetch,
  parsePolicyRedirect,
  type ApiVersion,
} from "./veracityApiClient.js";
import "../auth/session.types.js";

@Injectable()
export class VeracityApiService {
  /** Acquire a Veracity API token for the signed-in user on this request. */
  userApiToken(req: Request): Promise<string> {
    const account = req.session.user?.account;
    if (!account) {
      throw new Error("No authenticated user on request.");
    }
    return acquireUserApiToken(account);
  }

  fetch(
    version: ApiVersion,
    path: string,
    token: string,
    method: "GET" | "POST" = "GET",
  ): Promise<Response> {
    return veracityApiFetch(version, path, token, method);
  }

  parsePolicyRedirect(response: Response): Promise<string | null> {
    return parsePolicyRedirect(response);
  }
}
