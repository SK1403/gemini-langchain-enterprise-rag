#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
##
# Description:-
#
#       Streamlit web user interface for Multi-Terabyte Enterprise RAG Knowledge Hub.
#       Provides role-based access control (RBAC) filtering, multi-format file ingestion
#       (PDF, JSON, XML, CSV, TXT, MD), Google Cloud Storage (GCS) upload synchronization,
#       and grounded audit citations with token streaming.
#
##
# Development date    Developed by       Comments
# ----------------    ------------       ---------
# 14/11/2024          Saddam Khan        Initial implementation
# 18/12/2024          Saddam Khan        Enhanced BigQuery Vector Search UI and document ingestion
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

"""
Explanation: Streamlit web user interface for Multi-Terabyte Enterprise RAG Knowledge Hub.
             Orchestrates RBAC security filtering, multi-format file ingestion (PDF, JSON, XML,
             CSV, TXT, MD), Google Cloud Storage (GCS) upload synchronization, hybrid retrieval
             with cross-encoder re-ranking, and grounded audit citations with token streaming.
:param None: Reads configuration settings and handles browser-based user interactions
:return None: Renders interactive enterprise knowledge hub in web browser
"""

import os
import glob
from typing import Dict, Any, List, Optional
import streamlit as st
import pandas as pd
from config import settings
from rag_pipeline import EnterpriseRAGPipeline
from utils.auth import resolve_gcp_project, verify_adc
from utils.gcs import upload_to_gcs, list_gcs_blobs

ROLES: Dict[str, Dict[str, str]] = {
    "all": {"label": "🌐 General Employee (All Access)", "icon": "🌐", "desc": "Standard corporate policies and general documents."},
    "engineering": {"label": "💻 Engineering & DevOps", "icon": "💻", "desc": "Cloud infrastructure specs, SRE runbooks, architectural topologies."},
    "legal": {"label": "⚖️ Corporate Legal", "icon": "⚖️", "desc": "Master service agreements, NDAs, liability caps, compliance."},
    "finance": {"label": "💼 Finance & Treasury", "icon": "💼", "desc": "Capital allocations, treasury reports, vendor settlements."},
    "executive": {"label": "👔 Executive Leadership", "icon": "👔", "desc": "Unrestricted top-level strategic and financial access."},
}

ROLE_SUGGESTIONS: Dict[str, List[str]] = {
    "all": [
        "What is our corporate policy on Personal Data and GDPR notifications?",
        "Who is our Principal Cloud Architect and where are they located?",
        "What is the target RTO and RPO for disaster recovery?",
    ],
    "engineering": [
        "What are the CPU and memory limits for our Cloud Run enterprise-rag-api?",
        "Describe the automated regional failover protocol for us-central1.",
        "What subnets and firewall rules are defined in corp-core-vpc-prod?",
    ],
    "legal": [
        "What is the limitation of liability cap under our Enterprise Master Services Agreement?",
        "Are indemnification obligations capped or uncapped under MSA Section 2?",
        "What are the termination for convenience terms in our contract?",
    ],
    "finance": [
        "What was the total capital allocated in the 2024 Corporate Treasury Report?",
        "Detail Transaction TX-98401: who was the beneficiary, amount, and approval status?",
        "What cost centers were charged for cloud commitments and ERP licenses?",
    ],
    "executive": [
        "Summarize all major capital expenditures across engineering and cloud commitments.",
        "What are our top legal risk exceptions and SRE failover protocols?",
        "Give me a consolidated briefing of our IT infrastructure and executive leadership.",
    ],
}

def init_page_config() -> None:
    """
    Explanation:
        Sets Streamlit page layout configuration including browser page title,
        corporate hub favicon icon, and expanded wide layout mode.

    :param None: Reads no input parameters.
    :return None: Configures Streamlit page display settings.
    """
    st.set_page_config(
        page_title="Enterprise Knowledge Hub (Multi-Format RAG)",
        page_icon="🏢",
        layout="wide",
    )

def init_session_state() -> None:
    """
    Explanation:
        Initializes Streamlit session state stores for message logs, uploaded file sets,
        and enterprise pipeline persistence across reruns.

    :param None: Initializes state dictionary keys.
    :return None: Sets default session state variables.
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "uploaded_files_set" not in st.session_state:
        st.session_state.uploaded_files_set = set()

def render_sidebar(pipeline: Optional[EnterpriseRAGPipeline] = None) -> Dict[str, Any]:
    """
    Explanation: Renders the sidebar controls for RBAC role selection, sample data corpus pre-loading,
                 custom file upload, GCP project configuration, GCS bucket sync, and index clearing.
    :param  pipeline Optional[EnterpriseRAGPipeline]: Active pipeline instance if already initialized
    :return config Dict[str, Any]: Dictionary containing active user selections and uploaded files
    """
    with st.sidebar:
        st.header("🔐 Role-Based Access Control (RBAC)")
        selected_role_key = st.selectbox(
            "Active Employee Role",
            options=list(ROLES.keys()),
            format_func=lambda k: ROLES[k]["label"],
            index=0,
        )
        st.caption(f"**Clearance**: {ROLES[selected_role_key]['desc']}")

        st.markdown("---")
        st.header("📥 Multi-Format Ingestion")

        # Pre-load Sample Enterprise Corpus button
        if st.button("⚡ Ingest Sample Corpus (JSON, XML, MD, CSV, TXT)", use_container_width=True):
            sample_dir = os.path.join(os.path.dirname(__file__), "sample_data")
            if os.path.exists(sample_dir) and "pipeline" in st.session_state:
                files = glob.glob(os.path.join(sample_dir, "*.*"))
                loaded_count = 0
                for f in files:
                    fname = os.path.basename(f)
                    if fname not in st.session_state.uploaded_files_set:
                        with open(f, "rb") as fh:
                            st.session_state.pipeline.ingest_bytes(fh.read(), fname)
                        st.session_state.uploaded_files_set.add(fname)
                        loaded_count += 1
                st.success(f"Ingested {loaded_count} enterprise documents!")
                st.rerun()

        uploaded_files = st.file_uploader(
            "Upload Enterprise Files",
            type=["pdf", "json", "jsonl", "xml", "csv", "tsv", "txt", "md"],
            accept_multiple_files=True,
            help="Upload multi-terabyte enterprise knowledge files in any supported format.",
        )

        st.markdown("---")
        st.header("⚙️ GCP & Search Controls")
        is_valid, adc_project = verify_adc()
        if is_valid:
            st.success(f"ADC Active: `{adc_project or 'Configured'}`")
        else:
            st.warning("⚠️ ADC not found.")

        resolved_project = resolve_gcp_project(settings.project_id)
        gcp_project = st.text_input("GCP Project ID", value=resolved_project)
        gcs_bucket_name = st.text_input("GCS Knowledge Bucket", value=settings.gcs_bucket, placeholder="e.g. my-enterprise-kb-bucket")
        gcp_region = st.selectbox(
            "GCP Region",
            options=["us-central1", "europe-west1", "europe-west4", "asia-northeast1"],
            index=0,
        )
        model_choice = st.selectbox(
            "Gemini LLM",
            options=["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
            index=0,
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                if "pipeline" in st.session_state:
                    st.session_state.pipeline.clear_history("streamlit_session")
                st.session_state.messages = []
                st.rerun()
        with col2:
            if st.button("🧹 Clear Index", use_container_width=True):
                if "pipeline" in st.session_state:
                    st.session_state.pipeline.index.clear()
                st.session_state.uploaded_files_set.clear()
                st.rerun()

        return {
            "selected_role_key": selected_role_key,
            "uploaded_files": uploaded_files,
            "gcp_project": gcp_project,
            "gcs_bucket_name": gcs_bucket_name,
            "gcp_region": gcp_region,
            "model_choice": model_choice,
        }

def get_or_create_pipeline(
    gcp_project: str,
    gcp_region: str,
    model_choice: str,
) -> EnterpriseRAGPipeline:
    """
    Explanation: Manages the lifecycle of EnterpriseRAGPipeline, preserving indexed vectors across model switches.
    :param  gcp_project str: Target Google Cloud project ID
    :param  gcp_region str: Vertex AI geographical region
    :param  model_choice str: Selected Gemini LLM identifier
    :return pipeline EnterpriseRAGPipeline: Initialized RAG pipeline instance
    """
    pipeline_key = f"{gcp_project}_{gcp_region}_{model_choice}"
    if "current_pipeline_key" not in st.session_state or st.session_state.current_pipeline_key != pipeline_key:
        existing_index = st.session_state.pipeline.index if "pipeline" in st.session_state else None
        st.session_state.pipeline = EnterpriseRAGPipeline(
            project_id=gcp_project,
            location=gcp_region,
            model_name=model_choice,
        )
        if existing_index:
            st.session_state.pipeline.index = existing_index
        st.session_state.current_pipeline_key = pipeline_key
    return st.session_state.pipeline

def handle_document_ingestion(
    pipeline: EnterpriseRAGPipeline,
    uploaded_files: list,
    gcs_bucket_name: str,
    gcp_project: str,
) -> None:
    """
    Explanation: Parses and chunks user-uploaded enterprise files, indexing them into the hybrid index,
                 and optionally archiving raw copies to Google Cloud Storage (GCS).
    :param  pipeline EnterpriseRAGPipeline: Active enterprise RAG pipeline instance
    :param  uploaded_files list: List of UploadedFile objects from Streamlit
    :param  gcs_bucket_name str: Target GCS bucket for document archival
    :param  gcp_project str: Google Cloud Project ID
    :return None: Updates index and session state
    """
    if not uploaded_files:
        return

    for f in uploaded_files:
        if f.name not in st.session_state.uploaded_files_set:
            bytes_data = f.getvalue()
            chunks_count = pipeline.ingest_bytes(bytes_data, f.name)
            st.session_state.uploaded_files_set.add(f.name)

            # Direct GCS Bucket Upload Synchronization
            if gcs_bucket_name and gcs_bucket_name.strip():
                ok, gcs_res = upload_to_gcs(
                    file_bytes=bytes_data,
                    filename=f.name,
                    bucket_name=gcs_bucket_name,
                    folder="raw",
                    project_id=gcp_project,
                )
                if ok:
                    st.sidebar.success(f"☁️ Archived in GCS: `{gcs_res}`")
                else:
                    st.sidebar.warning(f"⚠️ GCS Note: {gcs_res}")
            else:
                st.sidebar.toast(f"Ingested {f.name}: {chunks_count} chunks")

def render_dashboard_and_chat(
    pipeline: EnterpriseRAGPipeline,
    selected_role_key: str,
) -> None:
    """
    Explanation: Renders the knowledge base metrics dashboard, role-based question cards,
                 message history, grounded citations, and streams real-time LLM answers.
    :param  pipeline EnterpriseRAGPipeline: Initialized RAG pipeline instance
    :param  selected_role_key str: Active employee role key for RBAC filtering
    :return None: Renders interactive UI components
    """
    stats = pipeline.get_stats()
    st.title("🏢 Enterprise Knowledge & Intelligence Hub")
    st.caption("Scalable Multi-Format RAG (PDF, JSON, XML, CSV, MD) with RBAC & Cross-Encoder Re-Ranking on Google Cloud.")

    # Metrics Row
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("Indexed Chunks", stats["total_chunks"])
    mcol2.metric("Documents Ingested", stats["unique_documents"])
    mcol3.metric("Formats Supported", len(stats.get("format_breakdown", {})))
    mcol4.metric("Active Role", selected_role_key.upper())

    if stats["total_chunks"] > 0:
        format_tags = " ".join([f"`{fmt.upper()}: {cnt}`" for fmt, cnt in stats.get("format_breakdown", {}).items()])
        st.caption(f"**Format Distribution**: {format_tags} | **Backend**: `{stats['backend']}`")

    st.markdown("---")

    # Suggested Questions per Role
    if not st.session_state.messages:
        st.markdown(f"##### 💡 Suggested Questions for **{ROLES[selected_role_key]['label']}**:")
        cols = st.columns(3)
        for idx, prompt_text in enumerate(ROLE_SUGGESTIONS.get(selected_role_key, ROLE_SUGGESTIONS["all"])[:3]):
            if cols[idx].button(prompt_text, key=f"q_{idx}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": prompt_text})
                st.rerun()

    # Display Historical Messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "results" in msg and msg["results"]:
                with st.expander(f"🔍 Grounded Citations & Re-Rank Diagnostics ({len(msg['results'])} Sources)"):
                    for res in msg["results"]:
                        c = res.chunk
                        loc = f"Page {c.page}" if c.page else f"Sec: {c.section}"
                        st.markdown(f"**• [{c.source} - {loc}]** `Format: {c.file_format.upper()}`")
                        st.caption(f"Scores: Dense={res.dense_score} | Sparse={res.sparse_score} | RRF={res.rrf_score} | Re-rank={res.final_score}")
                        st.code(c.text[:300] + ("..." if len(c.text) > 300 else ""))

    # Handle User Input
    prompt_input = st.chat_input("Ask a question across all enterprise documents, configs, XMLs, and logs...")
    pending_query = None

    if prompt_input:
        pending_query = prompt_input
        st.session_state.messages.append({"role": "user", "content": prompt_input})
        with st.chat_message("user"):
            st.markdown(prompt_input)
    elif st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        pending_query = st.session_state.messages[-1]["content"]

    if pending_query:
        with st.chat_message("assistant"):
            response_box = st.empty()
            full_text = ""

            try:
                for chunk in pipeline.stream_chat(
                    query=pending_query,
                    user_role=selected_role_key,
                    session_id="streamlit_session",
                ):
                    full_text += chunk
                    response_box.markdown(full_text + "▌")

                if full_text:
                    response_box.markdown(full_text)
                    recorded_results = list(pipeline.last_retrieved_results)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_text,
                        "results": recorded_results,
                    })

                    if recorded_results:
                        with st.expander(f"🔍 Grounded Citations & Re-Rank Diagnostics ({len(recorded_results)} Sources)"):
                            for res in recorded_results:
                                c = res.chunk
                                loc = f"Page {c.page}" if c.page else f"Sec: {c.section}"
                                st.markdown(f"**• [{c.source} - {loc}]** `Format: {c.file_format.upper()}`")
                                st.caption(f"Scores: Dense={res.dense_score} | Sparse={res.sparse_score} | RRF={res.rrf_score} | Re-rank={res.final_score}")
                                st.code(c.text[:300] + ("..." if len(c.text) > 300 else ""))
                else:
                    response_box.warning("No answer generated.")
            except Exception as e:
                err = str(e)
                if "BILLING_DISABLED" in err:
                    response_box.error(
                        f"💳 **Billing Required**\n\n"
                        f"Vertex AI requires billing enabled on project `{pipeline.project_id}`.\n\n"
                        f"👉 [Enable Billing](https://console.developers.google.com/billing/enable?project={pipeline.project_id})"
                    )
                else:
                    response_box.error(f"⚠️ Error: {err}")

def main() -> None:
    """
    Explanation:
        Main application orchestration entry point coordinating page layout initialization,
        sidebar configuration, pipeline lifecycle management, ingestion, and UI dashboard rendering.

    :param None: Reads execution configuration and coordinates Streamlit application lifecycle.
    :return None: Executes Streamlit application cycle.
    """
    init_page_config()
    init_session_state()
    cfg = render_sidebar()
    pipeline = get_or_create_pipeline(
        gcp_project=cfg["gcp_project"],
        gcp_region=cfg["gcp_region"],
        model_choice=cfg["model_choice"],
    )
    handle_document_ingestion(
        pipeline=pipeline,
        uploaded_files=cfg["uploaded_files"],
        gcs_bucket_name=cfg["gcs_bucket_name"],
        gcp_project=cfg["gcp_project"],
    )
    render_dashboard_and_chat(
        pipeline=pipeline,
        selected_role_key=cfg["selected_role_key"],
    )

if __name__ == "__main__":
    main()
