# User Briefing Work Todo

- [x] Update specs with latest Home Assistant config flow, options flow, subentry flow, and data-entry-flow UX guidance.
- [x] Add a dedicated configuration UX spec covering setup flow, options flow, subentry flow, reconfigure flow, and dashboard-related setup.
- [x] Add a concrete data-model and service-schema spec for providers, adapters, briefing results, and dashboard fragments.
- [x] Scaffold the integration repository structure for `user_briefing`.
- [x] Scaffold manifest, HACS metadata, README, constants, and integration bootstrap.
- [x] Scaffold config flow, options flow, subentry flow, and translation placeholders using current Home Assistant patterns.
- [x] Scaffold provider contracts, registry, built-in provider stubs, adapter stubs, renderer, and coordinator.
- [x] Scaffold dashboard template placeholders and docs.
- [x] Scaffold service definitions and service-schema placeholders.
- [x] Scaffold tests for config flow, registry, rendering, and provider contract basics.
- [x] Run focused validation on the scaffold structure and capture any follow-up gaps.
- [x] Update todo status and summarize completed work.

## Follow-up Work

- [ ] [Implement dynamic snippet entity lifecycle so add, update, and remove of subentries are reflected without relying on manual reload assumptions.](https://github.com/tamaygz/ha-userbriefing/issues/14)
- [ ] [Replace scaffold providers with real provider implementations one by one, starting with calendar, weather, task-summary, and compliment.](https://github.com/tamaygz/ha-userbriefing/issues/15)
- [ ] [Replace generic provider stub schemas with provider-specific setup and reconfigure selectors wherever Home Assistant offers stronger UX primitives.](https://github.com/tamaygz/ha-userbriefing/issues/16)
- [ ] [Implement structured alert support so providers can emit alerts separately from normal snippet text.](https://github.com/tamaygz/ha-userbriefing/issues/17)
- [ ] [Implement core composer logic that sorts promoted alerts to the top of the briefing before standard snippet content.](https://github.com/tamaygz/ha-userbriefing/issues/18)
- [ ] [Implement dashboard fragment composition into richer generated templates and expose at least one end-to-end per-user dashboard example.](https://github.com/tamaygz/ha-userbriefing/issues/19)
- [ ] [Implement notification payload helpers without enabling full delivery workflows yet.](https://github.com/tamaygz/ha-userbriefing/issues/20)
- [ ] [Add dedicated generated-at and per-snippet status entities, or explicitly revise the architecture/docs if attributes remain the long-term model.](https://github.com/tamaygz/ha-userbriefing/issues/21)
- [ ] [Expand service behavior tests to cover `generate`, `preview` response payloads, `refresh_snippet`, required target semantics, and unknown `config_entry_id` handling.](https://github.com/tamaygz/ha-userbriefing/issues/22)
- [ ] [Add flow behavior tests for post-create subentry chaining, duplicate-source prevention, singleton providers, and provider-driven reconfigure.](https://github.com/tamaygz/ha-userbriefing/issues/23)
- [ ] [Add coordinator tests for respecting `enabled`, `order`, `priority`, partial provider failure, and preview non-mutation.](https://github.com/tamaygz/ha-userbriefing/issues/24)
- [ ] [Add coordinator and rendering tests for alert severity ordering and alert promotion above normal content.](https://github.com/tamaygz/ha-userbriefing/issues/25)
- [ ] [Replace placeholder phrase assets with real per-provider scenario banks and add rendering tests for scenario selection.](https://github.com/tamaygz/ha-userbriefing/issues/26)