import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from rest_api.dependencies import get_mcp_client
from rest_api.schemas import RefineRequest, SearchResponse

router = APIRouter()


@router.post("/refine", response_model=SearchResponse)
async def refine(payload: RefineRequest, mcp_client=Depends(get_mcp_client)):
    results = await mcp_client.refine(
        payload.candidate_skus,
        payload.filters.model_dump(exclude_none=True),
        query=payload.query,
    )
    return SearchResponse(
        request_id=str(uuid.uuid4()),
        query=payload.query or "",
        generated_at=datetime.now(timezone.utc).isoformat(),
        results=results,
        result_count=len(results),
    )
