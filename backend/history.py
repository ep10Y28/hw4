"""Saved chat history for logged-in shoppers (Problem 8).

Storage: the existing `chat_messages` table in campus_customs.db, one row per
message (the shopper's message and the agent's reply are separate rows):

    id, user_id -> users.id, role ('user' | 'assistant'), content,
    products_json (product IDs + card data shown with a reply),
    results_label (heading for those cards; column added here if missing),
    created_at

Guests aren't saved. The website keeps their conversation in memory and sends
the last few turns with each message instead.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

import tools
from models import ChatResponse, ChatTurn, HistoryMessage

AGENT_HISTORY_TURNS = 20   # most recent messages the agent re-reads each turn
PAGE_HISTORY_LIMIT = 100   # most recent messages the website reloads


def ensure_history_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            products_json TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)")}
    if "results_label" not in cols:
        conn.execute("ALTER TABLE chat_messages ADD COLUMN results_label TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages(user_id, id)")
    conn.commit()


def save_turn(db_path: Path, user_id: int, message: str, response: ChatResponse) -> None:
    """Save the shopper's message and the agent's reply as two rows."""
    products = [card.model_dump() for card in response.products]
    with tools.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)",
            (user_id, message),
        )
        conn.execute(
            """
            INSERT INTO chat_messages (user_id, role, content, products_json, results_label)
            VALUES (?, 'assistant', ?, ?, ?)
            """,
            (user_id, response.reply, json.dumps(products), response.results_label),
        )
        conn.commit()


def _rows(db_path: Path, user_id: int, limit: int) -> list[sqlite3.Row]:
    with tools.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT role, content, products_json, results_label, created_at
            FROM chat_messages WHERE user_id = ? AND role IN ('user', 'assistant')
            ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def _product_ids(products_json: str | None) -> list[str]:
    if not products_json:
        return []
    try:
        data = json.loads(products_json)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):  # tolerate {"products": [...]} too
        data = data.get("products", [])
    return [p["product_id"] for p in data if isinstance(p, dict) and "product_id" in p]


def page_history(db_path: Path, user_id: int, limit: int = PAGE_HISTORY_LIMIT) -> list[HistoryMessage]:
    """History for the chat panel. Cards are rebuilt from the database, so prices and stock are current."""
    out = []
    for r in _rows(db_path, user_id, limit):
        ids = _product_ids(r["products_json"])
        cards = tools.product_cards(db_path, ids)
        out.append(
            HistoryMessage(
                role=r["role"],
                content=r["content"],
                products=cards,
                results_label=(r["results_label"] or "From your chat") if cards else None,
                created_at=r["created_at"],
            )
        )
    return out


def clear(db_path: Path, user_id: int) -> int:
    with tools.connect(db_path) as conn:
        n = conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount
        conn.commit()
    return n


def _as_model_messages(turns: list[tuple[str, str]]) -> list[ModelMessage]:
    """Turn (role, text) pairs into PydanticAI message history.

    Must start with a user message, so any leading assistant lines are dropped.
    """
    while turns and turns[0][0] != "user":
        turns = turns[1:]
    messages: list[ModelMessage] = []
    for role, text in turns:
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=text)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=text)]))
    return messages


def agent_history_for_user(db_path: Path, user_id: int, limit: int = AGENT_HISTORY_TURNS) -> list[ModelMessage]:
    """The shopper's recent saved messages, for the agent.

    Each earlier reply gets a note of the product IDs it showed, so follow-ups
    like "is the second one in medium?" can be resolved.
    """
    turns = []
    for r in _rows(db_path, user_id, limit):
        text = r["content"]
        ids = _product_ids(r["products_json"])
        if r["role"] == "assistant" and ids:
            text += f"\n[Products shown on the page with this reply, in order: {', '.join(ids)}]"
        turns.append((r["role"], text))
    return _as_model_messages(turns)


def agent_history_for_guest(history: list[ChatTurn]) -> list[ModelMessage]:
    """A guest's recent turns, sent by the browser. Only the last 10, as plain text."""
    return _as_model_messages([(t.role, t.content) for t in history[-10:]])
