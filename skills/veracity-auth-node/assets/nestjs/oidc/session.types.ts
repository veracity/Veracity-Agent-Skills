// Template (NestJS): src/auth/session.types.ts
// express-session augmentation shared by the NestJS OIDC guard, controller and Veracity
// controllers. NestJS runs on the Express platform by default, so the session lives on
// `req.session` exactly as in the Express adapter.
//
// NOTE (module system): these templates use ESM-style `.js` import specifiers. If your
// NestJS project compiles to CommonJS (the Nest default — "module": "commonjs"), drop the
// `.js` extension from the relative imports in every copied file to match your tsconfig.

import "express-session";
import type { SessionUser } from "./claims.js";

export type { SessionUser } from "./claims.js";

declare module "express-session" {
  interface SessionData {
    user?: SessionUser;
    authState?: string;
    returnUrl?: string;
  }
}
