"""Vector database connection and setup using ChromaDB."""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import chromadb
from chromadb.config import Settings

# Load environment variables
load_dotenv()

# Disable ChromaDB telemetry to suppress warnings
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Vector DB path - in the data directory
VECTOR_DB_DIR = Path(__file__).parent.parent / "data" / "vector_db"
VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

# Override with environment variable if provided
if os.getenv("VECTOR_DB_PATH"):
    VECTOR_DB_DIR = Path(os.getenv("VECTOR_DB_PATH"))

# Collection name
COLLECTION_NAME = "course_materials"

# Singleton vector store and client
_vector_store: Optional[Chroma] = None
_chroma_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Get or create the persistent ChromaDB client."""
    global _chroma_client

    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=str(VECTOR_DB_DIR),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

    return _chroma_client


def get_vector_store(reset: bool = False) -> Chroma:
    """Get or create the vector store.

    Args:
        reset: If True, delete existing data and create fresh store

    Returns:
        Chroma vector store instance
    """
    global _vector_store, _chroma_client

    if reset:
        _vector_store = None
        _chroma_client = None
        # Delete existing data
        if VECTOR_DB_DIR.exists():
            import shutil
            shutil.rmtree(VECTOR_DB_DIR)
            VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

    if _vector_store is None:
        # Create embeddings
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small"  # Cheaper and faster
        )

        # Get persistent client
        client = get_chroma_client()

        # Create or load vector store
        _vector_store = Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            collection_metadata={"hnsw:space": "cosine"}
        )

        print(f"[OK] Vector store initialized at: {VECTOR_DB_DIR}")

    return _vector_store


def get_vector_db_path() -> Path:
    """Get the path to the vector database directory."""
    return VECTOR_DB_DIR
