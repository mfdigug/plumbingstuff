# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A **mock backend** for a large AU plumbing ecommerce org, standing in for the real production "maX Voice BFF" (Backend-for-Frontend for a voice assistant) so a voice-agent integration can be built/tested against a realistic contract before real API access exists. Full contract notes and gap-tracking live in `docs/real-backend-contract.md`.

Chain: `REST API -> internal MCP server -> Elasticsearch`.

## Architecture / data flow

```
CLI (cli/demo_cli.py, manual QA REPL)
        │
        ▼
REST API (rest_api/, FastAPI, port 8080)
        │  POST /api/v1/product-search  → MCP tool call
        │  GET  /v1/availability        → MCP tool call
        │  /v1/customers, /v1/cart      → straight to Elasticsearch (bypasses MCP)
        ▼
MCP server (mcp_backend/, port 8100, streamable-HTTP)
        │  tools: product_search, check_availability
        ▼
Elasticsearch (port 9200) — indices: products, stock, customers, carts (mappings/*.json)
```

- MCP is used **only** for the "smart" tools (`product_search`, `check_availability`). Customer/cart CRUD is exact-match, so `rest_api/cart_store.py` talks directly to Elasticsearch via `mcp_backend/es_client.py`'s shared client — no MCP round trip.
- `rest_api/mcp_client.py` opens a **fresh streamable-HTTP MCP connection per tool call**, not a persistent one — deliberate, for anyio cancel-scope safety across FastAPI request tasks. Don't "fix" this into a shared connection.
- `mcp_backend/server.py` is never called externally — only `rest_api/mcp_client.py` talks to it.
- `common/settings.py` holds one shared `pydantic-settings` `Settings` object for both `mcp_backend` and `rest_api`. Its `resolved_es_host`/`resolved_mcp_server_url` properties prefer Render's `*_hostport` vars over plain `*_host`/`*_url` when present — a production-only override, not dead code.
- The REST `product-search` endpoint is deliberately **camelCase over the wire** (`CamelModel` in `rest_api/schemas.py`) to match the real external BFF contract, while every other endpoint stays snake_case. This asymmetry is intentional — don't unify it.

### Search internals (`mcp_backend/`)
- `extraction.py`: heuristic (regex/keyword, no LLM) splitting of an utterance into items with quantity/color/material/unstocked-brand tagging.
- `embeddings.py`: single source of truth for text→vector (`BAAI/bge-small-en-v1.5`, 384-dim). Must be used identically at index time and query time — this is a hard invariant.
- `search.py`: hybrid BM25 + kNN via ES's `rrf` retriever. **BM25 is a required relevance gate — kNN alone is not trustworthy** for this embedding model (see the comment block near the top of the file). Also shapes results into the real BFF's response contract (`status`: matched/needs_checking/not_found; `confidenceLevel`; `rationale`; `familyName`; `alternates`). This derivation logic (confidence/rationale/familyName) is **mock-only scaffolding** standing in for a real LLM re-ranker — flagged in the code to be deleted wholesale once real backend access lands. Don't treat it as permanent architecture.
- `availability.py`: per-store stock lookup; store metadata comes from `data/seed/store_locations.yaml` (static, not ES-indexed). A sku+store combo with no stock doc is synthesized as `"not_carried"` rather than omitted — silence would be ambiguous.

## Data pipeline

- `mappings/` — raw ES index-creation bodies (settings+mappings) for `products`/`stock`/`customers`/`carts`. Note `products_mapping.json`'s custom `trade_synonyms` filter and hand-picked `customer_filler_words` stopword list (deliberately not the generic English stopword list).
- `data/seed/` — committed, curated source-of-truth: `brands.yaml`, `categories.yaml` (drives combinatorial SKU generation), `slang_terms.yaml` (trade slang/mishearings, brand aliases), `explicit_products.yaml` (~45 hand-transcribed anchor products from real invoices), `store_locations.yaml`, `unstocked_brands.yaml` (forces `needs_checking` instead of silent brand substitution).
- `data/generated/` — gitignored build output, produced by the pipeline below.
- `scripts/run_pipeline.py` runs, in order: `generate_mock_catalog.py` → `generate_stock_levels.py` → `generate_customers.py` → `generate_embeddings.py` → `build_es_indices.py` → `load_es_data.py`. Stops on first failing step. **Re-run this after any change to `data/seed/*.yaml` or the embedding model.**

## Commands

Install (dev): `pip install -e ".[dev]"`

Local stack:
- ES only: `docker compose up -d elasticsearch`
- Full stack (ES + mcp-server + rest-api): `docker compose --profile server up -d`
- Add Kibana: `docker compose --profile dev-tools up -d kibana`

Seed/rebuild data (after ES is up): `python scripts/run_pipeline.py`

Run services standalone:
- MCP server: `python -m mcp_backend.server` (or `plumbing-mcp-server` console script); `--transport stdio|streamable-http` (default streamable-http)
- REST API: `uvicorn rest_api.main:app --host 0.0.0.0 --port 8080`
- Manual QA REPL: `python cli/demo_cli.py` (talks to REST, mirroring the real voice-agent caller) or `python cli/demo_cli.py --via-mcp` (bypasses REST, calls mcp_backend directly — useful for isolating ES/scoring bugs from the REST reshaping layer)

Tests: `pytest`
- Requires a **live Elasticsearch** — `tests/conftest.py`'s session-scoped `_require_elasticsearch` fixture skips the whole session if ES is unreachable (hint: `docker compose up -d elasticsearch` then `python scripts/run_pipeline.py`).
- Some `tests/test_rest_api/` tests also require a live mcp-server (`require_live_stack` fixture) — hint: `python -m mcp_backend.server`. Pure REST-layer tests (e.g. error mapping) don't need it.
- No mocking of Elasticsearch/MCP anywhere — tests exercise the real stack.
- `tests/fixtures/golden_queries.yaml` holds ~20 curated slang/ambiguous queries with acceptable-category-set expectations (not exact-SKU expectations) — matches the intentionally fuzzy hybrid scoring.
- No lint/format tooling is configured (no ruff/black/mypy in `pyproject.toml`, no standalone configs).

Render deploy: push → Render Blueprint from `render.yaml` (elasticsearch → private mcp-server → public rest-api). `render.yaml` documents a gotcha: Render's docker-runtime private services need an explicit `port:` field matching the `PORT` env var, or cross-service addressing breaks. After first deploy, seed once via the mcp-server's Render Shell: `curl -X POST "http://$ES_HOSTPORT/_license/start_trial?acknowledge=true"` (unlocks the RRF retriever) then `python scripts/run_pipeline.py`.

## Conventions

- Module docstrings carry load-bearing "why" design decisions (BM25-gating rationale, per-call MCP connections, not_carried-vs-omitted) — read them before changing behavior in `mcp_backend/search.py`, `rest_api/mcp_client.py`, `mcp_backend/availability.py`.
- `docs/real-backend-contract.md` tracks exactly which mock behaviors are deliberate simplifications to be removed once real API access lands — check it before "fixing" something that looks like a shortcut.
- `docs/manual-test-queries.md` is a curated list of ~25 manual QA queries with expected outcomes, organized by category (clean matches, brand slang, needs-checking, unstocked brand, not-found, multi-item, ambiguous words, multi-turn correction) — also documents known quirks (e.g. "flex" ambiguity between stormwater flex pipe and the "Armor Flex" insulation brand).
