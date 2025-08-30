import streamlit as st
from rag_youtube import generate_answer_chain, process_video
import time

st.set_page_config(page_title="YouTube RAG Assistant", page_icon="🎥")
st.title("🎬 YouTube RAG AI Assistant")
st.caption("_Ask questions directly from YouTube transcripts._")
st.divider()

with st.sidebar:
    st.header("About")
    st.markdown("""
    This app uses **RAG (Retrieval-Augmented Generation)** to process
    YouTube transcripts and answer your questions based only on the video content.
    """)


# --- Session state setup ---
if "video_ready" not in st.session_state:
    st.session_state.video_ready = False
if "query" not in st.session_state:
    st.session_state.query = ""
if "widget" not in st.session_state:
    st.session_state.widget = ""

def clear_query():
    st.session_state.query = st.session_state.widget
    st.session_state.widget = ""

# --- Step 1: Input video URL ---
video_url = st.text_input("Enter YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")
if st.button("Process Video"):
    alert = st.empty()
    if video_url:
        try:
            # Spinner while processing video
            with st.spinner("Processing video transcript... This may take a few seconds ⏳"):
                process_video(video_url)
                # Reset session state for new video
                st.session_state.query = ""
                st.session_state.widget = ""
                st.session_state.video_ready = True
        except Exception as e:
            st.error(str(e))
    else:
        st.warning("Please enter a valid video URL.")

# --- Step 2: Input question ---
st.text_input("Ask a question about the video:", key="widget", on_change=clear_query)
query = st.session_state.get("query", "")

if query:
    if st.session_state.video_ready:
        try:
            # Spinner while LLM is generating answer
            with st.spinner("Thinking... 🤔"):
                answer = generate_answer_chain(query)
            st.header("Answer")
            st.write(answer)
        except RuntimeError as e:
            st.error(str(e))
    else:
        st.warning("Please process a video first.")
