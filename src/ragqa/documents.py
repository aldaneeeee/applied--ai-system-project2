"""Document loading and chunking.

Reads ``.md``, ``.txt`` and ``.pdf`` files from a directory and splits them into
overlapping character chunks suitable for retrieval. Each chunk keeps a stable
``chunk_id`` and a human-readable ``source`` so answers can cite exactly where a
fact came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .logging_setup import get_logger

logger = get_logger()

SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf"}


@dataclass
class Document:
    """A source document loaded from disk."""

    doc_id: str  # filename, e.g. "rag.md"
    text: str


@dataclass
class Chunk:
    """A retrievable slice of a document."""

    chunk_id: str  # e.g. "rag.md#2"
    doc_id: str
    text: str
    score: float = 0.0  # populated by the retriever at query time

    def to_dict(self) -> dict:
        return {"chunk_id": self.chunk_id, "doc_id": self.doc_id, "text": self.text}

    @classmethod
    def from_dict(cls, d: dict) -> "Chunk":
        return cls(chunk_id=d["chunk_id"], doc_id=d["doc_id"], text=d["text"])


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            f"Reading {path.name} requires pypdf. Install it with `pip install pypdf`."
        ) from exc

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def load_documents(docs_dir: Path) -> list[Document]:
    """Load every supported document from ``docs_dir``.

    Raises ``FileNotFoundError`` if the directory is missing so the caller can
    surface a clear, actionable error rather than silently returning nothing.
    """
    docs_dir = Path(docs_dir)
    if not docs_dir.exists():
        raise FileNotFoundError(
            f"Documents directory not found: {docs_dir}. "
            "Add source files there or point RAGQA at another directory."
        )

    documents: list[Document] = []
    for path in sorted(docs_dir.iterdir()):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES or not path.is_file():
            continue
        try:
            if path.suffix.lower() == ".pdf":
                text = _read_pdf(path)
            else:
                text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, RuntimeError) as exc:
            # One bad file should not abort ingestion of the rest.
            logger.warning("Skipping %s: %s", path.name, exc)
            continue

        if not text.strip():
            logger.warning("Skipping %s: no extractable text.", path.name)
            continue

        documents.append(Document(doc_id=path.name, text=text))

    logger.info("Loaded %d document(s) from %s", len(documents), docs_dir)
    return documents


def chunk_document(doc: Document, chunk_size: int, overlap: int) -> list[Chunk]:
    """Split a single document into overlapping character chunks.

    Chunks break on paragraph/sentence boundaries where possible so that a chunk
    is a coherent unit of meaning rather than a mid-word cut.
    """
    text = doc.text.strip()
    if not text:
        return []

    if overlap >= chunk_size:  # guardrail against a config that never advances
        overlap = chunk_size // 4

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)

        # Try to end on a natural boundary within the last part of the window.
        if end < n:
            window = text[start:end]
            for sep in ("\n\n", "\n", ". ", " "):
                pos = window.rfind(sep)
                if pos != -1 and pos > chunk_size * 0.5:
                    end = start + pos + len(sep)
                    break

        piece = text[start:end].strip()
        if piece:
            chunks.append(Chunk(chunk_id=f"{doc.doc_id}#{idx}", doc_id=doc.doc_id, text=piece))
            idx += 1

        if end >= n:
            break
        start = max(end - overlap, start + 1)

    return chunks


def chunk_documents(docs: list[Document], chunk_size: int, overlap: int) -> list[Chunk]:
    """Chunk a list of documents into a flat list of chunks."""
    all_chunks: list[Chunk] = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc, chunk_size, overlap))
    logger.info("Produced %d chunk(s) from %d document(s)", len(all_chunks), len(docs))
    return all_chunks
