import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from rest_api.dependencies import get_mcp_client
from rest_api.schemas import SearchRequest, SearchResponse

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(payload: SearchRequest, mcp_client=Depends(get_mcp_client)):
    results = await mcp_client.search(payload.query, category=payload.category, max_results=payload.max_results)
    return SearchResponse(
        request_id=str(uuid.uuid4()),
        query=payload.query,
        generated_at=datetime.now(timezone.utc).isoformat(),
        results=results,
        result_count=len(results),
    )
