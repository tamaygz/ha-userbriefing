# Contributing

## Current state

This repository is currently scaffold-first. Architecture, flow UX, contracts, and backlog tracking are in place, while many providers and runtime behaviors are still stubs.

## Before changing code

1. Read `AGENTS.md`.
2. Read the linked spec or plan files relevant to the area you are changing.
3. If you are working from a backlog item, update both `TODO.md` and the linked GitHub issue with meaningful progress.

## Validation

At minimum, run:

```powershell
pytest -q
```

As the integration grows, expand validation to include workflow checks, richer Home Assistant behavior tests, and release validation.

## HACS and Home Assistant metadata

This repository includes:

- HACS metadata in `hacs.json`
- Home Assistant manifest and flow translations in `custom_components/user_briefing/`
- HACS validation workflow
- `hassfest` validation workflow
- local custom integration brand assets

Keep these aligned as the repository evolves.