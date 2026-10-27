"""
Reelbox - Database layer using SQLite
Stores reels, categories, and extracted data
"""

import aiosqlite
import os
import json
import secrets
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "reelvault.db"))


def get_db():
    return aiosqlite.connect(DB_PATH)


async def init_db():
    """Create tables if they don't exist."""
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                vault_token TEXT UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS reels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                platform TEXT DEFAULT 'instagram',
                title TEXT,
                description TEXT,
                category TEXT,
                subcategory TEXT,
                tags TEXT,
                summary TEXT,
                key_points TEXT,
                thumbnail_url TEXT,
                author_name TEXT,
                author_url TEXT,
                raw_metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_reels_user_id ON reels(user_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_reels_category ON reels(category)
        """)

        # Safe migration for existing DB
        try:
            await db.execute("ALTER TABLE users ADD COLUMN vault_token TEXT")
        except Exception:
            pass

        await db.commit()


async def get_or_create_vault_token(user_id: int) -> str:
    """Retrieve or generate a secure private vault token for a user."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT vault_token FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row and row["vault_token"]:
            return row["vault_token"]

        token = secrets.token_urlsafe(16)
        await db.execute("""
            INSERT INTO users (user_id, vault_token)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET vault_token = excluded.vault_token
        """, (user_id, token))
        await db.commit()
        return token


async def get_user_by_token(vault_token: str) -> dict | None:
    """Retrieve user record by private vault token."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT user_id, username, first_name, vault_token FROM users WHERE vault_token = ?",
            (vault_token,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def upsert_user(user_id: int, username: str = None, first_name: str = None):
    """Insert or update a user and ensure they have a vault token."""
    token = secrets.token_urlsafe(16)
    async with get_db() as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, vault_token)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(excluded.username, users.username),
                first_name = COALESCE(excluded.first_name, users.first_name)
        """, (user_id, username, first_name, token))
        await db.commit()


async def save_reel(user_id: int, reel_data: dict) -> int:
    """Save a processed reel to the database. Returns the reel ID."""
    async with get_db() as db:
        # Check for duplicate URL for this user
        cursor = await db.execute(
            "SELECT id FROM reels WHERE user_id = ? AND url = ?",
            (user_id, reel_data.get("url", ""))
        )
        existing = await cursor.fetchone()
        if existing:
            return -1  # Already exists

        cursor = await db.execute("""
            INSERT INTO reels (
                user_id, url, platform, title, description,
                category, subcategory, tags, summary, key_points,
                thumbnail_url, author_name, author_url, raw_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            reel_data.get("url", ""),
            reel_data.get("platform", "instagram"),
            reel_data.get("title", ""),
            reel_data.get("description", ""),
            reel_data.get("category", "Uncategorized"),
            reel_data.get("subcategory", ""),
            json.dumps(reel_data.get("tags", [])),
            reel_data.get("summary", ""),
            json.dumps(reel_data.get("key_points", [])),
            reel_data.get("thumbnail_url", ""),
            reel_data.get("author_name", ""),
            reel_data.get("author_url", ""),
            json.dumps(reel_data.get("raw_metadata", {})),
        ))
        await db.commit()
        return cursor.lastrowid


async def get_reels_by_user(
    user_id: int,
    category: str = None,
    platform: str = None,
    search: str = None,
    sort_by: str = "newest",
    limit: int = 100,
    offset: int = 0
):
    """Fetch reels for a user, with full global search and multiple filter options."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM reels WHERE user_id = ?"
        params = [user_id]

        if category and category.lower() != "all":
            query += " AND LOWER(category) = LOWER(?)"
            params.append(category)

        if platform and platform.lower() != "all":
            query += " AND LOWER(platform) = LOWER(?)"
            params.append(platform)

        if search:
            query += """ AND (
                LOWER(title) LIKE ? OR 
                LOWER(summary) LIKE ? OR 
                LOWER(description) LIKE ? OR 
                LOWER(tags) LIKE ? OR 
                LOWER(key_points) LIKE ? OR 
                LOWER(subcategory) LIKE ? OR 
                LOWER(category) LIKE ? OR 
                LOWER(author_name) LIKE ? OR 
                LOWER(url) LIKE ?
            )"""
            search_term = f"%{search.lower()}%"
            params.extend([search_term] * 9)

        if sort_by == "oldest":
            query += " ORDER BY created_at ASC"
        elif sort_by == "category":
            query += " ORDER BY category ASC, created_at DESC"
        else:
            query += " ORDER BY created_at DESC"

        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_reel_by_id(reel_id: int):
    """Fetch a single reel by its primary ID."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM reels WHERE id = ?", (reel_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_categories_by_user(user_id: int):
    """Get all categories and their counts for a user."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT category, COUNT(*) as count
            FROM reels
            WHERE user_id = ?
            GROUP BY category
            ORDER BY count DESC
        """, (user_id,))
        rows = await cursor.fetchall()
        return [{"category": row[0], "count": row[1]} for row in rows]


async def get_reel_count(user_id: int):
    """Get total reel count for a user."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM reels WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return row[0]


async def update_reel_category(user_id: int, reel_id: int, new_category: str) -> bool:
    """Update a reel's category (e.g. from Kanban drag & drop)."""
    async with get_db() as db:
        cursor = await db.execute(
            "UPDATE reels SET category = ? WHERE id = ? AND user_id = ?",
            (new_category, reel_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_reel(user_id: int, reel_id: int) -> bool:
    """Delete a reel. Returns True if deleted."""
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM reels WHERE id = ? AND user_id = ?",
            (reel_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_all_users_with_reels():
    """Get all users who have saved reels (for dashboard)."""
    async with get_db() as db:
        cursor = await db.execute("""
            SELECT u.user_id, u.username, u.first_name, COUNT(r.id) as reel_count
            FROM users u
            LEFT JOIN reels r ON u.user_id = r.user_id
            GROUP BY u.user_id
            HAVING reel_count > 0
            ORDER BY reel_count DESC
        """)
        rows = await cursor.fetchall()
        return [{"user_id": row[0], "username": row[1], "first_name": row[2], "reel_count": row[3]} for row in rows]


async def export_sync_data() -> dict:
    """Export all users and reels for backup/sync."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        c1 = await db.execute("SELECT user_id, username, first_name, vault_token, created_at FROM users")
        users = [dict(r) for r in await c1.fetchall()]
        c2 = await db.execute("SELECT * FROM reels")
        reels = [dict(r) for r in await c2.fetchall()]
        return {"users": users, "reels": reels}


async def import_sync_data(users: list, reels: list):
    """Import users and reels."""
    async with get_db() as db:
        for u in users:
            await db.execute("""
                INSERT INTO users (user_id, username, first_name, vault_token, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    vault_token=COALESCE(users.vault_token, excluded.vault_token)
            """, (u["user_id"], u.get("username"), u.get("first_name"), u.get("vault_token"), u.get("created_at")))

        for r in reels:
            await db.execute("""
                INSERT OR IGNORE INTO reels (
                    user_id, url, platform, title, description, category,
                    subcategory, tags, summary, key_points, thumbnail_url,
                    author_name, author_url, raw_metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r["user_id"], r["url"], r.get("platform", "instagram"),
                r.get("title"), r.get("description"), r.get("category"),
                r.get("subcategory"), r.get("tags"), r.get("summary"),
                r.get("key_points"), r.get("thumbnail_url"),
                r.get("author_name"), r.get("author_url"),
                r.get("raw_metadata"), r.get("created_at")
            ))
        await db.commit()
