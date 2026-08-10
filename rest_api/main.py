from contextlib import asynccontextmanager

from fastapi import FastAPI

from rest_api.errors import register_exception_handlers
from rest_api.mcp_client import MCPBackendClient
from rest_api.routers import availability, cart, customers, product_search


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mcp_client = MCPBackendClient()
    yield
    await app.state.mcp_client.close()


app = FastAPI(title="Plumbing Mock Backend API", version="0.1.0", lifespan=lifespan)
register_exception_handlers(app)

# Path fixed to match the real backend's contract -- this mock is a
# placeholder for it (see product_search.router) and will be swapped out.
app.include_router(product_search.router, prefix="/api/v1")
app.include_router(availability.router, prefix="/v1")
app.include_router(customers.router, prefix="/v1")
app.include_router(cart.router, prefix="/v1")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
