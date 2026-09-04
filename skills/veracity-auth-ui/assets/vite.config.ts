import basicSsl from '@vitejs/plugin-basic-ssl'
import react from '@vitejs/plugin-react'
import { defineConfig, type UserConfig } from 'vite'

// Local-dev proxy to the Veracity BFF. The frontend is served same-origin by
// Vite over HTTPS (basicSsl issues a self-signed dev certificate), so the BFF's
// secure auth cookie flows without CORS. Replace {BACKEND_SERVER_URL} with the
// BFF base URL (detected from launchSettings.json or provided by the user). Keep
// `/auth/challenge` before `/auth` so the more specific route wins, and keep
// `secure: false` because the local BFF uses a self-signed certificate.
export default defineConfig((): UserConfig => ({
  plugins: [react(), basicSsl()],
  server: {
    https: {},
    cors: false,
    proxy: {
      '/api': { changeOrigin: true, secure: false, target: '{BACKEND_SERVER_URL}' },
      '/auth': { changeOrigin: false, secure: false, target: '{BACKEND_SERVER_URL}' },
      '/signin-oidc': { secure: false, target: '{BACKEND_SERVER_URL}' },
      '/signout': { changeOrigin: false, secure: false, target: '{BACKEND_SERVER_URL}' }
    }
  }
}))
