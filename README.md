# User Briefing

Home Assistant custom integration scaffold for modular, per-user daily briefings.

[![Open your Home Assistant instance and show this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tamaygz&repository=ha-userbriefing&category=integration)
[![Open your Home Assistant instance and show your integrations.](https://my.home-assistant.io/badges/integrations.svg)](https://my.home-assistant.io/redirect/integrations/)

For future agent or contributor onboarding, start with `AGENTS.md`.

This repository is intentionally scaffolded around:

- one config entry per user
- one configurable snippet subentry per briefing purpose
- a registry-based provider plugin architecture
- adapter-based source integration
- phrase-driven rendering
- dashboard assembly from provider-exposed entities and card fragments

The current state is an actively developed integration. Core features are working; a subset of provider types and the deliver-routing path are still under development.

## Quick Test In Home Assistant

This repository is set up for the fastest current real-world test path through HACS.

1. Click the `Open in HACS` badge above.
2. Add the repository as a custom integration repository if Home Assistant prompts for it.
3. Download the integration from HACS.
4. Restart Home Assistant.
5. Click the `Open Integrations` badge above.
6. Add `User Briefing` from the Integrations page.

Current limitation:

- installation, setup, snippet onboarding, and briefing generation all work end-to-end; the `deliver` action is prepared but does not yet route to a real notification or TTS target.

## Design goals

- Great setup UX using current Home Assistant config-flow, options-flow, and subentry-flow patterns
- Easy addition or replacement of content providers without core rewrites
- Dashboard-first entity exposure, with notification hooks stubbed for later
- Clean reuse of existing Home Assistant ecosystems, such as task integrations, instead of reimplementing them

## Repository layout

- `custom_components/user_briefing/` integration source
- `blueprints/` bundled automation blueprints for push_snippet / clear_snippet
- `docs/` implementation-facing guidance
- `specs/` architectural and UX design
- `plan/` execution plan
- `research/` decision and research notes

## Status

Implemented and tested:

- integration manifest and HACS metadata
- config flow, options flow, reconfigure flow, and subentry flow
- provider contracts, registry, and plugin architecture
- real provider implementations: calendar, weather, task-summary, compliment, custom_text
- adapter primitives for HA entity and service data
- phrase-bank rendering with per-scenario variation
- alert emission, severity ordering, and alert promotion above snippet text
- dynamic snippet entity lifecycle (add/update/remove without reload)
- dashboard fragment composition and per-user dashboard template generation
- notification payload helpers
- `push_snippet` / `clear_snippet` services with slot store and TTL expiry
- bundled automation blueprints for push/clear workflows
- comprehensive automated tests (167 passing)

Still under development:

- stub providers: `home_status`, `news_headlines`, `beach_conditions`, `wind_conditions`
- `deliver` action routing to a real notification or TTS target
- mail-summary provider (planned post-v1)