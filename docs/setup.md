# Setup

## Fastest Home Assistant test path

Use the My Home Assistant HACS repository link from the README to open this repository directly in HACS.

Recommended flow:

1. Open the repository in HACS.
2. Add it as a custom repository if prompted.
3. Download the integration.
4. Restart Home Assistant.
5. Go to Integrations and add `User Briefing`.

## Planned setup experience

1. Add the integration from HACS.
2. Create one user profile via the main config flow.
3. Immediately continue into the first snippet subentry flow.
4. Add additional snippet providers as needed.
5. Assemble a dashboard from the exposed entities and dashboard templates.

## Current state

This repository contains the scaffold and specification for that setup flow. Provider implementations are intentionally stubbed at this stage.

That means the main thing you can validate in Home Assistant right now is:

- HACS install path
- integration discovery and add flow
- config flow and subentry onboarding skeleton