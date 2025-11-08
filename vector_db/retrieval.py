"""Retrieval utilities for semantic search in vector database."""
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document

from .connection import get_vector_store


def retrieve_assignment_context(
    query: str,
    assignment_id: Optional[int] = None,
    course_id: Optional[int] = None,
    user_id: Optional[int] = None,
    top_k: int = 5,
    source_types: Optional[List[str]] = None
) -> str:
    """Retrieve relevant context for an assignment from vector store.
    
    Args:
        query: Search query (e.g., assignment title + description)
        assignment_id: Filter by specific assignment ID
        course_id: Filter by course ID
        user_id: Filter by user ID
        top_k: Number of chunks to retrieve
        source_types: Filter by source types (e.g., ['assignment', 'rubric'])
        
    Returns:
        Formatted string with retrieved context
    """
    vector_store = get_vector_store()
    
    # Build filter - ChromaDB requires specific where clause format
    # Multiple conditions need to be combined with $and
    conditions = []
    
    if assignment_id is not None:
        conditions.append({"assignment_id": {"$eq": assignment_id}})
    if course_id is not None:
        conditions.append({"course_id": {"$eq": course_id}})
    if user_id is not None:
        conditions.append({"user_id": {"$eq": user_id}})
    if source_types and len(source_types) == 1:
        conditions.append({"source_type": {"$eq": source_types[0]}})
    elif source_types and len(source_types) > 1:
        # For multiple source types, use $or
        source_conditions = [{"source_type": {"$eq": st}} for st in source_types]
        conditions.append({"$or": source_conditions})
    
    # Combine conditions
    if len(conditions) > 1:
        filter_dict = {"$and": conditions}
    elif len(conditions) == 1:
        filter_dict = conditions[0]
    else:
        filter_dict = None
    
    # Perform similarity search
    if filter_dict:
        results = vector_store.similarity_search(
            query,
            k=top_k,
            filter=filter_dict
        )
    else:
        results = vector_store.similarity_search(query, k=top_k)
    
    if not results:
        return "No relevant context found in course materials."
    
    # Format results
    context_parts = []
    for i, doc in enumerate(results, 1):
        metadata = doc.metadata
        source_info = f"Source: {metadata.get('source_type', 'unknown')}"
        if 'doc_id' in metadata:
            source_info += f" ({metadata['doc_id']})"
        if 'page_number' in metadata:
            source_info += f", Page {metadata['page_number']}"
        
        context_parts.append(
            f"--- Context {i} ({source_info}) ---\n{doc.page_content}\n"
        )
    
    return "\n".join(context_parts)


def search_documents(
    query: str,
    top_k: int = 10,
    **filter_kwargs
) -> List[Document]:
    """Generic document search with filters.
    
    Args:
        query: Search query
        top_k: Number of results to return
        **filter_kwargs: Metadata filters (user_id, course_id, source_type, etc.)
        
    Returns:
        List of matching documents
    """
    vector_store = get_vector_store()
    
    if filter_kwargs:
        return vector_store.similarity_search(
            query,
            k=top_k,
            filter=filter_kwargs
        )
    else:
        return vector_store.similarity_search(query, k=top_k)


def get_collection_stats() -> Dict[str, Any]:
    """Get statistics about the vector database collection.
    
    Returns:
        Dictionary with collection statistics
    """
    vector_store = get_vector_store()
    collection = vector_store._collection
    
    count = collection.count()
    
    # Sample some documents to get metadata fields
    if count > 0:
        sample = collection.peek(limit=min(10, count))
        metadata_fields = set()
        source_types = set()
        
        for metadata in sample.get('metadatas', []):
            metadata_fields.update(metadata.keys())
            if 'source_type' in metadata:
                source_types.add(metadata['source_type'])
        
        return {
            "total_chunks": count,
            "metadata_fields": sorted(metadata_fields),
            "source_types": sorted(source_types),
        }
    
    return {
        "total_chunks": 0,
        "metadata_fields": [],
        "source_types": [],
    }
