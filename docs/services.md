# Services

Planned public services:

- `user_briefing.generate`
- `user_briefing.preview`
- `user_briefing.deliver`
- `user_briefing.refresh_snippet`

Current scaffold behavior:

- `generate` requires `config_entry_id` and updates coordinator-backed entity state.
- `preview` requires `config_entry_id`, returns rendered preview data, and does not mutate entity state.
- `deliver` requires `config_entry_id`, reads the last cached briefing (or generates a preview if none exists), and logs the notification payload. Actual push delivery is stubbed pending a configured target channel.
- `refresh_snippet` requires `config_entry_id` and `subentry_id`.

## Notification payload

`BriefingResult.delivery_payloads["notification"]` is populated by
`notification.build_notification_payload()` every time a briefing is generated
or previewed. The payload mirrors the field shape accepted by Home Assistant's
`notify` service so it can be forwarded directly once a delivery target is known.

Key payload fields:

- `title` — human-readable notification title derived from the config entry name
- `message` — rendered briefing text, truncated to 1 000 characters if needed
- `target` — `None`; a delivery target must be set by the caller
- `data.tag` — stable dedup and grouping key (`user_briefing_<user_key>`)
- `data.channel` — Android notification channel (`"user_briefing"`)
- `data.importance` — `"high"` when active alerts have `warning` or `critical` severity; `"default"` otherwise
- `data.push.thread-id` — iOS thread grouping key
- `data.badge` — count of active alerts
- `data.actions` — stub list (up to three) of future actionable notification buttons derived from snippet `SnippetAction` metadata

These services are still scaffold-level, but their targeting and preview semantics now reflect the intended architecture more closely.