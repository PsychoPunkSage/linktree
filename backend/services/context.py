import hashlib
import subprocess
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import re

CORE_PATH   = Path("data/context/core.md")
DETAIL_DIR  = Path("data/context/detail")
VECTORDB_PATH = "data/vectordb"

# Maps file stems to keywords that suggest the user wants the full file
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "experience": [
        "experience", "work", "job", "career", "company", "employer",
        "role", "position", "worked", "employed", "internship", "full-time",
        "part-time", "tenure", "history", "background", "previous", "client", "clients",
    ],
    "projects": [
        "project", "projects", "built", "created", "made", "developed",
        "repo", "repository", "github", "code", "portfolio", "side project",
        "open source", "open-source", "app", "application", "applications", "tool", "tools",
    ],
    "skills": [
        "skill", "skills", "language", "languages", "stack", "technology",
        "technologies", "know", "familiar", "proficient", "expertise",
        "tools", "framework", "frameworks", "tech", "backend", "frontend",
        "python", "rust", "golang", "typescript",
    ],
    "setup": [
        "setup", "config", "configuration", "machine", "workflow", "tool",
        "editor", "vim", "neovim", "arch", "linux", "dotfiles", "environment",
        "workstation", "desktop", "os", "terminal", "shell", "tmux", "window manager", "wm",
    ],
}

_collection = None

def _detail_files(key: str) -> list[Path]:
    if key:
        files = sorted(DETAIL_DIR.glob("*.md.enc"))
        if files:
            return files
    return sorted(DETAIL_DIR.glob("*.md"))

def _read_detail_file(path: Path, key: str) -> str:
    if key and path.suffix == ".enc":
        result = subprocess.run(
            ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-k", key],
            input=path.read_bytes(),
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Decryption failed for {path}: {result.stderr.decode()}")
        return result.stdout.decode()
    return path.read_text()

def _file_stem(path: Path) -> str:
    name = path.name
    if name.endswith(".md.enc"):
        return name[: -len(".md.enc")]
    return path.stem

def _compute_hash(key: str) -> str:
    h = hashlib.sha256()
    for f in _detail_files(key):
        h.update(f.read_bytes())
    return h.hexdigest()

def _chunk_markdown(text: str) -> list[str]:
    """Split on ## headers; return non-empty chunks."""
    chunks = re.split(r'\n(?=## )', text.strip())
    return [c.strip() for c in chunks if c.strip()]

def _detect_topics(question: str) -> list[str]:
    """Return list of file stems whose full content should be injected."""
    q = question.lower()
    return [stem for stem, kws in TOPIC_KEYWORDS.items() if any(kw in q for kw in kws)]


def _get_topic_chunks(stem: str) -> list[str]:
    """Return all chunks for a file stem, sorted by their position in the source file."""
    if _collection is None:
        return []
    results = _collection.get(where={"source": stem}, include=["documents", "metadatas"], limit=1000)
    if not results["documents"]:
        return []
    paired = list(zip(results["metadatas"], results["documents"]))
    paired.sort(key=lambda x: x[0]["chunk_index"])
    return [doc for _, doc in paired]

def init_context():
    from config import settings
    global _collection
    key = settings.context_encryption_key
    ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=str(VECTORDB_PATH))
    hash_file = Path(VECTORDB_PATH) / "context.hash"

    current_hash = _compute_hash(key)
    stored_hash  = hash_file.read_text().strip() if hash_file.exists() else ""

    if current_hash != stored_hash:
        try:
            client.delete_collection("context")
        except Exception:
            pass
        collection = client.create_collection("context", embedding_function=ef)

        all_ids, all_docs, all_metas = [], [], []
        for f in _detail_files(key):
            stem = _file_stem(f)
            for i, chunk in enumerate(_chunk_markdown(_read_detail_file(f, key))):
                all_ids.append(f"{stem}-{i}")
                all_docs.append(chunk)
                all_metas.append({"source": stem, "chunk_index": i})

        if all_ids:
            collection.add(ids=all_ids, documents=all_docs, metadatas=all_metas)

        hash_file.parent.mkdir(parents=True, exist_ok=True)
        hash_file.write_text(current_hash)
        _collection = collection
    else:
        _collection = client.get_collection("context", embedding_function=ef)
        # One-time migration: rebuild if existing chunks lack source metadata
        sample = _collection.get(limit=1, include=["metadatas"])
        first_meta = sample["metadatas"][0] if sample["metadatas"] else None
        if first_meta is None or "source" not in first_meta:
            try:
                client.delete_collection("context")
            except Exception:
                pass
            collection = client.create_collection("context", embedding_function=ef)
            all_ids, all_docs, all_metas = [], [], []
            for f in _detail_files(key):
                stem = _file_stem(f)
                for i, chunk in enumerate(_chunk_markdown(_read_detail_file(f, key))):
                    all_ids.append(f"{stem}-{i}")
                    all_docs.append(chunk)
                    all_metas.append({"source": stem, "chunk_index": i})
            if all_ids:
                collection.add(ids=all_ids, documents=all_docs, metadatas=all_metas)
            hash_file.write_text(current_hash)
            _collection = collection

def _build_semantic_context(question: str) -> str:
    """Semantic search context only — used as Groq fallback when topic injection is too large.
    Intentionally limited to 3 chunks to stay within Groq free-tier TPM limits.
    """
    core = CORE_PATH.read_text()
    if _collection is None or _collection.count() == 0:
        return core
    n = min(3, _collection.count())
    results = _collection.query(query_texts=[question], n_results=n)
    chunks  = results["documents"][0] if results["documents"] else []
    detail  = "\n\n---\n\n".join(chunks)
    return f"{core}\n\n---\n\n{detail}" if detail else core

def build_context(question: str) -> tuple[str, str]:
    """Return (gemini_context, groq_context).

    gemini_context: full topic-file injection when a topic is detected (large, Gemini can handle it).
    groq_context: semantic search result (small, safe for Groq free tier).
    Both are always populated so callers can choose based on which backend is responding.
    """
    core = CORE_PATH.read_text()
    groq_context = _build_semantic_context(question)

    topics = _detect_topics(question)
    if topics:
        parts = []
        for stem in topics:
            chunks = _get_topic_chunks(stem)
            if chunks:
                parts.append("\n\n".join(chunks))
        if parts:
            gemini_context = core + "\n\n---\n\n" + "\n\n---\n\n".join(parts)
            return gemini_context, groq_context
        return core, groq_context

    return groq_context, groq_context
