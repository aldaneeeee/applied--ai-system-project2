"""Optional Streamlit web UI for GroundedRAG.

Run with:  streamlit run app_streamlit.py

This is a thin presentation layer over the same `RagPipeline` used by the CLI,
so the UI and CLI always share identical behaviour.
"""

from __future__ import annotations

import streamlit as st

from src.ragqa.config import load_config
from src.ragqa.logging_setup import configure_logging
from src.ragqa.pipeline import RagPipeline

st.set_page_config(page_title="GroundedRAG", page_icon="🔎", layout="centered")


@st.cache_resource
def get_pipeline():
    config = load_config()
    configure_logging(config.log_level, config.log_dir)
    return config, RagPipeline.from_config(config)


config, pipeline = get_pipeline()

st.title("🔎 GroundedRAG")
st.caption(
    "Ask a question about the indexed documents. Answers are grounded in "
    "retrieved passages, self-verified, and cited — or the system abstains."
)

with st.sidebar:
    st.header("System")
    st.write(f"**Backend:** {config.resolved_backend()}")
    st.write(f"**Model:** {config.model}")
    st.write(f"**Indexed chunks:** {pipeline.retriever.num_chunks}")
    st.write(f"**top_k:** {config.top_k}  ·  **min score:** {config.min_score}")
    st.write(f"**Max retries:** {config.max_retries}")

question = st.text_input("Your question", placeholder="e.g. What is cosine similarity?")

if st.button("Ask", type="primary") and question.strip():
    with st.spinner("Planning, retrieving, answering, and verifying..."):
        result = pipeline.answer(question)

    if result.abstained:
        st.warning(result.answer)
    else:
        st.success("Answer")
        st.write(result.answer)

    cols = st.columns(4)
    cols[0].metric("Grounded", "yes" if result.grounded else "no")
    cols[1].metric("Abstained", "yes" if result.abstained else "no")
    cols[2].metric("Attempts", result.attempts)
    cols[3].metric("Top score", f"{result.retrieval_score:.3f}")

    if result.citations:
        st.subheader("Sources")
        for i, chunk in enumerate(result.citations, start=1):
            with st.expander(f"[{i}] {chunk.doc_id}  (score {chunk.score:.3f})"):
                st.write(chunk.text)

    with st.expander("Pipeline trace (plan → retrieve → answer → verify)"):
        st.json(result.trace)
