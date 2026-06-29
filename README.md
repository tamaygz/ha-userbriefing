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

The current state is an architecture-first scaffold, not a finished production integration.

## Quick Test In Home Assistant

This repository is set up for the fastest current real-world test path through HACS.

1. Click the `Open in HACS` badge above.
2. Add the repository as a custom integration repository if Home Assistant prompts for it.
3. Download the integration from HACS.
4. Restart Home Assistant.
5. Click the `Open Integrations` badge above.
6. Add `User Briefing` from the Integrations page.

Current limitation:

- this repository is scaffold-first, so installation and setup can be tested in Home Assistant now, but most providers and runtime behavior are still stubs.

## Design goals

- Great setup UX using current Home Assistant config-flow, options-flow, and subentry-flow patterns
- Easy addition or replacement of content providers without core rewrites
- Dashboard-first entity exposure, with notification hooks stubbed for later
- Clean reuse of existing Home Assistant ecosystems, such as task integrations, instead of reimplementing them

## Repository layout

- `custom_components/user_briefing/` integration scaffold
- `docs/` implementation-facing guidance
- `specs/` architectural and UX design
- `plan/` execution plan
- `research/` decision and research notes

## Status

Scaffolded areas:

- integration manifest and HACS metadata
- My Home Assistant and HACS testing shortcuts
- config flow, options flow, reconfigure flow, and subentry flow skeletons
- provider contracts and registry
- adapter stubs
- rendering and coordinator skeletons
- dashboard template placeholders
- service definitions
- initial tests and docs

## Next implementation layers

1. Wire real provider collection and normalization.
2. Wire subentry-backed runtime storage and entity creation.
3. Implement dashboard fragment composition.
4. Add focused provider implementations one by one.