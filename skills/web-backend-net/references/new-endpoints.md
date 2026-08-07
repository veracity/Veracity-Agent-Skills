# Adding New Endpoints

When implementing new features with new endpoints, follow this pattern:

1. Create a new static class in an `Endpoints/` folder
2. Define a static extension method on `IEndpointRouteBuilder`
3. Use the fluent API for metadata (`.WithName()`, `.WithSummary()`, `.WithTags()`, `.Produces<T>()`)
4. Map it in `Program.cs` on the versioned `apiGroup`

**Example pattern:**

```csharp
public static class MyFeatureEndpoints
{
    public static void MapMyFeatureEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/my-feature", async (IMyService service) =>
        {
            return await service.GetDataAsync();
        })
        .WithName("GetMyFeature")
        .WithSummary("Description of what this endpoint does")
        .WithTags("MyFeature")
        .Produces<MyResponse>(200)
        .Produces(401)
        .Produces(500);
    }
}
```

Then in `Program.cs`:
```csharp
apiGroup.MapMyFeatureEndpoints();
```

Key conventions:
- One file per feature/domain area
- Use typed results (`TypedResults.Ok(...)`) for compile-time safety
- Add FluentValidation validators in the same file or a `Validators/` folder
- The versioned `apiGroup` is unauthenticated in the baseline scaffold; an auth skill
  (e.g. `veracity-auth-net`) adds `.RequireAuthorization()` to the group and
  `.AllowAnonymous()` to specific public endpoints
