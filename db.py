"""SQLite database layer for Tomo."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from tomo.exceptions import DatabaseError

SCHEMA_VERSION = 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pet_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dir_type_map (
    pattern TEXT PRIMARY KEY,
    type_name TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    confirmed_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS growth_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    description TEXT,
    triggered_by TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_stats (
    date TEXT PRIMARY KEY,
    session_count INTEGER DEFAULT 0,
    total_calls INTEGER DEFAULT 0,
    skill_calls INTEGER DEFAULT 0,
    tool_breakdown TEXT,
    detected_type TEXT,
    llm_calls INTEGER DEFAULT 0,
    llm_failures INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    category TEXT DEFAULT "fact",
    importance INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0
);
"""

DEFAULT_PET_STATE = {
    "level": "1",
    "stage": "egg",
    "exp": "0",
    "energy": "100",
    "mood": "neutral",
    "satiation": "100",
    "total_sessions": "0",
    "total_calls": "0",
    "unlocked_achievements": "[]",
    "achievement_times": "{}",
    "affinity": "0",
}


class Database:
    """SQLite database for Tomo pet state and activity tracking."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseError(f"Cannot create database directory: {exc}") from exc
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(SCHEMA)
                conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to initialize database: {exc}") from exc
        # Enable WAL mode for better concurrent read/write performance
        self._execute("PRAGMA journal_mode=WAL", commit=True)
        self._migrate()
        self._ensure_default_state()

    def _migrate(self) -> None:
        """Run database migrations if needed."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT version FROM schema_version WHERE id = 1")
                row = cursor.fetchone()
                current_version = row[0] if row else 0
        except sqlite3.Error:
            current_version = 0

        if current_version >= SCHEMA_VERSION:
            return

        # Run migrations sequentially
        for version in range(current_version + 1, SCHEMA_VERSION + 1):
            self._apply_migration(version)

        # Update schema version
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO schema_version (id, version)
                    VALUES (1, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        version = excluded.version,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (SCHEMA_VERSION,),
                )
                conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to update schema version: {exc}") from exc

    def _apply_migration(self, version: int) -> None:
        """Apply a single migration."""
        if version == 2:
            # Add llm_calls and llm_failures to daily_stats
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("ALTER TABLE daily_stats ADD COLUMN llm_calls INTEGER DEFAULT 0")
                    conn.execute(
                        "ALTER TABLE daily_stats ADD COLUMN llm_failures INTEGER DEFAULT 0"
                    )
                    conn.commit()
            except sqlite3.OperationalError:
                pass  # Columns already exist

        if version == 3:
            # Add memory table and affinity default
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS memory (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            key TEXT UNIQUE NOT NULL,
                            value TEXT NOT NULL,
                            category TEXT DEFAULT "fact",
                            importance INTEGER DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            access_count INTEGER DEFAULT 0
                        )
                        """
                    )
                    conn.commit()
            except sqlite3.OperationalError:
                pass

    def _ensure_default_state(self) -> None:
        for key, value in DEFAULT_PET_STATE.items():
            if self.get_pet_state(key) is None:
                self.set_pet_state(key, value)

    def _execute(
        self,
        sql: str,
        parameters: tuple[Any, ...] = (),
        *,
        fetch_one: bool = False,
        fetch_all: bool = False,
        commit: bool = False,
    ) -> sqlite3.Row | list[sqlite3.Row] | None:
        """Execute SQL with unified error handling."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(sql, parameters)
                if commit:
                    conn.commit()
                if fetch_one:
                    return cursor.fetchone()
                if fetch_all:
                    return cursor.fetchall()
                return None
        except sqlite3.Error as exc:
            raise DatabaseError(f"Database error: {exc}") from exc

    def list_tables(self) -> list[str]:
        """Return a list of table names in the database."""
        rows = self._execute(
            "SELECT name FROM sqlite_master WHERE type='table'",
            fetch_all=True,
        )
        return [row["name"] for row in rows] if rows else []

    def get_pet_state(self, key: str) -> str | None:
        """Get a single pet state value by key."""
        row = self._execute(
            "SELECT value FROM pet_state WHERE key = ?",
            (key,),
            fetch_one=True,
        )
        return str(row[0]) if row else None

    def set_pet_state(self, key: str, value: str) -> None:
        """Set a single pet state value."""
        self._execute(
            """
            INSERT INTO pet_state (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
            commit=True,
        )

    def get_all_pet_state(self) -> dict[str, str]:
        """Get all pet state as a dictionary."""
        rows = self._execute(
            "SELECT key, value FROM pet_state",
            fetch_all=True,
        )
        return {row["key"]: row["value"] for row in rows} if rows else {}

    def upsert_dir_type(self, pattern: str, type_name: str, confidence: float) -> None:
        """Insert or update a directory type mapping."""
        self._execute(
            """
            INSERT INTO dir_type_map (pattern, type_name, confidence)
            VALUES (?, ?, ?)
            ON CONFLICT(pattern) DO UPDATE SET
                type_name = excluded.type_name,
                confidence = excluded.confidence
            """,
            (pattern, type_name, confidence),
            commit=True,
        )

    def get_dir_type_mappings(self) -> list[dict[str, Any]]:
        """Get all directory type mappings ordered by confidence."""
        rows = self._execute(
            "SELECT * FROM dir_type_map ORDER BY confidence DESC",
            fetch_all=True,
        )
        return [dict(row) for row in rows] if rows else []

    def detect_type_from_cwd(self, cwd: str) -> tuple[str | None, float]:
        """Detect work type from current working directory."""
        mappings = self.get_dir_type_mappings()
        for mapping in mappings:
            if mapping["pattern"].strip("%") in cwd:
                return mapping["type_name"], mapping["confidence"]
        return None, 0.0

    def log_growth_event(
        self,
        event_type: str,
        description: str,
        triggered_by: dict[str, Any] | None = None,
    ) -> None:
        """Log a growth event."""
        self._execute(
            """
            INSERT INTO growth_log (event_type, description, triggered_by)
            VALUES (?, ?, ?)
            """,
            (event_type, description, json.dumps(triggered_by) if triggered_by else None),
            commit=True,
        )

    def get_growth_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent growth logs."""
        rows = self._execute(
            "SELECT * FROM growth_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
            fetch_all=True,
        )
        return [dict(row) for row in rows] if rows else []

    def get_exp_history(self, limit: int = 30) -> list[dict[str, Any]]:
        """Get sync events with parsed exp info for growth visualization."""
        rows = self._execute(
            "SELECT timestamp, description FROM growth_log "
            "WHERE event_type = 'sync' AND description LIKE '%Exp +%' "
            "ORDER BY timestamp DESC LIMIT ?",
            (limit,),
            fetch_all=True,
        )
        if not rows:
            return []
        import re

        history = []
        for row in rows:
            desc = row["description"]
            match = re.search(r"Exp \+(\d+)", desc)
            if match:
                history.append(
                    {
                        "timestamp": row["timestamp"],
                        "exp_gained": int(match.group(1)),
                    }
                )
        return list(reversed(history))

    def get_daily_stats(self, date: str) -> dict[str, Any] | None:
        """Get daily stats for a specific date."""
        row = self._execute(
            "SELECT * FROM daily_stats WHERE date = ?",
            (date,),
            fetch_one=True,
        )
        if row is None:
            return None
        # fetch_one=True guarantees a single Row, not a list
        row_single: sqlite3.Row = row  # type: ignore[assignment]
        return {k: row_single[k] for k in row_single.keys()}

    def upsert_daily_stats(
        self,
        date: str,
        session_count: int = 0,
        total_calls: int = 0,
        skill_calls: int = 0,
        tool_breakdown: dict[str, Any] | None = None,
        detected_type: str | None = None,
        llm_calls: int = 0,
        llm_failures: int = 0,
    ) -> None:
        """Insert or update daily statistics."""
        self._execute(
            """
            INSERT INTO daily_stats (
                date, session_count, total_calls, skill_calls,
                tool_breakdown, detected_type, llm_calls, llm_failures
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                session_count = excluded.session_count,
                total_calls = excluded.total_calls,
                skill_calls = excluded.skill_calls,
                tool_breakdown = excluded.tool_breakdown,
                detected_type = excluded.detected_type,
                llm_calls = excluded.llm_calls,
                llm_failures = excluded.llm_failures
            """,
            (
                date,
                session_count,
                total_calls,
                skill_calls,
                json.dumps(tool_breakdown) if tool_breakdown else None,
                detected_type,
                llm_calls,
                llm_failures,
            ),
            commit=True,
        )

    def get_chat_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent chat history entries ordered oldest-first."""
        rows = self._execute(
            "SELECT role, content, timestamp FROM chat_history ORDER BY id DESC LIMIT ?",
            (limit,),
            fetch_all=True,
        )
        if not rows:
            return []
        return [
            {"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]}
            for row in reversed(rows)
        ]

    def add_chat_entry(self, role: str, content: str) -> None:
        """Append a chat entry to the history."""
        self._execute(
            "INSERT INTO chat_history (role, content) VALUES (?, ?)",
            (role, content),
            commit=True,
        )

    def clear_chat_history(self) -> None:
        """Delete all chat history."""
        self._execute("DELETE FROM chat_history", commit=True)

    # ------------------------------------------------------------------ #
    # Achievement state (fast path, avoids scanning growth_log)
    # ------------------------------------------------------------------ #

    def get_unlocked_achievement_keys(self) -> set[str]:
        """Return set of already-unlocked achievement keys from pet_state."""
        raw = self.get_pet_state("unlocked_achievements")
        if not raw:
            return set()
        try:
            return set(json.loads(raw))
        except json.JSONDecodeError:
            return set()

    def unlock_achievement(self, key: str) -> None:
        """Add an achievement key to the unlocked set and record unlock time."""
        keys = self.get_unlocked_achievement_keys()
        if key in keys:
            return
        keys.add(key)
        self.set_pet_state("unlocked_achievements", json.dumps(sorted(keys)))
        # Record unlock timestamp
        times = self.get_achievement_times()
        from datetime import datetime

        times[key] = datetime.now().isoformat()
        self.set_pet_state("achievement_times", json.dumps(times))

    def get_achievement_times(self) -> dict[str, str]:
        """Return dict of achievement_key -> unlock_timestamp."""
        raw = self.get_pet_state("achievement_times")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    # ------------------------------------------------------------------ #
    # Memory system
    # ------------------------------------------------------------------ #

    def set_memory(
        self,
        key: str,
        value: str,
        category: str = "fact",
        importance: int = 1,
    ) -> None:
        """Store a memory entry."""
        self._execute(
            """
            INSERT INTO memory (key, value, category, importance)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                category = excluded.category,
                importance = excluded.importance,
                last_accessed = CURRENT_TIMESTAMP,
                access_count = access_count + 1
            """,
            (key, value, category, importance),
            commit=True,
        )

    def get_memory(self, key: str) -> dict[str, Any] | None:
        """Retrieve a single memory by key."""
        row = self._execute(
            "SELECT * FROM memory WHERE key = ?",
            (key,),
            fetch_one=True,
        )
        if row:
            self._execute(
                """
                UPDATE memory
                SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE key = ?
                """,
                (key,),
                commit=True,
            )
            return dict(row)
        return None

    def get_memories(
        self,
        category: str | None = None,
        limit: int = 50,
        order_by: str = "last_accessed DESC",
    ) -> list[dict[str, Any]]:
        """Retrieve memories, optionally filtered by category."""
        if category:
            sql = f"SELECT * FROM memory WHERE category = ? ORDER BY {order_by} LIMIT ?"
            rows = self._execute(sql, (category, limit), fetch_all=True)
        else:
            sql = f"SELECT * FROM memory ORDER BY {order_by} LIMIT ?"
            rows = self._execute(sql, (limit,), fetch_all=True)
        return [dict(row) for row in rows] if rows else []

    def delete_memory(self, key: str) -> bool:
        """Delete a memory by key. Returns True if deleted."""
        self._execute(
            "DELETE FROM memory WHERE key = ?",
            (key,),
            commit=True,
        )
        return self.get_memory(key) is None

    def clear_memories(self, category: str | None = None) -> None:
        """Delete all memories, optionally filtered by category."""
        if category:
            self._execute(
                "DELETE FROM memory WHERE category = ?",
                (category,),
                commit=True,
            )
        else:
            self._execute("DELETE FROM memory", commit=True)

    def search_memories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search memories by key or value content."""
        pattern = f"%{query}%"
        rows = self._execute(
            """
            SELECT * FROM memory
            WHERE key LIKE ? OR value LIKE ?
            ORDER BY importance DESC, last_accessed DESC
            LIMIT ?
            """,
            (pattern, pattern, limit),
            fetch_all=True,
        )
        return [dict(row) for row in rows] if rows else []
