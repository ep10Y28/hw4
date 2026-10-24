"""Campus Customs backend: the FastAPI app.

Run from the backend/ folder:
    uvicorn main:app --reload --port 8000

Routes
    /api/products, /api/products/{id}  catalogue + stock (Problem 3)
    /images/products/<file>             product photos (Problem 3)
    /api/auth/...                       signup, login, logout, me (Problem 4, auth.py)
    /api/chat                           the shop agent (Problem 5, agent.py)
    /api/chat/history                   saved chat for the logged-in shopper (Problem 8, history.py)

The agent itself lives in four files next to this one:
    prompts/prompt.md   instructions (voice, honesty, safety)
    agent.py            the PydanticAI agent and how a chat turn runs
    tools.py            database lookups, Portkey model connection
    models.py           structured types (agent output, product cards, API bodies)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # keep the terminal readable

import agent
import audit
import guardrails
import history
import tools
from auth import PublicUser, build_router, ensure_auth_tables
from models import ChatRequest, ChatResponse, ChatTurn, CustomerInfo, HistoryMessage, ShopDeps

tools.load_env()
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s: %(message)s")
log = logging.getLogger("campus_customs")

DATA_DIR = tools.ROOT / "data"
DB_PATH = tools.DB_PATH
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


def connect() -> sqlite3.Connection:
    return tools.connect(DB_PATH)


@asynccontextmanager
async def lifespan(_: FastAPI):
    with connect() as conn:
        ensure_auth_tables(conn)
        history.ensure_history_table(conn)
    # Build the agent at startup so a missing key or prompt file shows up
    # right away in the terminal, not on the first chat message.
    try:
        agent.get_agent()
        log.info("Shop agent ready (model: %s, prompt: %s)", tools.chat_model_name(), tools.PROMPT_FILE.name)
    except Exception as exc:
        log.error("Shop agent NOT ready: %s", exc)
    yield


app = FastAPI(title="Campus Customs API", lifespan=lifespan)

# The Vite dev server runs on port 5173.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# catalogue.image_file_path is "products/<file>.jpg" (relative to data/), so
# "/images/" + image_file_path is a working URL.
app.mount("/images/products", StaticFiles(directory=DATA_DIR / "products"), name="images")

auth_router, current_user, optional_user = build_router(connect)
app.include_router(auth_router)


# ---------------------------------------------------------------- products

def product_from_row(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["colors"] = json.loads(item["colors"])
    item["search_tags"] = json.loads(item["search_tags"])
    item["image_url"] = "/images/" + item["image_file_path"]
    return item


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "model": tools.chat_model_name(), "agent_key_set": bool(os.environ.get("PORTKEY_API_KEY"))}


@app.get("/api/products")
def list_products() -> list[dict]:
    """All products with their total stock across sizes, for the Products page."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
                   GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS sizes_in_stock
            FROM catalogue c
            LEFT JOIN inventory i ON i.product_id = c.product_id
            GROUP BY c.product_id
            ORDER BY c.name
            """
        ).fetchall()
    out = []
    for r in rows:
        item = product_from_row(r)
        item["category"] = tools.category_for(item["garment_type"])
        sizes = set((item.pop("sizes_in_stock") or "").split(","))
        item["sizes_in_stock"] = [s for s in tools.SIZE_ORDER if s in sizes]
        out.append(item)
    return out


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    """One product with stock by size, for the single-item page."""
    with connect() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    item = product_from_row(row)
    sizes = sorted(
        ({"size": s["size"], "quantity": s["quantity"]} for s in stock),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99,
    )
    item["inventory"] = sizes
    item["total_stock"] = sum(s["quantity"] for s in sizes)
    item["category"] = tools.category_for(item["garment_type"])
    return item


# -------------------------------------------------------------------- chat

def load_customer(user: PublicUser) -> CustomerInfo:
    with connect() as conn:
        row = conn.execute("SELECT created_at FROM users WHERE id = ?", (user.id,)).fetchone()
    return CustomerInfo(
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        member_since=(row["created_at"] or "")[:10] if row else "",
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user: PublicUser | None = Depends(optional_user)) -> ChatResponse:
    """One shopper message in, one agent reply (plus product cards) out.

    - Logged in: the agent gets their profile and their saved history, and this
      turn is saved to chat_messages.
    - Guest: the agent gets the last few turns the browser sent; nothing is saved.
    - Page context: the page path, and the product if it's a product page.
      The product_id is checked against the database before the agent sees it.
    """
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is empty.")

    # Safety guardrail, step 1: redact card numbers / SSNs / passwords before the
    # model sees the message or it's saved; block prompt-injection attempts outright.
    check = guardrails.check_input(message)
    run_id = audit.new_run_id()
    who = f"user:{user.id}" if user else "guest"
    if check.redacted:
        log.warning("Guardrail redacted %s from a chat message", ", ".join(check.redacted))
        agent._safe_append([audit.event(run_id, who, "guardrail", action="redacted_input", what=check.redacted)])
    redacted_echo = check.text if check.text != message else None
    message = check.text
    if check.blocked:
        log.warning("Guardrail blocked a prompt-injection attempt")
        agent._safe_append([
            audit.event(run_id, who, "guardrail", action="blocked_input", message=audit.short(message, 200),
                        stop_reason="blocked", model_requests=0)
        ])
        blocked = ChatResponse(reply=guardrails.BLOCKED_REPLY, message_redacted=redacted_echo, notice=check.notice)
        if user:
            history.save_turn(DB_PATH, user.id, message, blocked)
        return blocked

    page_product = None
    if req.page and req.page.product_id:
        try:
            page_product = tools.get_product_info(DB_PATH, req.page.product_id)
        except tools.UnknownProduct:
            page_product = None  # stale or tampered ID: ignore it

    customer = load_customer(user) if user else None
    deps = ShopDeps(
        db_path=DB_PATH,
        customer=customer,
        page_path=req.page.path if req.page else None,
        page_product=page_product,
    )
    past = (
        history.agent_history_for_user(DB_PATH, user.id)
        if user
        else history.agent_history_for_guest(
            [ChatTurn(role=t.role, content=guardrails.check_input(t.content).text) for t in req.history]
        )
    )

    response = await agent.answer(message, deps, past, run_id=run_id)

    # Safety guardrail, step 2: no other customer's email, no quoting the hidden prompt.
    safe_reply, changes = guardrails.check_output(response.reply, customer.email if customer else None)
    if changes:
        log.warning("Guardrail changed a reply: %s", "; ".join(changes))
        agent._safe_append([audit.event(run_id, who, "guardrail", action="changed_output", what=changes)])
        response = response.model_copy(update={"reply": safe_reply})
    response = response.model_copy(update={"message_redacted": redacted_echo, "notice": check.notice})

    if user and response.reply != agent.FALLBACK_REPLY:
        history.save_turn(DB_PATH, user.id, message, response)
    return response


@app.get("/api/chat/history", response_model=list[HistoryMessage])
def get_history(user: PublicUser = Depends(current_user)) -> list[HistoryMessage]:
    """The logged-in shopper's saved chat, oldest first (last 100 messages)."""
    return history.page_history(DB_PATH, user.id)


@app.delete("/api/chat/history")
def delete_history(user: PublicUser = Depends(current_user)) -> dict:
    """Let a shopper wipe their own saved chat."""
    return {"deleted": history.clear(DB_PATH, user.id)}
