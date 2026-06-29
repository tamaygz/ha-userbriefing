# User Briefing Integration Architecture v1

## Summary

This integration should be a HACS-distributed Home Assistant custom integration that composes a per-user daily briefing from modular snippet providers. It should be UI-configurable, rule-based, phrase-driven, and extensible without forcing new snippet types into a monolithic options form.

## Domain Model

### User profile

One config entry represents one person.

Suggested stored data:

- stable user key or slug
- display name
- locale and language
- default delivery targets
- dashboard path or dashboard template key for deep links and generated views
- optional quiet-hours or availability gating later

Suggested unique ID:

- normalized user key or selected notification target identity

### Snippet instance

One config subentry represents one configured purpose within a single user briefing.

Examples:

- Work calendar
- Family calendar
- Sitges beach conditions
- Wind conditions for a specific beach
- Daily compliment
- News headlines

Each snippet instance should contain:

- snippet type
- enabled flag
- display order
- required vs optional
- source-specific filters
- per-snippet tone override if needed later

### Snippet result

Each provider should normalize output to a shared contract:

- `status`: `ok | empty | warning | error`
- `priority`: `required | optional`
- `alerts`: zero or more structured attention items emitted by the provider
- `title`: short human label
- `text`: rendered snippet text
- `data`: structured provider payload
- `meta`: timestamps, provider info, debug hints
- `scenario`: phrase-bank scenario key used during rendering

Alerts are distinct from the main snippet text. A provider may return normal informational content and also emit one or more alerts that must be promoted in the final briefing.

### Briefing result

The composer should return:

- ordered snippet results
- promoted alert list sorted ahead of regular snippet content
- final rendered text
- compact summary state
- generated timestamp
- delivery hints, such as recommended title and severity

## Configuration Model

### Main config flow

The main flow should create one user profile.

Suggested steps:

1. Basic identity and display settings
2. Delivery defaults
3. Initial creation complete
4. Optionally continue to add the first snippet subentry

UX guidance based on current Home Assistant docs:

- use translated field labels and `data_description` for anything that is not self-evident
- use selectors rather than raw strings whenever entity, text type, numbers, or list choices can be constrained
- use `title_placeholders` and translated `flow_title` patterns where dynamic titles improve clarity
- use `async_on_create_entry()` to continue directly into the first subentry flow after the user profile is created
- use sections for grouped or advanced settings instead of relying on advanced-mode flags

### Subentry flows

Use Home Assistant config subentries for snippet instances.

Why:

- matches the requested mental model of separate addable purposes
- supports multiple instances of the same type cleanly
- avoids giant options schemas
- gives a natural path for future provider-specific reconfigure steps

Each subentry flow should collect:

1. snippet type
2. type-specific source or selector values
3. ordering and priority
4. enablement and optional display settings

Subentry flow implementation should target the current Home Assistant API shape, including the 2025 `ConfigSubentryFlow` naming changes.

## Entities

Expose stateful entities so dashboards and automations can consume the integration without having to call services every time.

### Per-user entities

- final briefing sensor or text-like sensor
- briefing status sensor
- last generated timestamp sensor

### Per-snippet entities

- snippet rendered text sensor
- snippet status sensor
- snippet metadata attributes

Avoid making notification delivery the only way to access the output.

## Services

Suggested services:

- `user_briefing.generate`
  - Generate a user briefing and update entities.
- `user_briefing.preview`
  - Generate a briefing and return the rendered output without delivery side effects.
- `user_briefing.deliver`
  - Deliver the last generated briefing or a freshly generated one.
- `user_briefing.refresh_snippet`
  - Refresh one configured snippet instance.

Notification-specific behavior in v1 should stop at service contracts and payload helpers. Rich mobile actions should remain a later implementation concern, not a core runtime dependency.

Suggested service design:

- concise names
- selector-based fields in `services.yaml`
- target by `config_entry_id` for profile-level actions and by `config_entry_id` plus `subentry_id` for snippet-level actions
- return structured results suitable for scripts and future Assist exposure

Configuration mutability split:

- immutable identity or setup choices go in `ConfigEntry.data`
- mutable behavior settings go in `ConfigEntry.options`
- per-snippet mutable settings live on the subentry and are exposed through reconfigure-capable subentry flows

## Provider Architecture

Each snippet type should be implemented as a provider plugin with a strict interface.

The core integration should depend on provider contracts, not provider implementations. Adding a new content source should mean registering a new provider module and, if necessary, a source adapter, without editing the composer, entity layer, or delivery layer.

### Architectural boundaries

Split the system into four layers:

1. Core orchestration
2. Provider plugins
3. Source adapters
4. Rendering and delivery

Core orchestration owns:

- config entries and subentries
- provider registry lookup
- execution ordering
- alert promotion and ordering rules
- failure isolation
- final briefing assembly

Provider plugins own:

- provider-specific config schema
- provider-specific normalization rules
- scenario selection
- mapping normalized data to phrase variables

Source adapters own:

- reading data from Home Assistant entities, services, or external integration APIs
- translating upstream payloads into provider-friendly raw data

Rendering and delivery own:

- phrase selection
- final text formatting
- notification or dashboard output

This boundary is important because it makes providers exchangeable. A `weather_forecast` provider should be able to switch from one weather-backed adapter to another without changing the provider contract or the composer.

### Provider registry

Providers should be registered centrally through a registry module.

The registry should expose:

- provider key
- display name
- provider version
- supported config schema builder
- supported options schema builder if the provider has mutable runtime settings
- capability flags
- factory for provider instances

Suggested capability flags:

- supports multiple instances
- supports required or optional priority
- supports preview
- supports actionable follow-ups
- supports dashboard deep links
- supports dashboard card fragments
- supports phrase overrides

The config flow and subentry flow should read from this registry instead of hardcoding snippet types in multiple places.

For UX quality, the registry should also surface provider-specific form metadata such as section groupings, recommended defaults, and read-only display fields for options flows.

### Provider contract

Each provider should implement a stable interface with methods equivalent to:

1. describe
2. validate_config
3. build_config_schema
4. collect
5. normalize
6. choose_scenario
7. build_phrase_context
8. optional build_actions

Provider outputs should be fully normalized before the composer sees them. The composer should never need per-provider branching beyond capability-driven behavior.

Providers should be able to emit both:

- standard snippet content
- structured alerts that the core can lift to the top of the briefing

The core should own alert ordering and presentation rules so alert behavior stays consistent across providers.

### Adapter contract

Providers should not talk directly to arbitrary upstream integrations when a reusable adapter boundary is possible. Existing Home Assistant integrations (core and HACS) are the primary data source, and the integration ships reusable adapter primitives so consuming them is easy:

- `HomeAssistantEntityAdapter` reads state and attributes from any entity, regardless of which integration owns it
- `HomeAssistantServiceAdapter` calls any service (optionally with response) for richer data such as `calendar.get_events`, `weather.get_forecasts`, or `todo.get_items`

Providers declare their source via `get_adapter()`, and the default `async_collect()` delegates to that adapter. Examples:

- a calendar provider uses a service adapter over `calendar.get_events`
- a weather provider uses a service adapter over `weather.get_forecasts`
- a task-summary provider uses a service adapter over `todo.get_items` across any to-do backend
- a beach provider uses an entity adapter over the Catalunya Beaches integration's entities
- a mail-summary provider uses a stub adapter now and Gmail or IMAP adapters later

This makes it possible to swap data sources while preserving the user-facing snippet type.

### Failure isolation

Every provider execution should be isolated.

Rules:

- one provider failure must not break the whole briefing
- provider results must degrade to `warning` or `error` with explanatory metadata
- required snippets may still render a fallback phrase instead of disappearing silently

Alert handling rules:

- alerts are rendered before normal snippet content
- critical and warning alerts sort ahead of informational alerts
- providers may emit alerts even when their normal snippet content is empty
- alert promotion should not discard the originating snippet context; users still need to know what source raised the alert

### Compatibility strategy

The provider contract should be versioned internally.

Suggested rule:

- the core defines a provider API version
- every provider declares the API version it implements
- incompatible providers are skipped with a clear diagnostics message

This matters if you later allow third-party provider packs or local experimental providers.

Suggested responsibilities:

1. validate snippet configuration
2. fetch or derive raw input
3. normalize to shared payload
4. determine scenario key
5. render final snippet text via phrase bank

The provider should not decide how the whole briefing is assembled, how notification payloads are delivered, or how unrelated providers behave.

Suggested v1 providers:

- `compliment`
- `calendar`
- `weather_forecast`
- `beach_conditions`
- `wind_conditions`
- `task_summary`
- `news_headlines`
- `home_status`
- `mail_summary_stub`

The `task_summary` provider should not reimplement Todoist, Microsoft To Do, or other upstream task systems. It should consume existing Home Assistant task or to-do entities and actions through adapters.

The `mail_summary_stub` should accept a structured provider payload so later adapters can feed it from Gmail, IMAP, Microsoft Graph, or custom integrations without changing the composer contract.

## Dashboard Assembly

Dashboards should be assembled per user from the entities and metadata exposed by providers.

Rules:

- every provider should expose enough structured entity state and attributes to support a reusable dashboard card
- the integration should ship template card fragments or dashboard snippets where practical
- user profiles may reference a preferred dashboard template or view path
- dashboard assembly should remain decoupled from generation and notification delivery

Suggested outputs:

- per-provider card templates or YAML fragments
- one example full briefing dashboard composed from the built-in providers
- deep-link metadata for providers that can jump to related detail views

### Extension path

There should be two supported extension modes:

- built-in providers shipped with the integration
- local experimental providers placed in a dedicated internal provider folder and registered through the same registry contract

Even if third-party distribution is deferred, the architecture should be ready for it.

## Rendering and Phrase Banks

The phrase system should be owned by the integration, not primarily by Home Assistant templates.

Reasoning:

- easier to test than Jinja-heavy wording logic
- easier to version and ship in HACS releases
- easier to apply safety rules around warnings and alert tones

Suggested phrase-bank layout:

- one phrase asset file per snippet type
- multiple scenario buckets per file
- optional shared intro and outro bank

Suggested scenario buckets:

- `intro`
- `normal`
- `empty`
- `good`
- `warning`
- `bad`
- `error`

Rendering rules:

- required snippets remain in the final briefing unless provider failure makes them impossible
- optional empty snippets can be omitted from short notification form while still exposed as entities
- warning or safety phrases must not become overly jokey

## Scheduling and Delivery

Scheduling should remain outside the integration in Home Assistant automations.

Reasoning:

- matches the user's preference for one automation per user
- stays consistent with Home Assistant-native orchestration
- avoids rebuilding an internal scheduler too early

Delivery should be separate from composition.

Recommended delivery channels for v1:

- dashboard card or dashboard page

Notification delivery should remain interface-level only in v1. The spec should define payload contracts and future hooks, but not require first-pass implementation of actionable notification workflows.

Future delivery channels:

- mobile notification
- TTS
- email or messenger
- Assist or exposed script invocation

## Packaging Recommendations

Suggested manifest direction:

- `domain`: `user_briefing`
- `name`: `User Briefing`
- `config_flow`: `true`
- `integration_type`: `service`
- `iot_class`: `calculated`
- `codeowners`: `@tamaygz`

Suggested repository shape:

- root `hacs.json`
- root `README.md`
- `custom_components/user_briefing/*`
- `custom_components/user_briefing/providers/*`
- `custom_components/user_briefing/adapters/*`
- `custom_components/user_briefing/dashboard_templates/*`
- `docs/configuration-ux.md`
- `docs/contracts-and-schemas.md`
- `docs/*`
- `tests/*`

## Non-Goals for v1

- LLM-generated prose
- internal scheduling engine
- direct mail-provider implementations
- highly dynamic user-authored phrase editing UI
- exhaustive provider ecosystem on first release