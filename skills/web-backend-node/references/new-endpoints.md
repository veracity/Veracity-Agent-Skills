# Adding New Endpoints

When implementing new features with new endpoints, follow this pattern:

1. Create a new router module per feature/domain area in `src/routes/`.
2. Validate request input with `zod` at the top of the handler.
3. Mount the feature router on the versioned anchor (`apiV1`), not directly on `app`.

**Example pattern:**

```ts
// src/routes/myFeature.ts
import { Router, type Request, type Response } from "express";
import { z } from "zod";

export const myFeatureRouter: Router = Router();

const querySchema = z.object({
  top: z.coerce.number().int().min(1).max(100).default(10),
});

myFeatureRouter.get("/", async (req: Request, res: Response) => {
  const query = querySchema.safeParse(req.query);
  if (!query.success) {
    res.status(400).json({
      title: "Validation failed",
      status: 400,
      errors: query.error.flatten().fieldErrors,
    });
    return;
  }

  res.json({ items: [], top: query.data.top });
});
```

Then in `src/routes/apiV1.ts`:

```ts
import { myFeatureRouter } from "./myFeature.js";

apiV1.use("/my-feature", myFeatureRouter);
```

The route is now reachable at `/api/v1/my-feature`.

Key conventions:

- One router file per feature/domain area under `src/routes/`.
- Validate inputs with `zod`; return a `400` with field errors on failure (the shape mirrors the .NET ProblemDetails validation response).
- Throw or `next(err)` for unexpected failures — the global error handler in `app.ts` turns them into a ProblemDetails-style `500`.
- The versioned `apiV1` router is unauthenticated in the baseline scaffold; an auth skill (e.g. `veracity-auth-node`) inserts auth middleware before it and opts specific public routes out.
- Add a `supertest` test per feature (`src/routes/myFeature.test.ts`) exercising the happy path and the validation failure.
