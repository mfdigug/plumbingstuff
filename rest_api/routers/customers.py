from fastapi import APIRouter

from rest_api.customer_store import get_customer
from rest_api.schemas import CustomerProfileOut

router = APIRouter()


@router.get("/customers/{customer_id}", response_model=CustomerProfileOut)
async def get_customer_profile(customer_id: str):
    return get_customer(customer_id)
