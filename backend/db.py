import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path("data/portfolio.db")

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            ip TEXT,
            country TEXT,
            city TEXT,
            referrer TEXT,
            user_agent TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            inferred_type TEXT,
            inferred_company TEXT,
            technical_level TEXT,
            inferred_intent TEXT,
            confidence REAL,
            inference_notes TEXT,
            profile_updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS chat_logs (
            id TEXT PRIMARY KEY,
            session_id TEXT REFERENCES sessions(id),
            question TEXT,
            response TEXT,
            model_used TEXT,
            tokens_used INTEGER,
            response_ms INTEGER,
            flagged INTEGER DEFAULT 0,
            flag_reason TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_logs(session_id);
        CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_session_created ON sessions(created_at);
        """)

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def upsert_session(session_id: str, ip: str, referrer: str, user_agent: str):
    with get_conn() as conn:
        conn.execute("""
        INSERT OR IGNORE INTO sessions (id, ip, referrer, user_agent)
        VALUES (?, ?, ?, ?)
        """, (session_id, ip, referrer, user_agent))

def insert_chat_log(
    log_id: str, session_id: str, question: str, response: str,
    model_used: str, tokens_used: int, response_ms: int,
    flagged: bool = False, flag_reason: str = ""
):
    with get_conn() as conn:
        conn.execute("""
        INSERT INTO chat_logs
          (id, session_id, question, response, model_used,
           tokens_used, response_ms, flagged, flag_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (log_id, session_id, question, response, model_used,
              tokens_used, response_ms, int(flagged), flag_reason))

def update_session_profile(
    session_id: str, inferred_type: str, inferred_company: str,
    technical_level: str, inferred_intent: str,
    confidence: float, inference_notes: str
):
    with get_conn() as conn:
        conn.execute("""
        UPDATE sessions SET
            inferred_type = ?, inferred_company = ?, technical_level = ?,
            inferred_intent = ?, confidence = ?, inference_notes = ?,
            profile_updated_at = datetime('now')
        WHERE id = ?
        """, (inferred_type, inferred_company, technical_level,
              inferred_intent, confidence, inference_notes, session_id))

def get_recent_sessions(limit: int = 20) -> list:
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT s.*, COUNT(c.id) as question_count
        FROM sessions s
        LEFT JOIN chat_logs c ON c.session_id = s.id
        GROUP BY s.id
        ORDER BY s.created_at DESC
        LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]

def get_top_questions(days: int = 7, limit: int = 10) -> list:
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT question, COUNT(*) as count
        FROM chat_logs
        WHERE created_at >= datetime('now', ?)
          AND flagged = 0
        GROUP BY question
        ORDER BY count DESC
        LIMIT ?
        """, (f"-{days} days", limit)).fetchall()
    return [dict(r) for r in rows]

def get_stats_today() -> dict:
    with get_conn() as conn:
        visitors = conn.execute("""
        SELECT COUNT(DISTINCT id) FROM sessions
        WHERE created_at >= date('now')
        """).fetchone()[0]
        questions = conn.execute("""
        SELECT COUNT(*) FROM chat_logs
        WHERE created_at >= date('now')
        """).fetchone()[0]
        flagged = conn.execute("""
        SELECT COUNT(*) FROM chat_logs
        WHERE created_at >= date('now') AND flagged = 1
        """).fetchone()[0]
        model_counts = conn.execute("""
        SELECT model_used, COUNT(*) as cnt, AVG(response_ms) as avg_ms
        FROM chat_logs WHERE created_at >= date('now')
        GROUP BY model_used
        """).fetchall()
    return {
        "visitors": visitors,
        "questions": questions,
        "flagged": flagged,
        "models": [dict(r) for r in model_counts]
    }

def get_referrer_breakdown(days: int = 7) -> list:
    with get_conn() as conn:
        rows = conn.execute("""
        SELECT referrer, COUNT(*) as count
        FROM sessions
        WHERE created_at >= datetime('now', ?)
        GROUP BY referrer
        ORDER BY count DESC
        """, (f"-{days} days",)).fetchall()
    return [dict(r) for r in rows]
