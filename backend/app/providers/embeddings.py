"""Embedding provider adapter (design §10, §13).

`fake` is deterministic (hash-based) and default for dev/CI. `openai` uses
text-embedding-3-*. Anthropic has no first-party embeddings API — pair with
Voyage when you need a Claude-aligned embedding model (out of MVP scope).
"""
from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from typing import List, Optional

from ..config import get_settings


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        ...


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic unit-norm vectors from a hash of the text. No network."""

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> List[float]:
        vec: List[float] = []
        i = 0
        # Expand a SHA stream until we have `dim` floats in [-1, 1].
        while len(vec) < self.dim:
            h = hashlib.sha256(f"{i}:{text}".encode()).digest()
            for b in h:
                vec.append((b / 127.5) - 1.0)
                if len(vec) >= self.dim:
                    break
            i += 1
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        from openai import OpenAI  # lazy

        s = get_settings()
        self._client = OpenAI(api_key=s.openai_api_key or None)
        self._model = s.embedding_model

    def embed(self, texts: List[str]) -> List[List[float]]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [d.embedding for d in resp.data]


_provider: Optional[EmbeddingProvider] = None


def get_embedding_provider() -> EmbeddingProvider:
    global _provider
    if _provider is None:
        s = get_settings()
        if s.embedding_provider == "openai":
            _provider = OpenAIEmbeddingProvider()
        else:
            _provider = FakeEmbeddingProvider(s.fake_embedding_dim)
    return _provider


def reset_embedding_provider() -> None:
    global _provider
    _provider = None
