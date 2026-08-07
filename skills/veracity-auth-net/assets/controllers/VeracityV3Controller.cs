// Template: Veracity API V3 Controller (MVC Controllers style)
// Namespace: Replace "{{ProjectName}}" with the actual project namespace.
// File:      Controllers/VeracityV3Controller.cs
//
// Controllers equivalent of assets/VeracityV3Endpoints.cs. Uses a LITERAL
// "api/v1/veracity/v3" route (not Asp.Versioning.Mvc) so the paths match the
// fixed frontend contract exactly (e.g. GET /api/v1/veracity/v3/services).

using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Veracity.Common.Authentication;
using Veracity.Services.Api;
using Veracity.Services.Api.Models;

namespace {{ProjectName}}.Controllers;

[ApiController]
[Authorize]
[Route("api/v1/veracity/v3")]
[Produces("application/json")]
public class VeracityV3Controller : ControllerBase
{
    private readonly IMy _my;
    private readonly ILogger<VeracityV3Controller> _logger;

    public VeracityV3Controller(IMy my, ILogger<VeracityV3Controller> logger)
    {
        _my = my;
        _logger = logger;
    }

    [HttpGet("services")]
    [ProducesResponseType(typeof(IEnumerable<MyServiceReference>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    [ProducesResponseType(StatusCodes.Status502BadGateway)]
    public async Task<IActionResult> GetMyServices()
    {
        return Ok(await _my.MyServices());
    }

    [HttpGet("notifications/count")]
    [ProducesResponseType(typeof(int), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    [ProducesResponseType(StatusCodes.Status502BadGateway)]
    public async Task<IActionResult> GetMyNotificationsCount()
    {
        return Ok(await _my.GetMessageCount());
    }

    [HttpGet("policy/validate")]
    [ProducesResponseType(typeof(V3PolicyResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    [ProducesResponseType(typeof(V3PolicyResponse), StatusCodes.Status406NotAcceptable)]
    public async Task<IActionResult> ValidateMyPolicy()
    {
        try
        {
            var currentUrl = $"{Request.Scheme}://{Request.Host}{Request.PathBase}";
            await _my.ValidatePolicies(currentUrl);
        }
        catch (ServerException ex)
        {
            switch ((int)ex.Status)
            {
                case 406:
                    _logger.LogInformation(ex, "Veracity API V3 returned 406 (policy not accepted) for GET /my/policies/validate()");
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
                    return StatusCode(StatusCodes.Status406NotAcceptable, new V3PolicyResponse(false, url));
                default:
                    _logger.LogError(ex, "Veracity API V3 returned unexpected {StatusCode} for GET /my/policies/validate()", ex.Status);
                    throw;
            }
        }

        return Ok(new V3PolicyResponse(true, null));
    }
}

public record V3PolicyResponse(bool Compliant, string? RedirectUrl);
