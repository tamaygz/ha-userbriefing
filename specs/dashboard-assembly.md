# Dashboard Assembly Strategy

## Goal

Per-user dashboards should be easy to assemble from the entities and metadata exposed by User Briefing providers. The integration should not require users to handcraft every view from scratch when a provider already knows how its data is best presented.

## Principles

- Providers expose entities first.
- Dashboard fragments are optional but standardized.
- The integration ships examples and reusable templates where the UI pattern is stable.
- User-specific dashboards are compositions of provider fragments, not bespoke monoliths.
- Alerts should have a clear top-of-dashboard treatment when providers emit them.

## Fragment model

Each provider may declare one or more dashboard fragments.

Suggested fragment data:

- fragment key
- title
- description
- entity ids or entity roles required
- recommended card type
- optional badges or chips
- optional navigation path
- size or layout hint

## Built-in fragment examples

- `briefing_overview`
  - final briefing text entity
  - last generated timestamp
  - overall status
- `briefing_alerts`
  - promoted alert entities, badges, or markdown block shown above the standard briefing content
- `calendar_summary`
  - next event summary
  - count or agenda sensor
- `beach_conditions`
  - condition summary
  - wind or warning sensors
  - optional deep link to the related beach device or dashboard
- `task_summary`
  - incomplete count
  - top urgent tasks
  - navigation to Home Assistant task dashboard if supported

## Delivery relationship

Dashboard assembly is separate from notification delivery.

Rules:

- briefing generation updates entities
- dashboard cards read those entities
- notification interfaces may optionally link into the dashboard later
- alert fragments should render ahead of standard informational fragments when present

## Template strategy

Suggested packaged assets:

- per-provider YAML card fragments
- one sample full-user dashboard template using built-in providers
- optional compact and expanded variants

These templates should be examples and accelerators, not hard dependencies for runtime behavior.

## Compatibility expectations

- if a provider does not implement dashboard fragments, its entities must still be enough for manual dashboard use
- fragment contracts should be versioned with provider API changes
- template examples should be validated against actual entity names or roles during testing