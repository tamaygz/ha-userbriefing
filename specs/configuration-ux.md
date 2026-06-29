# Configuration UX Strategy

## Goal

User Briefing should feel native in Home Assistant setup. The configuration UX should use modern config-flow, options-flow, and subentry-flow capabilities so users can onboard a briefing profile and add content modules with minimal friction.

## Current Home Assistant guidance applied

This strategy incorporates current developer guidance from the Home Assistant config flow, options flow, data entry flow, and quality-scale docs, including:

- use selectors and translated field descriptions
- store immutable setup in `ConfigEntry.data` and mutable settings in `ConfigEntry.options`
- use `async_on_create_entry()` when chaining into subentry setup
- use current `OptionsFlow` access via `self.config_entry`
- avoid `OptionsFlowWithConfigEntry` in new code
- avoid advanced-mode gating and instead use sections or separate steps
- support reconfigure flows for non-optional setup mutations
- support subentry reconfigure flows using current `ConfigSubentryFlow` APIs

## Main config flow

### Step 1: Profile basics

Collect:

- user display name
- user key or slug
- language or locale

UX notes:

- use sections if optional localization or presentation fields are grouped
- use `data_description` for identity fields so users understand naming implications

### Step 2: Delivery and dashboard defaults

Collect:

- preferred dashboard path or template
- preferred delivery target references
- optional compact vs expanded default mode

UX notes:

- use selectors where Home Assistant entities or dashboard identifiers can be constrained
- show advanced presentation options inside collapsible sections, not behind advanced mode checks

### Step 3: Create entry and continue

After creating the config entry, automatically start the first snippet subentry flow via `async_on_create_entry()` so the user lands directly in the "add first content block" path.

## Subentry flow strategy

### Entry step

Use `async_show_menu()` or a selector-driven first step to let the user choose the snippet type.

The choice list should come from the provider registry so the UI stays aligned with available providers.

### Provider-specific step

The selected provider contributes:

- its config schema
- its field descriptions
- recommended defaults
- any section grouping

### Common snippet settings step

Collect:

- enabled
- display order
- priority
- optional title override

This shared step keeps the provider-specific step focused on source configuration.

## Options flow strategy

Use options flows for mutable profile-level behavior only.

Examples:

- default output style
- default dashboard template selection
- global rendering preferences

Implementation guidance:

- use `OptionsFlow` or `OptionsFlowWithReload` as appropriate
- rely on `self.config_entry`
- use `add_suggested_values_to_schema()` for pre-filled edits
- use read-only selectors for values users should see but not mutate in options

## Reconfigure strategy

Use a reconfigure step for identity-level changes that are not mere preferences.

Examples:

- changing a stable user key if supported
- migrating a dashboard binding model

Reconfigure must update the existing entry rather than create a new one.

## Subentry reconfigure strategy

Each provider type should support subentry reconfiguration where meaningful.

Examples:

- switch a calendar source
- change a beach location
- change a task list entity

Target the current `ConfigSubentryFlow` API shape, including parent entry access via the renamed helper methods introduced in 2025.

## Long-running and progressive UX

If any provider setup needs long-running work, use `async_show_progress()` and `async_show_progress_done()` instead of leaving the user on a stale form.

Potential use cases:

- discovering a large external source list
- validating a remote account-backed adapter later

## Translation strategy

Provide high-quality translations for:

- config steps
- option steps
- config subentry steps
- menu options
- section titles and descriptions
- validation and abort reasons

The spec should explicitly use `data_description` for any field where the expected value is not obvious.

## UX anti-patterns to avoid

- no advanced-mode gating for optional fields
- no raw text input when a selector is more appropriate
- no mixing mutable preferences into `ConfigEntry.data`
- no hardcoded snippet types in flow code outside the registry
- no giant one-page options form when subentries model the problem better