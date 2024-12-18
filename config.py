#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
##
# Description:-
#
#       Enterprise RAG Configuration module.
#       Encapsulates environment parameters, GCP project/region settings,
#       hybrid dense/sparse search weighting, chunking parameters, and GCS bucket bindings.
#
##
# Development date    Developed by       Comments
# ----------------    ------------       ---------
# 14/11/2024          Saddam Khan        Initial implementation
# 18/12/2024          Saddam Khan        Added BigQuery vector index and hybrid search settings
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class EnterpriseSettings:
    """
    Explanation: Configuration parameters for Enterprise RAG indexing, search weights, and model inference
    :param  project_id str: GCP project identifier
    :param  location str: Target GCP region
    :param  model_name str: Gemini foundation model identifier
    :param  embedding_model str: Text embedding model ID
    :param  temperature float: Generation temperature
    :param  max_output_tokens int: Maximum token generation limit
    :param  chunk_size int: Semantic chunk character limit
    :param  chunk_overlap int: Overlap character count between chunks
    :param  hybrid_top_k int: Number of dense/sparse candidates to pool
    :param  rerank_top_k int: Final count of re-ranked chunks
    :param  dense_weight float: Weight factor for dense vector similarity in RRF
    :param  sparse_weight float: Weight factor for BM25 lexical score in RRF
    :param  gcs_bucket str: Optional Google Cloud Storage bucket for document persistence
    :param  vertex_index_endpoint str: Optional Vertex AI Vector Search endpoint ID
    :param  vertex_deployed_index_id str: Optional deployed index ID
    """
    project_id: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    model_name: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
    temperature: float = float(os.getenv("MODEL_TEMPERATURE", "0.2"))
    max_output_tokens: int = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))
    
    # RAG Tuning Parameters
    chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "1200"))
    chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))
    hybrid_top_k: int = int(os.getenv("HYBRID_TOP_K", "10"))
    rerank_top_k: int = int(os.getenv("RERANK_TOP_K", "4"))
    dense_weight: float = float(os.getenv("DENSE_WEIGHT", "0.65"))
    sparse_weight: float = float(os.getenv("SPARSE_WEIGHT", "0.35"))
    
    # Enterprise Storage / Index Targets (Optional GCP Integration)
    gcs_bucket: str = os.getenv("ENTERPRISE_GCS_BUCKET", "")
    vertex_index_endpoint: str = os.getenv("VERTEX_INDEX_ENDPOINT", "")
    vertex_deployed_index_id: str = os.getenv("VERTEX_DEPLOYED_INDEX_ID", "")

settings = EnterpriseSettings()
