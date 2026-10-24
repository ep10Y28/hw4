"""Tool logic and helpers for the Campus Customs agent.

Everything here is plain Python: database lookups, the Portkey model
connection, and loading the prompt file. agent.py wires these into the agent.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path

import httpx
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from models import FilteredProduct, FilterResult, PriceInfo, ProductCard, ProductInfo, ProductMatch, SizeStock, StockReport

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
DB_PATH = ROOT / "data" / "campus_customs.db"
PROMPT_FILE = BACKEND_DIR / "prompts" / "prompt.md"

DEFAULT_CHAT_MODEL = "gpt-5.6-terra"
DEFAULT_BASE_URL = "https://api.portkey.ai/v1"


# ------------------------------------------------------------------ setup

def load_env() -> None:
    """Load hw4/.env (one folder up from backend/) so PORTKEY_API_KEY is set."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env")
    load_dotenv(BACKEND_DIR / ".env")  # optional override, if one exists


def chat_model_name() -> str:
    return os.environ.get("PORTKEY_MODEL_CHAT") or os.environ.get("PORTKEY_MODEL_SMART") or DEFAULT_CHAT_MODEL


def build_model(model_name: str | None = None) -> OpenAIChatModel:
    """Point PydanticAI at the course's Portkey gateway.

    Lesson from HW1: this Portkey setup rejects requests that carry an
    `Authorization: Bearer` header and wants the key ONLY in `x-portkey-api-key`.
    The OpenAI SDK always adds Authorization, so an httpx hook strips it
    right before each request goes out.
    """
    key = os.environ.get("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it to hw4/.env.")

    headers = {"x-portkey-api-key": key}
    if os.environ.get("PORTKEY_VIRTUAL_KEY"):
        headers["x-portkey-virtual-key"] = os.environ["PORTKEY_VIRTUAL_KEY"]

    async def strip_bearer(request: httpx.Request) -> None:
        request.headers.pop("Authorization", None)

    http_client = httpx.AsyncClient(
        headers=headers,
        timeout=httpx.Timeout(60.0),
        event_hooks={"request": [strip_bearer]},
    )
    client = AsyncOpenAI(
        api_key="portkey-key-is-in-header",  # placeholder; stripped by the hook
        base_url=os.environ.get("PORTKEY_BASE_URL", DEFAULT_BASE_URL),
        http_client=http_client,
        max_retries=1,
    )
    return OpenAIChatModel(model_name or chat_model_name(), provider=OpenAIProvider(openai_client=client))


def load_prompt(path: Path = PROMPT_FILE) -> str:
    return path.read_text(encoding="utf-8")


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ----------------------------------------------------------------- search

# Shoppers say "tee" or "sweatshirt"; the catalogue's garment types are written
# 22 different ways. Map common words onto the words the catalogue uses.
SYNONYMS = {
    "tee": "t-shirt", "tees": "t-shirt", "tshirt": "t-shirt", "tshirts": "t-shirt",
    "shirts": "shirt", "hoody": "hoodie", "hoodies": "hoodie", "sweatshirts": "sweatshirt",
    "crew": "crewneck", "crewnecks": "crewneck", "quarterzip": "quarter-zip", "qzip": "quarter-zip",
    "zip-up": "zip", "fleeces": "fleece", "jackets": "jacket", "grey": "gray",
}
STOPWORDS = {
    "a", "an", "the", "do", "you", "have", "any", "in", "of", "for", "me", "i", "want", "show",
    "find", "looking", "something", "some", "with", "and", "or", "is", "are", "there", "what",
    "your", "got", "need", "like", "please", "yale",  # every product is Yale
}


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower())
    return [SYNONYMS.get(w, w) for w in words if w not in STOPWORDS]


def search_products(db_path: Path, query: str, limit: int = 12) -> list[ProductMatch]:
    """Keyword search over name, garment type, colors, tags, and description.

    Name and garment-type hits count most, then colors and tags, then the
    description. Products that match none of the words are left out.
    """
    words = _tokens(query)
    if not words:
        return []
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT product_id, name, garment_type, colors, search_tags, description FROM catalogue"
        ).fetchall()

    scored: list[tuple[float, sqlite3.Row]] = []
    for r in rows:
        name = r["name"].lower()
        gtype = r["garment_type"].lower()
        colors = " ".join(json.loads(r["colors"])).lower()
        tags = " ".join(json.loads(r["search_tags"])).lower()
        desc = r["description"].lower()
        score = 0.0
        matched = 0
        for w in words:
            hit = 0.0
            if w in name or w in gtype:
                hit = 3.0
            elif w in colors:
                hit = 2.0
            elif w in tags:
                hit = 1.5
            elif w in desc:
                hit = 1.0
            if hit:
                matched += 1
                score += hit
        if matched:
            # Reward products that match more of the shopper's words.
            scored.append((score * matched / len(words), r))

    scored.sort(key=lambda t: (-t[0], t[1]["name"]))
    return [
        ProductMatch(
            product_id=r["product_id"],
            name=r["name"],
            garment_type=r["garment_type"],
            colors=json.loads(r["colors"]),
            description=r["description"],
        )
        for _, r in scored[:limit]
    ]


def short_text(text: str, limit: int = 90) -> str:
    """First ~90 characters of a description, cut at a word boundary."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


def existing_product_ids(db_path: Path, ids: list[str]) -> set[str]:
    if not ids:
        return set()
    marks = ",".join("?" * len(ids))
    with connect(db_path) as conn:
        rows = conn.execute(f"SELECT product_id FROM catalogue WHERE product_id IN ({marks})", ids).fetchall()
    return {r["product_id"] for r in rows}


def product_cards(db_path: Path, ids: list[str]) -> list[ProductCard]:
    """Build cards for the given IDs from the database, in the order given."""
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    with connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT c.product_id, c.name, c.garment_type, c.price, c.image_file_path, c.colors, c.description,
                   COALESCE(SUM(i.quantity), 0) AS total_stock
            FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
            WHERE c.product_id IN ({marks})
            GROUP BY c.product_id
            """,
            ids,
        ).fetchall()
    by_id = {
        r["product_id"]: ProductCard(
            product_id=r["product_id"],
            name=r["name"],
            garment_type=r["garment_type"],
            price=r["price"],
            image_url="/images/" + r["image_file_path"],
            short_description=short_text(r["description"]),
            colors=json.loads(r["colors"]),
            total_stock=r["total_stock"],
        )
        for r in rows
    }
    seen: set[str] = set()
    cards = []
    for pid in ids:
        if pid in by_id and pid not in seen:
            seen.add(pid)
            cards.append(by_id[pid])
    return cards


# ------------------------------------------------- product info, price, stock

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
LOW_STOCK = 5  # 1-5 units left counts as "low stock"

# What shoppers type -> the size codes in the inventory table.
SIZE_WORDS = {
    "xs": "XS", "x-small": "XS", "xsmall": "XS", "extra small": "XS", "extra-small": "XS",
    "s": "S", "sm": "S", "small": "S",
    "m": "M", "med": "M", "medium": "M",
    "l": "L", "lg": "L", "large": "L",
    "xl": "XL", "x-large": "XL", "xlarge": "XL", "extra large": "XL", "extra-large": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "2x": "XXL",
    "extra extra large": "XXL", "double xl": "XXL",
}


class UnknownProduct(LookupError):
    pass


def normalize_size(size: str | None) -> str | None:
    """'medium' -> 'M', 'Xl' -> 'XL', '2XL' -> 'XXL'. Unknown words come back uppercased."""
    if size is None or not size.strip():
        return None
    key = re.sub(r"\s+", " ", size.strip().lower())
    return SIZE_WORDS.get(key, key.upper())


def stock_status(quantity: int) -> str:
    if quantity <= 0:
        return "sold out"
    if quantity <= LOW_STOCK:
        return "low stock"
    return "in stock"


def get_product_info(db_path: Path, product_id: str) -> ProductInfo:
    with connect(db_path) as conn:
        r = conn.execute(
            "SELECT product_id, name, garment_type, description, colors FROM catalogue WHERE product_id = ?",
            (product_id,),
        ).fetchone()
    if r is None:
        raise UnknownProduct(product_id)
    return ProductInfo(
        product_id=r["product_id"],
        name=r["name"],
        garment_type=r["garment_type"],
        description=r["description"],
        colors=json.loads(r["colors"]),
    )


def get_prices(db_path: Path, product_ids: list[str]) -> tuple[list[PriceInfo], list[str]]:
    """Prices for the given IDs, in the order asked, plus any IDs that don't exist."""
    ids = list(dict.fromkeys(product_ids))
    if not ids:
        return [], []
    marks = ",".join("?" * len(ids))
    with connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT product_id, name, price FROM catalogue WHERE product_id IN ({marks})", ids
        ).fetchall()
    found = {r["product_id"]: PriceInfo(product_id=r["product_id"], name=r["name"], price_usd=r["price"]) for r in rows}
    return [found[i] for i in ids if i in found], [i for i in ids if i not in found]


def check_stock(db_path: Path, product_id: str, size: str | None = None) -> StockReport:
    with connect(db_path) as conn:
        product = conn.execute("SELECT name FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if product is None:
            raise UnknownProduct(product_id)
        rows = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    sizes = sorted(
        (SizeStock(size=r["size"], quantity=r["quantity"], status=stock_status(r["quantity"])) for r in rows),
        key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else 99,
    )
    report = StockReport(
        product_id=product_id,
        name=product["name"],
        sizes=sizes,
        total_quantity=sum(s.quantity for s in sizes),
        sizes_in_stock=[s.size for s in sizes if s.quantity > 0],
        sizes_sold_out=[s.size for s in sizes if s.quantity <= 0],
    )
    wanted = normalize_size(size)
    if wanted:
        match = next((s for s in sizes if s.size == wanted), None)
        report.requested_size = wanted
        if match is None:
            report.requested_size_status = "not a size we carry"
        else:
            report.requested_size_quantity = match.quantity
            report.requested_size_status = match.status
    return report


# -------------------------------------------- categories + filtered search
# The catalogue writes garment types 22 different ways. These rules (checked in
# order) fold them into the six categories shoppers think in.
CATEGORY_RULES = [
    ("T-shirts", ("t-shirt",)),
    ("Quarter-zips", ("quarter-zip",)),
    ("Jackets & fleece", ("jacket", "fleece")),
    ("Hoodies", ("hood",)),
    ("Crewnecks", ("crewneck", "mockneck")),
    ("Long sleeve", ("long-sleeve", "performance")),
]
CATEGORY_NAMES = [c for c, _ in CATEGORY_RULES]
CATEGORY_WORDS = {
    "hoodie": "Hoodies", "hoodies": "Hoodies", "hooded": "Hoodies",
    "crewneck": "Crewnecks", "crewnecks": "Crewnecks", "crew": "Crewnecks", "sweatshirt": "Crewnecks",
    "sweatshirts": "Crewnecks", "tee": "T-shirts", "tees": "T-shirts", "t-shirt": "T-shirts",
    "t-shirts": "T-shirts", "tshirt": "T-shirts", "shirt": "T-shirts", "shirts": "T-shirts",
    "quarter-zip": "Quarter-zips", "quarter-zips": "Quarter-zips", "quarter zip": "Quarter-zips",
    "1/4 zip": "Quarter-zips", "jacket": "Jackets & fleece", "jackets": "Jackets & fleece",
    "fleece": "Jackets & fleece", "long sleeve": "Long sleeve", "long-sleeve": "Long sleeve",
}


# What a shopper's color word should match in the catalogue's color names.
COLOR_FAMILIES = {
    "blue": ("blue", "navy"),
    "navy": ("navy",),
    "yale blue": ("blue", "navy"),
    "gray": ("gray", "grey", "heather", "charcoal", "silver"),
    "grey": ("gray", "grey", "heather", "charcoal", "silver"),
    "white": ("white", "cream", "ivory", "natural"),
    "black": ("black",),
    "red": ("red", "crimson", "maroon", "cardinal"),
    "green": ("green", "olive", "forest"),
    "pink": ("pink", "rose"),
}


def color_family(color: str) -> tuple[str, ...]:
    c = color.strip().lower()
    return COLOR_FAMILIES.get(c, (SYNONYMS.get(c, c),))


def category_for(garment_type: str) -> str:
    g = garment_type.lower()
    for name, words in CATEGORY_RULES:
        if any(w in g for w in words):
            return name
    return "Crewnecks"  # every current product matches a rule; safe default


def normalize_category(category: str | None) -> str | None:
    if not category:
        return None
    c = category.strip()
    for name in CATEGORY_NAMES:
        if c.lower() == name.lower():
            return name
    return CATEGORY_WORDS.get(c.lower())


def filter_products(
    db_path: Path,
    query: str | None = None,
    category: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    size: str | None = None,
    in_stock_only: bool = True,
    sort: str = "best_match",
    limit: int = 12,
) -> FilterResult:
    """Every filter is applied in code against the database, in one call."""
    applied: dict[str, str | float | bool] = {}
    notes: list[str] = []
    cat = normalize_category(category)
    if category and not cat:
        notes.append(f"Unknown category '{category}', ignored. Categories: {', '.join(CATEGORY_NAMES)}.")
    elif cat:
        applied["category"] = cat
    wanted_size = normalize_size(size)
    if wanted_size and wanted_size not in SIZE_ORDER:
        notes.append(f"'{size}' is not a size we carry (we stock {', '.join(SIZE_ORDER)}); size filter ignored.")
        wanted_size = None
    if wanted_size:
        applied["size_in_stock"] = wanted_size
    if color:
        applied["color"] = color.strip().lower()
    if max_price is not None:
        applied["max_price"] = float(max_price)
    if min_price is not None:
        applied["min_price"] = float(min_price)
    if in_stock_only:
        applied["in_stock_only"] = True

    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT c.product_id, c.name, c.garment_type, c.colors, c.search_tags, c.description, c.price,
                   COALESCE(SUM(i.quantity), 0) AS total_stock
            FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
            GROUP BY c.product_id
            """
        ).fetchall()
        size_qty: dict[str, int] = {}
        if wanted_size:
            size_qty = {
                r["product_id"]: r["quantity"]
                for r in conn.execute("SELECT product_id, quantity FROM inventory WHERE size = ?", (wanted_size,))
            }

    words = _tokens(query) if query else []
    if words:
        applied["query"] = query.strip()
    kept: list[tuple[float, sqlite3.Row]] = []
    for r in rows:
        colors = [c.lower() for c in json.loads(r["colors"])]
        if cat and category_for(r["garment_type"]) != cat:
            continue
        if color:
            # Match the garment's main color (listed first), so "white" doesn't
            # return navy hoodies that only have white lettering. Colors match by
            # family: a shopper asking for "blue" means navy too.
            if not any(word in colors[0] for word in color_family(color)):
                continue
        if max_price is not None and r["price"] > max_price:
            continue
        if min_price is not None and r["price"] < min_price:
            continue
        if wanted_size and size_qty.get(r["product_id"], 0) <= 0:
            continue
        if in_stock_only and r["total_stock"] <= 0:
            continue
        score = 0.0
        if words:
            text = " ".join([r["name"], r["garment_type"], " ".join(colors), r["search_tags"], r["description"]]).lower()
            hits = sum(1 for w in words if w in text)
            if hits == 0:
                continue
            score = hits / len(words)
        kept.append((score, r))

    if sort == "price_low":
        kept.sort(key=lambda t: (t[1]["price"], t[1]["name"]))
    elif sort == "price_high":
        kept.sort(key=lambda t: (-t[1]["price"], t[1]["name"]))
    else:
        kept.sort(key=lambda t: (-t[0], t[1]["name"]))

    products = [
        FilteredProduct(
            product_id=r["product_id"],
            name=r["name"],
            category=category_for(r["garment_type"]),
            colors=json.loads(r["colors"]),
            price_usd=r["price"],
            total_stock=r["total_stock"],
            size=wanted_size,
            size_quantity=size_qty.get(r["product_id"]) if wanted_size else None,
        )
        for _, r in kept[: max(1, min(limit, 12))]
    ]
    if not kept:
        notes.append("Nothing matches all of these filters. Try relaxing one (price, color, or size).")
    return FilterResult(
        filters_applied=applied,
        total_matches=len(kept),
        products=products,
        note=" ".join(notes) or None,
    )
