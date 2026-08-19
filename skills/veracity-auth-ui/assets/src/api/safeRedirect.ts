// Redirect guards for the client. User- or response-supplied URLs must be validated
// before they drive a browser navigation, otherwise an attacker can (a) phish the user
// off to an untrusted site after login (CWE-601 open redirect) or (b) execute script by
// smuggling a `javascript:` URI into `window.location.href` (CWE-80 XSS).
//
//  - toRelativeReturnUrl(): coerces a `returnUrl` to a safe, same-origin RELATIVE path
//    (anything absolute, protocol-relative, or backslash-obfuscated collapses to "/").
//  - sanitizeRedirectUrl(): validates an ABSOLUTE URL (e.g. the BFF policy `redirectUrl`)
//    and returns a re-serialized, safe URL string (or null). Only https same-origin or
//    approved-Veracity-host targets are allowed; every other scheme (javascript:, data:,
//    blob:, http:, …) is rejected. Callers MUST navigate to the returned value, not the
//    original input, so the tainted source never reaches the sink.
//  - isAllowedRedirect(): boolean convenience wrapper over sanitizeRedirectUrl().

// Approved hosts for cross-origin policy/subscription redirects. Extend this list if
// the BFF may legitimately redirect to another Veracity-owned domain.
const ALLOWED_REDIRECT_HOSTS = ['veracity.com']

export function toRelativeReturnUrl(raw: string | null | undefined, fallback = '/'): string {
  if (typeof raw !== 'string') return fallback
  const value = raw.trim()
  // Must be a single-slash root-relative path.
  if (!value.startsWith('/')) return fallback
  // Block protocol-relative ("//host") and backslash-obfuscated ("/\host") forms.
  if (value.startsWith('//') || value.startsWith('/\\')) return fallback
  if (value.includes('\\')) return fallback
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f\u007f]/.test(value)) return fallback
  if (value.includes('://')) return fallback
  return value
}

// Returns a sanitized, safe-to-navigate URL string, or null when the input is not an
// allowed target. The returned value is re-serialized from a parsed URL (never the raw
// input), which both blocks dangerous schemes (javascript:/data:/…) and breaks the
// source-to-sink taint flow for CWE-80 (XSS) / CWE-601 (open redirect).
export function sanitizeRedirectUrl(rawUrl: string | null | undefined): string | null {
  if (typeof rawUrl !== 'string' || rawUrl.length === 0) return null
  let url: URL
  try {
    url = new URL(rawUrl, window.location.origin)
  } catch {
    return null
  }
  // Same-origin targets: allow only http/https (rejects javascript:, data:, blob:, …).
  if (url.origin === window.location.origin) {
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null
  }
  // Cross-origin targets must be HTTPS and on an approved Veracity host.
  if (url.protocol !== 'https:') return null
  const host = url.hostname.toLowerCase()
  const allowed = ALLOWED_REDIRECT_HOSTS.some(
    (h) => host === h || host.endsWith(`.${h}`),
  )
  return allowed ? url.href : null
}

export function isAllowedRedirect(rawUrl: string | null | undefined): boolean {
  return sanitizeRedirectUrl(rawUrl) !== null
}

