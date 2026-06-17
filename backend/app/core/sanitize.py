from __future__ import annotations

from html.parser import HTMLParser

# Element contents that must be dropped entirely (tags + inner text).
_DANGEROUS_TAGS = frozenset(
    {"script", "style", "iframe", "object", "embed", "noscript", "svg", "math"}
)


class _TagStripper(HTMLParser):
    """Collect safe text while discarding HTML tags.

    Tag delimiters are ignored. Text inside dangerous elements (e.g. ``script``)
    is skipped as well so ``<script>alert(1)</script>Hello`` becomes ``Hello``.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in _DANGEROUS_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _DANGEROUS_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Self-closing dangerous tags carry no inner text to skip.
        pass

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._chunks.append(data)

    def get_text(self) -> str:
        return "".join(self._chunks)


def sanitize_user_text(raw: str) -> str:
    """Strip HTML/script markup from user-supplied text.

    Comments are rendered as plain text in the UI, so removing tags here is a
    defense-in-depth measure against stored XSS without altering ordinary prose.
    """
    stripper = _TagStripper()
    stripper.feed(raw)
    stripper.close()
    return stripper.get_text().strip()
