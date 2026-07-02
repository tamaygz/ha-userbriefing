"""Structural validation tests for bundled YAML assets.

Covers blueprint files under blueprints/automation/user_briefing/ and
dashboard template examples under
custom_components/user_briefing/dashboard_templates/.

These tests parse each YAML file and assert the presence of key structural
fields so that accidental corruption is caught early without requiring a live
Home Assistant instance.
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest


# ---------------------------------------------------------------------------
# YAML loading helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent


def _make_ha_loader() -> type:
    """Return a YAML Loader subclass that silently handles HA-specific custom tags.

    Home Assistant blueprint YAML files use ``!input`` and other custom tags
    that the standard SafeLoader does not recognise.  Instead of failing, we
    treat any unknown tag as an ordinary string scalar so structural tests can
    still inspect the surrounding document keys.
    """

    class _HALoader(yaml.SafeLoader):
        pass

    # Register a catch-all multi-constructor for any unrecognised tag.
    # The node is returned as a plain Python string (its value or tag name).
    def _ignore_unknown(loader: yaml.Loader, tag_suffix: str, node: yaml.Node) -> object:
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        return loader.construct_mapping(node)

    _HALoader.add_multi_constructor("", _ignore_unknown)
    return _HALoader


def _load_yaml(path: Path) -> object:
    """Load and return the parsed YAML at *path*, tolerating HA custom tags."""
    with path.open(encoding="utf-8") as fh:
        return yaml.load(fh, Loader=_make_ha_loader())  # noqa: S506 — custom loader, not bare load


# ---------------------------------------------------------------------------
# Blueprint files
# ---------------------------------------------------------------------------


_BLUEPRINT_DIR = _REPO_ROOT / "blueprints" / "automation" / "user_briefing"

_BLUEPRINT_FILES = sorted(_BLUEPRINT_DIR.glob("*.yaml"))


@pytest.mark.parametrize("blueprint_path", _BLUEPRINT_FILES, ids=lambda p: p.name)
def test_blueprint_is_valid_yaml(blueprint_path: Path) -> None:
    """Each blueprint file must parse as valid YAML without errors."""
    doc = _load_yaml(blueprint_path)
    assert doc is not None, f"{blueprint_path.name} must not be empty"


@pytest.mark.parametrize("blueprint_path", _BLUEPRINT_FILES, ids=lambda p: p.name)
def test_blueprint_has_required_top_level_keys(blueprint_path: Path) -> None:
    """Each blueprint must have 'blueprint' and 'action' top-level keys."""
    doc = _load_yaml(blueprint_path)
    assert isinstance(doc, dict), f"{blueprint_path.name} must be a YAML mapping"
    assert "blueprint" in doc, f"{blueprint_path.name} missing 'blueprint' key"
    assert "action" in doc, f"{blueprint_path.name} missing 'action' key"


@pytest.mark.parametrize("blueprint_path", _BLUEPRINT_FILES, ids=lambda p: p.name)
def test_blueprint_metadata_fields(blueprint_path: Path) -> None:
    """Blueprint metadata must include name, description, domain, and min HA version."""
    doc = _load_yaml(blueprint_path)
    meta = doc["blueprint"]
    assert isinstance(meta, dict)
    assert "name" in meta, f"{blueprint_path.name}: blueprint.name is required"
    assert "description" in meta, f"{blueprint_path.name}: blueprint.description is required"
    assert "domain" in meta, f"{blueprint_path.name}: blueprint.domain is required"
    assert meta["domain"] == "automation", (
        f"{blueprint_path.name}: blueprint.domain must be 'automation'"
    )
    assert "homeassistant" in meta, f"{blueprint_path.name}: blueprint.homeassistant is required"
    assert "min_version" in meta["homeassistant"], (
        f"{blueprint_path.name}: blueprint.homeassistant.min_version is required"
    )


def test_push_snippet_blueprint_has_config_entry_and_subentry_inputs() -> None:
    """push_snippet blueprint must expose config_entry_id and subentry_id inputs."""
    path = _BLUEPRINT_DIR / "push_snippet.yaml"
    assert path.exists(), "push_snippet.yaml must exist"
    doc = _load_yaml(path)

    # Inputs can be nested inside sections; flatten them for inspection.
    raw_inputs: dict = doc.get("blueprint", {}).get("input", {})
    all_input_keys: set[str] = set()
    for key, value in raw_inputs.items():
        if isinstance(value, dict) and "input" in value:
            all_input_keys.update(value["input"].keys())
        else:
            all_input_keys.add(key)

    assert "config_entry_id" in all_input_keys, (
        "push_snippet blueprint must have a config_entry_id input"
    )
    assert "subentry_id" in all_input_keys, (
        "push_snippet blueprint must have a subentry_id input"
    )
    assert "text" in all_input_keys, (
        "push_snippet blueprint must have a text input"
    )


def test_clear_snippet_blueprint_has_config_entry_and_subentry_inputs() -> None:
    """clear_snippet blueprint must expose config_entry_id and subentry_id inputs."""
    path = _BLUEPRINT_DIR / "clear_snippet.yaml"
    assert path.exists(), "clear_snippet.yaml must exist"
    doc = _load_yaml(path)

    raw_inputs: dict = doc.get("blueprint", {}).get("input", {})
    all_input_keys: set[str] = set()
    for key, value in raw_inputs.items():
        if isinstance(value, dict) and "input" in value:
            all_input_keys.update(value["input"].keys())
        else:
            all_input_keys.add(key)

    assert "config_entry_id" in all_input_keys
    assert "subentry_id" in all_input_keys


# ---------------------------------------------------------------------------
# Dashboard template examples
# ---------------------------------------------------------------------------


_TEMPLATE_DIR = _REPO_ROOT / "custom_components" / "user_briefing" / "dashboard_templates"

_TEMPLATE_FILES = sorted(_TEMPLATE_DIR.glob("*.yaml"))


@pytest.mark.parametrize("template_path", _TEMPLATE_FILES, ids=lambda p: p.name)
def test_dashboard_template_is_valid_yaml(template_path: Path) -> None:
    """Each dashboard template must parse as valid YAML without errors."""
    doc = _load_yaml(template_path)
    assert doc is not None, f"{template_path.name} must not be empty"


@pytest.mark.parametrize("template_path", _TEMPLATE_FILES, ids=lambda p: p.name)
def test_dashboard_template_has_title_and_views(template_path: Path) -> None:
    """Dashboard templates must have 'title' and 'views' keys at the top level."""
    doc = _load_yaml(template_path)
    assert isinstance(doc, dict), f"{template_path.name} must be a mapping"
    assert "title" in doc, f"{template_path.name} missing 'title'"
    assert "views" in doc, f"{template_path.name} missing 'views'"
    assert isinstance(doc["views"], list), f"{template_path.name}: 'views' must be a list"
    assert len(doc["views"]) > 0, f"{template_path.name}: 'views' must not be empty"


def test_default_template_contains_briefing_cards() -> None:
    """The default template must contain at least overview and one snippet card."""
    path = _TEMPLATE_DIR / "default.yaml"
    assert path.exists(), "default.yaml must exist"
    doc = _load_yaml(path)

    cards = doc["views"][0]["cards"]
    card_titles = [c.get("title", "") for c in cards if isinstance(c, dict)]
    # Expect an alerts card and an overview card among the generated cards.
    assert any("Alert" in t or "alert" in t for t in card_titles), (
        "default.yaml must include an alerts card"
    )
    assert any("Overview" in t or "Briefing" in t for t in card_titles), (
        "default.yaml must include an overview/briefing card"
    )

