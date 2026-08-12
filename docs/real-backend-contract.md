# Real backend contract notes — maX Voice BFF API (2.0.0)

Working notes captured from the real API docs (OpenAPI spec `maX Voice BFF API`,
`/max-voice-bff/api/openapi`), kept here so we can align `mcp_backend`/`rest_api`
against the real contract incrementally without re-pasting the docs each time.
This is the system this repo mocks (see `pyproject.toml` description and the
"real backend's contract" comments throughout `mcp_backend/search.py` /
`rest_api/main.py`).

Source: two doc excerpts pasted 2026-08-12 — the guide-style overview of
`POST /api/v1/product-search`, and the Swagger "Try it out" operation detail
for the same endpoint (fuller field list + error responses).

## What the service is

"maX Voice BFF" = Backend-for-Frontend for the maX Voice assistant. Clients
(iOS app, admin web UI, partner integrations hitting `/api/v1/*`) only ever
talk to this BFF; it fans out to a core GraphQL service, Amazon Bedrock,
Polly, and S3. Base path is `/max-voice-bff`, so the product-search route is
really `/max-voice-bff/api/v1/product-search`.

## `POST /api/v1/product-search`

**Request**
```json
{ "query": "I need a 90mm stormwater flex and a roll of PTFE tape", "region": "AU", "branchId": "1234" }
```
- Send the raw spoken sentence — do NOT pre-split into items. Multi-item
  extraction is part of the pipeline and uses cross-item context (e.g. "20mm
  copper pipe and some elbows" — the elbows inherit the 20mm from the first
  item). This matches our `mcp_backend/server.py` tool docstring already.
- `userId` is taken from the auth credential and is ignored if sent in the body.
- `region` / `branchId` optional. (`threadId`/`clientId` are mentioned as
  optional elsewhere in the guide but don't appear in this endpoint's own
  request schema — possibly copied from a shared block; unconfirmed for
  product-search specifically.)

**Pipeline, per their description**: extraction → two retrieval backends run
in parallel (Elasticsearch for keywords, a vector index for meaning) → fused
→ grouped into product families → re-ranked by an LLM (Bedrock). "Three model
calls plus retrieval" — budget **seconds**, not milliseconds (their captured
example: 12.8s total, 3.2s retrieval, 9.6s across two model calls). A voice
client should cover the wait with a holding phrase.

**Response envelope** (top level):
- `requestId` — identifies the call in their telemetry; log it.
- `intent` — `"product_search"`.
- `items` — one entry per distinct thing the customer asked for.
- `summary` — human-readable one-liner.
- `truncatedItems` — count of items dropped to stay under a 20-item cap.
  Nonzero means the response only covers a prefix of the utterance; caller
  should split and re-call.
- `timings` — `{extractionMs, searchMs, rankMs, totalMs}`.

**Per item** (`items[]`):
- `itemIndex`, `itemName`, `spokenText` (array — the literal words that drove
  the search for *this* item, meant to be quoted back to the customer instead
  of the catalogue description), `quantity`.
- `status` — **the whole contract boils down to this field**:
  - `matched` → take `products[0]`, no question needed.
  - `needs_checking` → confirm before adding; lead with `products[0]`,
    quoting `spokenText`.
  - `not_found` → `products` is empty. Still a 200, not an error — a
    legitimate zero-result outcome to raise with the customer.
- `products` — the ranked shortlist. Each has its own verdict.
- `alternates` — everything else retrieval found, deduplicated, shortlist
  excluded, **no ranking verdict at all** (no rank/confidenceLevel/rationale
  — just catalogue display fields: `productCode`, `description`,
  `unitOfMeasure`(+`2`), `gstExempt`, `packRatio`, `imageUrl`). When the
  customer says "no, the other one," it's very likely already in this list —
  offer it directly, no extra request needed. Only re-call when they name
  something in neither list.

**Per shortlisted product** (`products[]`):
- `productCode`, `description`, `brand` (opaque numeric string, e.g.
  `"103000"` — matches how our mock already fakes this via `_brand_code`),
  `quantity`, `unitOfMeasure` / `unitOfMeasure2` / `packRatio`, `gstExempt`,
  `imageUrl`.
- `rank` (1-based position within the shortlist).
- `confidenceLevel` — **categorical**: `"high"` / `"medium"` / `"low"`. This
  is what drives the item's `status`. There is **no numeric score anywhere in
  the response** ("no internal scores on this response; everything present
  is meant to be used") — deliberately different from our mock's
  `confidence: float` / `search_score` fields.
- `rationale` — a short, human-written, **quotable** sentence explaining the
  verdict (e.g. "the grey variant is the highest-selling exact match").
  Written by the LLM re-ranking pass, not a templated string.
- `familyName` — groups variants of the *same underlying product* (e.g. grey
  vs. white PTFE tape of the same size/brand are one family; a genuinely
  different product is a different family). New concept, no analog in our
  current schema.

## Gaps vs. our mock — closed 2026-08-12

All six gaps below are now closed in `mcp_backend/search.py` /
`rest_api/schemas.py`. Kept here as a record of what changed and why, not as
an open list:

1. **`status`** is now the real 3-valued enum (`matched` / `needs_checking` /
   `not_found`), typed as a `Literal` in `ProductSearchItemOut`.
2. **`confidenceLevel` + `rationale`** added; the old numeric `confidence`/
   `search_score` fields are gone from the external shape entirely, matching
   the real contract's "no score of any kind" stance.
3. **`familyName`** added (see "Mock simplifications" below for how it's
   derived).
4. **`alternates`** (renamed from `extended_candidates`) is now the lean,
   score-free catalogue-display shape the real contract uses — no
   `rank`/`confidenceLevel`/`rationale`/`familyName`/`brand`/`quantity`.
5. Shortlist/alternate caps left as-is (`matched_per_item=4`,
   `extended_per_item=8`) — close enough to the real example (2 shortlisted +
   8 alternates); not worth chasing an exact number since the real re-ranker
   decides this dynamically and we don't have one.
6. Also removed, since neither exists in the real contract: the invented
   top-level `extraction` block and the flattened top-level `products` list.
   Per-item fields (`itemIndex`/`itemName`/`spokenText`/`quantity`) already
   carry what `extraction` used to duplicate.

Fields that already matched and still do: request shape
(`query`/`region`/`branchId`), envelope (`requestId`/`intent`/`summary`/
`truncatedItems`/`timings`), per-product `brand`/`unitOfMeasure(2)`/
`packRatio`/`gstExempt`/`imageUrl`/`quantity`.

## Mock simplifications, on purpose

This mock does not call a real re-ranking LLM (the real backend's Bedrock
pass) and does not run two independent retrieval backends. Everything the
real contract attributes to that pipeline is derived instead from the single
existing BM25+kNN hybrid signal already computed in
`mcp_backend/search.py::search_products`:

- **`confidenceLevel`** — the existing numeric `confidence` bucketed at two
  thresholds (`HIGH_CONFIDENCE_THRESHOLD=0.65`, `MEDIUM_CONFIDENCE_THRESHOLD=
  0.35`). Tune freely; there's nothing authoritative about these numbers.
- **`rationale`** — a templated sentence keyed off the same match-reason logic
  (`_match_reason`) that already existed for internal debugging, not a
  generated one.
- **`familyName`** — `f"{brand} {subcategory}"`, a cheap grouping heuristic.
  No attribute-stripping cleverness (e.g. it won't notice that two entries
  differ only by color) — good enough for a mock, not a real family model.
- **`status`** — `matched` iff the top shortlisted product's confidenceLevel
  is `"high"`, else `needs_checking` (or `not_found` with zero candidates).
  This is also where the earlier, separately-discussed "ES should match
  precisely first, MCP falls back to semantic search" idea landed: rather
  than a second literal retrieval path, a strong literal/BM25 hit reads as
  high confidence and a weak/semantic-only hit reads as low — same effect,
  no new architecture.

**None of this is meant to survive contact with the real API.** When real
access lands, delete `_confidence_level`/`_rationale`/`_family_name` and the
status-derivation logic in `_build_item_result` wholesale — they exist only so
agent/bridging-phrase work has real fields to build against in the meantime.

## Auth, errors, rate limits, telemetry (context, not yet relevant to our mock)

- **Auth**: 4 credential channels gated by route group — `/api/threads`,
  `/api/chat`, `/api/voice`, `/api/selection` accept JWT (bearer,
  `x-forwarded-access-token`, or `max_voice_token` cookie) *or* an admin
  session cookie; `/api/v1/*` (our endpoint) accepts **JWT only, no admin
  cookie fallback**; `/api/admin/*` is Okta admin session only; `/api/eval/*`
  is a static bearer token; `/health-check*` and `/api/auth/*` need nothing.
  Sharp edge: if a session cookie is present it wins over a bearer token with
  no fallback — a stale cookie causes 401 even with a valid JWT also sent.
- **Errors**: `{error, code?}`; validation failures are
  `{error: "Validation failed", code: "VALIDATION_ERROR", details: [{path, message}]}`.
  Admin/eval routes and `/api/chat` sometimes double-encode the upstream error
  into the `error`/`message` string.
- **Rate limits**: 600 req/min/IP overall, 200/min for `/api/admin/*`, and
  `/api/v1/*` has its *own* separate 600/min counter. 429 with
  `Retry-After: 60`. `/health-check*` and `/api-docs` unlimited.
- **Telemetry**: every turn (from `/api/chat` or `/api/v1/product-search`)
  lands in `chat_turn_telemetry` with a `channel` (`chat` vs `product_search`)
  — any aggregation must filter on it. `clientId` tags a specific partner
  integration (null for app traffic); eval sweeps tag `clientId:
  "max-voice-eval"` with no `threadId` and should usually be excluded.
- **Selection vs. cart**: a "selection" is the BFF's own per-thread list of
  gathered products (inert until acted on); the maX **cart** belongs to the
  iOS app and this service never writes to it — `finalize` just stamps the
  selection and hands its id to the app. Not relevant to a pure search
  integration — "if you own the conversation, you own the basket."
- Endpoint is fully **read-only**: no session, no basket, no server-side state
  to keep in sync with the caller.
