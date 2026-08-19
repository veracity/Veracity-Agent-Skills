// Template (NestJS): src/auth/safeRedirect.ts
// Open-redirect guard (CWE-601). The OIDC `returnUrl` is caller-supplied, so it must
// never be used to build a redirect without validation. `safeReturnUrl` returns a
// guaranteed application-relative path: anything that is absolute, protocol-relative
// (`//host`), backslash-obfuscated, scheme-bearing, or otherwise not a plain
// root-relative path collapses to the safe `fallback` ("/").

export function safeReturnUrl(raw: unknown, fallback = "/"): string {
  if (typeof raw !== "string") return fallback;
  const value = raw.trim();
  // Must be a single-slash root-relative path.
  if (!value.startsWith("/")) return fallback;
  // Block protocol-relative ("//host") and backslash-obfuscated ("/\\host") forms.
  if (value.startsWith("//") || value.startsWith("/\\")) return fallback;
  // Reject backslashes, control characters, and any embedded scheme/host.
  if (value.includes("\\")) return fallback;
  if (/[\u0000-\u001f\u007f]/.test(value)) return fallback;
  if (value.includes("://")) return fallback;
  return value;
}
