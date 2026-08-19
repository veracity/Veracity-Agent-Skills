// Template: Open-redirect guard (CWE-601) for the Veracity OIDC sign-in returnUrl.
// File: Extensions/SafeRedirect.cs
//
// The `returnUrl` accepted by /auth/challenge is caller-supplied and must never drive a
// redirect without validation. `Uri.IsWellFormedUriString(returnUrl, UriKind.Relative)`
// is NOT sufficient on its own — a protocol-relative value such as "//evil.com" is a
// well-formed relative URI, yet the browser treats it as an absolute cross-origin URL.
// This mirrors ASP.NET Core's built-in Url.IsLocalUrl logic: only single-slash
// root-relative paths (and "~/" app-relative paths) are accepted; anything absolute,
// protocol-relative ("//host"), or backslash-obfuscated ("/\\host") collapses to "/".

internal static class SafeRedirect
{
    /// <summary>Returns <paramref name="returnUrl"/> when it is a safe local path, otherwise <paramref name="fallback"/>.</summary>
    public static string SanitizeReturnUrl(string? returnUrl, string fallback = "/")
        => IsLocalUrl(returnUrl) ? returnUrl! : fallback;

    /// <summary>Local-URL check equivalent to ASP.NET Core's Url.IsLocalUrl.</summary>
    public static bool IsLocalUrl(string? url)
    {
        if (string.IsNullOrEmpty(url))
            return false;

        // Allows "/" and "/foo" but not "//" or "/\" (protocol-relative / backslash tricks).
        if (url[0] == '/')
            return url.Length == 1 || (url[1] != '/' && url[1] != '\\');

        // Allows "~/" app-relative paths but not "~//" or "~/\".
        if (url[0] == '~' && url.Length > 1 && url[1] == '/')
            return url.Length == 2 || (url[2] != '/' && url[2] != '\\');

        return false;
    }
}
