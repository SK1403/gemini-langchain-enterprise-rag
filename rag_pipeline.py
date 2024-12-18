#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
##
# Description:-
#
#       End-to-End Multi-Terabyte Enterprise RAG Pipeline for Google Cloud Platform.
#       Orchestrates multi-format file ingestion (PDF, JSON, XML, CSV, TXT, MD),
#       hybrid dense/sparse vector indexing, role-based access control (RBAC),
#       cross-encoder re-ranking, and grounded multi-turn synthesis with Gemini.
#
##
# Development date    Developed by       Comments
# ----------------    ------------       ---------
# 14/11/2024          Saddam Khan        Initial implementation
# 18/12/2024          Saddam Khan        Added hybrid semantic-BM25 retrieval and Gemini synthesis
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from typing import Generator, Dict, Any, List, Optional
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory, BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import BaseMessage

from config import settings
from parsers.base import DocumentChunk
from parsers.factory import ParserFactory
from indexing.hybrid_index import EnterpriseHybridIndex, SearchResult
from utils.auth import resolve_gcp_project

class EnterpriseRAGPipeline:
    """
    Explanation: Multi-Terabyte Enterprise Retrieval-Augmented Generation Orchestrator.
                 Integrates document parsers, hybrid indexing with RBAC filtering,
                 cross-encoder re-ranking, and grounded streaming generation via Gemini on Vertex AI.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
    ):
        """
        Explanation: Initializes EnterpriseRAGPipeline with Vertex AI configuration and hybrid index
        :param  project_id Optional[str]: GCP project identifier hosting Vertex AI
        :param  location Optional[str]: GCP region for model endpoints
        :param  model_name Optional[str]: Gemini generative foundation model identifier
        :param  temperature float: Generation temperature parameter
        :return None: Instantiates pipeline orchestrator
        """
        self.project_id = resolve_gcp_project(project_id or settings.project_id)
        self.location = location or settings.location
        self.model_name = model_name or settings.model_name
        self.temperature = temperature

        # Hybrid Index
        self.index = EnterpriseHybridIndex(project_id=self.project_id, location=self.location)

        # In-memory conversation sessions: session_id -> InMemoryChatMessageHistory
        self._sessions: Dict[str, InMemoryChatMessageHistory] = {}
        self.last_retrieved_results: List[SearchResult] = []

        # Initialize Vertex AI LLM
        self.llm = ChatVertexAI(
            model=self.model_name,
            project=self.project_id if self.project_id else None,
            location=self.location,
            temperature=self.temperature,
            max_output_tokens=settings.max_output_tokens,
            max_retries=1,
        )

        # Build Conversational Prompt & Chain
        self._build_chain()

    def _build_chain(self):
        """
        Explanation: Constructs strict enterprise grounding prompt template and LangChain runnable chain
        :return None: Binds prompt, LLM, and session history handler
        """
        system_template = (
            "You are the Enterprise AI Knowledge Intelligence Assistant for our organization.\n"
            "Your objective is to provide accurate, grounded, and concise answers based on the provided enterprise documents.\n\n"
            "=== VERIFIED ENTERPRISE KNOWLEDGE CONTEXT ===\n"
            "{context}\n"
            "=============================================\n\n"
            "Strict Enterprise Operational Rules:\n"
            "1. Grounding Rule: Answer strictly using the verified enterprise knowledge context above.\n"
            "2. Citation Rule: Always cite the source for every factual statement using standard markdown tags: "
            "[Source: filename (Section/Page)].\n"
            "3. Gap Identification: If the provided documents do not contain the answer or lack required context, "
            "clearly state: 'The uploaded enterprise documents do not contain this information.' Do not fabricate policies, specs, or financial figures.\n"
            "4. Formatting: Present complex comparisons and metrics using clean markdown tables."
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_template),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])

        self.chain = self.prompt | self.llm
        self.conversational_chain = RunnableWithMessageHistory(
            self.chain,
            self._get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    def _get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """
        Explanation: Retrieves or creates an in-memory conversation history instance for the session
        :param  session_id str: Unique identifier of conversational session
        :return history BaseChatMessageHistory: Message history storage
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = InMemoryChatMessageHistory()
        return self._sessions[session_id]

    def ingest_bytes(self, content: bytes, filename: str, allowed_roles: Optional[List[str]] = None) -> int:
        """
        Explanation: Dispatches binary file bytes to parser factory and adds extracted chunks to hybrid index
        :param  content bytes: Raw binary data of document
        :param  filename str: Filename with extension for parser detection
        :param  allowed_roles Optional[List[str]]: Authorized RBAC roles allowed to access document
        :return chunk_count int: Total number of parsed and indexed chunks
        """
        parser = ParserFactory.get_parser(filename)
        kwargs = {}
        if allowed_roles:
            kwargs["allowed_roles"] = allowed_roles
        chunks = parser.parse_bytes(content, filename, **kwargs)
        self.index.add_chunks(chunks)
        return len(chunks)

    def ingest_text(self, text: str, filename: str, allowed_roles: Optional[List[str]] = None) -> int:
        """
        Explanation: Dispatches string text content to parser factory and indexes resulting chunks
        :param  text str: Text string to chunk and index
        :param  filename str: Source document identifier
        :param  allowed_roles Optional[List[str]]: Authorized user roles
        :return chunk_count int: Total number of parsed chunks
        """
        parser = ParserFactory.get_parser(filename)
        kwargs = {}
        if allowed_roles:
            kwargs["allowed_roles"] = allowed_roles
        chunks = parser.parse_text(text, filename, **kwargs)
        self.index.add_chunks(chunks)
        return len(chunks)

    def stream_chat(
        self,
        query: str,
        user_role: str = "all",
        session_id: str = "default_session",
    ) -> Generator[str, None, None]:
        """
        Explanation: Executes RBAC-filtered hybrid retrieval, builds grounded context, and streams Gemini tokens
        :param  query str: User prompt or research question
        :param  user_role str: Active security role of requesting user
        :param  session_id str: Conversation identifier for multi-turn history
        :return token Generator[str, None, None]: Real-time stream of response tokens
        """
        # 1. Retrieve & Re-rank
        self.last_retrieved_results = self.index.search(
            query=query,
            user_role=user_role,
            top_k=settings.hybrid_top_k,
            rerank_top_k=settings.rerank_top_k,
        )

        # 2. Format Context
        if self.last_retrieved_results:
            context_blocks = []
            for res in self.last_retrieved_results:
                c = res.chunk
                loc = f"Page {c.page}" if c.page else f"Section: {c.section}"
                context_blocks.append(
                    f"--- Source: {c.source} ({loc}) [Format: {c.file_format.upper()}] ---\n{c.text}"
                )
            context = "\n\n".join(context_blocks)
        else:
            context = "NO MATCHING DOCUMENTS FOUND UNDER CURRENT USER ACCESS ROLE."

        # 3. Stream from Conversational Chain
        for chunk in self.conversational_chain.stream(
            {"input": query, "context": context},
            config={"configurable": {"session_id": session_id}},
        ):
            if chunk.content:
                yield chunk.content

    def clear_history(self, session_id: str = "default_session"):
        """
        Explanation: Clears conversational chat memory for a specified session ID
        :param  session_id str: Session identifier to purge
        :return None: Resets session history in place
        """
        if session_id in self._sessions:
            self._sessions[session_id].clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Explanation: Queries telemetry statistics from underlying enterprise hybrid index
        :return stats Dict[str, Any]: Telemetry map including chunk counts, format distributions, and backend
        """
        return self.index.get_stats()
