# User Briefing Integration Plan

## Requirements

- REQ-001: Build a Home Assistant custom integration for per-user daily briefings with UI-based setup.
- REQ-002: Model each person as an independent config entry so scheduling and delivery can differ by user.
- REQ-003: Model each briefing purpose as a separately configurable item that a user can add multiple times with different filters.
- REQ-004: Support rule-based briefing composition only for v1; no LLM is required for snippet generation or wording.
- REQ-005: Use scenario-based phrase banks with variable replacement so wording changes while staying deterministic, friendly, and sometimes funny.
- REQ-006: Expose one final briefing entity per user and one entity per snippet instance for dashboard reuse.
- REQ-007: Separate briefing generation from briefing delivery so notifications, dashboard views, and later voice channels can reuse the same rendered result.
- REQ-008: Provide scheduled and on-demand generation paths.
- REQ-009: Support v1 snippet/provider types for calendar, weather forecast, beach or wind conditions, a generic task-summary interface over existing Home Assistant task ecosystems, news headlines, home status, compliments, and a mail-summary stub contract.
- REQ-010: Keep design and packaging consistent with the author's existing Home Assistant integrations where practical.
- REQ-011: Use Home Assistant-native config flows, services, selectors, and HACS packaging conventions.
- REQ-012: Leave a clean extension path for future additions such as actionable notifications, Assist exposure, and richer provider adapters.
- REQ-013: Define a strict plugin architecture so content providers can be added, replaced, versioned, disabled, or omitted without changing the core composer.
- REQ-014: Separate snippet provider logic from source adapters, phrase rendering, and delivery so one concern can evolve without forcing changes in the others.
- REQ-015: Keep mobile notification support at the interface and payload-contract level in v1; do not hardwire actionable notification behavior into the first implementation.
- REQ-016: Make dashboard assembly a first-class output of the architecture by specifying reusable per-provider card fragments or templates that can be composed into per-user briefing dashboards.
- REQ-017: Use current Home Assistant flow UX capabilities, including sections, selectors, read-only fields where applicable, `data_description`, and post-create subentry continuation.
- REQ-018: Avoid deprecated advanced-mode gating in flows and instead present advanced settings through explicit sections or dedicated steps.
- REQ-019: Use current options-flow patterns by relying on `self.config_entry`, avoiding `OptionsFlowWithConfigEntry` in new code, and using reload-aware flows where appropriate.
- REQ-020: Allow providers to emit structured alerts in addition to their standard informational content.
- REQ-021: Ensure promoted alerts are rendered at the top of the briefing to gain user attention while preserving the underlying source context.
- REQ-022: Make consuming existing Home Assistant and HACS integrations the primary data path. Providers should read existing entities and services through reusable adapter primitives so adding a new source needs minimal code.

## Phases

- [x] TASK-001: Define domain, config-entry model, subentry model, manifest metadata, and HACS metadata.
- [x] TASK-002: Design config flow for user creation and subentry flows for snippet instances.
- [x] TASK-003: Define provider contract, snippet result schema, briefing composer pipeline, and phrase-bank contract.
- [x] TASK-004: Specify entities, services, and delivery boundaries.
- [x] TASK-005: Design v1 providers and stub adapters, including the mail-summary interface and the generic task-summary interface.
- [x] TASK-006: Define documentation layout, dashboard templates or card fragments, and automation patterns for notification and dashboard use.
- [x] TASK-007: Define test plan for config flows, providers, rendering, services, and regression coverage.
- [x] TASK-008: Review optional feature additions with the user before locking the v1 spec.
- [x] TASK-009: Define plugin registry, provider capability metadata, adapter contracts, and compatibility rules.
- [x] TASK-010: Define configuration UX details for main config flow, options flow, reconfigure flow, and subentry onboarding using the latest Home Assistant UI patterns.
- [x] TASK-011: Implement dynamic snippet entity lifecycle so subentry creation, update, and removal are reflected in runtime entities without undocumented reload assumptions.
- [x] TASK-012: Replace stub providers with real provider implementations, starting with calendar, weather, task-summary, and compliment.
- [x] TASK-013: Implement provider-specific reconfigure schemas and richer selectors for built-in providers.
- [ ] TASK-014: Implement dashboard fragment composition and at least one full per-user dashboard template generated from provider fragments.
- [ ] TASK-015: Implement notification payload helper generation while keeping delivery workflows stubbed.
- [ ] TASK-016: Decide and implement the final dedicated entity surface for generated-at and per-snippet status, or revise architecture docs to match the chosen entity model.
- [ ] TASK-017: Expand automated tests for coordinator behavior, flow behavior, service responses, and runtime edge cases.
- [ ] TASK-018: Replace placeholder phrase assets with real scenario-based phrase banks and add rendering coverage.
- [ ] TASK-019: Define and implement a shared alert contract so providers can emit structured alerts independently of their normal snippet text.
- [ ] TASK-020: Implement alert promotion, severity ordering, and alert-aware rendering in the coordinator and renderer.
- [ ] TASK-021: Add dashboard fragments or cards for promoted alerts so alert state is visible before normal informational snippets.
- [x] TASK-022: Provide reusable adapter primitives (`HomeAssistantEntityAdapter`, `HomeAssistantServiceAdapter`) and a provider `get_adapter()` seam so existing integrations can be consumed with minimal provider code.
- [x] TASK-023: Add adapter recipes/wiring for the first real providers (calendar via `calendar.get_events`, weather via `weather.get_forecasts`, task summary via `todo.get_items`) and document the pattern for contributors.

## Alternatives

- ALT-001: Use a Home Assistant package or blueprint instead of a custom integration.
  - Rejected because the requested model needs reusable per-user setup, extensible snippet instances, and a provider/plugin architecture.
- ALT-002: Store all user and snippet configuration in one large options flow.
  - Rejected because multi-instance snippet configuration becomes brittle and hard to extend.
- ALT-003: Use Jinja custom templates as the primary phrase engine.
  - Rejected for the main architecture because Python-owned phrase packs are easier to test, version, and evolve, though Jinja remains useful for prototypes.
- ALT-004: Use one master automation that loops through all users.
  - Rejected for v1 because one automation per user is simpler to reason about and matches the user's preference.
- ALT-005: Use an LLM to summarize all briefing content.
  - Rejected for v1 because the user explicitly wants rule-based composition and pre-authored phrase variation.

## Dependencies

- DEP-001: Home Assistant config entries and config-subentry flows.
- DEP-002: Home Assistant selectors and service action schemas.
- DEP-003: Optional built-in integrations used as data sources or delivery channels: `calendar`, `weather`, `todo`, `mobile_app`, `notify`, `conversation`.
- DEP-003A: Existing Home Assistant task-service integrations should be consumed through Home Assistant task or to-do entities or actions instead of bespoke provider-specific implementations.
- DEP-004: Optional custom integrations used as snippet sources, including `ha-catalunya-beaches`.
- DEP-005: HACS metadata and README conventions consistent with the author's existing repositories.
- DEP-006: Phrase-bank assets bundled in the integration package.
- DEP-007: Internal provider registry and optional provider auto-discovery within the integration package.

## Files

- FILE-001: `custom_components/user_briefing/manifest.json`
- FILE-002: root `hacs.json`
- FILE-003: `custom_components/user_briefing/__init__.py`
- FILE-004: `custom_components/user_briefing/config_flow.py`
- FILE-005: `custom_components/user_briefing/const.py`
- FILE-006: `custom_components/user_briefing/coordinator.py`
- FILE-007: `custom_components/user_briefing/services.yaml`
- FILE-008: `custom_components/user_briefing/strings.json`
- FILE-009: `custom_components/user_briefing/entity.py`
- FILE-010: `custom_components/user_briefing/sensor.py`
- FILE-011: `custom_components/user_briefing/providers/base_stub.py`
- FILE-012: `custom_components/user_briefing/providers/*.py`
- FILE-012A: `custom_components/user_briefing/providers/registry.py`
- FILE-012B: `custom_components/user_briefing/providers/contracts.py`
- FILE-012C: `custom_components/user_briefing/adapters/*.py`
- FILE-012D: `custom_components/user_briefing/subentries.py`
- FILE-013: `custom_components/user_briefing/phrases/README.md`
- FILE-014: `custom_components/user_briefing/models.py`
- FILE-015: `custom_components/user_briefing/rendering.py`
- FILE-016: `README.md`
- FILE-016A: `AGENTS.md`
- FILE-017: `docs/setup.md`
- FILE-018: `docs/configuration.md`
- FILE-019: `docs/services.md`
- FILE-019A: `docs/dashboards.md`
- FILE-019B: `custom_components/user_briefing/dashboard_templates/*.yaml`
- FILE-019C: `specs/configuration-ux.md`
- FILE-019D: `specs/contracts-and-schemas.md`
- FILE-020: `tests/test_config_flow.py`
- FILE-021: `tests/test_registry.py`
- FILE-022: `tests/test_rendering.py`
- FILE-023: future flow/coordinator/service/provider behavior tests

## Testing

- TEST-001: Validate main config flow creates one config entry per user with stable unique IDs.
- TEST-002: Validate subentry flows support multiple snippet instances of the same type with distinct filters.
- TEST-003: Validate phrase selection is deterministic under a seeded random strategy and safe for warning scenarios.
- TEST-004: Validate each provider returns structured results for `ok`, `empty`, `warning`, and `error` paths.
- TEST-005: Validate final briefing rendering preserves required snippets, ordering, and delivery-neutral output.
- TEST-006: Validate services for generate, preview, and deliver accept expected payloads and return useful results.
- TEST-007: Validate dashboard entities update correctly after manual refresh and scheduled refresh.
- TEST-008: Validate optional integrations missing from the system degrade gracefully instead of breaking setup.
- TEST-009: Validate a provider can be added or removed from the registry without changing core composition code.
- TEST-010: Validate provider capability flags drive config UI and runtime behavior correctly.
- TEST-011: Validate adapter failures remain isolated to the owning provider instance.
- TEST-012: Validate dashboard card fragments generated by providers stay compatible with the exposed entities and can be composed per user.
- TEST-013: Validate config flows use translated labels and `data_description`, post-create next-flow behavior, and section-based grouping instead of advanced-mode gating.
- TEST-014: Validate options flow uses current `self.config_entry` patterns and reload behavior correctly.
- TEST-015: Validate coordinator generation skips disabled snippets and sorts enabled snippets by configured order.
- TEST-016: Validate preview returns response data without mutating cached entity state.
- TEST-017: Validate services require explicit config-entry targets and reject unknown config-entry IDs.
- TEST-018: Validate dynamic snippet entity creation and teardown when subentries change.
- TEST-019: Validate providers can emit alerts without losing their normal snippet content.
- TEST-020: Validate promoted alerts sort ahead of regular briefing content by severity and source order rules.
- TEST-021: Validate adapter primitives read entity state/attributes and service responses, and degrade gracefully when sources are missing.

## Risks

- RISK-001: Phrase-bank scope can expand quickly if every snippet type gets too many scenario combinations in v1.
- RISK-002: Cross-platform notification features differ between Android and iOS, especially for action buttons.
- RISK-003: External provider variance can make some snippets noisy, stale, or incomplete.
- RISK-004: If scheduling logic moves into the integration too early, it may duplicate Home Assistant automation capabilities.
- RISK-005: Too many exposed scripts or overly broad Assist exposure can hurt voice reliability later.
- RISK-006: Mail summary support can sprawl if adapter contracts are not strict from the beginning.
- RISK-007: A weak provider contract would let snippet implementations leak transport or rendering concerns into the core.
- RISK-008: Dashboard fragments can drift from actual entity capabilities if template contracts are not versioned and tested alongside providers.

## References

- ASSUMPTION-001: The integration domain should use underscores, not hyphens, for long-term Home Assistant compatibility.
- ASSUMPTION-002: `integration_type: service` and `iot_class: calculated` are the best manifest defaults for an aggregator-style briefing integration.
- ASSUMPTION-003: One automation per user remains outside the integration as a Home Assistant-native responsibility.
- ASSUMPTION-004: Phrase assets are bundled with the integration and optionally overridden later, not authored in Home Assistant helpers for v1.
- ASSUMPTION-005: Task summaries should integrate with existing Home Assistant task or to-do entities and services rather than reimplement upstream task providers.
- REF-001: `https://github.com/tamaygz/ha-catalunya-beaches`
- REF-002: `https://github.com/tamaygz/hacs-wledext-effects`
- REF-003: `https://github.com/tamaygz/hacs-stremio`
- REF-004: `https://developers.home-assistant.io/docs/core/integration/config_flow/`
- REF-005: `https://developers.home-assistant.io/docs/config_entries_options_flow_handler/`
- REF-006: `https://developers.home-assistant.io/docs/creating_integration_manifest/`
- REF-007: `https://www.home-assistant.io/docs/templating/custom-templates/`
- REF-008: `https://companion.home-assistant.io/docs/notifications/actionable-notifications/`
- REF-009: `https://www.home-assistant.io/integrations/todo/`
- REF-010: `https://www.home-assistant.io/voice_control/exposing_scripts_to_llms/`