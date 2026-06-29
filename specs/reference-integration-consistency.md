# Reference Integration Consistency Notes

This note distills patterns from:

- `ha-catalunya-beaches`
- `hacs-wledext-effects`
- `hacs-stremio`

## Observed conventions

### Packaging and metadata

- All three repositories are HACS-oriented custom integrations.
- All three use a root `hacs.json` with minimal metadata.
- All three use `config_flow: true` in `manifest.json`.
- All three declare `documentation`, `issue_tracker`, `codeowners`, and a semantic version in the manifest.
- The repos keep `custom_components/<domain>/` as the main integration directory.

### Integration style

- `ha-catalunya-beaches` and `stremio` are service-oriented integrations.
- `wled_context_effects` is device-oriented because each config entry maps to a concrete WLED target.
- For User Briefing, `integration_type: service` is the closest match.
- For User Briefing, `iot_class: calculated` is a better fit than `cloud_polling` or `local_polling` because the integration composes results from other integrations rather than owning a transport.

### Config flow behavior

- Config flows are UI-first and multi-step when needed.
- Unique IDs are set early to prevent duplicates.
- Selectors and constrained inputs are used instead of raw free-text when possible.
- Mutable configuration tends to live in options or follow-up flow steps.

### Service documentation

- `services.yaml` entries use short imperative names and concrete descriptions.
- Service fields include selectors and examples where useful.
- Services are exposed as user-facing automation building blocks, not internal-only helpers.

### README style

- README files lead with a concise value proposition.
- Installation and setup sections appear early.
- Entities or features are enumerated clearly.
- Automation and dashboard examples are included.
- Follow-up docs are split into `docs/` where complexity grows.

## Recommendations for User Briefing

### Metadata

- Use a root `hacs.json` similar in minimalism to the reference repos.
- Use a manifest with explicit `integration_type` and `iot_class`.
- Use semantic versioning from the first public release.

### Domain and naming

- Prefer `user_briefing` as the manifest domain and component folder.
- Use `User Briefing` as the visible integration name.
- Use concise entity and service names that read well in automations.

### Config UX

- Keep the main flow focused on the user profile.
- Use subentry flows for addable snippet purposes.
- Use selectors heavily for source choices, ordering, notification targets, and snippet filters.

### Service surface

- Follow the existing repos' style with a small, explicit set of public services.
- Prefer verbs such as `generate`, `preview`, `deliver`, and `refresh_snippet`.

### Documentation shape

- README should include features, installation, setup flow, snippet concept, dashboard examples, and notification examples.
- Split advanced material into docs files once provider count grows.

## Consistency choices intentionally different from the reference repos

- Use config subentries because the user's mental model is one user with many configurable purposes.
- Use a phrase-bank asset system in Python instead of a template-first design.
- Expose per-snippet entities because the briefing content itself is first-class UI output, not just a backing service result.