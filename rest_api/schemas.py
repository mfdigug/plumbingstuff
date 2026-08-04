from typing import Optional

from pydantic import BaseModel, Field


class ProductCandidateOut(BaseModel):
    sku: str
    name: str
    brand: str
    category: str
    subcategory: str
    price_aud: float
    attributes: dict = {}
    confidence: float
    match_reason: str


class SearchCatalogueRequest(BaseModel):
    # One entry per distinct product the customer asked for -- even a single
    # item goes in as a one-element array, e.g. items=["mixer tap"].
    items: list[str] = Field(min_length=1)
    category: Optional[str] = None
    max_results_per_item: int = Field(default=4, ge=1, le=20)


class ItemSearchResult(BaseModel):
    query: str
    matches: list[ProductCandidateOut]
    match_count: int


class SearchCatalogueResponse(BaseModel):
    request_id: str
    generated_at: str
    results: list[ItemSearchResult]


class StoreStockOut(BaseModel):
    store_id: str
    store_name: str
    suburb: str
    state: str
    postcode: str
    qty_on_hand: int
    status: str
    eta_days: Optional[int] = None
    last_updated: Optional[str] = None


class AvailabilityResponse(BaseModel):
    sku: str
    generated_at: str
    locations: list[StoreStockOut]


class AddressOut(BaseModel):
    street: str
    suburb: str
    state: str
    postcode: str


class CustomerProfileOut(BaseModel):
    customer_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    preferred_store_id: str
    address: AddressOut


class AddCartItemRequest(BaseModel):
    sku: str
    quantity: int = Field(default=1, ge=1)


class CartItemOut(BaseModel):
    sku: str
    name: str
    brand: str
    quantity: int
    unit_price_aud: float
    subtotal_aud: float
    added_at: Optional[str] = None


class CartResponse(BaseModel):
    customer_id: str
    items: list[CartItemOut]
    subtotal_aud: float
    updated_at: Optional[str] = None
