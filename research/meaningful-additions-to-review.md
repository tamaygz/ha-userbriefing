# Meaningful Additions To Review With The User

These additions are grounded in Home Assistant docs and are intentionally separated from the core v1 architecture so they can be accepted or deferred explicitly.

## Candidate A: Actionable mobile notifications

Why it matters:

- Home Assistant Companion supports notification action buttons that send events back to Home Assistant.
- This fits a daily briefing well because the briefing can become interactive instead of passive.

Good briefing-specific actions:

- open the dedicated briefing dashboard
- regenerate briefing
- snooze this user's briefing
- mark a to-do item done
- open the related calendar or beach snippet view

Decision note:

- Accepted only as a future-facing interface contract for v1.
- Android and iOS support differs, so the integration should provide payload helpers later while Home Assistant automations handle final action logic.

Reference:

- `https://companion.home-assistant.io/docs/notifications/actionable-notifications/`

## Candidate B: Generic task-summary interface over existing Home Assistant task ecosystems

Why it matters:

- Home Assistant already integrates multiple task ecosystems such as Todoist and Microsoft To Do.
- The briefing integration should consume those through Home Assistant entities or actions instead of recreating provider-specific task logic.

Suggested v1 behavior:

- summarize incomplete count
- optionally list top N urgent or due tasks
- optionally provide an action to open the to-do dashboard
- allow swapping the underlying task adapter without changing the user-facing snippet type

Reference:

- `https://www.home-assistant.io/integrations/todo/`

## Candidate C: Assist or voice entry point for briefing playback

Why it matters:

- Home Assistant allows scripts to be exposed to LLM-based conversation agents as callable tools.
- Even though v1 is rule-based, a voice path is useful for on-demand access: "give me my briefing".

Suggested scope:

- do not make voice primary in v1
- provide one script-friendly service contract so a later exposed script can call it cleanly

Reference:

- `https://www.home-assistant.io/voice_control/exposing_scripts_to_llms/`

## Candidate D: Deep-link aware dashboard navigation and reusable dashboard card assembly

Why it matters:

- Mobile notification actions can open specific Lovelace dashboards or views directly.
- This pairs well with a per-user briefing dashboard.
- Provider-exposed entities can also be composed into reusable per-user dashboards from common card fragments.

Suggested use:

- every user profile can store a preferred dashboard path
- notification buttons can jump directly into that dashboard view
- providers can declare recommended cards or fragments for dashboard assembly

Reference:

- `https://companion.home-assistant.io/docs/notifications/actionable-notifications/`

## Recommendation

Recommended to include in the next design revision:

- Include Candidate B in v1.
- Keep Candidate A in the architecture now as a stubbed future interface only.
- Keep Candidate C as a v1.1 design target unless voice is a near-term priority.
- Include Candidate D in the core architecture so dashboards can be assembled from provider entities and reusable card templates.