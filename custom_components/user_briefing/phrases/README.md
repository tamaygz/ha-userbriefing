# Phrase assets

This folder holds per-provider phrase banks used by the rendering layer.

## Format

Each file is named `{provider_key}.yaml` and contains a `scenarios` mapping from
scenario key to a list of phrase templates:

```yaml
scenarios:
  some_scenario:
    - "Template one with {variable}."
    - "Template two with {variable}."
  empty:
    - "Nothing here."
    - "All clear."
```

Templates are interpolated with `str.format_map` using the snippet's `data` dict, so
providers must populate their `data` dict with any variables the templates reference.
If interpolation fails the renderer falls back gracefully to the pre-computed
`snippet.text`.

## Scenario selection

The renderer picks a template deterministically using an MD5 hash of
`"{instance_id}:{scenario}"` modulo the number of available templates.  The same
snippet instance always receives the same wording, but different instances rotate
through the available options, giving variety across a multi-snippet briefing.

## Covered providers

| File | Scenarios |
|------|-----------|
| `calendar.yaml` | `upcoming_events`, `empty`, `error` |
| `weather_forecast.yaml` | `forecast_ready`, `empty`, `error` |
| `task_summary.yaml` | `tasks_ready`, `empty`, `error` |
| `compliment.yaml` | `compliment` |

Providers that do not yet have a phrase bank file fall back to their inline
`snippet.text` unchanged.

## Adding a new phrase bank

1. Create `{provider_key}.yaml` in this folder using the format above.
2. Ensure the provider populates `snippet.data` with all variables the templates
   reference (add or update `build_phrase_context()` or the `normalize()` return
   value as needed).
3. Add scenario rendering tests in `tests/test_rendering.py` following the existing
   parametrized pattern.
