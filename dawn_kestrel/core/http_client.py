"""
HTTP client wrapper with retry logic and error handling.

Provides robust HTTP communication with exponential backoff
and comprehensive error handling for AI provider requests.
"""

import httpx
import logging
import asyncio
from typing import Optional, Dict, Any, Union
from decimal import Decimal


logger = logging.getLogger(__name__)


class HTTPClientError(Exception):
    """Custom HTTP client error with retry info"""
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        retry_count: int = 0
    ):
        self.message = message
        self.status_code = status_code
        self.retry_count = retry_count
        super().__init__(message)


class HTTPClientWrapper:
    """Wrapper for httpx with retry logic and comprehensive error handling"""

    def __init__(
        self,
        base_timeout: float = 600.0,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 32.0,
        backoff_multiplier: float = 2.0
    ):
        self.base_timeout = base_timeout
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier

    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """POST request with retry logic"""
        return await self._request_with_retry(
            method="POST",
            url=url,
            json=json,
            headers=headers,
            timeout=timeout
        )

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """GET request with retry logic"""
        return await self._request_with_retry(
            method="GET",
            url=url,
            headers=headers,
            timeout=timeout
        )

    async def stream(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ):
        """Streaming request with retry logic"""
        return self._stream_with_retry(
            method=method,
            url=url,
            json=json,
            headers=headers,
            timeout=timeout
        )

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """Execute HTTP request with retry logic"""
        actual_timeout = timeout if timeout is not None else self.base_timeout
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=actual_timeout) as client:
                    if method == "POST":
                        response = await client.post(
                            url=url,
                            json=json,
                            headers=headers
                        )
                    elif method == "GET":
                        response = await client.get(
                            url=url,
                            headers=headers
                        )
                    else:
                        raise HTTPClientError(
                            f"Unsupported HTTP method: {method}"
                        )

                    self._check_response_status(response)
                    response.raise_for_status()
                    return response

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.max_retries:
                    backoff = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Timeout on attempt {attempt + 1}/{self.max_retries + 1}: {url}. "
                        f"Retrying in {backoff}s..."
                    )
                    await asyncio.sleep(backoff)

            except httpx.NetworkError as e:
                last_error = e
                if attempt < self.max_retries:
                    backoff = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Network error on attempt {attempt + 1}/{self.max_retries + 1}: {url}. "
                        f"Retrying in {backoff}s..."
                    )
                    await asyncio.sleep(backoff)

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                last_error = e

                if self._is_retryable_error(status_code) and attempt < self.max_retries:
                    backoff = self._calculate_backoff(attempt)
                    logger.warning(
                        f"HTTP {status_code} on attempt {attempt + 1}/{self.max_retries + 1}: {url}. "
                        f"Retrying in {backoff}s..."
                    )
                    await asyncio.sleep(backoff)
                else:
                    raise HTTPClientError(
                        f"HTTP error {status_code}: {str(e)}",
                        status_code=status_code,
                        retry_count=attempt + 1
                    )

            except httpx.RequestError as e:
                last_error = e
                if attempt < self.max_retries:
                    backoff = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Request error on attempt {attempt + 1}/{self.max_retries + 1}: {url}. "
                        f"Retrying in {backoff}s..."
                    )
                    await asyncio.sleep(backoff)

        raise HTTPClientError(
            f"Failed after {self.max_retries + 1} attempts: {str(last_error)}",
            retry_count=self.max_retries
        )

    async def _stream_with_retry(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ):
        """Execute streaming HTTP request with retry logic (for initial connection only)"""
        actual_timeout = timeout if timeout is not None else self.base_timeout
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=actual_timeout) as client:
                    if method == "POST":
                        response_stream = client.stream(
                            method="POST",
                            url=url,
                            json=json,
                            headers=headers
                        )
                    else:
                        raise HTTPClientError(
                            f"Unsupported HTTP method for streaming: {method}"
                        )

                    yield response_stream
                    return

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.max_retries:
                    backoff = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Timeout on streaming attempt {attempt + 1}/{self.max_retries + 1}: {url}. "
                        f"Retrying in {backoff}s..."
                    )
                    await asyncio.sleep(backoff)

            except httpx.NetworkError as e:
                last_error = e
                if attempt < self.max_retries:
                    backoff = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Network error on streaming attempt {attempt + 1}/{self.max_retries + 1}: {url}. "
                        f"Retrying in {backoff}s..."
                    )
                    await asyncio.sleep(backoff)

        raise HTTPClientError(
            f"Failed to establish streaming connection after {self.max_retries + 1} attempts: {str(last_error)}",
            retry_count=self.max_retries
        )

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        backoff = min(
            self.initial_backoff * (self.backoff_multiplier ** attempt),
            self.max_backoff
        )
        return float(backoff)

    def _check_response_status(self, response: httpx.Response) -> None:
        """Check response for error status codes"""
        status_code = response.status_code

        if status_code == 401:
            raise HTTPClientError(
                "Authentication failed: Invalid or expired API key",
                status_code=status_code
            )
        elif status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise HTTPClientError(
                f"Rate limit exceeded. Retry after {retry_after}s",
                status_code=status_code
            )
        elif status_code >= 500:
            raise HTTPClientError(
                f"Server error: {status_code}",
                status_code=status_code
            )

    def _is_retryable_error(self, status_code: int) -> bool:
        """Determine if HTTP error is retryable"""
        return status_code in [429, 500, 502, 503, 504]


def create_http_client(
    base_timeout: float = 600.0,
    max_retries: int = 3
) -> HTTPClientWrapper:
    """Factory function to create HTTP client wrapper"""
    return HTTPClientWrapper(
        base_timeout=base_timeout,
        max_retries=max_retries
    )
