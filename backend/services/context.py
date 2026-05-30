import hashlib
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import re

CORE_PATH   = Path("data/context/core.md")
DETAIL_DIR  = Path("data/context/detail")
VECTORDB_PATH = "data/vectordb"

_collection = None

def _compute_hash() -> str:
    h = hashlib.sha256()
    for f in sorted(DETAIL_DIR.glob("*.md")):
        h.update(f.read_bytes())
    return h.hexdigest()

def _chunk_markdown(text: str) -> list[str]:
    """Split on ## headers; return non-empty chunks."""
    chunks = re.split(r'\n(?=## )', text.strip())
    return [c.strip() for c in chunks if c.strip()]

def init_context():
    global _collection
    ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=str(VECTORDB_PATH))
    hash_file = Path(VECTORDB_PATH) / "context.hash"

    current_hash = _compute_hash()
    stored_hash  = hash_file.read_text().strip() if hash_file.exists() else ""

    if current_hash != stored_hash:
        # Context files changed — rebuild collection
        try:
            client.delete_collection("context")
        except Exception:
            pass
        collection = client.create_collection("context", embedding_function=ef)

        all_ids, all_docs = [], []
        for f in sorted(DETAIL_DIR.glob("*.md")):
            for i, chunk in enumerate(_chunk_markdown(f.read_text())):
                all_ids.append(f"{f.stem}-{i}")
                all_docs.append(chunk)

        if all_ids:
            collection.add(ids=all_ids, documents=all_docs)

        hash_file.parent.mkdir(parents=True, exist_ok=True)
        hash_file.write_text(current_hash)
        _collection = collection
    else:
        _collection = client.get_collection("context", embedding_function=ef)

def build_context(question: str) -> str:
    core = CORE_PATH.read_text()

    if _collection is None or _collection.count() == 0:
        return core

    results = _collection.query(query_texts=[question], n_results=5)
    chunks  = results["documents"][0] if results["documents"] else []
    detail  = "\n\n---\n\n".join(chunks)
    return f"{core}\n\n---\n\n{detail}" if detail else core
