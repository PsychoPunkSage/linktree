import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_mock_collection(docs):
    """Return a mock ChromaDB collection that returns all docs as query results."""
    col = MagicMock()
    col.count.return_value = len(docs)
    col.query.return_value = {"documents": [docs]}
    return col


def _make_mock_client(collection):
    client = MagicMock()
    client.create_collection.return_value = collection
    client.get_collection.return_value = collection
    return client


def test_build_context_returns_core_and_relevant_chunks(tmp_path, monkeypatch):
    core = tmp_path / "core.md"
    core.write_text("# Core\nI am Abhinav, a kernel developer.")

    detail = tmp_path / "detail"
    detail.mkdir()
    (detail / "skills.md").write_text("## C Skills\nExpert in C, Linux kernel modules.")
    (detail / "hobbies.md").write_text("## Hobbies\nI like hiking and cooking.")

    expected_docs = ["## C Skills\nExpert in C, Linux kernel modules.", "## Hobbies\nI like hiking and cooking."]
    mock_collection = _make_mock_collection(expected_docs)
    mock_client = _make_mock_client(mock_collection)

    # Mock chromadb entirely so this test doesn't need ML packages
    with patch.dict("sys.modules", {"chromadb": MagicMock(), "chromadb.utils": MagicMock(), "chromadb.utils.embedding_functions": MagicMock()}):
        import importlib
        import services.context as ctx_module
        importlib.reload(ctx_module)

        monkeypatch.setattr(ctx_module, "CORE_PATH", core)
        monkeypatch.setattr(ctx_module, "DETAIL_DIR", detail)
        monkeypatch.setattr(ctx_module, "VECTORDB_PATH", str(tmp_path / "vectordb"))

        with patch("chromadb.PersistentClient", return_value=mock_client):
            ctx_module.init_context()

        ctx_module._collection = mock_collection
        result = ctx_module.build_context("what C skills do you have?")

    assert "I am Abhinav" in result
    assert "kernel modules" in result
