"""Helpers for working with config subentries."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def iter_config_subentries(config_entry: Any, subentry_type: str | None = None) -> Iterable[Any]:
    """Iterate config subentries defensively across possible runtime shapes."""
    subentries = getattr(config_entry, "subentries", ())

    if isinstance(subentries, dict):
        first_value = next(iter(subentries.values()), None)
        if first_value is not None and hasattr(first_value, "subentry_type"):
            for subentry in subentries.values():
                if subentry_type is None or getattr(subentry, "subentry_type", None) == subentry_type:
                    yield subentry
            return

        if subentry_type is not None:
            values = subentries.get(subentry_type, ())
            if isinstance(values, dict):
                yield from values.values()
            else:
                yield from values
            return

        for values in subentries.values():
            if isinstance(values, dict):
                yield from values.values()
            else:
                yield from values
        return

    for subentry in subentries:
        if subentry_type is None or getattr(subentry, "subentry_type", None) == subentry_type:
            yield subentry