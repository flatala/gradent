"""Document ingestion utilities for vector database."""
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from .connection import get_vector_store


def create_text_splitter(chunk_size: int = 1000, chunk_overlap: int = 200) -> RecursiveCharacterTextSplitter:
    """Create a text splitter for chunking documents.
    
    Args:
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks for context
        
    Returns:
        Text splitter instance
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )


def ingest_text_chunks(
    text: str,
    metadata: Dict[str, Any],
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[str]:
    """Ingest text by chunking and adding to vector store.
    
    Args:
        text: Text content to ingest
        metadata: Metadata for all chunks (user_id, course_id, doc_id, etc.)
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of document IDs added to vector store
    """
    if not text or not text.strip():
        return []
    
    # Create text splitter
    text_splitter = create_text_splitter(chunk_size, chunk_overlap)
    
    # Split text into chunks
    chunks = text_splitter.split_text(text)
    
    # Create documents with metadata
    documents = []
    for i, chunk in enumerate(chunks):
        doc_metadata = {
            **metadata,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        documents.append(Document(page_content=chunk, metadata=doc_metadata))
    
    # Add to vector store
    vector_store = get_vector_store()
    ids = vector_store.add_documents(documents)
    
    print(f"✓ Ingested {len(chunks)} chunks for {metadata.get('doc_id', 'unknown')}")
    
    return ids


def ingest_document(
    text: str,
    doc_id: str,
    source_type: str,
    user_id: Optional[int] = None,
    course_id: Optional[int] = None,
    assignment_id: Optional[int] = None,
    additional_metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[str]:
    """Ingest a complete document into the vector store.
    
    Args:
        text: Document text content
        doc_id: Unique identifier for this document
        source_type: Type of document (e.g., 'assignment', 'lecture', 'rubric')
        user_id: User ID this document belongs to
        course_id: Course ID this document belongs to
        assignment_id: Assignment ID if this is assignment-related
        additional_metadata: Any additional metadata to store
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of document IDs added to vector store
    """
    # Build metadata
    metadata = {
        "doc_id": doc_id,
        "source_type": source_type,
    }
    
    if user_id is not None:
        metadata["user_id"] = user_id
    if course_id is not None:
        metadata["course_id"] = course_id
    if assignment_id is not None:
        metadata["assignment_id"] = assignment_id
    
    if additional_metadata:
        metadata.update(additional_metadata)
    
    # Ingest text chunks
    return ingest_text_chunks(text, metadata, chunk_size, chunk_overlap)


def ingest_file(
    file_path: Path,
    doc_id: str,
    source_type: str,
    **kwargs
) -> List[str]:
    """Ingest a text file into the vector store.
    
    Args:
        file_path: Path to the file
        doc_id: Unique identifier for this document
        source_type: Type of document
        **kwargs: Additional arguments passed to ingest_document
        
    Returns:
        List of document IDs added to vector store
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Read file content
    text = file_path.read_text(encoding='utf-8')
    
    # Add file metadata
    kwargs.setdefault("additional_metadata", {})
    kwargs["additional_metadata"]["file_name"] = file_path.name
    kwargs["additional_metadata"]["file_path"] = str(file_path)
    
    # Ingest document
    return ingest_document(text, doc_id, source_type, **kwargs)
