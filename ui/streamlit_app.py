"""Streamlit UI for PolicyGuard AI."""

import os
import uuid
from typing import Any, cast

import requests
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

# Configuration

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Show connection info in debug mode
if st.sidebar.checkbox("Show Debug Info"):
    st.sidebar.info(f"Backend URL: {API_BASE_URL}")

# Page Config
st.set_page_config(page_title="PolicyGuard AI", page_icon="📚", layout="wide")

# Custom CSS
st.markdown(
    """
<style>

.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    color: #1f77b4;
    margin-bottom: 0.5rem;
}

.sub-header {
    font-size: 1.2rem;
    color: #666;
    margin-bottom: 2rem;
}

.source-box {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 0.5rem 0;
}

.metric-box {
    background-color: #e8f4f8;
    padding: 0.8rem;
    border-radius: 0.5rem;
    text-align: center;
}

.answer-box {
    background-color: #eef6ff;
    padding: 1.2rem;
    border-radius: 0.7rem;
    border: 1px solid #b8d9ff;
    margin-top: 1rem;
    white-space: pre-wrap;
}

</style>
""",
    unsafe_allow_html=True,
)


# Upload Document
def upload_document(file: UploadedFile, document_id: str, role: str, api_key: str) -> bool:
    """Upload document to API."""

    allowed_types = [".pdf", ".docx"]

    if not any(file.name.endswith(ext) for ext in allowed_types):
        raise ValueError("Only PDF and DOCX files are allowed")

    try:
        files = {"file": (file.name, file.getvalue(), file.type)}

        data = {"document_id": document_id, "role": role}

        response = requests.post(
            f"{API_BASE_URL}/api/ingest",
            files=files,
            data=data,
            headers={"X-API-Key": api_key},
            timeout=120,
        )

        print("UPLOAD STATUS:", response.status_code)
        print("UPLOAD RESPONSE:", response.text)

        return response.status_code == 200

    except Exception as e:
        st.error(f"Upload Error: {str(e)}")
        return False


# Ask Question
def ask_question(query: str, role: str, limit: int, api_key: str) -> dict[str, Any] | None:
    """Ask question via API."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/ask",
            json={
                "session_id": st.session_state.session_id,
                "query": query,
                "role": role,
                "limit": limit,
            },
            headers={"X-API-Key": api_key},
            timeout=60,
        )

        if response.status_code == 200:
            return cast(dict[str, Any], response.json())

        st.error(f"API Error: {response.status_code}")
        st.code(response.text)
        return None

    except requests.RequestException as e:
        st.error(f"Request failed: {e}")
        return None


# Display Answer
def display_answer(response: dict[str, Any] | None) -> None:
    """Display answer + metadata + sources."""

    if not response:
        return

    answer = response.get("answer", "No answer found")
    metadata = response.get("metadata", {})
    sources = response.get("sources", [])

    # Answer
    st.markdown("## Answer")

    st.markdown(
        f"""
        <div class="answer-box">
            {answer}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Metadata
    st.markdown("### Metadata")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Chunks Used", metadata.get("num_chunks_used", 0))

    with col2:
        st.metric("Latency", f"{metadata.get('latency_seconds', 0):.2f}s")

    with col3:
        st.metric("Model", metadata.get("model", "N/A"))

    col4, col5, col6 = st.columns(3)

    with col4:
        st.metric("Confidence", f"{metadata.get('confidence', 0):.2f}")

    with col5:
        st.metric("Tokens", metadata.get("total_tokens", "N/A"))

    with col6:
        st.metric("Context", "Yes" if response.get("context_used") else "No")

    # Sources
    sources = response.get("sources", [])

    if sources:
        unique_sources = []
        seen = set()

        for source in sources:
            key = (
                source.get("document_id"),
                source.get("chunk_id"),
                source.get("text"),
            )

            if key not in seen:
                seen.add(key)
                unique_sources.append(source)

        sources = unique_sources

        st.markdown("### Sources")

        # Group chunks by document
        grouped_sources: dict[str, list[dict[str, Any]]] = {}

        for source in sources:

            document_id = source.get("document_id", "Unknown")

            if document_id not in grouped_sources:
                grouped_sources[document_id] = []

            grouped_sources[document_id].append(source)

        # Render grouped sources
        for document_id, document_sources in grouped_sources.items():

            with st.expander(f"{document_id} ({len(document_sources)} relevant chunks found)"):

                for i, source in enumerate(document_sources, 1):
                    score = source.get("score", 0)
                    chunk_id = source.get("chunk_id", "N/A")
                    preview = source.get("text", "No preview available")

                    st.markdown(f"**Chunk {i}**")
                    st.markdown(f"**Chunk ID:** {chunk_id}")
                    st.caption(f"Similarity: {score:.3f}")
                    st.write(preview)
                    st.divider()


# Health Status
def display_health_status() -> None:
    """Display backend health."""

    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)

        if response.status_code == 200:

            health = response.json()

            status = health.get("status", "unknown")

            if status == "healthy":
                st.success("✅ System Healthy")
            else:
                st.warning("⚠️ System Degraded")

            components = health.get("components", {})

            for name, info in components.items():

                if isinstance(info, dict):

                    comp_status = info.get("status", "unknown")

                    emoji = "✅" if comp_status in ("healthy", "configured") else "❌"

                    st.text(f"{emoji} {name.title()}: {comp_status}")

                else:
                    st.text(f"{name.title()}: {info}")

        else:
            st.error("API Unreachable")

    except Exception:
        st.error("Cannot connect to API")


# Main App
def main() -> None:

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    # Header
    st.markdown('<div class="main-header">📚 PolicyGuard AI</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="sub-header">AI Document Assistant with Role-Based Access</div>',
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:

        st.header("⚙️ Settings")

        # API KEY
        api_key = st.text_input("API Key", type="password", placeholder="Enter API key")

        # Role
        role = st.selectbox("Your Role", ["employee", "manager", "admin"])

        st.divider()

        # Upload
        st.header("📤 Upload Document")

        uploaded_file = st.file_uploader("Choose PDF or DOCX", type=["pdf", "docx"])

        if uploaded_file:

            document_id = st.text_input("Document ID", value=uploaded_file.name)

            doc_role = st.selectbox("Required Role", ["employee", "manager", "admin"])

            if st.button(" Upload & Process", use_container_width=True):

                if not api_key:
                    st.warning("Please enter API key")

                else:
                    with st.spinner("Uploading..."):

                        success = upload_document(uploaded_file, document_id, doc_role, api_key)

                        if success:
                            st.success("Upload successful")
                        else:
                            st.error("Upload failed")

        st.divider()

        st.header(" System Status")

        display_health_status()

    # Session State
    if "response" not in st.session_state:
        st.session_state.response = None

    # Chat Area
    st.header(" Ask a Question")

    with st.form("chat_form", clear_on_submit=False):

        query = st.text_input(
            "Question", placeholder="Ask about company policies...", label_visibility="collapsed"
        )

        col1, col2 = st.columns([1, 5])

        with col1:
            limit = st.number_input("Max Results", min_value=1, max_value=10, value=5)

        submitted = st.form_submit_button("Ask", use_container_width=True)

        if submitted:

            if not api_key:
                st.warning(" Please enter API key")

            elif not query.strip():
                st.warning(" Please enter a question")

            else:

                with st.spinner("Thinking..."):

                    response = ask_question(query=query, role=role, limit=limit, api_key=api_key)

                    st.session_state.response = response

    # Render Response
    display_answer(st.session_state.response)


# Run App
if __name__ == "__main__":
    main()
