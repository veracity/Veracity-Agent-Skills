// Open-redirect guard (CWE-601) for the client. User- or response-supplied URLs must
// be validated before they drive a browser navigation, otherwise an attacker can
// craft a link that phishes the user off to an untrusted site after login.
//
//  - toRelativeReturnUrl(): coerces a `returnUrl` to a safe, same-origin RELATIVE path
//    (anything absolute, protocol-relative, or backslash-obfuscated collapses to "/").
//  - isAllowedRedirect(): validates an ABSOLUTE URL (e.g. the BFF policy `redirectUrl`)
//    against an allow-list of approved Veracity domains before navigating cross-origin.

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

export function isAllowedRedirect(rawUrl: string | null | undefined): boolean {
  if (typeof rawUrl !== 'string' || rawUrl.length === 0) return false
  let url: URL
  try {
    url = new URL(rawUrl, window.location.origin)
  } catch {
    return false
  }
  // Same-origin relative targets are always safe.
  if (url.origin === window.location.origin) return true
  // Cross-origin targets must be HTTPS and on an approved Veracity host.
  if (url.protocol !== 'https:') return false
  const host = url.hostname.toLowerCase()
  return ALLOWED_REDIRECT_HOSTS.some(
    (allowed) => host === allowed || host.endsWith(`.${allowed}`),
  )
}
