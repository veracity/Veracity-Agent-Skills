using Azure.Extensions.AspNetCore.DataProtection.Keys;
using Azure.Identity;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Caching.StackExchangeRedis;
using Microsoft.Extensions.Options;
using StackExchange.Redis;
using Veracity.Common.Authentication;
using Veracity.Common.OAuth.Providers;
{{VeracityApiUsings}}

public static class VeracityAuthExtensions
{
    public static IServiceCollection AddVeracityAuthentication(this IServiceCollection services, IConfiguration configuration, IHostEnvironment environment)
    {
        // Add Veracity authentication
        services.AddVeracity(configuration);

        if (environment.IsDevelopment())
        {
            services.AddSingleton(ConstructDataProtector)
                .AddSingleton(ConstructDistributedCache);
        }
        else
        {
            // Use Redis as distributed cache
            var redisConnectionString = configuration.GetConnectionString("Redis")
                ?? throw new InvalidOperationException("Redis connection string 'Redis' is required.");

            services.AddStackExchangeRedisCache(options => { options.Configuration = redisConnectionString; });

            // Use Azure Key Vault for data protection key storage
            var keyVaultKeyUri = configuration["DataProtection:KeyVaultKeyUri"]
                ?? throw new InvalidOperationException("DataProtection:KeyVaultKeyUri configuration is required.");

            var redis = ConnectionMultiplexer.Connect(redisConnectionString);
            services.AddDataProtection()
                .PersistKeysToStackExchangeRedis(redis, "DataProtection-Keys")
                .ProtectKeysWithAzureKeyVault(new Uri(keyVaultKeyUri), new DefaultAzureCredential());

            services.AddSingleton(ConstructDataProtector);
        }

        {{VeracityApiRegistration}}

        // Configure authentication
        services.AddAuthentication(options =>
        {
            options.DefaultScheme = CookieAuthenticationDefaults.AuthenticationScheme;
            options.DefaultChallengeScheme = OpenIdConnectDefaults.AuthenticationScheme;
        })
        .AddVeracityAuthentication(configuration)
        .AddCookie();

        services.Configure<CookieAuthenticationOptions>(
            CookieAuthenticationDefaults.AuthenticationScheme, options =>
        {
            options.Cookie.Name = "__Host-auth";
        });

        services.Configure<OpenIdConnectOptions>(
            OpenIdConnectDefaults.AuthenticationScheme, options =>
        {
            // Use a 302 redirect instead of the form_post HTML page
            // (form_post breaks when CSP blocks inline scripts).
            options.AuthenticationMethod = OpenIdConnectRedirectBehavior.RedirectGet;

            options.Events ??= new OpenIdConnectEvents();
            var existingRedirectToIdentityProvider = options.Events.OnRedirectToIdentityProvider;
            options.Events.OnRedirectToIdentityProvider = async context =>
            {
                if (context.Request.Path.StartsWithSegments("/api"))
                {
                    context.Response.StatusCode = StatusCodes.Status401Unauthorized;
                    context.HandleResponse();
                    return;
                }
                if (existingRedirectToIdentityProvider != null)
                    await existingRedirectToIdentityProvider(context);
            };
        });

        services.AddAuthorization();

        return services;
    }

    /// <summary>
    /// Adds middleware that recovers from a stale authentication cookie whose backing token cache entry
    /// has been evicted (e.g. after an app restart in development, or if Redis is flushed in production).
    /// The stale cookie is cleared and the user is transparently redirected to sign in again.
    /// </summary>
    public static IApplicationBuilder UseVeracityTokenCacheRecovery(this IApplicationBuilder app)
    {
        var logger = app.ApplicationServices
            .GetRequiredService<ILoggerFactory>()
            .CreateLogger(nameof(UseVeracityTokenCacheRecovery));

        return app.Use(async (context, next) =>
        {
            try
            {
                await next(context);
            }
            catch (ServerException ex)
            {
                logger.LogWarning(ex,
                    "Veracity ServerException intercepted: Status={Status} Message={Message}. " +
                    "User={User} Path={Path}",
                    ex.Status, ex.Message,
                    context.User.Identity?.Name,
                    context.Request.Path);

                if ((int)ex.Status == StatusCodes.Status401Unauthorized
                    && (context.User.Identity?.IsAuthenticated ?? false))
                {
                    logger.LogInformation(
                        "Token cache miss detected for authenticated user {User}. Signing out and redirecting to re-authenticate.",
                        context.User.Identity?.Name);

                    await context.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
                    var returnUrl = SafeRedirect.SanitizeReturnUrl(context.Request.Path + context.Request.QueryString);
                    await context.ChallengeAsync(OpenIdConnectDefaults.AuthenticationScheme,
                        new AuthenticationProperties { RedirectUri = returnUrl });
                    return;
                }

                throw;
            }
        });
    }

    private static IDistributedCache ConstructDistributedCache(IServiceProvider s)
    {
        return new MemoryDistributedCache(new OptionsWrapper<MemoryDistributedCacheOptions>(new MemoryDistributedCacheOptions()));
    }

    private static Veracity.Common.Authentication.IDataProtector ConstructDataProtector(IServiceProvider s)
    {
        return new DataProtector<IDataProtectionProvider>(s.GetDataProtectionProvider(), (p, data) => p.CreateProtector("token").Protect(data), (p, data) => p.CreateProtector("token").Unprotect(data));
    }
}
