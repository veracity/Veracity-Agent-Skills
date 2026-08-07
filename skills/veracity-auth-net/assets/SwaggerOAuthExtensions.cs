// Template: Swagger UI with OAuth2 Authorization Code + PKCE
// Namespace: Replace "{{ProjectName}}" with the actual project namespace.
// File:      Extensions/SwaggerOAuthExtensions.cs
// Note:      Only include this file when the user opts in to Swagger OAuth2 Authorization.

using Asp.Versioning.ApiExplorer;
using Microsoft.OpenApi;

namespace {{ProjectName}}.Extensions;

public static class SwaggerOAuthExtensions
{
    /// <summary>
    /// Registers Swagger generation with an OAuth2 Authorization Code + PKCE
    /// security definition bound to the Veracity B2C tenant.
    /// ClientId is read from Swagger:ClientId in appsettings.
    /// ClientSecret is read from Swagger:ClientSecret (user-secrets / Key Vault — never committed to source).
    /// </summary>
    public static IServiceCollection AddSwaggerWithOAuth(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        services.AddSwaggerGen(options =>
        {
            options.SwaggerDoc("v1", new OpenApiInfo { Title = "{{ProjectName}} API", Version = "v1" });

            var audience = configuration["Jwt:Audience"]!;

            var b2cSection = configuration.GetRequiredSection("Swagger");
            var instance = b2cSection["Instance"] ?? "https://login.veracity.com";
            var domain = b2cSection["Domain"] ?? "dnvglb2cprod.onmicrosoft.com";
            var policy = b2cSection["SignUpSignInPolicyId"] ?? "B2C_1A_Identity";
            var baseUrl = $"{instance}/{domain}/{policy}";
            var scopeName = b2cSection["ScopeName"] ?? "user_impersonation";
            var scopeKey = $"https://{domain}/{audience}/{scopeName}";

            options.AddSecurityDefinition("oauth2", new OpenApiSecurityScheme
            {
                Type = SecuritySchemeType.OAuth2,
                Flows = new OpenApiOAuthFlows
                {
                    AuthorizationCode = new OpenApiOAuthFlow
                    {
                        AuthorizationUrl = new Uri($"{baseUrl}/oauth2/v2.0/authorize"),
                        TokenUrl = new Uri($"{baseUrl}/oauth2/v2.0/token"),
                        Scopes = new Dictionary<string, string>
                        {
                            { scopeKey, "Access this API" }
                        }
                    }
                }
            });

            options.AddSecurityRequirement(doc => new OpenApiSecurityRequirement
            {
                {
                    new OpenApiSecuritySchemeReference("oauth2"),
                    new List<string> { scopeKey }
                }
            });
        });

        return services;
    }

    /// <summary>
    /// Enables the Swagger and Swagger UI middleware. The "Authorize" dialog
    /// is pre-populated with ClientId and ClientSecret read from configuration
    /// so developers don't need to type them manually.
    /// </summary>
    public static WebApplication UseSwaggerWithOAuth(this WebApplication app)
    {
        app.UseSwagger();
        app.UseSwaggerUI(options =>
        {
            options.SwaggerEndpoint("/swagger/v1/swagger.json", "{{ProjectName}} API V1");
            options.OAuthClientId(app.Configuration["Swagger:ClientId"]);
            options.OAuthClientSecret(app.Configuration["Swagger:ClientSecret"]);
            options.OAuthUsePkce();
            options.EnablePersistAuthorization();
            options.UseRequestInterceptor("(req) => { if (req.headers && req.headers.Authorization) return req; var auth = window.ui?.authSelectors?.authorized(); if (auth) { var oauth2 = auth.get('oauth2'); if (oauth2) { var token = oauth2.get('token')?.get('access_token'); if (token) req.headers.Authorization = 'Bearer ' + token; } } return req; }");
        });

        return app;
    }
}
