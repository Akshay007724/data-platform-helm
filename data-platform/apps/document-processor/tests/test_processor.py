import pytest

from services.chunker import chunk_text
from services.extractors.base import ExtractedContent, PageContent


class TestChunker:
    def test_empty_text(self):
        assert chunk_text("") == []

    def test_whitespace_text(self):
        assert chunk_text("   \n\n  ") == []

    def test_single_short_chunk(self):
        text = "Hello world"
        chunks = chunk_text(text, chunk_size=512, overlap=0)
        assert chunks == ["Hello world"]

    def test_paragraph_splitting(self):
        text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
        chunks = chunk_text(text, chunk_size=40, overlap=0)
        assert len(chunks) >= 2
        assert all(len(c) <= 60 for c in chunks)  # allow some tolerance

    def test_overlap_applied(self):
        text = "A" * 100 + "\n\n" + "B" * 100 + "\n\n" + "C" * 100
        chunks = chunk_text(text, chunk_size=120, overlap=20)
        # Second chunk should contain tail of first
        assert len(chunks) >= 2
        if len(chunks) > 1:
            # Overlap means second chunk starts with end of previous
            first_tail = chunks[0][-20:]
            assert chunks[1].startswith(first_tail)

    def test_long_paragraph_split(self):
        text = " ".join(["word"] * 200)
        chunks = chunk_text(text, chunk_size=50, overlap=0)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c) <= 55  # slight buffer for word boundaries

    def test_returns_list_of_strings(self):
        chunks = chunk_text("Some text here", chunk_size=512, overlap=0)
        assert isinstance(chunks, list)
        assert all(isinstance(c, str) for c in chunks)


class TestExtractedContent:
    def test_page_content_defaults(self):
        page = PageContent(page=1, text="hello")
        assert page.images == []

    def test_extracted_content(self):
        page = PageContent(page=1, text="hello", images=[b"fake_img"])
        content = ExtractedContent(pages=[page], file_type="pdf")
        assert len(content.pages) == 1
        assert content.file_type == "pdf"
        assert content.pages[0].images == [b"fake_img"]

    def test_multipage(self):
        pages = [PageContent(page=i, text=f"Page {i}") for i in range(1, 4)]
        content = ExtractedContent(pages=pages, file_type="word")
        assert len(content.pages) == 3
