"""
Streamlit web UI for the Music Recommender + AI DJ.

Run with:  streamlit run app.py

This is a thin layer over the same AIDJ workflow the CLI uses, so both always
behave the same way.
"""

import streamlit as st

from src.ai_dj import AIDJ
from src.llm import LLMError, get_backend
from src.logging_setup import PROJECT_ROOT, configure_logging
from src.recommender import load_songs

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

st.set_page_config(page_title="AI DJ", page_icon="🎧", layout="centered")


@st.cache_resource
def get_dj():
    configure_logging()
    songs = load_songs(str(PROJECT_ROOT / "data" / "songs.csv"))
    return AIDJ(songs, backend=get_backend())


try:
    dj = get_dj()
except (LLMError, ValueError) as exc:
    st.error(f"Could not start the AI DJ: {exc}")
    st.stop()

st.title("🎧 Mood Catcher AI DJ")
st.caption("Describe what you want to hear. The original recommender ranks the songs; "
           "the AI DJ interprets your request and explains the picks.")

with st.sidebar:
    st.header("System")
    st.write(f"**Backend:** {dj.backend.name}")
    st.write(f"**Songs in catalog:** {len(dj.songs)}")
    k = st.slider("Songs to recommend", 1, 10, 5)

request = st.text_input("Your request", placeholder="e.g. mellow lofi for studying late at night")

if st.button("Recommend", type="primary"):
    result = dj.run(request, k=k)
    if result.status != "ok":
        st.warning(result.message)
    else:
        p = result.profile
        st.write(f"**Interpreted as:** genre = `{p['genre']}`, mood = `{p['mood']}`, "
                 f"energy = `{p['energy']}`")
        st.success(result.explanation)
        st.table([
            {"#": i, "Title": s["title"], "Artist": s["artist"], "Genre": s["genre"],
             "Mood": s["mood"], "Score": round(score, 2), "Reasons": "; ".join(reasons)}
            for i, (s, score, reasons) in enumerate(result.recommendations, start=1)
        ])
        st.caption(f"Explanation source: {result.explanation_source}")
    for warning in result.warnings:
        st.info(warning)
    with st.expander("Agent trace (validate → interpret → normalize → recommend → verify)"):
        st.json(result.trace)
