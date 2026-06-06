from app.ingestion.chunker import chunk_document
from app.ingestion.parser import ParsedDoc


def _doc(n_paras=40, words=60):
    paras = [("para%d " % i) + " ".join(["word"] * words) for i in range(n_paras)]
    text = "\n\n".join(paras)
    return ParsedDoc(text=text, page_breaks=[(0, 1), (len(text) // 2, 2)])


def test_produces_multiple_chunks_with_small_target():
    doc = _doc()
    chunks = chunk_document(doc, target_tokens=100, overlap_tokens=20)
    assert len(chunks) >= 2
    # indices are contiguous from 0
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_offsets_and_pages_are_within_bounds():
    doc = _doc()
    chunks = chunk_document(doc, target_tokens=100, overlap_tokens=20)
    for c in chunks:
        assert 0 <= c.char_start < c.char_end <= len(doc.text)
        assert c.text == doc.text[c.char_start:c.char_end].strip() or c.text in doc.text
        assert c.page_start in (1, 2) and c.page_end in (1, 2)
        assert c.token_count >= 1


def test_overlap_creates_continuity():
    doc = _doc()
    chunks = chunk_document(doc, target_tokens=100, overlap_tokens=40)
    # consecutive chunks should overlap (next starts before previous end)
    overlaps = [chunks[i + 1].char_start < chunks[i].char_end
                for i in range(len(chunks) - 1)]
    assert any(overlaps)


def test_short_text_single_chunk():
    doc = ParsedDoc(text="just a short source.", page_breaks=[(0, 1)])
    chunks = chunk_document(doc, target_tokens=800, overlap_tokens=120)
    assert len(chunks) == 1
    assert chunks[0].text == "just a short source."
