"""Rendering helpers for User Briefing."""

from __future__ import annotations

from .models import BriefingResult, SnippetResult


def render_snippet_text(snippet: SnippetResult) -> str:
    """Return the snippet text.

    The scaffold keeps rendering intentionally simple until phrase assets are wired.
    """
    return snippet.text.strip()


def render_briefing_text(briefing: BriefingResult) -> str:
    """Render a final briefing string from normalized snippets."""
    rendered_parts = [render_snippet_text(snippet) for snippet in briefing.snippets]
    return "\n\n".join(part for part in rendered_parts if part)