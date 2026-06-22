from __future__ import annotations

from app.core.sanitize import sanitize_user_text


def test_sanitize_strips_script_tag_and_inner_content():
    assert sanitize_user_text("<script>alert(1)</script>Hello") == "Hello"


def test_sanitize_strips_style_tag_and_inner_content():
    assert sanitize_user_text("<style>body{display:none}</style>Visible") == "Visible"


def test_sanitize_keeps_plain_text():
    assert sanitize_user_text("Printer still broken") == "Printer still broken"


def test_sanitize_strips_non_dangerous_html_tags():
    assert sanitize_user_text("<b>Printer</b> still broken") == "Printer still broken"


def test_sanitize_strips_img_tag_without_inner_text():
    assert sanitize_user_text('<img src="x" onerror="alert(1)">Safe') == "Safe"
