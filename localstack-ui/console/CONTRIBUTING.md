# Contributing to the Console

## Add a new service view

1. **Register the service** in `src/routes/registry.ts` under
   `SERVICES_BY_CLOUD[cloud]`. The `id` must match the key that
   `/_localstack/clouds/{cloud}/health` reports.

2. **Implement the routes** in `src/routes/{cloud}/services.tsx` (or a
   new file). Use `<ResourcePage>` from `src/components/resource-page/`
   and TanStack Query for all reads/writes.

3. **Add a Terraform generator** in `src/lib/iac/generators.ts`. Pass
   the snippet to `<ResourcePage iac={{ tool: "terraform", snippet }}/>`
   to wire up the "Show as Terraform" drawer.

4. **Add an API client** in `src/lib/api/{cloud}.ts`. AWS uses the
   official `@aws-sdk/*` clients with `endpoint: http://localhost:4566`
   and credentials `test/test`. Azure / GCP use `fetch` against the
   path-routed gateway.

5. **Register the route** in `src/router.tsx` (`createRoute({...})`).

## Skins

Per-cloud visual tokens live in `src/lib/skins.ts` (`SKINS` map). The
Tailwind theme reads them via CSS variables defined in
`src/styles/globals.css` (`[data-cloud=...]` blocks). To tweak the
brand colours, edit `SKINS` — `applySkin(name)` is called automatically
when the cloud picker changes.

## Testing

```bash
bun run test            # vitest (unit)
bun run test:e2e        # playwright (requires running stack on :4577)
bun run typecheck       # tsc --noEmit
bun run lint            # eslint
```

The Python side has its own coverage:

```bash
pytest tests/unit/console/                            # validators
SKIP_CONSOLE_SMOKE=0 pytest tests/aws/test_console_endpoints_smoke.py
```

## File layout cheat-sheet

```
src/
├── App.tsx                   # shell + drawers
├── main.tsx                  # bootstraps providers + router
├── router.tsx                # route tree
├── routes/
│   ├── HomeIndex.tsx
│   ├── registry.ts           # service catalogue
│   ├── aws/services.tsx
│   ├── azure/services.tsx
│   └── gcp/services.tsx
├── components/
│   ├── shell/                # TopBar · Sidebar · Breadcrumbs
│   ├── resource-page/        # shared list/detail layout
│   ├── iac/                  # IaC inline drawer
│   ├── cloud-shell/          # CLI bridge drawer
│   └── ui/                   # shadcn primitives
├── lib/
│   ├── api/{aws,azure,gcp,clouds}.ts
│   ├── cloud-context.tsx
│   ├── skins.ts
│   ├── iac/generators.ts
│   ├── iac-drawer-store.ts
│   ├── cli-bridge.ts
│   ├── queryClient.ts
│   └── utils.ts
└── styles/globals.css
```
