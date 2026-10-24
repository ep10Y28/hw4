"""Structured types for the Campus Customs chatbot.

The agent never writes product cards itself. It returns product IDs, and the
backend looks each ID up in the database to build the card, so every price,
name, and photo on screen comes from the database rather than the model.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

MAX_PRODUCTS_PER_REPLY = 12


# ------------------------------------------------------------- agent output

class ShopAnswer(BaseModel):
    """What the agent must return at the end of every turn."""

    reply: str = Field(
        description=(
            "The message to show the shopper, in the Campus Customs voice. "
            "Plain text; short '-' bullet lines are fine."
        )
    )
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_PRODUCTS_PER_REPLY,
        description=(
            "product_id values, exactly as returned by search_products, for the items "
            "this reply recommends or talks about. Most relevant first. Empty if none. "
            "The website shows these as product cards on the page."
        ),
    )
    results_label: str | None = Field(
        default=None,
        max_length=60,
        description=(
            "A short heading for the product cards, e.g. 'Navy hoodies' or 'Baseball gear'. "
            "Null when product_ids is empty."
        ),
    )


# ---------------------------------------------------------- tool results

class ProductMatch(BaseModel):
    """One search result handed to the agent."""

    product_id: str
    name: str
    garment_type: str
    colors: list[str]
    description: str


Category = Literal["Hoodies", "Crewnecks", "T-shirts", "Quarter-zips", "Jackets & fleece", "Long sleeve"]


class FilteredProduct(BaseModel):
    """filter_products: one product that passed every filter, with its price and stock."""

    product_id: str
    name: str
    category: Category
    colors: list[str]
    price_usd: float = Field(description="Price in US dollars, from the catalogue.")
    total_stock: int
    size: str | None = Field(default=None, description="The size filtered on, normalized (e.g. 'M').")
    size_quantity: int | None = Field(default=None, description="Units in stock in that size.")


class FilterResult(BaseModel):
    """What filter_products returns: the matches plus the filters actually applied."""

    filters_applied: dict[str, str | float | bool]
    total_matches: int = Field(description="How many products passed the filters (before the limit).")
    products: list[FilteredProduct]
    note: str | None = None


class ProductInfo(BaseModel):
    """get_product_info: what the product is and looks like."""

    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]


class PriceInfo(BaseModel):
    """get_prices: the price of one product, straight from the catalogue."""

    product_id: str
    name: str
    price_usd: float = Field(description="Price in US dollars, e.g. 68.0 means $68.00.")


StockStatus = Literal["in stock", "low stock", "sold out"]


class SizeStock(BaseModel):
    size: str
    quantity: int = Field(description="Units on hand right now. 0 means sold out.")
    status: StockStatus


class StockReport(BaseModel):
    """check_stock: stock for one product, overall and (if asked) for one size."""

    product_id: str
    name: str
    sizes: list[SizeStock] = Field(description="Every size, XS to XXL, with its quantity and status.")
    total_quantity: int
    sizes_in_stock: list[str]
    sizes_sold_out: list[str]
    requested_size: str | None = Field(
        default=None, description="The size the shopper asked about, normalized (e.g. 'medium' -> 'M')."
    )
    requested_size_quantity: int | None = None
    requested_size_status: StockStatus | Literal["not a size we carry"] | None = None


# --------------------------------------------------- API (website <-> backend)

class PageContext(BaseModel):
    """Where the shopper is on the site when they send a message (sent by the website)."""

    path: str = Field(default="/", max_length=200)
    product_id: str | None = Field(default=None, max_length=120)


class ChatTurn(BaseModel):
    """One earlier message, sent by the website for guests only (their chat isn't saved)."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    page: PageContext | None = None
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)  # guests only; ignored when logged in


class ProductCard(BaseModel):
    """A product as the website shows it in chat. Built from the database, not the model."""

    product_id: str
    name: str
    garment_type: str
    price: float
    image_url: str
    short_description: str
    colors: list[str]
    total_stock: int


class HistoryMessage(BaseModel):
    """One saved message, as GET /api/chat/history returns it."""

    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    results_label: str | None = None
    created_at: str


class ChatResponse(BaseModel):
    """What /api/chat returns. `products` + `results_label` are rendered as cards on the page."""

    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    results_label: str | None = None
    # Problem 9 safety guardrail: what was actually sent/saved, and why, if it was changed.
    message_redacted: str | None = None
    notice: str | None = None


# ------------------------------------------------------------ dependencies

class CustomerInfo(BaseModel):
    """The logged-in shopper, as the agent sees them. No password hash, no session data."""

    user_id: int
    first_name: str
    last_name: str
    email: str
    member_since: str = Field(description="Date the account was created, YYYY-MM-DD.")


@dataclass
class ShopDeps:
    """What every agent run gets.

    db_path       where the database is (every tool reads from it)
    customer      the logged-in shopper, or None for a guest
    page_path     the page they're on, e.g. "/products" or "/products/basic-hoodie-big-yale"
    page_product  the product on that page (checked against the database), or None
    """

    db_path: Path
    customer: CustomerInfo | None = None
    page_path: str | None = None
    page_product: ProductInfo | None = None
