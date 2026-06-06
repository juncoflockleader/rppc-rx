import pytest

from app.ingestion.parser import ParseError, ParsedDoc, parse


def test_text_passthrough_and_cleaning():
    doc = parse("text_paste", b"line one\r\n\r\n\r\nline two   \n")
    assert "line one" in doc.text and "line two" in doc.text
    assert "\r" not in doc.text
    assert "\n\n\n" not in doc.text  # collapsed


def test_markdown_treated_as_text():
    doc = parse("md", b"# Title\n\nBody text.")
    assert doc.text.startswith("# Title")
    assert doc.page_for_offset(0) == 1


def test_empty_source_raises_human_readable():
    with pytest.raises(ParseError):
        parse("txt", b"   \n  ")


def test_unsupported_type_raises():
    with pytest.raises(ParseError):
        parse("docx", b"...")


def test_page_for_offset_maps_breaks():
    doc = ParsedDoc(text="x" * 100, page_breaks=[(0, 1), (50, 2), (80, 3)])
    assert doc.page_for_offset(10) == 1
    assert doc.page_for_offset(60) == 2
    assert doc.page_for_offset(90) == 3
