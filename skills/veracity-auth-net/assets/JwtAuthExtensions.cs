// Template: Veracity JWT Bearer Authentication Extension
// Namespace: Replace "{{ProjectName}}" with the actual project namespace.
// File:      Extensions/JwtAuthExtensions.cs

using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

namespace {{ProjectName}}.Extensions;

public static class JwtAuthExtensions
{
    /// <summary>
    /// Registers JWT Bearer authentication that validates tokens issued by
    /// the Veracity Azure AD B2C tenant. Use this for stateless APIs consumed
    /// by SPAs, mobile apps, or service-to-service calls where the caller
    /// already holds a bearer token.
    /// </summary>
    public static IServiceCollection AddJwtBearerAuthentication(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
            .AddJwtBearer(options =>
            {
                options.Authority = configuration["Jwt:Authority"];
                options.Audience = configuration["Jwt:Audience"];
                options.TokenValidationParameters = new TokenValidationParameters
                {
                    ValidateIssuer = true,
                    ValidateAudience = true,
                    ValidateLifetime = true,
                    ValidateIssuerSigningKey = true,
                    ClockSkew = TimeSpan.FromMinutes(1)
                };
            });

        services.AddAuthorization();

        return services;
    }
}
