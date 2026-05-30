import pytest
from pathlib import Path
import shutil

def test_build_context_returns_core_and_relevant_chunks(tmp_path, monkeypatch):
    # Set up fake context dirs
    core = tmp_path / "core.md"
    core.write_text("# Core\nI am Abhinav, a kernel developer.")

    detail = tmp_path / "detail"
    detail.mkdir()
    (detail / "skills.md").write_text("## C Skills\nExpert in C, Linux kernel modules.")
    (detail / "hobbies.md").write_text("## Hobbies\nI like hiking and cooking.")

    # Patch the paths used by context.py
    import services.context as ctx_module
    monkeypatch.setattr(ctx_module, "CORE_PATH", core)
    monkeypatch.setattr(ctx_module, "DETAIL_DIR", detail)
    monkeypatch.setattr(ctx_module, "VECTORDB_PATH", str(tmp_path / "vectordb"))

    ctx_module.init_context()
    result = ctx_module.build_context("what C skills do you have?")

    assert "I am Abhinav" in result        # core always present
    assert "kernel modules" in result      # relevant chunk retrieved
