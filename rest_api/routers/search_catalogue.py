import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from rest_api.dependencies import get_mcp_client
from rest_api.schemas import SearchCatalogueRequest, SearchCatalogueResponse

router = APIRouter()


@router.post("/search_catalogue", response_model=SearchCatalogueResponse)
async def search_catalogue(payload: SearchCatalogueRequest, mcp_client=Depends(get_mcp_client)):
    results = await mcp_client.search_catalogue(
        items=payload.items,
        category=payload.category,
        max_results_per_item=payload.max_results_per_item,
    )
    return SearchCatalogueResponse(
        request_id=str(uuid.uuid4()),
        generated_at=datetime.now(timezone.utc).isoformat(),
        results=results,
    )
