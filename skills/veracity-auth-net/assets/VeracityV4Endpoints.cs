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
                        string? url = null;
                        if (!string.IsNullOrEmpty(ex.ErrorData))
                        {
                            try
                            {
                                var body = JsonSerializer.Deserialize<JsonElement>(ex.ErrorData);
                                url = body.TryGetProperty("url", out var u) ? u.GetString()
                                    : body.TryGetProperty("information", out var info) ? info.GetString() : null;
                            }
                            catch (JsonException jsonEx)
                            {
                                logger.LogWarning(jsonEx, "Failed to parse 406 policy response body");
                            }
                        }
                        return Results.Json(new V4PolicyResponse(false, url), statusCode: 406);
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
        .Produces(404)
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
}

public record V4PolicyResponse(bool Compliant, string? RedirectUrl);
