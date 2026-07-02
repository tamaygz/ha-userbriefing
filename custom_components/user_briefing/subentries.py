"""Helpers for working with config subentries."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def iter_config_subentries(config_entry: Any, subentry_type: str | None = None) -> Iterable[Any]:
    """Iterate config subentries defensively across possible runtime shapes.

    In production Home Assistant, ``config_entry.subentries`` is stored as a
    ``MappingProxyType[str, ConfigSubentry]``.  ``MappingProxyType`` is *not* a
    subclass of ``dict``, so the original ``isinstance(subentries, dict)`` check
    would fall through to the bare iteration path which iterates over the mapping
    *keys* (string subentry IDs) rather than the subentry objects — yielding nothing
    and causing the briefing to always appear empty.  Using ``Mapping`` from
    ``collections.abc`` correctly matches both ``dict`` and ``MappingProxyType``.
    """
    subentries = getattr(config_entry, "subentries", ())

    if isinstance(subentries, Mapping):
        first_value = next(iter(subentries.values()), None)
        if first_value is not None and hasattr(first_value, "subentry_type"):
            for subentry in subentries.values():
                if subentry_type is None or getattr(subentry, "subentry_type", None) == subentry_type:
                    yield subentry
            return

        if subentry_type is not None:
            values = subentries.get(subentry_type, ())
            if isinstance(values, Mapping):
                yield from values.values()
            else:
                yield from values
            return

        for values in subentries.values():
            if isinstance(values, Mapping):
                yield from values.values()
            else:
                yield from values
        return

    for subentry in subentries:
        if subentry_type is None or getattr(subentry, "subentry_type", None) == subentry_type:
            yield subentry


def get_config_subentry_data(
    config_subentry: Any,
    option_keys: Iterable[str] = (),
) -> dict[str, Any]:
    """Return subentry data without compatibility-mirrored option values."""
    data = dict(getattr(config_subentry, "data", {}) or {})
    for key in option_keys:
        data.pop(key, None)
    return data


def get_config_subentry_options(
    config_subentry: Any,
    fallback_keys: Iterable[str] = (),
) -> dict[str, Any]:
    """Return subentry options, falling back to mirrored values stored in data."""
    data = getattr(config_subentry, "data", {}) or {}
    options = dict(getattr(config_subentry, "options", {}) or {})
    for key in fallback_keys:
        if key not in options and key in data:
            options[key] = data[key]
    return options