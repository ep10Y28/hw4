"""The Campus Customs shop agent (PydanticAI).

How the agent is put together:
  - Instructions: backend/prompts/prompt.md, plus two blocks written by code on
    every turn from ShopDeps: who is chatting (name, email) and what page they're
    on (including the product, if it's a product page).
  - History: the shopper's recent saved messages (logged in) or the last few
    turns sent by the browser (guest), passed as message_history.
  - Model: an OpenAI model reached through the course Portkey gateway
    (tools.build_model). The name comes from PORTKEY_MODEL_CHAT /
    PORTKEY_MODEL_SMART in .env, with gpt-5.6-terra as the default.
  - Tools: search_products, filter_products (Problem 9), get_product_info,
    get_prices, check_stock, get_customer_profile.
    Every tool reads campus_customs.db; none of them guess.
  - Output: models.ShopAnswer, a reply plus the product IDs it talks about.
    An output check rejects any product ID that isn't in the database, so the
    model can't put a made-up product on screen.

main.py calls `answer()` for every chat message.
"""

from __future__ import annotations

import logging
import time

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import UsageLimits

import audit
import tools
from pydantic_ai.messages import ModelMessage

from models import ChatResponse, CustomerInfo, FilterResult, PriceInfo, ProductInfo, ProductMatch, ShopAnswer, ShopDeps, StockReport

log = logging.getLogger("campus_customs.agent")

MAX_MODEL_REQUESTS = 8  # per chat message: caps cost and runaway tool loops
FALLBACK_REPLY = (
    "Sorry, I hit a snag on my end. Please try again in a moment, or browse the Products page."
)


def build_agent(model=None) -> Agent[ShopDeps, ShopAnswer]:
    """Create the agent. Pass a model to override Portkey (used in offline tests)."""
    agent: Agent[ShopDeps, ShopAnswer] = Agent(
        model if model is not None else tools.build_model(),
        deps_type=ShopDeps,
        output_type=ShopAnswer,
        instructions=tools.load_prompt(),
        retries=2,
    )

    @agent.instructions
    def who_is_chatting(ctx: RunContext[ShopDeps]) -> str:
        c = ctx.deps.customer
        if c is None:
            return (
                "## Who is chatting\n"
                "A guest (not logged in). You don't know their name or email. Their chat is not saved; "
                "if they want it saved, they can create an account."
            )
        return (
            "## Who is chatting\n"
            f"Logged-in customer: {c.first_name} {c.last_name}, email {c.email}, member since {c.member_since}. "
            "Their earlier messages with you are included above, so you can pick up where you left off. "
            "Use their first name naturally, at most once in a while. Only mention their email if they ask about their account."
        )

    @agent.instructions
    def current_page(ctx: RunContext[ShopDeps]) -> str:
        path = ctx.deps.page_path or "unknown"
        p = ctx.deps.page_product
        if p is None:
            return f"## Current page\nThe shopper is on page {path}. They are not viewing a single product."
        return (
            "## Current page\n"
            f"The shopper is viewing the product page for {p.name} (product_id: {p.product_id}, "
            f"{p.garment_type}, colors: {', '.join(p.colors)}). "
            'When they say "this", "it", "this one", or ask about a size or color without naming an item, '
            "they mean this product. Use this product_id with the tools directly; no search is needed for it. "
            "If they clearly name a different item, go with what they named."
        )

    @agent.tool
    def search_products(ctx: RunContext[ShopDeps], query: str) -> list[ProductMatch] | str:
        """Search the Campus Customs catalogue.

        Args:
            query: A few words describing what the shopper wants, e.g. "navy hoodie",
                "baseball crewneck", "Harvard Yale t-shirt", "gray quarter-zip".
                Returns up to 12 matches, best first.
        """
        matches = tools.search_products(ctx.deps.db_path, query)
        if not matches:
            return "No products matched that search. Try fewer or different words."
        return matches

    @agent.tool
    def filter_products(
        ctx: RunContext[ShopDeps],
        category: str | None = None,
        query: str | None = None,
        color: str | None = None,
        max_price: float | None = None,
        min_price: float | None = None,
        size_in_stock: str | None = None,
        sort: str = "best_match",
    ) -> FilterResult:
        """Find products matching several conditions at once, checked against the database.

        Use this whenever the shopper gives a price limit, a size they need in stock, a main
        color, or a category, e.g. "hoodies under $70 in medium" or "cheapest gray quarter-zip".
        The results include each product's price and stock, so no extra lookups are needed.

        Args:
            category: One of Hoodies, Crewnecks, T-shirts, Quarter-zips, Jackets & fleece, Long sleeve.
            query: Extra keywords, e.g. "baseball", "Harvard", "Berkeley", "bulldog".
            color: The garment's main color, e.g. "navy", "gray", "white".
            max_price: Highest price in USD, inclusive.
            min_price: Lowest price in USD, inclusive.
            size_in_stock: Only items with at least one unit in this size ("M", "medium", "XL").
            sort: "best_match", "price_low", or "price_high".
        """
        return tools.filter_products(
            ctx.deps.db_path,
            query=query,
            category=category,
            color=color,
            max_price=max_price,
            min_price=min_price,
            size=size_in_stock,
            sort=sort,
        )

    @agent.tool
    def get_product_info(ctx: RunContext[ShopDeps], product_id: str) -> ProductInfo:
        """Full description, garment type, and colors for one product.

        Args:
            product_id: Exactly as returned by search_products.
        """
        try:
            return tools.get_product_info(ctx.deps.db_path, product_id)
        except tools.UnknownProduct:
            raise ModelRetry(f"'{product_id}' is not a product_id. Call search_products first and use its IDs.")

    @agent.tool
    def get_prices(ctx: RunContext[ShopDeps], product_ids: list[str]) -> list[PriceInfo]:
        """Current price (USD) for one or more products. Call this before stating any price.

        Args:
            product_ids: One or more IDs exactly as returned by search_products (max 10).
        """
        prices, unknown = tools.get_prices(ctx.deps.db_path, product_ids[:10])
        if unknown and not prices:
            raise ModelRetry(f"None of these are product_ids: {unknown}. Call search_products first.")
        return prices

    @agent.tool
    def check_stock(ctx: RunContext[ShopDeps], product_id: str, size: str | None = None) -> StockReport:
        """Units in stock for one product, for every size, plus the size the shopper asked about.

        Call this before saying anything about availability.

        Args:
            product_id: Exactly as returned by search_products.
            size: The size the shopper asked about, in their words ("medium", "XL", "2XL"), or
                omit it to get all sizes.
        """
        try:
            return tools.check_stock(ctx.deps.db_path, product_id, size)
        except tools.UnknownProduct:
            raise ModelRetry(f"'{product_id}' is not a product_id. Call search_products first and use its IDs.")

    @agent.tool
    def get_customer_profile(ctx: RunContext[ShopDeps]) -> CustomerInfo | str:
        """The logged-in shopper's account details (name, email, member since).

        Use when they ask about their account, e.g. "what email is my account under?".
        """
        if ctx.deps.customer is None:
            return "The shopper is a guest (not logged in). There is no account to look up."
        return ctx.deps.customer

    @agent.output_validator
    def only_real_products(ctx: RunContext[ShopDeps], output: ShopAnswer) -> ShopAnswer:
        ids = list(dict.fromkeys(output.product_ids))  # drop duplicates, keep order
        unknown = set(ids) - tools.existing_product_ids(ctx.deps.db_path, ids)
        if unknown:
            raise ModelRetry(
                f"These product_ids are not in the catalogue: {sorted(unknown)}. "
                "Use only IDs returned by search_products."
            )
        if not output.reply.strip():
            raise ModelRetry("reply is empty. Write a message for the shopper.")
        return output.model_copy(update={"product_ids": ids})

    return agent


_agent: Agent[ShopDeps, ShopAnswer] | None = None


def get_agent() -> Agent[ShopDeps, ShopAnswer]:
    """Build the agent once, the first time it's needed."""
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


async def answer(
    message: str,
    deps: ShopDeps,
    history: list[ModelMessage] | None = None,
    run_id: str | None = None,
) -> ChatResponse:
    """Run the agent on one shopper message (with earlier turns) and package the reply for the website.

    Every run is written to the append-only audit trail (output/audit_trail.json):
    a turn_start entry, one model_step entry per loop iteration (tools called,
    short args and results, stop reason, tokens), and a turn_end entry.
    """
    run_id = run_id or audit.new_run_id()
    who = f"user:{deps.customer.user_id}" if deps.customer else "guest"
    model_name = tools.chat_model_name()
    entries = [
        audit.event(
            run_id, who, "turn_start",
            message=audit.short(message, 200),
            page=deps.page_path,
            page_product=deps.page_product.product_id if deps.page_product else None,
            history_messages=len(history or []),
        )
    ]
    started = time.monotonic()
    try:
        result = await get_agent().run(
            message,
            deps=deps,
            message_history=history or None,
            usage_limits=UsageLimits(request_limit=MAX_MODEL_REQUESTS),
        )
    except Exception as exc:  # model down, rate limit, bad output after retries, loop limit, etc.
        log.exception("Agent run failed")
        stop = "usage_limit" if isinstance(exc, UsageLimitExceeded) else "error"
        entries.append(
            audit.event(
                run_id, who, "turn_end",
                stop_reason=stop,
                error=f"{type(exc).__name__}: {audit.short(str(exc), 200)}",
                duration_ms=round((time.monotonic() - started) * 1000),
            )
        )
        _safe_append(entries)
        return ChatResponse(reply=FALLBACK_REPLY)

    output: ShopAnswer = result.output
    cards = tools.product_cards(deps.db_path, output.product_ids)
    try:
        usage = result.usage() if callable(result.usage) else result.usage  # method in PydanticAI 1.x, property in 2.x
        entries += audit.steps_from_messages(result.new_messages(), run_id, who, model_name)
        entries.append(
            audit.event(
                run_id, who, "turn_end",
                stop_reason="final_result",
                reply=audit.short(output.reply, 200),
                product_ids=output.product_ids,
                results_label=output.results_label,
                model_requests=getattr(usage, "requests", None),
                tool_call_count=getattr(usage, "tool_calls", None),
                tokens={"input": getattr(usage, "input_tokens", None), "output": getattr(usage, "output_tokens", None)},
                duration_ms=round((time.monotonic() - started) * 1000),
            )
        )
    except Exception:
        log.exception("Could not build audit entries")
    _safe_append(entries)
    return ChatResponse(
        reply=output.reply,
        products=cards,
        results_label=(output.results_label or "From your chat") if cards else None,
    )


def _safe_append(entries: list[dict]) -> None:
    """Auditing must never break the chat: log and carry on if the write fails."""
    try:
        audit.append(entries)
    except Exception:
        log.exception("Could not write audit trail")
