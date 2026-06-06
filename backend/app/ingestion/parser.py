"""Document parsing (design §11.1 step 2-3).

Produces clean text plus a page map (char offset -> page number) so chunks can
carry page citations. text/md are passthrough (single page). PDF uses pypdf,
extracting per page. Scanned/image PDFs (no extractable text) raise a
human-readable error (§18); OCR is out of MVP scope.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple


class ParseError(Exception):
    """Carries a user-facing message (design §18)."""


@dataclass
class ParsedDoc:
    text: str
    # (char_offset_start, page_number) breakpoints, ascending by offset.
    page_breaks: List[Tuple[int, int]] = field(default_factory=list)

    def page_for_offset(self, offset: int) -> int:
        page = 1
        for start, pno in self.page_breaks:
            if offset >= start:
                page = pno
            else:
                break
        return page


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse(source_type: str, data: bytes) -> ParsedDoc:
    if source_type in ("text_paste", "txt", "md"):
        text = _clean(data.decode("utf-8", errors="replace"))
        if not text:
            raise ParseError("The source contains no readable text.")
        return ParsedDoc(text=text, page_breaks=[(0, 1)])
    if source_type == "pdf":
        return _parse_pdf(data)
    raise ParseError(f"Unsupported source type '{source_type}'.")


def _parse_pdf(data: bytes) -> ParsedDoc:
    try:
        import io

        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover
        raise ParseError("PDF support is unavailable on the server.") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise ParseError(
            "This PDF could not be opened. It may be corrupted or password-protected."
        ) from exc

    parts: List[str] = []
    breaks: List[Tuple[int, int]] = []
    offset = 0
    for i, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        page_text = _clean(page_text)
        breaks.append((offset, i))
        parts.append(page_text)
        offset += len(page_text) + 2  # account for the "\n\n" join below

    text = "\n\n".join(parts).strip()
    if not text:
        raise ParseError(
            "No text could be extracted from this PDF. Scanned/image-only PDFs "
            "are not supported yet."
        )
    return ParsedDoc(text=text, page_breaks=breaks)
