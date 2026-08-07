export interface AuthStatus {
  result: boolean
}

export interface CurrentUser {
  id: string
  displayName: string
  email: string
  firstName?: string | null
  lastName?: string | null
}

// Build a safe, RELATIVE return URL from the current location. Never derive this
// from arbitrary/external input — the BFF only accepts relative returnUrls.
function currentReturnUrl(): string {
  return window.location.pathname + window.location.search + window.location.hash
}

// Full-page navigation to the BFF OIDC challenge. B2C performs sign-in (or silent
// re-auth if a session already exists) and redirects back to returnUrl via
// /signin-oidc. A full navigation is required — fetch() would follow the 302 into
// B2C cross-origin and fail with CORS.
export function signIn(returnUrl: string = currentReturnUrl()): void {
  window.location.href = `/auth/challenge?returnUrl=${encodeURIComponent(returnUrl)}`
}

// Full-page navigation to the BFF sign-out endpoint.
export function signOut(): void {
  window.location.href = '/signout'
}

// GET /auth -> { result: boolean }. Returns false on any error. This is a public
// endpoint, so it never forces a redirect.
export async function getAuthStatus(): Promise<boolean> {
  try {
    const res = await fetch('/auth', { credentials: 'include' })
    if (!res.ok) return false
    const data = (await res.json()) as AuthStatus
    return data?.result ?? false
  } catch {
    return false
  }
}

// GET /api/me. Call this ONLY after getAuthStatus() reports true. A 401 here means
// the auth cookie is valid but the server-side token cache lapsed (e.g. restart);
// a silent re-auth via the OIDC challenge recovers it.
export async function getCurrentUser(): Promise<CurrentUser | null> {
  try {
    const res = await fetch('/api/me', { credentials: 'include' })
    if (res.status === 401 || res.redirected) {
      signIn()
      return null
    }
    if (!res.ok) return null
    return (await res.json()) as CurrentUser
  } catch {
    return null
  }
}
