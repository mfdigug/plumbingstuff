from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


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


class ProductSearchCandidateOut(CamelModel):
    # This is the "alternates" shape: plain catalogue display facts only, no
    # ranking verdict -- matches the real backend's contract, which attaches
    # no score of any kind to an alternate.
    product_code: str
    description: str
    brand: Optional[str] = None
    quantity: Optional[int] = None
    unit_of_measure: Optional[str] = None
    unit_of_measure2: Optional[str] = None
    gst_exempt: Optional[bool] = None
    image_url: Optional[str] = None
    pack_ratio: Optional[int] = None


class MatchedProductOut(ProductSearchCandidateOut):
    # Shortlisted products additionally carry the re-ranking verdict. The real
    # backend exposes no numeric score here -- only a categorical level plus a
    # quotable, human-written rationale (see mcp_backend/search.py for how
    # this mock derives both from its own BM25+kNN signal).
    rank: int
    confidence_level: Literal["high", "medium", "low"]
    rationale: str
    family_name: Optional[str] = None


class ProductSearchItemOut(CamelModel):
    item_index: int
    item_name: str
    spoken_text: list[str]
    quantity: int
    status: Literal["matched", "needs_checking", "not_found"]
    products: list[MatchedProductOut]
    alternates: list[ProductSearchCandidateOut]


class TimingsOut(CamelModel):
    extraction_ms: int
    search_ms: int
    rank_ms: int
    total_ms: int


class ProductSearchResponse(CamelModel):
    request_id: str
    intent: str
    items: list[ProductSearchItemOut]
    summary: str
    truncated_items: int
    timings: TimingsOut
