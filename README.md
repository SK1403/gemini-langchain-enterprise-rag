# 🏢 Enterprise Multi-Format Hybrid RAG (PDF, JSON, XML, CSV, MD)

A production-grade, enterprise-scale **Retrieval-Augmented Generation (RAG)** platform designed for multi-terabyte heterogeneous knowledge bases, powered by **Python 3.11**, **Google Cloud Vertex AI (Gemini 1.5/2.0)**, **LangChain**, and **Streamlit**.

---

## 🌟 Architectural Highlights

1. **Multi-Format Enterprise Ingestion**:
   - **📄 Native & Scanned PDFs**: Page-level extraction, table detection, and layout preservation (`pypdf`).
   - **🌲 Complex Nested JSON / JSONL**: Schema unwinding, recursive flattening, and semantic entity generation.
   - **📑 Hierarchical XML**: XML tree traversal, attribute extraction, and transactional record chunking.
   - **📊 Tabular CSV / TSV**: Header-preserving markdown table batching.
   - **📝 Markdown & Plain Text**: H1/H2/H3 heading-aware section splitting.

2. **⚡ Hybrid Dense + Sparse Search Index**:
   - **Dense Vector Search**: Powered by Google Cloud `text-embedding-004` (with seamless local fallback).
   - **Sparse Lexical Search**: BM25 inverted index for exact keyword, acronym, and transaction ID matching.
   - **Reciprocal Rank Fusion (RRF)**: Fuses semantic and lexical candidate ranks:
     $$RRF(d) = \frac{w_{dense}}{60 + rank_{dense}} + \frac{w_{sparse}}{60 + rank_{sparse}}$$

3. **🔐 Role-Based Access Control (RBAC)**:
   - Chunks are tagged with `allowed_roles` (e.g., `["engineering"]`, `["legal"]`, `["finance"]`, `["executive"]`, `["all"]`).
   - Query-time security filtering guarantees employees only retrieve documents matching their clearance.

4. **🎯 Cross-Encoder Re-Ranking & Citations**:
   - Re-ranks top-$K$ candidates to maximize precision before prompt injection.
   - Full audit trail: Document name, page number, section, and similarity scores attached to every answer.

---

## 📁 Repository Layout

```
gemini-langchain-enterprise-rag/
├── app.py                  # Streamlit Enterprise Knowledge Hub UI
├── rag_pipeline.py         # End-to-end RAG orchestrator & Gemini streaming
├── cli.py                  # Terminal enterprise Q&A tool with RBAC simulation
├── ingest.py               # Batch folder ingestion utility
├── config.py               # Enterprise configuration dataclass
├── Dockerfile              # Cloud Run deployment container
├── requirements.txt        # Pinned dependencies
├── indexing/
│   ├── __init__.py
│   └── hybrid_index.py     # Dense vector, BM25, RRF, RBAC & Re-ranking engine
├── parsers/
│   ├── __init__.py
│   ├── base.py             # BaseParser & DocumentChunk schema
│   ├── factory.py          # Universal parser router
│   ├── pdf_parser.py       # PDF layout and page extractor
│   ├── json_parser.py      # Nested JSON/JSONL flattener
│   ├── xml_parser.py       # Hierarchical XML record extractor
│   ├── csv_parser.py       # Tabular Markdown table chunker
│   └── text_parser.py      # Heading-aware markdown/text chunker
├── utils/
│   ├── __init__.py
│   └── auth.py             # Google Cloud ADC verification
└── sample_data/            # Sample enterprise data
    ├── cloud_infrastructure.json
    ├── financial_transactions.xml
    ├── legal_master_agreement.txt
    ├── system_runbook.md
    └── employee_directory.csv
```

---

## 🚀 Getting Started

### 1. Environment Setup

```bash
cd gemini-langchain-enterprise-rag
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Google Cloud ADC

```bash
gcloud auth application-default login
cp .env.example .env
```

### 3. Run the Web Knowledge Portal

```bash
.venv/bin/streamlit run app.py --server.port=8503
```
Open `http://localhost:8503`:
1. Select an **Active Employee Role** (e.g. `Legal`, `Engineering`, `Finance`).
2. Click **⚡ Ingest Sample Corpus** to index the sample JSON, XML, MD, and CSV files in seconds.
3. Ask domain questions or test suggested questions to see RBAC filtering in action!

### 4. Run Batch Ingestion & Terminal CLI

```bash
# Ingest an entire directory of documents
.venv/bin/python ingest.py sample_data/

# Run interactive terminal Q&A
.venv/bin/python cli.py
```

---

## 🚢 Production Deployment (Cloud Run)

```bash
gcloud run deploy enterprise-rag-hub \
  --source . \
  --region us-central1 \
  --platform managed \
  --session-affinity \
  --min-instances=1 \
  --max-instances=20 \
  --cpu=2 \
  --memory=4Gi
```
