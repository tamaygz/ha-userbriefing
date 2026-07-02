"""Unit tests for subentry compatibility helpers."""

from __future__ import annotations

from types import MappingProxyType, SimpleNamespace

import pytest

from custom_components.user_briefing.subentries import (
    get_config_subentry_data,
    get_config_subentry_options,
    iter_config_subentries,
)


def _sub(data: object, options: object) -> SimpleNamespace:
    return SimpleNamespace(data=data, options=options)


class TestGetConfigSubentryOptions:
    def test_returns_options_when_key_present(self) -> None:
        sub = _sub(data={"enabled": False}, options={"enabled": True})
        assert get_config_subentry_options(sub, ["enabled"])["enabled"] is True

    def test_falls_back_to_data_when_key_absent_from_options(self) -> None:
        sub = _sub(data={"enabled": True, "source_ref": "x"}, options={})
        result = get_config_subentry_options(sub, ["enabled"])
        assert result["enabled"] is True

    def test_options_win_over_data_for_same_key(self) -> None:
        sub = _sub(data={"enabled": False}, options={"enabled": True})
        result = get_config_subentry_options(sub, ["enabled"])
        assert result["enabled"] is True

    def test_non_fallback_key_not_included_in_result(self) -> None:
        sub = _sub(data={"source_ref": "x"}, options={})
        result = get_config_subentry_options(sub, ["enabled"])
        assert "source_ref" not in result

    def test_handles_none_data(self) -> None:
        sub = _sub(data=None, options={})
        assert get_config_subentry_options(sub, ["enabled"]) == {}

    def test_handles_none_options_falls_back_to_data(self) -> None:
        sub = _sub(data={"enabled": True}, options=None)
        result = get_config_subentry_options(sub, ["enabled"])
        assert result["enabled"] is True

    def test_handles_both_none(self) -> None:
        sub = _sub(data=None, options=None)
        assert get_config_subentry_options(sub, ["enabled"]) == {}

    def test_no_fallback_keys_returns_options_copy(self) -> None:
        sub = _sub(data={"x": 1}, options={"y": 2})
        result = get_config_subentry_options(sub)
        assert result == {"y": 2}

    def test_all_four_common_keys_fall_back_when_stored_in_data(self) -> None:
        """Core compatibility scenario: settings stored in data on old HA."""
        sub = _sub(
            data={
                "provider_key": "calendar",
                "enabled": True,
                "order": 5,
                "priority": "required",
                "title_override": "My Cal",
            },
            options={},
        )
        result = get_config_subentry_options(
            sub, ["enabled", "order", "priority", "title_override"]
        )
        assert result["enabled"] is True
        assert result["order"] == 5
        assert result["priority"] == "required"
        assert result["title_override"] == "My Cal"


class TestGetConfigSubentryData:
    def test_strips_option_keys(self) -> None:
        sub = _sub(
            data={"provider_key": "calendar", "enabled": True, "order": 5},
            options={},
        )
        result = get_config_subentry_data(sub, ["enabled", "order"])
        assert "enabled" not in result
        assert "order" not in result
        assert result["provider_key"] == "calendar"

    def test_keys_not_in_data_are_silently_ignored(self) -> None:
        sub = _sub(data={"provider_key": "calendar"}, options={})
        result = get_config_subentry_data(sub, ["enabled"])
        assert result == {"provider_key": "calendar"}

    def test_no_option_keys_returns_full_data_copy(self) -> None:
        sub = _sub(data={"a": 1, "b": 2}, options={})
        assert get_config_subentry_data(sub) == {"a": 1, "b": 2}

    def test_handles_none_data(self) -> None:
        sub = _sub(data=None, options={})
        assert get_config_subentry_data(sub, ["enabled"]) == {}

    def test_returns_copy_not_original(self) -> None:
        original = {"provider_key": "calendar"}
        sub = _sub(data=original, options={})
        result = get_config_subentry_data(sub)
        result["provider_key"] = "mutated"
        assert original["provider_key"] == "calendar"

    def test_provider_key_preserved_after_stripping_common_keys(self) -> None:
        """Core compatibility scenario: mixed data from fallback storage path."""
        sub = _sub(
            data={
                "provider_key": "calendar",
                "source_ref": "calendar.work",
                "enabled": True,
                "order": 10,
                "priority": "optional",
                "title_override": None,
            },
            options={},
        )
        result = get_config_subentry_data(
            sub, ["enabled", "order", "priority", "title_override"]
        )
        assert result == {"provider_key": "calendar", "source_ref": "calendar.work"}


class TestIterConfigSubentries:
    """Tests for the iter_config_subentries helper."""

    def _subentry(self, subentry_id: str, subentry_type: str = "snippet") -> SimpleNamespace:
        return SimpleNamespace(
            subentry_id=subentry_id,
            subentry_type=subentry_type,
            data={"provider_key": "compliment"},
            options={"enabled": True},
        )

    def test_plain_dict_id_keyed_yields_values(self) -> None:
        """Regular dict with id-keyed subentry objects is the basic happy path."""
        sub = self._subentry("s1")
        entry = SimpleNamespace(subentries={"s1": sub})
        assert list(iter_config_subentries(entry, "snippet")) == [sub]

    def test_mapping_proxy_type_id_keyed_yields_values(self) -> None:
        """MappingProxyType is what HA uses in production; must not iterate over keys."""
        sub = self._subentry("s1")
        entry = SimpleNamespace(subentries=MappingProxyType({"s1": sub}))
        result = list(iter_config_subentries(entry, "snippet"))
        assert result == [sub], (
            "iter_config_subentries iterated over keys instead of values; "
            "MappingProxyType must be handled the same as dict"
        )

    def test_mapping_proxy_type_filters_by_subentry_type(self) -> None:
        """Type filter is applied correctly when subentries is a MappingProxyType."""
        snippet_sub = self._subentry("s1", subentry_type="snippet")
        other_sub = self._subentry("s2", subentry_type="other")
        entry = SimpleNamespace(
            subentries=MappingProxyType({"s1": snippet_sub, "s2": other_sub})
        )
        assert list(iter_config_subentries(entry, "snippet")) == [snippet_sub]

    def test_mapping_proxy_type_no_filter_yields_all(self) -> None:
        """Passing subentry_type=None with a MappingProxyType yields all subentries."""
        sub1 = self._subentry("s1")
        sub2 = self._subentry("s2", subentry_type="other")
        entry = SimpleNamespace(subentries=MappingProxyType({"s1": sub1, "s2": sub2}))
        result = list(iter_config_subentries(entry, None))
        assert len(result) == 2
        assert sub1 in result
        assert sub2 in result

    def test_empty_mapping_proxy_yields_nothing(self) -> None:
        entry = SimpleNamespace(subentries=MappingProxyType({}))
        assert list(iter_config_subentries(entry, "snippet")) == []

    def test_missing_subentries_attribute_yields_nothing(self) -> None:
        entry = SimpleNamespace()
        assert list(iter_config_subentries(entry, "snippet")) == []
