using Asp.Versioning;
using FluentValidation;
using Veracity.Common.Authentication;
using {{ProjectName}}.Middleware;

var builder = WebApplication.CreateBuilder(args);

// Required for Swashbuckle to discover minimal API endpoints.
builder.Services.AddEndpointsApiExplorer();

builder.Services.AddApiVersioning(options =>
{
    options.DefaultApiVersion = new ApiVersion(1, 0);
    options.AssumeDefaultVersionWhenUnspecified = true;
    options.ReportApiVersions = true;
    options.ApiVersionReader = ApiVersionReader.Combine(
        new UrlSegmentApiVersionReader(),
        new HeaderApiVersionReader("X-Api-Version"));
})
.AddApiExplorer(options =>
{
    options.GroupNameFormat = "'v'VVV";
    options.SubstituteApiVersionInUrl = true;
});

// OpenAPI / Swagger
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new() { Title = "{{ProjectName}} API", Version = "v1" });
});

// FluentValidation
builder.Services.AddValidatorsFromAssemblyContaining<Program>();

// Health checks
builder.Services.AddHealthChecks()
    .AddCheck("api-ready", () => Microsoft.Extensions.Diagnostics.HealthChecks.HealthCheckResult.Healthy(), tags: new[] { "ready" });

// CSP & Security Headers
builder.Services.Configure<CSPOptions>(builder.Configuration.GetSection("CSP"));

builder.Services.AddVeracityAuthentication(builder.Configuration, builder.Environment);

var app = builder.Build();

// Global error handler
app.UseExceptionHandler(errorApp =>
{
    errorApp.Run(async context =>
    {
        context.Response.ContentType = "application/problem+json";
        var exception = context.Features.Get<Microsoft.AspNetCore.Diagnostics.IExceptionHandlerFeature>()?.Error;
        var problem = new Microsoft.AspNetCore.Mvc.ProblemDetails
        {
            Status = StatusCodes.Status500InternalServerError,
            Title = "An error occurred",
            Detail = app.Environment.IsDevelopment() ? exception?.Message : null
        };
        context.Response.StatusCode = problem.Status!.Value;
        await context.Response.WriteAsJsonAsync(problem);
    });
});

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "{{ProjectName}} API V1");
    });
}
app.UseVeracityTokenCacheRecovery();
app.UseHttpsRedirection();
app.UseMiddleware<SecurityHeadersMiddleware>();
app.UseAuthentication();
app.UseVeracity();
app.UseAuthorization();

// Health check endpoints (anonymous)
app.MapHealthChecks("/health").AllowAnonymous();
app.MapHealthChecks("/health/ready", new Microsoft.AspNetCore.Diagnostics.HealthChecks.HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready")
}).AllowAnonymous();
app.MapHealthChecks("/health/live", new Microsoft.AspNetCore.Diagnostics.HealthChecks.HealthCheckOptions
{
    Predicate = _ => false
}).AllowAnonymous();

app.MapAuthEndpoints();

// Map versioned endpoint groups
var api = app.NewVersionedApi();
var apiGroup = api.MapGroup("/api/v{version:apiVersion}")
    .HasApiVersion(1.0)
    .RequireAuthorization();
{{EndpointMapping}}

app.Run();
