using Microsoft.Extensions.Options;
using Microsoft.Extensions.Primitives;

namespace {{ProjectName}}.Middleware;

public class SecurityHeadersMiddleware
{
    private readonly RequestDelegate _next;
    private readonly IDictionary<string, string>? _cspSettings;

    public SecurityHeadersMiddleware(RequestDelegate next, IOptions<CSPOptions> cspOp)
    {
        _next = next;
        _cspSettings = cspOp.Value?.Settings;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        if (_cspSettings != null)
        {
            var cspValues = new List<string>();
            foreach (var cspSetting in _cspSettings)
            {
                cspValues.Add(string.Join(" ", cspSetting.Key, cspSetting.Value));
            }
            if (cspValues.Count > 0)
            {
                context.Response.Headers.Append("Content-Security-Policy", string.Join("; ", cspValues.ToArray()));
            }
        }
        context.Response.Headers.Append("X-Content-Type-Options", new StringValues("nosniff"));
        context.Response.Headers.Append("X-Frame-Options", new StringValues("SAMEORIGIN"));
        context.Response.Headers.Append("X-XSS-Protection", new StringValues("0"));
        context.Response.Headers.Append("X-Permitted-Cross-Domain-Policies", new StringValues("none"));
        context.Response.Headers.Append("Strict-Transport-Security", new StringValues("max-age=31536000; includeSubDomains"));
        context.Response.Headers.Append("Referrer-Policy", new StringValues("no-referrer"));

        await _next(context);
    }
}
