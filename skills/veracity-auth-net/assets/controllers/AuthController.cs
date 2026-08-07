// Template: Veracity OIDC Auth Controller (MVC Controllers style)
// Namespace: Replace "{{ProjectName}}" with the actual project namespace.
// File:      Controllers/AuthController.cs
//
// Controllers equivalent of assets/AuthEndpoints.cs. Exposes the SAME fixed
// endpoint contract the frontend (veracity-auth-ui) depends on:
//   GET /auth            -> anonymous, returns { result: bool }
//   GET /api/me          -> [Authorize], returns the current user
//   GET /auth/challenge  -> anonymous, triggers OIDC sign-in (?returnUrl= relative)
//   GET /signout         -> anonymous, clears cookie + OIDC session
// These routes are intentionally NOT versioned (they must match the contract exactly).

using System.Security.Claims;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace {{ProjectName}}.Controllers;

[ApiController]
public class AuthController : ControllerBase
{
    private readonly IConfiguration _configuration;

    public AuthController(IConfiguration configuration)
    {
        _configuration = configuration;
    }

    [HttpGet("/auth")]
    [AllowAnonymous]
    [ProducesResponseType(typeof(AuthStatusResponse), StatusCodes.Status200OK)]
    public ActionResult<AuthStatusResponse> GetAuthStatus()
    {
        var isAuthenticated = User.Identity?.IsAuthenticated ?? false;
        return Ok(new AuthStatusResponse(isAuthenticated));
    }

    [HttpGet("/api/me")]
    [Authorize]
    [ProducesResponseType(typeof(CurrentUserResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public ActionResult<CurrentUserResponse> GetCurrentUser()
    {
        if (User.Identity?.IsAuthenticated != true)
            return Unauthorized();

        var claims = User.Claims;
        var user = new CurrentUserResponse(
            Id: claims.FirstOrDefault(x => x.Type == ClaimTypes.NameIdentifier)?.Value ?? "",
            DisplayName: claims.FirstOrDefault(c => c.Type == "name")?.Value ?? "",
            Email: claims.FirstOrDefault(c => c.Type == ClaimTypes.Email)?.Value ?? "",
            FirstName: claims.FirstOrDefault(c => c.Type == ClaimTypes.GivenName)?.Value,
            LastName: claims.FirstOrDefault(c => c.Type == ClaimTypes.Surname)?.Value);

        return Ok(user);
    }

    [HttpGet("/auth/challenge")]
    [AllowAnonymous]
    [ApiExplorerSettings(IgnoreApi = true)]
    public IActionResult ChallengeSignIn([FromQuery] string? returnUrl = null)
    {
        var redirectUri = !string.IsNullOrEmpty(returnUrl) && Uri.IsWellFormedUriString(returnUrl, UriKind.Relative)
            ? returnUrl
            : "/";

        return Challenge(
            new AuthenticationProperties { RedirectUri = redirectUri },
            OpenIdConnectDefaults.AuthenticationScheme);
    }

    [HttpGet("/signout")]
    [AllowAnonymous]
    [ApiExplorerSettings(IgnoreApi = true)]
    public async Task<IActionResult> SignOutUser()
    {
        var logoutRedirectUri = _configuration["Veracity:LogoutRedirectUri"] ?? "https://www.veracity.com/auth/logout";

        await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
        await HttpContext.SignOutAsync(OpenIdConnectDefaults.AuthenticationScheme,
            new AuthenticationProperties { RedirectUri = logoutRedirectUri });

        return Redirect("/");
    }
}

public record AuthStatusResponse(bool Result);

public record CurrentUserResponse(
    string Id,
    string DisplayName,
    string Email,
    string? FirstName,
    string? LastName);
