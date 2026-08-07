// Template: Veracity API V4 Controller (MVC Controllers style)
// Namespace: Replace "{{ProjectName}}" with the actual project namespace.
// File:      Controllers/VeracityV4Controller.cs
//
// Controllers equivalent of assets/VeracityV4Endpoints.cs. Uses a LITERAL
// "api/v1/veracity/v4" route (not Asp.Versioning.Mvc) so the paths match the
// fixed frontend contract exactly (e.g. GET /api/v1/veracity/v4/me/applications).

using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Veracity.Common.Authentication;
using Veracity.Core.Api.V4;
using Veracity.Core.Api.V4.Responses;

namespace {{ProjectName}}.Controllers;

[ApiController]
[Authorize]
[Route("api/v1/veracity/v4")]
[Produces("application/json")]
public class VeracityV4Controller : ControllerBase
{
    private readonly IVeracityGraphClient _veracityClient;
    private readonly IConfiguration _configuration;
    private readonly ILogger<VeracityV4Controller> _logger;

    public VeracityV4Controller(IVeracityGraphClient veracityClient, IConfiguration configuration, ILogger<VeracityV4Controller> logger)
    {
        _veracityClient = veracityClient;
        _configuration = configuration;
        _logger = logger;
    }

    [HttpGet("me/applications")]
    [ProducesResponseType(typeof(IEnumerable<ApplicationLicenseResponse>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    [ProducesResponseType(StatusCodes.Status502BadGateway)]
    public async Task<IActionResult> GetMyApplications()
    {
        return Ok(await _veracityClient.Me.GetMyApplications());
    }

    [HttpGet("me/tenants")]
    [ProducesResponseType(typeof(IEnumerable<TenantResponseEx>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    [ProducesResponseType(StatusCodes.Status502BadGateway)]
    public async Task<IActionResult> GetMyTenants()
    {
        return Ok(await _veracityClient.Me.GetMyTenants());
    }

    [HttpGet("policy/validate")]
    [ProducesResponseType(typeof(V4PolicyResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(typeof(V4PolicyResponse), StatusCodes.Status406NotAcceptable)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    [ProducesResponseType(StatusCodes.Status502BadGateway)]
    public async Task<IActionResult> PolicyVerification()
    {
        // The service (application) ID whose policies/subscription are validated comes from
        // configuration (ServiceId) — this is the Veracity service the app registration
        // is connected to. It is not taken from the request so callers cannot validate an arbitrary app.
        var serviceIdValue = _configuration["ServiceId"];
        if (!Guid.TryParse(serviceIdValue, out var serviceId))
        {
            _logger.LogError("ServiceId is not configured or is not a valid GUID. Set it to the ID of the Veracity service this application is connected to.");
            return Problem("Veracity service ID is not configured.", statusCode: StatusCodes.Status500InternalServerError);
        }

        try
        {
            var currentUrl = $"{Request.Scheme}://{Request.Host}{Request.PathBase}";
            await _veracityClient.Me.VerifyUserPolicy(serviceId, currentUrl);
        }
        catch (ServerException ex)
        {
            switch ((int)ex.Status)
            {
                case 406:
                    _logger.LogInformation(ex, "Veracity API V4 returned 406 (policy not accepted) for GET /me/policy-verification");
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
                            _logger.LogWarning(jsonEx, "Failed to parse 406 policy response body");
                        }
                    }
                    return StatusCode(StatusCodes.Status406NotAcceptable, new V4PolicyResponse(false, url));
                default:
                    _logger.LogError(ex, "Veracity API V4 returned unexpected {StatusCode} for GET /me/policy-verification", ex.Status);
                    throw;
            }
        }

        return Ok(new V4PolicyResponse(true, null));
    }

    [HttpGet("tenants/{tenantId}/applications")]
    [ProducesResponseType(typeof(PagedList<ApplicationResponse>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    [ProducesResponseType(StatusCodes.Status502BadGateway)]
    public async Task<IActionResult> GetTenantApplications(string tenantId)
    {
        return Ok(await _veracityClient.Applications.Query(tenantId).ExecuteAsync());
    }
}

public record V4PolicyResponse(bool Compliant, string? RedirectUrl);
