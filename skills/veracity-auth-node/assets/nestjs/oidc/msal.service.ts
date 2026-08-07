// Template (NestJS): src/auth/msal.service.ts
// Injectable wrapper over the framework-agnostic MSAL core (msalClient.ts) so the OIDC
// controller and Veracity services can depend on it via Nest DI.

import { Injectable } from "@nestjs/common";
import type { AccountInfo, AuthenticationResult } from "@azure/msal-node";
import {
  getAuthCodeUrl,
  acquireTokenByCode,
  acquireTokenSilent,
} from "./msalClient.js";

@Injectable()
export class MsalService {
  getAuthCodeUrl(state: string): Promise<string> {
    return getAuthCodeUrl(state);
  }

  acquireTokenByCode(code: string): Promise<AuthenticationResult> {
    return acquireTokenByCode(code);
  }

  acquireTokenSilent(account: AccountInfo, scopes: string[]): Promise<AuthenticationResult> {
    return acquireTokenSilent(account, scopes);
  }
}
