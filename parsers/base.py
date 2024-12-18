#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
##
# Description:-
#
#       Base abstraction module for enterprise multi-format document parsers.
#       Defines the canonical DocumentChunk dataclass containing text payload,
#       provenance metadata, and Role-Based Access Control (RBAC) permissions.
#
##
# Development date    Developed by       Comments
# ----------------    ------------       ---------
# 14/11/2024          Saddam Khan        Initial implementation
# 18/12/2024          Saddam Khan        Added structured chunking metadata and token boundary logic
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import datetime

@dataclass
class DocumentChunk:
    """
    Explanation: Canonical enterprise document chunk holding content and metadata
    :param  chunk_id str: Unique identifier for the chunk
    :param  text str: Extracted textual content
    :param  source str: Originating file name or URI
    :param  file_format str: Format extension (e.g., pdf, json, xml, csv)
    :param  section str: Structural section, header, or worksheet identifier
    :param  page Optional[int]: 1-based page number if applicable
    :param  allowed_roles List[str]: List of RBAC security roles granted access
    :param  metadata Dict[str, Any]: Additional arbitrary document metadata
    :param  timestamp str: Ingestion ISO timestamp
    """
    chunk_id: str
    text: str
    source: str
    file_format: str
    section: str = "General"
    page: Optional[int] = None
    allowed_roles: List[str] = field(default_factory=lambda: ["all"])
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())

class BaseParser(ABC):
    """
    Explanation: Abstract base class defining document parsing interface across all supported formats
    """

    @abstractmethod
    def parse_bytes(self, content: bytes, filename: str, **kwargs) -> List[DocumentChunk]:
        """
        Explanation: Parses binary file byte stream into structured document chunks
        :param  content bytes: Raw binary payload
        :param  filename str: Source filename
        :param  kwargs: Optional parser parameters including allowed_roles
        :return chunks List[DocumentChunk]: Extracted and structured document chunks
        """
        pass

    @abstractmethod
    def parse_text(self, content: str, filename: str, **kwargs) -> List[DocumentChunk]:
        """
        Explanation: Parses text string into structured document chunks
        :param  content str: Text content to chunk
        :param  filename str: Source filename
        :param  kwargs: Optional parser parameters
        :return chunks List[DocumentChunk]: Extracted document chunks
        """
        pass
