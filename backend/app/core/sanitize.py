from __future__ import annotations

from html.parser import HTMLParser


class _TagStripper(HTMLParser):
    """Collect text content while discarding every HTML tag.

    Using the stdlib parser (rather than a regex) means malformed or nested
    markup such as ``<scr<script>ipt>`` is still neutralised.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def get_text(self) -> str:
        return "".join(self._chunks)


def sanitize_user_text(raw: str) -> str:
    """Strip HTML/script markup from user-supplied text.

    Comments are rendered as plain text in the UI, so removing tags here is a
    defense-in-depth measure against stored XSS (AGENTS.md §5 rule #7) without
    altering ordinary prose.
    """
    stripper = _TagStripper()
    stripper.feed(raw)
    stripper.close()
    return stripper.get_text().strip()
