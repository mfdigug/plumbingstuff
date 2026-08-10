from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


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


# --- product-search: agent-facing contract, camelCase over the wire (see
# POST /v1/product-search) -- kept snake_case in Python via alias_generator so
# this stays idiomatic internally while matching the external field names the
# calling agent expects.
class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ProductSearchRequest(CamelModel):
    query: str = Field(min_length=1)
    region: Optional[str] = None
    branch_id: Optional[str] = None


class ExtractedItemOut(CamelModel):
    item_index: int
    item_name: str
    quantity: int
    color: str
    material: str
    additional_context: str
    semantic_search_hint: str
    source_spans: list[str]


class ExtractionOut(CamelModel):
    intent: str
    items: list[ExtractedItemOut]
    search_hint: str


class ProductSearchCandidateOut(CamelModel):
    # Real backend runs two independent retrieval paths (a direct ES sales-rank
    # query, and its own semantic/hybrid search) and fields are only populated
    # by whichever path(s) actually produced this candidate -- e.g. an
    # "elasticsearch"-sourced hit carries brand/es_*/source_rank, an
    # "mcp"-sourced one carries country/pack_ratio instead. Only the fields
    # every candidate has regardless of source are required here.
    product_code: str
    description: str
    search_score: float
    item_index: int
    item_name: str
    source: str
    confidence: float
    brand: Optional[str] = None
    es_sales_rank: Optional[int] = None
    es_relevance_score: Optional[float] = None
    es_relevance_normalized: Optional[float] = None
    es_query_strategy: Optional[str] = None
    source_rank: Optional[int] = None
    unit_of_measure: Optional[str] = None
    unit_of_measure2: Optional[str] = None
    gst_exempt: Optional[bool] = None
    image_url: Optional[str] = None
    country: Optional[str] = None
    pack_ratio: Optional[int] = None


class MatchedProductOut(ProductSearchCandidateOut):
    found_by: list[str]
    found_by_both: bool
    top_rank_agreement: bool
    fused_score: float
    quantity: int


class ProductSearchItemOut(CamelModel):
    item_index: int
    item_name: str
    spoken_text: list[str]
    quantity: int
    status: str
    products: list[MatchedProductOut]
    extended_candidates: list[ProductSearchCandidateOut]


class TimingsOut(CamelModel):
    extraction_ms: int
    search_ms: int
    rank_ms: int
    total_ms: int


class ProductSearchResponse(CamelModel):
    request_id: str
    intent: str
    extraction: ExtractionOut
    items: list[ProductSearchItemOut]
    products: list[MatchedProductOut]
    summary: str
    truncated_items: int
    timings: TimingsOut
