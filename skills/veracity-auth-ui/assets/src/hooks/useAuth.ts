import { useEffect, useState } from 'react'

import { CurrentUser, getAuthStatus, getCurrentUser, signIn, signOut } from '../api/auth'
import { isAllowedRedirect } from '../api/safeRedirect'
import { validatePolicy } from '../api/veracity'

export interface UseAuthOptions {
  // When true, after the user is authenticated the hook calls the BFF policy-compliance
  // endpoint and, if the user is not compliant, redirects them to the returned URL
  // (e.g. to accept the latest Veracity terms). Set by App.tsx from the scaffold flag.
  enablePolicyCheck?: boolean
}

export interface UseAuth {
  loading: boolean
  isAuthenticated: boolean
  user: CurrentUser | null
  signIn: () => void
  signOut: () => void
}

// Checks /auth on load. Fetches /api/me ONLY once /auth reports authenticated, so
// anonymous visitors are never force-redirected — login stays optional and the
// 401 -> challenge recovery in getCurrentUser only fires for an already-signed-in
// user whose token cache lapsed. When enablePolicyCheck is set, a signed-in user is
// additionally checked for policy compliance and redirected if non-compliant.
export function useAuth({ enablePolicyCheck = false }: UseAuthOptions = {}): UseAuth {
  const [loading, setLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState<CurrentUser | null>(null)

  useEffect(() => {
    let active = true

    const load = async () => {
      const authed = await getAuthStatus()
      if (!active) return
      setIsAuthenticated(authed)

      if (authed) {
        const me = await getCurrentUser()
        if (!active) return
        setUser(me)

        if (enablePolicyCheck && me) {
          const policy = await validatePolicy()
          if (!active) return
          if (policy && !policy.compliant && policy.redirectUrl && isAllowedRedirect(policy.redirectUrl)) {
            // Full-page navigation so the user lands on the Veracity policy /
            // subscription page; the app resumes once they return compliant. The
            // redirect target is validated against an allow-list of approved
            // Veracity domains first (open-redirect guard, CWE-601).
            window.location.href = policy.redirectUrl
            return
          }
        }
      }

      setLoading(false)
    }

    void load()

    return () => {
      active = false
    }
  }, [enablePolicyCheck])

  return { loading, isAuthenticated, user, signIn: () => signIn(), signOut }
}
