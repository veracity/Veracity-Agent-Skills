// Optional Veracity API calls, proxied through the BFF. These endpoints only exist
// when the BFF was generated with the matching Veracity API version via the
// veracity-auth-net skill. They are mapped under the BFF's versioned API group
// (`/api/v{version}`), so the full paths are:
//   - V3 services:     GET /api/v1/veracity/v3/services
//   - V4 applications: GET /api/v1/veracity/v4/me/applications
//   - Policy validate: GET /api/v1/veracity/v{3|4}/policy/validate
// Each helper returns null on any error (including 404 when the endpoint was not
// generated) so the UI can degrade gracefully.

// The BFF policy-compliance endpoint (V3 or V4, matching the BFF's Veracity API
// version). Substituted at scaffold time by veracity-auth-ui.
const POLICY_VALIDATE_PATH = '{POLICY_VALIDATE_PATH}'

export interface VeracityService {
  serviceId?: string
  name?: string
  [key: string]: unknown
}

export interface VeracityApplication {
  id?: string
  name?: string
  [key: string]: unknown
}

export interface PolicyComplianceResult {
  // false when the user must accept the latest Veracity terms or lacks a required
  // subscription; redirectUrl (when present) is where they should be sent to fix it.
  compliant: boolean
  redirectUrl?: string | null
}

// GET /api/v1/veracity/v3/services -> the services the current user can access.
export async function getMyServices(): Promise<VeracityService[] | null> {
  try {
    const res = await fetch('/api/v1/veracity/v3/services', { credentials: 'include' })
    if (!res.ok) return null
    return (await res.json()) as VeracityService[]
  } catch {
    return null
  }
}

// GET /api/v1/veracity/v4/me/applications -> the applications licensed to the user.
export async function getMyApplications(): Promise<VeracityApplication[] | null> {
  try {
    const res = await fetch('/api/v1/veracity/v4/me/applications', { credentials: 'include' })
    if (!res.ok) return null
    return (await res.json()) as VeracityApplication[]
  } catch {
    return null
  }
}

// GET {POLICY_VALIDATE_PATH} -> checks whether the signed-in user is compliant with
// the Veracity policy / subscription for the service this app is connected to. The
// BFF returns { compliant, redirectUrl }; an HTTP 406 also carries that body and
// signals the user must accept the latest terms (or lacks a subscription) and should
// be redirected to redirectUrl. Returns null on any other error (including 404 when
// the endpoint was not generated) so a missing endpoint degrades gracefully.
export async function validatePolicy(): Promise<PolicyComplianceResult | null> {
  try {
    const res = await fetch(POLICY_VALIDATE_PATH, { credentials: 'include' })
    if (res.status === 406 || res.ok) {
      return (await res.json()) as PolicyComplianceResult
    }
    return null
  } catch {
    return null
  }
}
