import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_backend.es_client import get_es_client  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def _require_elasticsearch():
    es = get_es_client()
    try:
        reachable = es.ping()
    except Exception:
        reachable = False
    if not reachable:
        pytest.skip(
            "Elasticsearch not reachable -- run `docker compose up -d elasticsearch` "
            "and `python scripts/run_pipeline.py` first."
        )


@pytest.fixture(scope="session")
def golden_queries():
    with open(FIXTURES_DIR / "golden_queries.yaml") as f:
        return yaml.safe_load(f)["queries"]
