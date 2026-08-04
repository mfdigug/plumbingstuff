from fastapi import APIRouter

from rest_api.cart_store import add_item, get_cart, remove_item
from rest_api.schemas import AddCartItemRequest, CartResponse

router = APIRouter()


@router.get("/cart/{customer_id}", response_model=CartResponse)
async def view_cart(customer_id: str):
    return get_cart(customer_id)


@router.post("/cart/{customer_id}/items", response_model=CartResponse)
async def add_cart_item(customer_id: str, payload: AddCartItemRequest):
    return add_item(customer_id, payload.sku, payload.quantity)


@router.delete("/cart/{customer_id}/items/{sku}", response_model=CartResponse)
async def remove_cart_item(customer_id: str, sku: str):
    return remove_item(customer_id, sku)
