# Dashboards

Dashboards are intended to be assembled from:

- profile-level briefing entities
- snippet-level entities
- provider-declared dashboard fragments
- normalized `SnippetResult` / `AlertItem` output
- packaged YAML template examples

The current entity surface for dashboard use is:

- one profile briefing text sensor
- one profile briefing status sensor
- one profile last-generated timestamp sensor
- one snippet text sensor per configured snippet
- one snippet status sensor per configured snippet

Generated dashboard composition now adds:

- a top-of-dashboard `briefing_alerts` markdown section derived from normalized alerts
- a `briefing_overview` card for the profile-level entities
- provider fragment cards when a provider declares them
- a fallback snippet card when a provider does not declare dashboard fragments

The packaged templates under `custom_components/user_briefing/dashboard_templates/` now include end-to-end Alex examples for the default and compact layouts.