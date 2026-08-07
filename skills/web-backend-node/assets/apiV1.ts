// Template: src/routes/apiV1.ts
// The versioned API router anchor (equivalent of the .NET versioned apiGroup).
// New feature routes hang off this router:
//
//   apiV1.get("/my-feature", (req, res) => { ... });
//
// It starts out empty; the baseline is unauthenticated — an auth skill (e.g.
// veracity-auth-node) protects it by inserting auth middleware before it in app.ts.

import { Router } from "express";

export const apiV1: Router = Router();
