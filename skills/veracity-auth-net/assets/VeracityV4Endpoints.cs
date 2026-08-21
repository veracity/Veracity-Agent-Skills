using System.Text.Json;
using Veracity.Common.Authentication;
using Veracity.Core.Api.V4;
using Veracity.Core.Api.V4.Responses;

public static class VeracityV4Endpoints
{
    public static void MapV4Endpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/veracity/v4/me/applications", async (IVeracityGraphClient veracityClient) =>
        {
            return await veracityClient.Me.GetMyApplications();
        })
        .WithName("GetMyApplications")
        .WithSummary("Get the applications for the current authenticated user")
        .WithTags("Api V4")
        .Produces<IEnumerable<ApplicationLicenseResponse>>(200)
        .Produces(401)
        .Produces(400)
        .Produces(404)
        .Produces(500)
        .Produces(502);

        app.MapGet("/veracity/v4/me/tenants", async (IVeracityGraphClient veracityClient) =>
        {
            return await veracityClient.Me.GetMyTenants();
        })
        .WithName("GetMyTenants")
        .WithSummary("Get the tenants for the current authenticated user")
        .WithTags("Api V4")
        .Produces<IEnumerable<TenantResponseEx>>(200)
        .Produces(401)
        .Produces(400)
        .Produces(404)
        .Produces(500)
        .Produces(502);

        app.MapGet("/veracity/v4/policy/validate", async (HttpRequest request, IVeracityGraphClient veracityClient, IConfiguration configuration, ILogger<IVeracityGraphClient> logger) =>
        {
            // The service (application) ID whose policies/subscription are validated comes from
            // configuration (ServiceId) — this is the Veracity service the app registration
            // is connected to. It is not taken from the request so callers cannot validate an arbitrary app.
            var serviceIdValue = configuration["ServiceId"];
            if (!Guid.TryParse(serviceIdValue, out var serviceId))
            {
                logger.LogError("ServiceId is not configured or is not a valid GUID. Set it to the ID of the Veracity service this application is connected to.");
                return Results.Problem("Veracity service ID is not configured.", statusCode: 500);
            }

            try
            {
                var currentUrl = $"{request.Scheme}://{request.Host}{request.PathBase}";
                await veracityClient.Me.VerifyUserPolicy(serviceId, currentUrl);
            }
            catch (ServerException ex)
            {
                switch ((int)ex.Status)
                {
                    case 406:
                        logger.LogInformation(ex, "Veracity API V4 returned 406 (policy not accepted) for GET /me/policy-verification");
                        return Results.Json(new V4PolicyResponse(false, TryGetRedirectUrl(ex.ErrorData, logger)), statusCode: 406);
                    case 403:
                        // A 403 from the downstream API can carry a redirect URL in its error detail
                        // (e.g. the user must accept terms / complete a subscription step). When a redirect
                        // URL is present, surface it as a 406 so the client can redirect the user; otherwise
                        // the 403 is a genuine authorization failure and is returned as-is.
                        var redirectUrl = TryGetRedirectUrl(ex.ErrorData, logger);
                        if (!string.IsNullOrEmpty(redirectUrl))
                        {
                            logger.LogInformation(ex, "Veracity API V4 returned 403 with a redirect URL for GET /me/policy-verification; returning 406");
                            return Results.Json(new V4PolicyResponse(false, redirectUrl), statusCode: 406);
                        }
                        logger.LogWarning(ex, "Veracity API V4 returned 403 without a redirect URL for GET /me/policy-verification");
                        return Results.Json(new V4PolicyResponse(false, null), statusCode: 403);
                    default:
                        logger.LogError(ex, "Veracity API V4 returned unexpected {StatusCode} for GET /me/policy-verification", ex.Status);
                        throw;
                }
            }

            return Results.Ok(new V4PolicyResponse(true, null));
        })
        .WithName("PolicyVerification")
        .WithSummary("Validate policies for the current authenticated user")
        .WithTags("Api V4")
        .Produces<V4PolicyResponse>(200)
        .Produces(401)
        .Produces(400)
        .Produces<V4PolicyResponse>(403)
        .Produces(404)
        .Produces<V4PolicyResponse>(406)
        .Produces(500)
        .Produces(502);

        app.MapGet("/veracity/v4/tenants/{tenantId}/applications", async (IVeracityGraphClient veracityClient, string tenantId) =>
        {
            return await veracityClient.Applications.Query(tenantId).ExecuteAsync();
        })
        .WithName("GetTenantApplications")
        .WithSummary("Get the applications for the specified tenant")
        .WithTags("Api V4")
        .Produces<PagedList<ApplicationResponse>>(200)
        .Produces(401)
        .Produces(400)
        .Produces(404)
        .Produces(500)
        .Produces(502);
    }

    // Extracts a redirect/information URL from a downstream Veracity API error body, if present.
    private static string? TryGetRedirectUrl(string? errorData, ILogger logger)
    {
        if (string.IsNullOrEmpty(errorData))
        {
            return null;
        }

        try
        {
            var body = JsonSerializer.Deserialize<JsonElement>(errorData);
            if (body.ValueKind != JsonValueKind.Object)
            {
                return null;
            }

            return body.TryGetProperty("url", out var u) ? u.GetString()
                : body.TryGetProperty("redirectUrl", out var r) ? r.GetString()
                : body.TryGetProperty("information", out var info) ? info.GetString()
                : null;
        }
        catch (JsonException jsonEx)
        {
            logger.LogWarning(jsonEx, "Failed to parse Veracity API V4 policy error response body");
            return null;
        }
    }
}

public record V4PolicyResponse(bool Compliant, string? RedirectUrl);
