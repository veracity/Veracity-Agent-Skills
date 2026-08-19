using System.Security.Claims;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.AspNetCore.Http.HttpResults;

public static class AuthEndpoints
{
    public static IEndpointRouteBuilder MapAuthEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/auth", GetAuthStatus)
            .WithName("GetAuthStatus")
            .WithSummary("Check if the user is signed in")
            .WithTags("Auth")
            .Produces<AuthStatusResponse>(200)
            .AllowAnonymous();

        app.MapGet("/api/me", GetCurrentUser)
            .WithName("GetCurrentUser")
            .WithSummary("Get the current authenticated user")
            .WithTags("Auth")
            .Produces<CurrentUserResponse>(200)
            .Produces(401)
            .RequireAuthorization();

        app.MapGet("/auth/challenge", (HttpContext context, string? returnUrl = null) =>
        {
            var redirectUri = SafeRedirect.SanitizeReturnUrl(returnUrl);

            return Results.Challenge(
                new AuthenticationProperties { RedirectUri = redirectUri },
                [OpenIdConnectDefaults.AuthenticationScheme]);
        })
        .WithName("AuthChallenge")
        .WithSummary("Trigger OpenID Connect sign-in")
        .WithTags("Auth")
        .AllowAnonymous()
        .ExcludeFromDescription();

        app.MapGet("/signOut", async (HttpContext context, IConfiguration config) =>
        {
            var logoutRedirectUri = config["Veracity:LogoutRedirectUri"] ?? "https://www.veracity.com/auth/logout";

            await context.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
            await context.SignOutAsync(OpenIdConnectDefaults.AuthenticationScheme,
                new AuthenticationProperties { RedirectUri = logoutRedirectUri });

            return Results.Redirect("/");
        })
        .WithName("SignOut")
        .WithSummary("Sign out the current user")
        .WithTags("Auth")
        .AllowAnonymous()
        .ExcludeFromDescription();

        return app;
    }

    private static Ok<AuthStatusResponse> GetAuthStatus(HttpContext context)
    {
        var isAuthenticated = context.User.Identity?.IsAuthenticated ?? false;
        return TypedResults.Ok(new AuthStatusResponse(isAuthenticated));
    }

    private static Results<Ok<CurrentUserResponse>, UnauthorizedHttpResult> GetCurrentUser(HttpContext context)
    {
        if (context.User.Identity?.IsAuthenticated != true)
            return TypedResults.Unauthorized();

        var claims = context.User.Claims;
        var user = new CurrentUserResponse(
            Id: claims.FirstOrDefault(x => x.Type == ClaimTypes.NameIdentifier)?.Value ?? "",
            DisplayName: claims.FirstOrDefault(c => c.Type == "name")?.Value ?? "",
            Email: claims.FirstOrDefault(c => c.Type == ClaimTypes.Email)?.Value ?? "",
            FirstName: claims.FirstOrDefault(c => c.Type == ClaimTypes.GivenName)?.Value,
            LastName: claims.FirstOrDefault(c => c.Type == ClaimTypes.Surname)?.Value);

        return TypedResults.Ok(user);
    }
}

public record AuthStatusResponse(bool Result);

public record CurrentUserResponse(
    string Id,
    string DisplayName,
    string Email,
    string? FirstName,
    string? LastName);
