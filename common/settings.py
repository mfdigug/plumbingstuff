from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    es_host: str = "http://localhost:9200"
    es_index_products: str = "products"
    es_index_stock: str = "stock"
    es_index_customers: str = "customers"
    es_index_carts: str = "carts"

    embedding_model_name: str = "BAAI/bge-small-en-v1.5"

    mcp_transport: str = "streamable-http"
    mcp_server_host: str = "127.0.0.1"
    mcp_server_port: int = 8100
    mcp_server_url: str = "http://127.0.0.1:8100/mcp"

    rest_api_host: str = "0.0.0.0"
    rest_api_port: int = 8080


settings = Settings()
