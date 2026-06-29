# Dashboards

Dashboards are intended to be assembled from:

- profile-level briefing entities
- snippet-level entities
- provider-declared dashboard fragments
- packaged YAML template examples

The current entity surface for dashboard use is:

- one profile briefing text sensor
- one profile briefing status sensor
- one profile last-generated timestamp sensor
- one snippet text sensor per configured snippet
- one snippet status sensor per configured snippet

The scaffold includes placeholder dashboard templates under `custom_components/user_briefing/dashboard_templates/`.