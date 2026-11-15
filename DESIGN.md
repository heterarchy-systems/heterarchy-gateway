# Native desktop design

Gateway desktop is a small macOS SwiftUI application. It exposes only the owner controls needed to register a Workspace, observe the registered count, configure an optional existing hostname, control MCP on port 7979, and decide a real pending authorization request.

The application delegates every operation to the authenticated Gateway owner entry command:

```text
uv run --locked --python 3.14.7t python -m app.bootstrap desktop --config <path> <operation>
```

It runs that command from the Gateway repository selected by `GATEWAY_PROJECT_ROOT` or the app bundle's `GatewayProjectRoot`. The default config is `~/.config/heterarchy-gateway/desktop.json`. Swift contains no backend credentials, persistence logic, direct backend HTTP calls, fabricated status, or retry loop. A failed process, extra output, unknown response fields, inconsistent result, or incomplete complete-count response fails closed.

The browser companion remains an isolated MCP provider execution component under `browser-companion/`. It has its own TypeScript guard, build, tests, and sealed Chrome artifact. It is not part of the desktop GUI.
