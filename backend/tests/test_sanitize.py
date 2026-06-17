from __future__ import annotations

from app.core.sanitize import sanitize_user_text


def test_sanitize_strips_script_tag_and_inner_content():
    assert sanitize_user_text("<script>alert(1)</script>Hello") == "Hello"


def test_sanitize_strips_style_tag_and_inner_content():
    assert sanitize_user_text("<style>body{display:none}</style>Visible") == "Visible"


def test_sanitize_keeps_plain_text():
    assert sanitize_user_text("Printer still broken") == "Printer still broken"
