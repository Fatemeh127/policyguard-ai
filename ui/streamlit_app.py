"""Streamlit UI for PolicyGuard AI."""

import streamlit as st
import requests
from typing import Dict, Any, Optional

# Configuration

API_BASE_URL = "http://backend:8000"

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
def upload_document(file, document_id: str, role: str, api_key: str) -> bool:
    """Upload document to API."""

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
def ask_question(query: str, role: str, limit: int, api_key: str) -> Optional[Dict[str, Any]]:
    """Ask question via API."""

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/ask",
            json={"query": query, "role": role, "limit": limit},
            headers={"X-API-Key": api_key},
            timeout=60,
        )

        if response.status_code == 200:
            return response.json()

        st.error(f"API Error: {response.status_code}")
        st.code(response.text)

        return None

    except Exception as e:
        st.error(f"Request Error: {str(e)}")
        return None


# Display Answer
def display_answer(response: Optional[Dict[str, Any]]):
    """Display answer + metadata + sources."""

    if not response:
        return

    answer = response.get("answer", "No answer found")

    st.markdown("## Answer")

    st.markdown(
        f"""
        <div class="answer-box">
            {answer}
        </div>
        """,
        unsafe_allow_html=True,
    )

    metadata = response.get("metadata", {})

    st.markdown("###  Metadata")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Chunks Used", metadata.get("num_chunks_used", 0))

    with col2:
        st.metric("Latency", f"{metadata.get('latency_seconds', 0):.2f}s")

    with col3:
        st.metric("Model", metadata.get("model", "N/A"))

    with col4:
        st.metric("Context", "Yes" if response.get("context_used") else "No")

    # Sources
    sources = response.get("sources", [])

    if sources:
        st.markdown("### Sources")

        for i, source in enumerate(sources, 1):

            html = f"""
            <div style="
                padding:15px;
                border-radius:10px;
                background-color:#f5f5f5;
                margin-bottom:10px;
            ">
                <b>Source {i}</b><br><br>

                <b>Document:</b> {source.get("document_id", "Unknown")}<br>

                <b>Chunk ID:</b> {source.get("chunk_id", "N/A")}<br>

                <b>Score:</b> {source.get("score", 0):.3f}
            </div>
            """

            st.markdown(html, unsafe_allow_html=True)

    # if sources:
    #     st.markdown("###  Sources")

    #     for i, source in enumerate(sources, 1):

    #         st.markdown(
    #             f"""
    #             <div class="source-box">
    #                 <b>Source {i}</b><br><br>

    #                 <b>Document:</b> {source.get("document_id", "Unknown")}<br>

    #                 <b>Chunk ID:</b> {source.get("chunk_id", "N/A")}<br>

    #                 <b>Score:</b> {source.get("score", 0):.3f}
    #             </div>
    #             """,
    #             unsafe_allow_html=True
    #         )


# Health Status
def display_health_status():
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

                    emoji = "✅" if comp_status == "healthy" or "configured" else "❌"

                    st.text(f"{emoji} {name.title()}: {comp_status}")

                else:
                    st.text(f"{name.title()}: {info}")

        else:
            st.error("API Unreachable")

    except Exception:
        st.error("Cannot connect to API")


# Main App
def main():

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
