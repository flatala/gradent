"""Vector database connection and setup using ChromaDB."""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
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

# Singleton vector store
_vector_store: Optional[Chroma] = None


def get_vector_store(reset: bool = False) -> Chroma:
    """Get or create the vector store.
    
    Args:
        reset: If True, delete existing data and create fresh store
        
    Returns:
        Chroma vector store instance
    """
    global _vector_store
    
    if reset:
        _vector_store = None
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
        
        # Configure ChromaDB settings with telemetry disabled
        chroma_settings = Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
        
        # Create or load vector store
        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(VECTOR_DB_DIR),
            collection_metadata={"hnsw:space": "cosine"},
            client_settings=chroma_settings
        )
        
        print(f"[OK] Vector store initialized at: {VECTOR_DB_DIR}")
    
    return _vector_store


def get_vector_db_path() -> Path:
    """Get the path to the vector database directory."""
    return VECTOR_DB_DIR
