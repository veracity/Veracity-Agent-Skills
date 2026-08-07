// Template: src/config/env.ts
// zod-validated environment loader. Equivalent of appsettings + dotnet user-secrets.
// Loading order (last wins): .env -> .env.<NODE_ENV> -> .env.local
//
// Auth skills (e.g. veracity-auth-node) extend this schema with their own fields.

import { config as loadEnv } from "dotenv";
import { z } from "zod";

const nodeEnv = process.env.NODE_ENV ?? "development";

// Last file loaded wins; dotenv does not override already-set vars, so load most-specific last.
loadEnv({ path: ".env" });
loadEnv({ path: `.env.${nodeEnv}` });
loadEnv({ path: ".env.local", override: true });

const schema = z.object({
  NODE_ENV: z.string().default("development"),
  PORT: z.coerce.number().default(54438),

  // --- HTTPS local dev (optional; parity with the .NET baseline's HTTPS default) ---
  TLS_CERT_FILE: z.string().optional(),
  TLS_KEY_FILE: z.string().optional(),
});

const parsed = schema.safeParse(process.env);

if (!parsed.success) {
  console.error("Invalid environment configuration:", parsed.error.flatten().fieldErrors);
  throw new Error("Environment validation failed. See errors above.");
}

export const env = parsed.data;
