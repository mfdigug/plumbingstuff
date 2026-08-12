import uuid

from fastapi import APIRouter, Depends

from rest_api.dependencies import get_mcp_client
from rest_api.schemas import ProductSearchRequest, ProductSearchResponse

router = APIRouter()


@router.post("/product-search", response_model=ProductSearchResponse, response_model_exclude_none=True)
async def product_search(payload: ProductSearchRequest, mcp_client=Depends(get_mcp_client)):
    result = await mcp_client.product_search(payload.query)
    return ProductSearchResponse(request_id=str(uuid.uuid4()), **result)
