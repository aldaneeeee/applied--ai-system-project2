"""TF-IDF vector retriever.

A deliberately dependency-light, fully local retriever: it vectorises chunks
with TF-IDF and ranks them by cosine similarity. This keeps the whole system
reproducible and offline-capable (no embedding API, no model downloads) while
still demonstrating real vector search over a document corpus.

The index can be persisted to disk with :meth:`save` and reloaded with
:meth:`load`, so ingestion is a distinct, cacheable step.
"""

from __future__ import annotations

from pathlib import Path

from .documents import Chunk
from .logging_setup import get_logger

logger = get_logger()

_VECTORIZER_FILE = "vectorizer.joblib"
_MATRIX_FILE = "matrix.joblib"
_CHUNKS_FILE = "chunks.joblib"


class TfidfRetriever:
    """Vector-search retriever backed by scikit-learn's TF-IDF."""

    def __init__(self) -> None:
        self._vectorizer = None
        self._matrix = None
        self._chunks: list[Chunk] = []

    # -- Building / persistence --------------------------------------------
    def build(self, chunks: list[Chunk]) -> "TfidfRetriever":
        if not chunks:
            raise ValueError("Cannot build a retriever from zero chunks.")

        from sklearn.feature_extraction.text import TfidfVectorizer

        self._chunks = chunks
        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
        )
        self._matrix = self._vectorizer.fit_transform(c.text for c in chunks)
        logger.info(
            "Built TF-IDF index: %d chunks, %d features",
            self._matrix.shape[0],
            self._matrix.shape[1],
        )
        return self

    def save(self, index_dir: Path) -> None:
        if self._vectorizer is None:
            raise RuntimeError("Nothing to save: build the index first.")
        import joblib

        index_dir = Path(index_dir)
        index_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._vectorizer, index_dir / _VECTORIZER_FILE)
        joblib.dump(self._matrix, index_dir / _MATRIX_FILE)
        joblib.dump([c.to_dict() for c in self._chunks], index_dir / _CHUNKS_FILE)
        logger.info("Saved index to %s", index_dir)

    @classmethod
    def load(cls, index_dir: Path) -> "TfidfRetriever":
        import joblib

        index_dir = Path(index_dir)
        required = [index_dir / f for f in (_VECTORIZER_FILE, _MATRIX_FILE, _CHUNKS_FILE)]
        missing = [p.name for p in required if not p.exists()]
        if missing:
            raise FileNotFoundError(
                f"Index at {index_dir} is incomplete (missing {', '.join(missing)}). "
                "Run `ingest` to build it."
            )

        retriever = cls()
        retriever._vectorizer = joblib.load(index_dir / _VECTORIZER_FILE)
        retriever._matrix = joblib.load(index_dir / _MATRIX_FILE)
        retriever._chunks = [Chunk.from_dict(d) for d in joblib.load(index_dir / _CHUNKS_FILE)]
        logger.info("Loaded index from %s (%d chunks)", index_dir, len(retriever._chunks))
        return retriever

    # -- Querying ----------------------------------------------------------
    @property
    def num_chunks(self) -> int:
        return len(self._chunks)

    def retrieve(self, queries: list[str], top_k: int) -> list[Chunk]:
        """Retrieve the top-``k`` chunks across one or more query strings.

        When several queries are supplied (e.g. from the planning step), each
        chunk keeps its best score across those queries, then the global top-k
        are returned sorted by score. Returned ``Chunk`` objects are copies with
        their ``score`` populated.
        """
        if self._vectorizer is None or self._matrix is None:
            raise RuntimeError("Retriever is not built or loaded.")

        queries = [q for q in queries if q and q.strip()]
        if not queries:
            return []

        from sklearn.metrics.pairwise import linear_kernel

        query_vecs = self._vectorizer.transform(queries)
        # linear_kernel on L2-normalised TF-IDF rows == cosine similarity.
        sims = linear_kernel(query_vecs, self._matrix)  # shape: (n_queries, n_chunks)
        best_per_chunk = sims.max(axis=0)  # best score for each chunk

        ranked = sorted(
            range(len(self._chunks)),
            key=lambda i: float(best_per_chunk[i]),
            reverse=True,
        )[:top_k]

        results: list[Chunk] = []
        for i in ranked:
            base = self._chunks[i]
            results.append(
                Chunk(chunk_id=base.chunk_id, doc_id=base.doc_id, text=base.text,
                      score=round(float(best_per_chunk[i]), 4))
            )
        return results
