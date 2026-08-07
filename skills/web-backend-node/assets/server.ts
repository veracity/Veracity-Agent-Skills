// Template: src/server.ts
// Bootstrap: load + validate env, create the app, listen on the configured port.
// Serves HTTPS when TLS_CERT_FILE / TLS_KEY_FILE are set (parity with the .NET baseline,
// which runs HTTPS by default via launchSettings.json). Plain HTTP is fine when the app
// sits behind an HTTPS proxy (e.g. a frontend dev server or a reverse proxy).

import { readFileSync } from "node:fs";
import { createServer as createHttpsServer } from "node:https";
import { env } from "./config/env.js";
import { createApp } from "./app.js";

const app = createApp();

if (env.TLS_CERT_FILE && env.TLS_KEY_FILE) {
  const options = {
    cert: readFileSync(env.TLS_CERT_FILE),
    key: readFileSync(env.TLS_KEY_FILE),
  };
  createHttpsServer(options, app).listen(env.PORT, () => {
    // eslint-disable-next-line no-console
    console.log(`__PROJECT_NAME__ listening on https://localhost:${env.PORT} (${env.NODE_ENV})`);
  });
} else {
  app.listen(env.PORT, () => {
    // eslint-disable-next-line no-console
    console.log(`__PROJECT_NAME__ listening on http://localhost:${env.PORT} (${env.NODE_ENV})`);
  });
}
