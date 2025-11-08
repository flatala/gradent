"""Vector database package for semantic search over course materials."""
from .connection import get_vector_store, get_vector_db_path
from .ingestion import ingest_document, ingest_text_chunks
from .retrieval import retrieve_assignment_context

__all__ = [
    "get_vector_store",
    "get_vector_db_path",
    "ingest_document",
    "ingest_text_chunks",
    "retrieve_assignment_context",
]
