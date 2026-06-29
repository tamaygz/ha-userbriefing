# User Briefing Agent Entry Point

This file is the starting point for any future agent working on this project.

Read this first, then open the files it points to based on the task you are doing.

## What This Project Is

This repository contains a Home Assistant custom integration scaffold for modular, per-user daily briefings.

Core design choices:

- one config entry per user profile
- one config subentry per configured briefing snippet
- provider-registry architecture for content modules
- adapter layer for upstream integrations and data sources
- dashboard-first entity exposure
- notification logic intentionally stubbed for later
- providers may emit structured alerts that are promoted to the top of the briefing

This is not a finished integration yet. It is an architecture-first scaffold with flow UX, contracts, stubs, and initial tests.

## Start Here By Task Type

### If your task is general implementation

Read in this order:

1. `TODO.md`
2. `specs/user-briefing-architecture-v1.md`
3. `specs/provider-plugin-architecture.md`
4. `specs/contracts-and-schemas.md`
5. `custom_components/user_briefing/`

### If your task is config/setup UX

Read in this order:

1. `specs/configuration-ux.md`
2. `custom_components/user_briefing/config_flow.py`
3. `custom_components/user_briefing/strings.json`
4. `plan/design-user-briefing-1.md`

### If your task is provider/plugin work

Read in this order:

1. `specs/provider-plugin-architecture.md`
2. `specs/contracts-and-schemas.md`
3. `custom_components/user_briefing/providers/contracts.py`
4. `custom_components/user_briefing/providers/registry.py`
5. the relevant provider file under `custom_components/user_briefing/providers/`
6. the relevant adapter file under `custom_components/user_briefing/adapters/`

### If your task is dashboard/UI work

Read in this order:

1. `specs/dashboard-assembly.md`
2. `docs/dashboards.md`
3. `custom_components/user_briefing/dashboard_templates/`
4. provider files that expose dashboard fragments

### If your task is tests/validation

Read in this order:

1. `TODO.md`
2. `plan/design-user-briefing-1.md`
3. files under `tests/`
4. the implementation files being changed

## File Map

## Top Level

- `README.md`
  - High-level repository summary and current scaffold status.
- `TODO.md`
  - The current working todo list and remaining follow-up work.
- `hacs.json`
  - HACS metadata for the custom integration.
- `AGENTS.md`
  - This file. Future-agent entry point.

## Plan

- `plan/design-user-briefing-1.md`
  - Master implementation plan.
  - Use it for requirements, phases, testing expectations, risks, and remaining follow-up direction.

## Specs

- `specs/user-briefing-architecture-v1.md`
  - Main architecture spec.
  - Use it for the overall system shape and boundaries.

- `specs/provider-plugin-architecture.md`
  - Provider/plugin and adapter architecture.
  - Use it before changing provider contracts, registration, replaceability, or compatibility behavior.

- `specs/contracts-and-schemas.md`
  - Concrete model and schema contracts.
  - Use it before adding or changing datamodels, service payloads, or dashboard fragment contracts.

- `specs/configuration-ux.md`
  - Config flow, options flow, reconfigure flow, and subentry UX strategy.
  - Use it before changing setup logic or translations.

- `specs/dashboard-assembly.md`
  - Dashboard composition strategy.
  - Use it before changing dashboard templates, provider card fragments, or dashboard-facing entity shape.

- `specs/reference-integration-consistency.md`
  - Notes comparing this project to the author's other Home Assistant integrations.
  - Use it to stay consistent in packaging, README shape, and Home Assistant conventions.

## Research

- `research/meaningful-additions-to-review.md`
  - Design decisions from web research and user confirmations.
  - Use it to understand why tasks are generic interfaces, why notifications are stubbed, and why dashboard assembly is first-class.

## Docs

- `docs/setup.md`
  - Short setup intent for the integration.
- `docs/configuration.md`
  - Summary of how data, options, and subentries are split.
- `docs/services.md`
  - Current public service surface.
- `docs/dashboards.md`
  - Dashboard composition intent and template direction.

## Integration Code

All integration code lives under `custom_components/user_briefing/`.

- `manifest.json`
  - Home Assistant integration metadata.
- `__init__.py`
  - Integration bootstrap and config-entry setup/unload.
- `const.py`
  - Shared constants and service names.
- `models.py`
  - Dataclasses for profile, provider metadata, snippets, briefing results, and dashboard fragments.
- `config_flow.py`
  - Main config flow, options flow, reconfigure flow, and subentry flow.
- `coordinator.py`
  - Briefing generation orchestration scaffold.
- `entity.py`
  - Shared entity base.
- `sensor.py`
  - Profile-level and snippet-level sensors.
- `rendering.py`
  - Final text rendering helpers.
- `services.py`
  - Public service registration and current stub routing.
- `services.yaml`
  - Home Assistant service descriptions and field selectors.
- `strings.json`
  - Flow translations and UX labels.
- `subentries.py`
  - Helpers for accessing subentries defensively.

## Providers

Provider code lives under `custom_components/user_briefing/providers/`.

- `contracts.py`
  - Base provider and adapter contracts.
- `registry.py`
  - Provider registration and instantiation.
- `base_stub.py`
  - Shared scaffold implementation for built-in stub providers.
- `calendar.py`
  - Calendar provider scaffold.
- `weather_forecast.py`
  - Weather provider scaffold.
- `beach_conditions.py`
  - Beach conditions provider scaffold.
- `wind_conditions.py`
  - Wind conditions provider scaffold.
- `compliment.py`
  - Compliment provider scaffold.
- `news_headlines.py`
  - News provider scaffold.
- `home_status.py`
  - Home-status provider scaffold.
- `task_summary.py`
  - Generic task-summary provider scaffold using existing Home Assistant task ecosystems.
- `mail_summary_stub.py`
  - Mail-summary interface scaffold for future adapters.
- `__init__.py`
  - Provider package marker.

## Adapters

Adapter code lives under `custom_components/user_briefing/adapters/`.

- `base.py`
  - Base stub adapter.
- `calendar.py`
  - Calendar adapter scaffold.
- `todo.py`
  - Task/todo adapter scaffold.
- `weather.py`
  - Weather adapter scaffold.
- `catalunya_beaches.py`
  - Catalunya Beaches adapter scaffold.
- `__init__.py`
  - Adapter package marker.

## Dashboard Templates

- `custom_components/user_briefing/dashboard_templates/default.yaml`
  - Default dashboard template placeholder.
- `custom_components/user_briefing/dashboard_templates/compact.yaml`
  - Compact dashboard template placeholder.

## Phrase Assets

- `custom_components/user_briefing/phrases/README.md`
  - Placeholder note for future phrase-bank assets.

## Tests

- `tests/test_config_flow.py`
  - Current structural flow smoke test.
- `tests/test_registry.py`
  - Provider registry smoke test.
- `tests/test_rendering.py`
  - Basic rendering smoke test.
- `tests/__init__.py`
  - Test package marker.

## Working Rules For Future Agents

1. Treat the spec files as the source of truth for architecture until implementation clearly supersedes them.
2. Keep the provider/plugin boundary clean: do not hardcode provider-specific logic into the coordinator, services, or dashboard assembly.
3. Keep alert handling consistent: providers detect and emit structured alerts, but the core owns alert ordering and promotion.
4. Preserve the Home Assistant UX direction:
   - selectors over raw text when possible
   - `data_description` for non-obvious fields
   - sections instead of advanced-mode gating
   - `OptionsFlow` using `self.config_entry`
   - subentry-based snippet setup
5. Do not turn notification logic into a full delivery system yet unless the task explicitly asks for that.
6. Reuse existing Home Assistant ecosystems for tasks and other data sources; do not rebuild upstream integrations inside this project.
7. Update `TODO.md` when significant implementation milestones are completed.

## What Is Still Stubbed

These areas are scaffolded but not fully implemented yet:

- real provider collection logic
- rich phrase-bank rendering
- full subentry-driven entity creation beyond the current scaffold
- dashboard fragment composition into finished user dashboards
- notification payload helpers and delivery routing
- complete Home Assistant behavior tests

If you are implementing one of these, update both the code and the relevant spec/docs so future agents do not inherit stale guidance.

## Ignore / Non-Source Files

If present, `.mypy_cache/` directories are tool artifacts and not part of the intended source of truth.