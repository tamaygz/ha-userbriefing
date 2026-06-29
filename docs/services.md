# Services

Planned public services:

- `user_briefing.generate`
- `user_briefing.preview`
- `user_briefing.deliver`
- `user_briefing.refresh_snippet`

Current scaffold behavior:

- `generate` requires `config_entry_id` and updates coordinator-backed entity state.
- `preview` requires `config_entry_id`, returns rendered preview data, and does not mutate entity state.
- `deliver` is still a stub for future delivery interfaces.
- `refresh_snippet` requires `config_entry_id` and `subentry_id`.

These services are still scaffold-level, but their targeting and preview semantics now reflect the intended architecture more closely.