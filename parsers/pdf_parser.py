#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
##
# Description:-
#
#       Enterprise PDF Parser with Page Extraction and Boundary-Aware Chunking.
#       Processes enterprise PDFs while retaining page metadata, security roles,
#       and paragraph structure for granular retrieval.
#
##
# Development date    Developed by       Comments
# ----------------    ------------       ---------
# 14/11/2024          Saddam Khan        Initial implementation
# 18/12/2024          Saddam Khan        Added page-level text extraction and metadata preservation
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

"""
Explanation:
    This module provides boundary-aware document splitting and page-level
    parsing for PDF documents, supporting role-based access control metadata.

:param None: Module definitions.
:return None: Parser class and chunking helper functions.
"""

import io
import re
from typing import List, Optional
from pypdf import PdfReader
from parsers.base import BaseParser, DocumentChunk
from config import settings


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Explanation:
        Hierarchical text splitter preserving paragraph and sentence boundaries.

    :param text <str>: Raw text content to split into chunks.
    :param chunk_size <int>: Maximum character length per chunk.
    :param chunk_overlap <int>: Overlap character count between consecutive chunks.
    :return List[str]: Array of extracted text chunks.
    """
    if not text.strip():
        return []
    
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = (current_chunk + "\n\n" + para) if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(para) > chunk_size:
                # Sub-split long paragraph by sentences
                sentences = re.split(r"(?<=[.?!])\s+", para)
                sub_chunk = ""
                for s in sentences:
                    if len(sub_chunk) + len(s) + 1 <= chunk_size:
                        sub_chunk = (sub_chunk + " " + s) if sub_chunk else s
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = s
                if sub_chunk:
                    current_chunk = sub_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

class PDFParser(BaseParser):
    """Enterprise PDF parser with page extraction and section tracking."""

    def parse_bytes(self, content: bytes, filename: str, **kwargs) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        reader = PdfReader(io.BytesIO(content))
        allowed_roles = kwargs.get("allowed_roles", ["all"])
        
        # Auto-infer department if present in filename
        lower_name = filename.lower()
        if "legal" in lower_name:
            allowed_roles = ["legal", "executive", "all"]
        elif "finance" in lower_name:
            allowed_roles = ["finance", "executive", "all"]
        elif "engineer" in lower_name or "cloud" in lower_name or "tech" in lower_name:
            allowed_roles = ["engineering", "all"]

        for page_idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                continue

            sub_chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
            for idx, c in enumerate(sub_chunks):
                # Detect potential section title from first line
                first_line = c.split("\n")[0][:80].strip()
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{filename}#p{page_idx}_c{idx}",
                        text=c,
                        source=filename,
                        file_format="pdf",
                        section=first_line or f"Page {page_idx}",
                        page=page_idx,
                        allowed_roles=allowed_roles,
                        metadata={
                            "total_pages": len(reader.pages),
                            "chunk_length": len(c),
                        },
                    )
                )

        return chunks

    def parse_text(self, content: str, filename: str, **kwargs) -> List[DocumentChunk]:
        return self.parse_bytes(content.encode("utf-8"), filename, **kwargs)
