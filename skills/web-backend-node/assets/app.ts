// Template: src/app.ts
// Express application wiring: security headers, body parsing, health checks, error
// handler, and the versioned API router anchor. This baseline has NO authentication —
// auth middleware is layered on later by an auth skill (e.g. veracity-auth-node).

import express, { type Express, type NextFunction, type Request, type Response } from "express";
import helmet from "helmet";
import { apiV1 } from "./routes/apiV1.js";

export function createApp(): Express {
  const app = express();

  app.set("trust proxy", 1);

  // Security headers (equivalent of the .NET SecurityHeadersMiddleware + CSP).
  // CSP defaults are intentionally generic ('self'-only) so the baseline has no
  // external dependencies. Auth skills extend these directives when they add their
  // own CDN and login endpoints.
  app.use(
    helmet({
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          scriptSrc: ["'self'"],
          styleSrc: ["'self'", "'unsafe-inline'"],
          imgSrc: ["'self'", "data:"],
          connectSrc: ["'self'"],
        },
      },
    }),
  );

  app.use(express.json());

  // --- Health checks (always anonymous, registered before any auth middleware) ---
  app.get("/health", (_req: Request, res: Response) => {
    res.json({ status: "healthy" });
  });
  app.get("/health/ready", (_req: Request, res: Response) => {
    res.json({ status: "ready" });
  });
  app.get("/health/live", (_req: Request, res: Response) => {
    res.json({ status: "live" });
  });

  // --- Auth middleware is wired here by an auth skill (before the versioned API) ---

  // --- Versioned API anchor (equivalent of the .NET versioned apiGroup) ---
  // New feature routes hang off apiV1 (src/routes/apiV1.ts). It starts out empty;
  // the baseline is unauthenticated — an auth skill protects it.
  app.use("/api/v1", apiV1);

  // --- Global error handler (equivalent of the .NET ProblemDetails handler) ---
  // Registered last. Returns an application/problem+json style body without leaking
  // internals in production.
  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    // eslint-disable-next-line no-console
    console.error(err);
    res.status(500).json({
      type: "https://tools.ietf.org/html/rfc9110#section-15.6.1",
      title: "An error occurred while processing your request.",
      status: 500,
    });
  });

  return app;
}
