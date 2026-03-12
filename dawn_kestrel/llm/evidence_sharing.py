from __future__ import annotations

import asyncio
import hashlib
import json
from collections import OrderedDict
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dawn_kestrel.llm.client import LLMResponse


@runtime_checkable
class SupportsToDict(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class LLMRequestFingerprint:
    provider_id: str
    model: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None
    options: dict[str, Any]


@runtime_checkable
class EvidenceSharingStrategy(Protocol):
    async def get(self, request: LLMRequestFingerprint) -> LLMResponse | None: ...

    async def set(self, request: LLMRequestFingerprint, response: LLMResponse) -> None: ...

    async def clear(self) -> None: ...


class NoOpEvidenceSharingStrategy:
    async def get(self, request: LLMRequestFingerprint) -> LLMResponse | None:
        return None

    async def set(self, request: LLMRequestFingerprint, response: LLMResponse) -> None:
        return None

    async def clear(self) -> None:
        return None


class HashMapEvidenceSharingStrategy:
    def __init__(self, max_entries: int = 1000) -> None:
        self._store: OrderedDict[str, LLMResponse] = OrderedDict()
        self._lock = asyncio.Lock()
        self._max_entries = max(1, max_entries)

    def _request_key(self, request: LLMRequestFingerprint) -> str:
        payload = asdict(request)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    async def get(self, request: LLMRequestFingerprint) -> LLMResponse | None:
        key = self._request_key(request)
        async with self._lock:
            result = self._store.get(key)
            if result is None:
                return None
            self._store.move_to_end(key)
            return result

    async def set(self, request: LLMRequestFingerprint, response: LLMResponse) -> None:
        key = self._request_key(request)
        async with self._lock:
            self._store[key] = response
            self._store.move_to_end(key)
            while len(self._store) > self._max_entries:
                self._store.popitem(last=False)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()


def create_request_fingerprint(
    provider_id: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    options: SupportsToDict | dict[str, Any] | None,
) -> LLMRequestFingerprint:
    if options is None:
        normalized_options: dict[str, Any] = {}
    elif isinstance(options, dict):
        normalized_options = options
    else:
        normalized_options = options.to_dict()
    normalized_options = {str(key): value for key, value in normalized_options.items()}
    return LLMRequestFingerprint(
        provider_id=provider_id,
        model=model,
        messages=messages,
        tools=tools,
        options=normalized_options,
    )
