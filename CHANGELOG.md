## v0.6.0 — 2026-06-17

### Fixed
- SLM hallucination: model now receives RAG-retrieved context chunks at inference time instead of answering from weights alone
- `n_ctx` bumped from 2048 → 4096 on Modal to accommodate context

### Changed
- `modal/app.py`: accepts `context` in request body; builds `"Context:\n{ctx}\n\nQuestion: {q}"` user message when context present; falls back to question-only when empty
- `services/slm.py`: `stream_from_slm()` now accepts `context` param and passes it to Modal endpoint
- `routers/chat.py`: SLM branch now calls `build_context()` and passes `groq_ctx` (trimmed) to SLM — same RAG pipeline Gemini uses
- `modal/app.py` SYSTEM_PROMPT: instructs model to answer from context only, not memory


## v0.5.0 — 2026-06-17

### Changed
- System prompt rewritten in first person — chatbot now speaks as Abhinav ("I", "me", "my") instead of third-person narrator
- HARD_RESPONSE and SOFT_RESPONSE updated to first-person voice
- HARD_RESPONSE sharpened: "Not a chance. Try asking something worth my time."
- System prompt instructs model to shut down rude/invasive questions bluntly and without apology

### Added
- Relationship/personal life questions added to HARD_PATTERNS (girlfriend, boyfriend, dating, single, married, hook up, etc.)
- More sexual/explicit terms added to HARD_PATTERNS (dick, cock, pussy, rape, horny, etc.)
- Jailbreak phrases added to HARD_PATTERNS (pretend you are, forget your instructions, dan mode, developer mode, etc.)
- FILTER_PROMPT tightened: defaults to SOFT on ambiguity; general knowledge/coding help/random topics explicitly classified as SOFT
- Relationship and invasive personal questions explicitly classified as HARD in filter prompt

### Fixed
- Off-topic questions (general knowledge, coding help, jokes, etc.) no longer slip through as PASS — filter now defaults to SOFT when in doubt


## v0.4.0 — 2026-06-13

### Added
- Modal SLM integration: HTTP client service (`services/slm.py`) for SLM-first routing
- SLM-first routing logic in chat endpoint — falls back to Gemini/Groq if Modal unavailable
- Modal endpoint and enablement fields added to config and `.env`
- Async stream generator for Modal SLM to fix token buffering caused by sync I/O blocking event loop

### Fixed
- Database file added to `.gitignore` to resolve deployment merge conflicts
- Stream function converted from sync to async to unblock FastAPI event loop


## v0.3.0 — 2026-06-10 — 2026-06-11

### Added
- SLM fine-tuning pipeline: Qwen2.5-3B-Instruct via Unsloth + QLoRA (`training/`)
- QA dataset (`training/qa_dataset.jsonl`) — 370 Q&A pairs
- GGUF export pipeline with robust file discovery

### Fixed
- Responsive UI overflow on mobile and tablet viewports
- Dynamic viewport height (`dvh`) unit for mobile browser UI compatibility
- Safe-area-inset support for notch/Dynamic Island avoidance
- Viewport-fit=cover for full notch and safe-area control

### Changed
- Optimised responsive spacing and padding across mobile, tablet, and desktop breakpoints


## v0.2.0 — 2026-06-08 — 2026-06-09

### Added
- Deploy script pre-flight validation with environment checks and helpful error messaging
- Caddyfile reverse proxy configuration for `api.psychopunksage.dev`

### Fixed
- Shell variable naming conflict with read-only `UID` and `GID` in deploy script
- Frontend API endpoint reverted to production URL after local testing


## v0.1.0 — 2026-05-29

- Initial release
