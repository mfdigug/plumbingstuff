"""Single source of truth for turning text into vectors — used identically at
index time (scripts/generate_embeddings.py) and query time (search.py), so
index and query vectors are never produced by two different code paths.
"""
from functools import lru_cache

from common.settings import settings

EMBEDDING_DIMS = 384


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model_name)


def embed_texts(texts):
    model = _get_model()
    vectors = model.encode(list(texts), normalize_embeddings=False, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed_text(text):
    return embed_texts([text])[0]
