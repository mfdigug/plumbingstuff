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


class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    max_results: int = Field(default=20, ge=1, le=50)


class SearchResponse(BaseModel):
    request_id: str
    query: str
    generated_at: str
    results: list[ProductCandidateOut]
    result_count: int


class RefineFiltersIn(BaseModel):
    brand: Optional[str] = None
    size: Optional[str] = None
    finish: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    connection_type: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None


class RefineRequest(BaseModel):
    candidate_skus: list[str]
    filters: RefineFiltersIn = RefineFiltersIn()
    query: Optional[str] = None


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
