# Automation Push Provider — Custom Content Injection via Automations

## Goal

Allow end users to feed any custom content into their briefing using standard Home Assistant
automations or scripts, without writing code or building a bespoke integration adapter.
The feature should feel native: discoverable through the config flow, callable from the
actions developer tools, and wrappable in a bundled automation blueprint.

## Background

All built-in providers pull data — they own their adapter and collection logic. This covers
well-known sources (calendar, weather, tasks) but leaves a gap: users with custom sensors,
external API calls via `rest`, `scrape`, or `command_line`, or any other Home Assistant entity
or template value have no first-class way to include that data in their briefing today.

The "anything adapter" problem requires a push pattern rather than another pull adapter.

## Design Overview

Two complementary paths both support the push story.

### Path A — Push service + `custom_text` provider (primary)

The integration exposes a new service action `user_briefing.push_snippet`. An automation
fires it to write content into a named coordinator-managed slot. On the next `generate()`,
the `custom_text` provider reads the slot and renders a snippet.

```
Automation trigger (any)
  └─► user_briefing.push_snippet
        config_entry_id: <profile>
        subentry_id: <slot>
        text: "{{ states('sensor.my_thing') }}"
        title: "My custom note"
        expires_in_hours: 24
          └─► coordinator slot_store[subentry_id]
                └─► custom_text provider
                      └─► SnippetResult → briefing
```

### Path B — Entity-watching `custom_text` (secondary / power users)

The `custom_text` provider can also be configured in `entity` mode, pointing its
`source_ref` at any `input_text`, `template`, `sensor`, or `command_line` entity. The
provider reads via `HomeAssistantEntityAdapter`. Users manage entity state through their own
automations. No new service call is needed — the entity is the slot.

Path B reuses existing adapter primitives and requires no new service surface. It is simpler
but has no TTL expiry support and cannot carry severity metadata.

---

## `custom_text` Provider

### Provider metadata

| Field                      | Value                  |
|----------------------------|------------------------|
| `key`                      | `custom_text`          |
| `name`                     | Custom text            |
| `supports_multiple_instances` | `True`             |
| `supports_preview`         | `True`                 |
| `supports_alerts`          | `True`                 |
| `supports_required_priority` | `True`               |
| `default_order_group`      | `general`              |

### Config subentry setup (Path A — slot mode)

Setup step collects:

- `slot_label` (optional): human-readable label for the slot in the UI. Shown in the
  subentry list. Defaults to `"Custom text"`.
- `mode`: `"slot"` (push service) or `"entity"` (entity watcher). Selector `select`.

### Config subentry setup (Path B — entity mode)

Additional step shown only when `mode = "entity"`:

- `source_ref`: entity selector filtered to `input_text`, `sensor`, and `template` domains.

### Subentry options

Both modes:

- `enabled`: bool
- `order`: number
- `priority`: select (`normal`, `high`, `required`)
- `title_override`: optional text

Slot mode only:

- `default_text`: optional text shown when slot is empty (if blank, snippet is skipped).

### `async_collect()` behavior

**Slot mode**: reads `coordinator.slot_store[subentry_id]` and returns its `SlotEntry`
as the raw payload. If no entry exists or the slot is empty, returns `{"empty": True}`.

**Entity mode**: delegates to `HomeAssistantEntityAdapter` with `source_ref`. If entity
state is unavailable or blank, returns `{"empty": True}`.

### `normalize()` behavior

- If `payload.get("empty")` → return `SnippetResult` with `status="skipped"`.
- If `severity` is set on the slot entry → emit as `AlertItem` in addition to normal
  snippet text, following the existing alert contract.
- Otherwise → return normal `SnippetResult` with `text` from the payload.

---

## `SlotEntry` dataclass

Added to `models.py`:

```python
@dataclass(slots=True)
class SlotEntry:
    text: str
    title: str | None = None
    severity: str | None = None          # "info" | "warning" | "critical" | None
    pushed_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None   # None means no expiry
```

The coordinator holds `slot_store: dict[str, SlotEntry]` in memory (not persisted across
restarts; automations are responsible for re-pushing after HA restart if needed).

On each `async_generate()` the coordinator prunes expired entries before dispatching to
providers.

---

## Service actions

### `user_briefing.push_snippet`

Writes a `SlotEntry` into `coordinator.slot_store[subentry_id]`.

**Fields:**

| Field             | Required | Selector        | Notes                                                   |
|-------------------|----------|-----------------|---------------------------------------------------------|
| `config_entry_id` | yes      | `config_entry`  | Scoped to `integration: user_briefing`                  |
| `subentry_id`     | yes      | `text`          | Must reference a `custom_text` subentry in slot mode    |
| `text`            | yes      | `template`      | Supports HA template syntax                             |
| `title`           | no       | `text`          | Overrides the snippet title                             |
| `severity`        | no       | `select`        | `info`, `warning`, `critical` — promotes to alert block |
| `expires_in_hours`| no       | `number` (0–168) | 0 means no expiry. Defaults to 0 (no expiry).          |

**Validation:** the service handler must confirm the resolved `subentry_id` belongs to a
`custom_text` provider configured in `slot` mode. Raise `ServiceValidationError` otherwise.

### `user_briefing.clear_snippet`

Removes a `SlotEntry` from `coordinator.slot_store[subentry_id]`, effectively making the
slot empty until the next push.

**Fields:**

| Field             | Required | Selector        |
|-------------------|----------|-----------------|-
| `config_entry_id` | yes      | `config_entry`  |
| `subentry_id`     | yes      | `text`          |

---

## Bundled Automation Blueprints

Two blueprints ship in `blueprints/automation/user_briefing/`:

### `push_snippet.yaml` — Push a custom briefing snippet

```yaml
blueprint:
  name: "User Briefing: Push a custom snippet"
  description: >
    Push any text into a User Briefing custom slot when a trigger fires.
    Use this to inject any content into your briefing — sensor readings,
    package tracking, custom reminders, LLM-generated text, or anything else
    you can express as a Home Assistant template.
  domain: automation
  author: ha-userbriefing
  homeassistant:
    min_version: "2024.6.0"
  input:
    config_entry_section:
      name: Briefing profile
      input:
        config_entry_id:
          name: Profile
          description: The User Briefing profile to write into.
          selector:
            config_entry:
              integration: user_briefing
        subentry_id:
          name: Snippet slot
          description: >
            The ID of the custom_text snippet slot to write to.
            Copy this from the subentry list in the integration settings.
          selector:
            text:
    content_section:
      name: Content
      input:
        text:
          name: Snippet text
          description: Supports Home Assistant templates.
          selector:
            template:
        title:
          name: Title (optional)
          default: ""
          selector:
            text:
        severity:
          name: Severity
          description: >
            Set to warning or critical to promote this snippet to the
            alert block at the top of the briefing.
          default: ""
          selector:
            select:
              options:
                - label: Normal snippet
                  value: ""
                - label: Info
                  value: info
                - label: Warning
                  value: warning
                - label: Critical
                  value: critical
    expiry_section:
      name: Expiry
      collapsed: true
      input:
        expires_in_hours:
          name: Auto-clear after (hours)
          description: Set to 0 to keep the snippet until manually cleared.
          default: 0
          selector:
            number:
              min: 0
              max: 168
              step: 1
              unit_of_measurement: "h"

trigger: []

action:
  - action: user_briefing.push_snippet
    data:
      config_entry_id: !input config_entry_id
      subentry_id: !input subentry_id
      text: !input text
      title: !input title
      severity: !input severity
      expires_in_hours: !input expires_in_hours
```

### `clear_snippet.yaml` — Clear a custom briefing snippet

```yaml
blueprint:
  name: "User Briefing: Clear a custom snippet"
  description: >
    Remove the content from a User Briefing custom slot when a trigger fires.
    Useful for resetting stale content (e.g. clearing a package-tracking note
    once the parcel arrives).
  domain: automation
  author: ha-userbriefing
  homeassistant:
    min_version: "2024.6.0"
  input:
    config_entry_id:
      name: Profile
      selector:
        config_entry:
          integration: user_briefing
    subentry_id:
      name: Snippet slot
      selector:
        text:

trigger: []

action:
  - action: user_briefing.clear_snippet
    data:
      config_entry_id: !input config_entry_id
      subentry_id: !input subentry_id
```

---

## UI / Config Flow Integration

### Subentry config flow for `custom_text`

Step 1 — Mode selection:
- `slot_label` text input
- `mode` select: `"Push service (automation-driven)"` / `"Entity watcher"`

Step 2A (slot mode) — confirm and show the `subentry_id` to copy into the blueprint.

Step 2B (entity mode) — entity selector for `source_ref`.

The flow should surface the `subentry_id` value in step 2A because users need it to wire
the blueprint. Showing it in the UI at setup time prevents the need to dig into developer
tools.

---

## Out of Scope for this Issue

- Persistent slot storage across HA restarts (future: use `storage` helpers).
- Script blueprint variant (automation blueprint covers the primary use case).
- Slot push via event bus (deferred; service action is the idiomatic HA pattern).
- Multi-slot batch push in a single service call.

---

## Relationship to Existing Architecture

- `custom_text` is a new provider registered in `providers/registry.py`.
- Slot store lives in the coordinator, scoped per config entry.
- Push/clear service handlers follow the existing `_resolve_coordinator` pattern in
  `services.py`.
- `SlotEntry` is a new model in `models.py` alongside `SnippetResult` and `AlertItem`.
- The `custom_text` provider follows the `BriefingProvider` contract without needing a
  new adapter (slot mode) or with `HomeAssistantEntityAdapter` reuse (entity mode).
- Blueprints are stored under `blueprints/automation/user_briefing/` which HA discovers
  automatically from within a custom integration directory.
