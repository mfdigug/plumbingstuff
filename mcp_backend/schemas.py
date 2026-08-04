from typing import Optional

from pydantic import BaseModel


class ProductCandidate(BaseModel):
    sku: str
    name: str
    brand: str
    category: str
    subcategory: str
    price_aud: float
    attributes: dict = {}
    confidence: float
    match_reason: str


class RefineFilters(BaseModel):
    brand: Optional[str] = None
    size: Optional[str] = None
    finish: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    connection_type: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None


class StoreStock(BaseModel):
    sku: str
    store_id: str
    store_name: str
    suburb: str
    state: str
    postcode: str
    qty_on_hand: int
    status: str  # "in_stock" | "out_of_stock" | "special_order" | "not_carried"
    eta_days: Optional[int] = None
    last_updated: Optional[str] = None
