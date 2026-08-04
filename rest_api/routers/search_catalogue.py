import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from rest_api.dependencies import get_mcp_client
from rest_api.schemas import SearchCatalogueRequest, SearchResponse

router = APIRouter()


@router.post("/search_catalogue", response_model=SearchResponse)
async def search_catalogue(payload: SearchCatalogueRequest, mcp_client=Depends(get_mcp_client)):
    results = await mcp_client.search_catalogue(
        query=payload.query,
        category=payload.category,
        max_results=payload.max_results,
        candidate_skus=payload.candidate_skus,
        filters=payload.filters.model_dump(exclude_none=True) if payload.candidate_skus else None,
    )
    return SearchResponse(
        request_id=str(uuid.uuid4()),
        query=payload.query or "",
        generated_at=datetime.now(timezone.utc).isoformat(),
        results=results,
        result_count=len(results),
    )
