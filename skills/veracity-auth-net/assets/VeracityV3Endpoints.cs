using System.Text.Json;
using Veracity.Common.Authentication;
using Veracity.Services.Api;
using Veracity.Services.Api.Models;

public static class VeracityV3Endpoints
{
    public static void MapV3Endpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/veracity/v3/services", async (IMy my, ILogger<IMy> logger) =>
        {
            return await my.MyServices();
        })
        .WithName("GetMyServices")
        .WithSummary("Get all the services the current user can access")
        .WithTags("ApiV3")
        .Produces<IEnumerable<MyServiceReference>>(200)
        .Produces(401)
        .Produces(400)
        .Produces(404)
        .Produces(500)
        .Produces(502);

        app.MapGet("/veracity/v3/notifications/count", async (IMy my, ILogger<IMy> logger) =>
        {
            return await my.GetMessageCount();
        })
        .WithName("GetMyNotificationsCount")
        .WithSummary("Get the notification count for the current user")
        .WithTags("ApiV3")
        .Produces<int>(200)
        .Produces(401)
        .Produces(400)
        .Produces(404)
        .Produces(500)
        .Produces(502);

        app.MapGet("/veracity/v3/policy/validate", async (HttpRequest request, IMy my, ILogger<IMy> logger) =>
        {
            try
            {
                var currentUrl = $"{request.Scheme}://{request.Host}{request.PathBase}";
                await my.ValidatePolicies(currentUrl);
            }
            catch (ServerException ex)
            {
                switch ((int)ex.Status)
                {
                    case 406:
                        logger.LogInformation(ex, "Veracity API V3 returned 406 (policy not accepted) for GET /my/policies/validate()");
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
                        return Results.Json(new V3PolicyResponse(false, url), statusCode: 406);
                    default:
                        logger.LogError(ex, "Veracity API V3 returned unexpected {StatusCode} for GET /my/policies/validate()", ex.Status);
                        throw;
                }
            }

            return Results.Ok(new V3PolicyResponse(true, null));
        })
        .WithName("ValidateMyPolicy")
        .WithSummary("Validate policies for the current user")
        .WithTags("ApiV3")
        .Produces(200)
        .Produces(401)
        .Produces(403)
        .Produces(406);
    }
}

public record V3PolicyResponse(bool Compliant, string? RedirectUrl);
