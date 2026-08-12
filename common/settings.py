from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    es_host: str = "http://localhost:9200"
    # Set on Render via `fromService`/`property: hostport` -- takes precedence over
    # es_host when present, since Render's internal hostnames aren't known upfront.
    es_hostport: str = ""
    es_index_products: str = "products"
    es_index_stock: str = "stock"
    es_index_customers: str = "customers"
    es_index_carts: str = "carts"

    embedding_model_name: str = "BAAI/bge-small-en-v1.5"

    mcp_transport: str = "streamable-http"
    mcp_server_host: str = "127.0.0.1"
    mcp_server_port: int = 8100
    mcp_server_url: str = "http://127.0.0.1:8100/mcp"
    # Same idea as es_hostport, for reaching mcp-server from rest-api on Render.
    mcp_server_hostport: str = ""

    @property
    def resolved_es_host(self) -> str:
        if self.es_hostport:
            return f"http://{self.es_hostport}"
        return self.es_host

    @property
    def resolved_mcp_server_url(self) -> str:
        if self.mcp_server_hostport:
            return f"http://{self.mcp_server_hostport}/mcp"
        return self.mcp_server_url


settings = Settings()
