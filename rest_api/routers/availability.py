from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends

from rest_api.cart_store import product_exists
from rest_api.dependencies import get_mcp_client
from rest_api.errors import NotFoundError
from rest_api.schemas import AvailabilityResponse

router = APIRouter()


@router.get("/availability", response_model=AvailabilityResponse)
async def availability(
    sku: str,
    store_id: Optional[str] = None,
    state: Optional[str] = None,
    postcode: Optional[str] = None,
    mcp_client=Depends(get_mcp_client),
):
    if not product_exists(sku):
        raise NotFoundError("sku_not_found", f"No product with sku '{sku}'")

    locations = await mcp_client.availability(sku, store_id=store_id, state=state, postcode=postcode)
    return AvailabilityResponse(
        sku=sku,
        generated_at=datetime.now(timezone.utc).isoformat(),
        locations=locations,
    )
