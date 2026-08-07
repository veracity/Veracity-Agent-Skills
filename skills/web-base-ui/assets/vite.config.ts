import basicSsl from '@vitejs/plugin-basic-ssl'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev server + bundler config for the baseline welcome-page app. The dev server runs
// over HTTPS: `@vitejs/plugin-basic-ssl` issues a self-signed certificate, so the app
// is served from `https://localhost:...` (browsers show a one-time trust warning on
// first load — accept it to proceed). There is no backend proxy here on purpose: a
// static welcome page needs none. Skills that add a backend (e.g. veracity-auth-ui)
// MERGE a `server.proxy` block into this file without removing the `react()` or
// `basicSsl()` plugins or any `resolve.alias` a design system may have added.
export default defineConfig({
  plugins: [react(), basicSsl()],
  server: {
    https: {},
    open: true
  }
})
