from typing import Optional

from pydantic import BaseModel, Field, model_validator


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


class RefineFiltersIn(BaseModel):
    brand: Optional[str] = None
    size: Optional[str] = None
    finish: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    connection_type: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None


class SearchCatalogueRequest(BaseModel):
    # To search: set `items` (an array, one entry per distinct product asked for --
    # even a single item goes in as a one-element array). Leave `candidate_skus` unset.
    # To narrow a previous search: set `candidate_skus` (+ `filters` and/or `query`).
    items: Optional[list[str]] = None
    category: Optional[str] = None
    max_results_per_item: int = Field(default=4, ge=1, le=20)
    candidate_skus: Optional[list[str]] = None
    filters: RefineFiltersIn = RefineFiltersIn()
    query: Optional[str] = None  # refine mode only: optional re-rank phrase

    @model_validator(mode="after")
    def _require_items_or_candidates(self):
        if not self.items and not self.candidate_skus:
            raise ValueError("either `items` (to search) or `candidate_skus` (to narrow) is required")
        return self


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
