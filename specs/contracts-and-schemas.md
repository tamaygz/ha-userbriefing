# Contracts And Schemas

## Goal

Define concrete contracts for the scaffold so the plugin system, services, rendering, and dashboards have stable shared types from the start.

## Core models

### User profile entry data

Immutable or identity-like setup data:

- `user_key`
- `display_name`
- `locale`

### User profile entry options

Mutable profile behavior:

- `dashboard_template`
- `dashboard_path`
- `default_delivery_mode`
- `rendering_style`

### Snippet subentry data

- `provider_key`
- `source_ref`
- `source_type`

### Snippet subentry options

- `enabled`
- `order`
- `priority`
- `title_override`
- `provider_options`

## Provider contract

Suggested provider methods:

- `describe() -> ProviderMetadata`
- `build_config_schema() -> vol.Schema | selector-based schema`
- `build_reconfigure_schema(existing_data, existing_options) -> vol.Schema`
- `build_options_schema() -> vol.Schema | None`
- `validate_config(config) -> dict`
- `validate_reconfigure_config(config) -> dict`
- `get_adapter() -> ProviderAdapter | None`
- `async_collect(config) -> RawProviderPayload`
- `normalize(payload, instance_id) -> SnippetResult`
- `build_phrase_context(result) -> dict`
- `get_instance_title(config) -> str`
- `get_instance_unique_key(config) -> str | None`
- `build_dashboard_fragments(entity_id_prefix) -> list[DashboardFragment]`

Scenario selection currently happens inside `normalize()`; it may move to a dedicated `choose_scenario()` step when real phrase banks land.

## Adapter contract

Adapters consume existing Home Assistant integrations and normalize their output for providers.

Base interface (`ProviderAdapter`):

- `__init__(hass)`
- `async_fetch(context) -> dict` (required)
- `async_describe_source(source_ref) -> dict` (optional, for validation and UX hints)

Reusable primitives shipped with the integration:

- `HomeAssistantEntityAdapter` reads `state` and `attributes` for any `entity_id` passed as `context["source_ref"]`
- `HomeAssistantServiceAdapter` calls a service using `context["service_domain"]`, `context["service_name"]`, optional `service_data` and `target`, returning the service response
- `StubAdapter` returns an empty payload for sources that are not wired yet

Providers connect to an adapter via `get_adapter()`; the default `async_collect()` delegates to it. Adapters should stay narrow and source-specific, and prefer existing integration entities or services over direct external access.

## Result contract

### SnippetResult

- `provider_key`
- `instance_id`
- `status`
- `priority`
- `alerts`
- `title`
- `text`
- `scenario`
- `data`
- `meta`
- `actions`

### AlertItem

- `alert_key`
- `provider_key`
- `severity`
- `title`
- `text`
- `source_label`
- `navigation_path`
- `meta`

### BriefingResult

- `user_key`
- `generated_at`
- `summary_state`
- `alerts`
- `snippets`
- `rendered_text`
- `delivery_payloads`

## Dashboard fragment contract

- `fragment_key`
- `provider_key`
- `title`
- `card_type`
- `entities`
- `badges`
- `navigation_path`
- `layout_hint`

## Alert handling contract

- providers may emit both regular snippet text and alerts in the same generation pass
- alerts must be structured and sortable by severity
- the composer must render alerts before the normal snippet body order
- dashboard assembly should support alert-focused cards or chips where applicable

## Service schema direction

### `user_briefing.generate`

Suggested fields:

- `config_entry_id`

### `user_briefing.preview`

Suggested fields:

- `config_entry_id`

Suggested response payload:

- `user_key`
- `summary_state`
- `rendered_text`
- `snippet_count`

### `user_briefing.deliver`

Suggested fields:

- `config_entry_id`
- future delivery mode selector
- future use cached vs regenerate flag

### `user_briefing.refresh_snippet`

Suggested fields:

- `config_entry_id`
- `subentry_id`

## Schema decisions

- use selectors wherever Home Assistant supports better constrained UX
- use read-only selectors in options flows for context the user should see but not edit
- use suggested values when editing mutable data
- use section grouping for non-trivial schemas