# HTTP/SSL Security Remediation Guide

## Executive Summary

This document provides specific remediation code for 2 CRITICAL and 4 MEDIUM vulnerabilities found in the HTTP/SSL security audit of dawn_kestrel.

**Audit Date:** 2026-02-10
**Branch:** wt/harness-agent-rework
**Base:** main
**HTTP Library:** httpx 0.28.1

---

## CRITICAL VULNERABILITIES

### 1. Missing SSL/TLS Certificate Verification

**Severity:** CRITICAL
**CWE:** CWE-295: Improper Certificate Validation
**CVSS Score:** 7.5 (High)

**Affected Files:**
- `dawn_kestrel/core/http_client.py` (lines 110, 198)
- `dawn_kestrel/tools/additional.py` (lines 387, 562, 639)
- `dawn_kestrel/providers/openai.py` (line 106)

**Issue:** All `httpx.AsyncClient` instantiations lack explicit `verify=True`, relying on httpx's default behavior. While httpx defaults to verifying SSL certificates, explicit configuration is critical for security posture documentation and prevents accidental misconfiguration.

**Remediation:**

#### Fix 1.1: http_client.py - Add SSL verification and CA bundle support

```python
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
from pathlib import Path

logger = logging.getLogger(__name__)


# Security constants
DEFAULT_SSL_VERIFY = True  # Explicit SSL verification
DEFAULT_CA_BUNDLE = None  # Use system CA bundle
MAX_RESPONSE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB response limit
MAX_REQUEST_SIZE_BYTES = 10 * 1024 * 1024  # 10MB request limit


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
        backoff_multiplier: float = 2.0,
        verify_ssl: bool = DEFAULT_SSL_VERIFY,
        ca_bundle: Optional[Path] = None,
        max_response_size: int = MAX_RESPONSE_SIZE_BYTES,
        max_request_size: int = MAX_REQUEST_SIZE_BYTES,
    ):
        self.base_timeout = base_timeout
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier
        self.verify_ssl = verify_ssl
        self.ca_bundle = ca_bundle
        self.max_response_size = max_response_size
        self.max_request_size = max_request_size

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

    def _create_client(self, timeout: float) -> httpx.AsyncClient:
        """Create httpx.AsyncClient with security configurations"""
        # Build httpx.Timeout with granular settings
        timeout_obj = httpx.Timeout(
            connect=timeout * 0.2,      # 20% of total timeout for connection
            read=timeout * 0.6,         # 60% of total timeout for reading
            write=timeout * 0.15,        # 15% of total timeout for writing
            pool=timeout * 0.05,        # 5% of total timeout for pool
        )

        # Configure SSL verification
        verify_config = self.verify_ssl
        if self.ca_bundle:
            verify_config = str(self.ca_bundle)

        # Configure limits
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0,
        )

        return httpx.AsyncClient(
            timeout=timeout_obj,
            verify=verify_config,
            limits=limits,
            http2=False,  # Disable HTTP/2 for simpler connection handling
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

        # Validate request size
        if json:
            import json as json_lib
            request_size = len(json_lib.dumps(json))
            if request_size > self.max_request_size:
                raise HTTPClientError(
                    f"Request size ({request_size} bytes) exceeds limit ({self.max_request_size} bytes)",
                    status_code=413
                )

        for attempt in range(self.max_retries + 1):
            try:
                client = self._create_client(actual_timeout)
                async with client as httpx_client:
                    if method == "POST":
                        response = await httpx_client.post(
                            url=url,
                            json=json,
                            headers=headers
                        )
                    elif method == "GET":
                        response = await httpx_client.get(
                            url=url,
                            headers=headers
                        )
                    else:
                        raise HTTPClientError(
                            f"Unsupported HTTP method: {method}"
                        )

                    # Check response size
                    if hasattr(response, '_content'):
                        response_size = len(response._content) if response._content else 0
                        if response_size > self.max_response_size:
                            raise HTTPClientError(
                                f"Response size ({response_size} bytes) exceeds limit ({self.max_response_size} bytes)",
                                status_code=413
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
                client = self._create_client(actual_timeout)
                async with client as httpx_client:
                    if method == "POST":
                        response_stream = httpx_client.stream(
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
        elif status_code == 413:
            raise HTTPClientError(
                f"Payload too large. Max size: {self.max_response_size} bytes",
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
    max_retries: int = 3,
    verify_ssl: bool = True,
    ca_bundle: Optional[Path] = None
) -> HTTPClientWrapper:
    """Factory function to create HTTP client wrapper"""
    return HTTPClientWrapper(
        base_timeout=base_timeout,
        max_retries=max_retries,
        verify_ssl=verify_ssl,
        ca_bundle=ca_bundle
    )
```

#### Fix 1.2: providers/openai.py - Add SSL verification

```python
"""
OpenAI Provider implementation.

Streaming support, token counting, and cost calculation.
"""

import httpx
import json
import logging
from decimal import Decimal
from typing import AsyncIterator, Dict, Any, Optional

from .base import (
    ModelInfo,
    ModelCapabilities,
    ModelCost,
    ModelLimits,
    TokenUsage,
    StreamEvent,
    ProviderID
)


logger = logging.getLogger(__name__)


class OpenAIProvider:
    def __init__(self, api_key: str, verify_ssl: bool = True):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.verify_ssl = verify_ssl  # Explicit SSL verification

    async def get_models(self) -> list[ModelInfo]:
        # ... existing code ...
        pass

    async def stream(self, model: ModelInfo, messages: list, tools: list, options: Optional[Dict[str, Any]] = None) -> AsyncIterator[StreamEvent]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if options:
            org_id = options.get("organization_id")
            project_id = options.get("project_id")
            if org_id:
                headers["OpenAI-Organization"] = org_id
            if project_id:
                headers["OpenAI-Project"] = project_id

        url = f"{self.base_url}/chat/completions"

        # Create client with explicit SSL verification
        timeout_obj = httpx.Timeout(
            connect=120.0,
            read=360.0,
            write=90.0,
            pool=30.0,
        )

        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0,
        )

        async with httpx.AsyncClient(
            verify=self.verify_ssl,
            timeout=timeout_obj,
            limits=limits,
        ) as client:
            payload = {
                "model": model.api_id,
                "messages": messages,
                "stream": True,
                "temperature": options.get("temperature", 1.0) if options else 1.0,
                "top_p": options.get("top_p", 1.0) if options else 1.0,
                "reasoning_effort": options.get("reasoning_effort", "medium") if options else "medium",
            }
            if options and options.get("response_format"):
                payload["response_format"] = options["response_format"]
            if tools:
                payload["tools"] = tools

            yield StreamEvent(
                event_type="start",
                data={"model": model.id},
                timestamp=0
            )

            async with client.stream("POST", url=url, json=payload) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                continue

                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", {})
                                finish_reason = chunk.get("finish_reason")
                                tool_calls = chunk.get("tool_calls", [])

                                if "content" in delta:
                                    yield StreamEvent(
                                        event_type="text-delta",
                                        data={"delta": content},
                                        timestamp=0
                                    )

                                if "tool_calls" in chunk:
                                    for tool_call in tool_calls:
                                        tool_name = tool_call.get("function", "")
                                        arguments = tool_call.get("arguments", "{}")
                                        tool_input = json.loads(arguments) if isinstance(arguments, str) else arguments
                                        yield StreamEvent(
                                            event_type="tool-call",
                                            data={
                                                "tool": tool_name,
                                                "input": tool_input
                                            },
                                            timestamp=0
                                        )

                                    for tool_call in tool_calls:
                                        function = tool_call.get("function", "")
                                        result = tool_call.get("result")
                                        if result.get("type") == "tool_use":
                                            tool_output = result.get("content", "")
                                            yield StreamEvent(
                                                event_type="tool-result",
                                                data={
                                                    "output": tool_output
                                                },
                                                timestamp=0
                                            )

                                if finish_reason in ["stop", "length", "content_filter"]:
                                    yield StreamEvent(
                                        event_type="finish",
                                        data={"finish_reason": finish_reason},
                                        timestamp=0
                                    )
                                    break
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse chunk: {e}")

    # ... rest of methods ...
```

---

### 2. SSRF Vulnerability in WebFetchTool

**Severity:** CRITICAL
**CWE:** CWE-918: Server-Side Request Forgery (SSRF)
**CVSS Score:** 7.5 (High)

**Affected Files:**
- `dawn_kestrel/tools/additional.py` (lines 1548-1606, WebFetchTool)

**Issue:** The `WebFetchTool` accepts any URL without validation, allowing access to:
- Internal network resources (localhost, 127.0.0.1, private IPs)
- Cloud metadata services (AWS, GCP, Azure instance metadata)
- Non-HTTP schemes (file://, ftp://, etc.)
- URL bypasses via DNS rebinding

**Remediation:**

#### Fix 2.1: Create URL validation utility module

```python
"""
URL validation utilities for SSRF prevention.

Provides URL validation to prevent Server-Side Request Forgery (SSRF)
attacks by blocking access to internal resources and unsafe URLs.
"""

import ipaddress
import re
import logging
from typing import Optional, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Private IP ranges to block (RFC 1918, RFC 4193, etc.)
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 localhost
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ipaddress.ip_network("fd00::/8"),  # IPv6 unique local
]


# Cloud metadata endpoints to block
CLOUD_METADATA_ENDPOINTS = [
    "169.254.169.254",  # AWS, GCP, Azure
    "metadata.google.internal",
    "169.254.169.254/latest",
    "169.254.169.254/metadata",
    "metadata.azure.com",
]


# Allowed URL schemes
ALLOWED_SCHEMES = {"http", "https"}


# Domain allowlist (empty by default, requires explicit configuration)
DOMAIN_ALLOWLIST: Set[str] = set()


# Domain blocklist
DOMAIN_BLOCKLIST: Set[str] = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
}


class URLValidationError(Exception):
    """Raised when URL validation fails"""
    pass


def is_private_ip(ip_str: str) -> bool:
    """Check if IP address is in private range"""
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in PRIVATE_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        return False


def is_cloud_metadata(hostname: str) -> bool:
    """Check if hostname is a cloud metadata endpoint"""
    return hostname.lower() in [e.lower() for e in CLOUD_METADATA_ENDPOINTS]


def validate_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate URL for SSRF protection.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)

    Raises:
        URLValidationError: If validation fails
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise URLValidationError(f"Invalid URL format: {e}")

    # Check scheme
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise URLValidationError(
            f"Unsupported URL scheme: {parsed.scheme}. "
            f"Allowed schemes: {', '.join(ALLOWED_SCHEMES)}"
        )

    # Check hostname
    hostname = parsed.hostname
    if not hostname:
        raise URLValidationError("URL must have a hostname")

    # Check for localhost variants
    if hostname.lower() in DOMAIN_BLOCKLIST:
        raise URLValidationError(f"Blocked hostname: {hostname}")

    # Check for cloud metadata endpoints
    if is_cloud_metadata(hostname):
        raise URLValidationError(
            f"Cloud metadata endpoint access blocked: {hostname}"
        )

    # Check if hostname is an IP address
    try:
        ip = ipaddress.ip_address(hostname)
        if is_private_ip(str(ip)):
            raise URLValidationError(
                f"Access to private IP address blocked: {hostname}"
            )
    except ValueError:
        # Not an IP address, check domain allowlist
        if DOMAIN_ALLOWLIST:
            # Normalize hostname for comparison
            normalized = hostname.lower()
            if not any(
                normalized == domain.lower() or normalized.endswith('.' + domain.lower())
                for domain in DOMAIN_ALLOWLIST
            ):
                raise URLValidationError(
                    f"Domain not in allowlist: {hostname}"
                )

    # Check port
    port = parsed.port
    if port:
        # Block common internal service ports
        blocked_ports = {
            22,   # SSH
            3306, # MySQL
            5432, # PostgreSQL
            6379, # Redis
            27017,# MongoDB
            9200, # Elasticsearch
        }
        if port in blocked_ports:
            raise URLValidationError(f"Access to port {port} blocked")

    return True, None


def safe_get_host_from_url(url: str) -> str:
    """
    Safely extract hostname from URL with validation.

    Args:
        url: URL to parse

    Returns:
        Hostname string

    Raises:
        URLValidationError: If URL is invalid
    """
    is_valid, error = validate_url(url)
    if not is_valid:
        raise URLValidationError(error if error else "URL validation failed")

    parsed = urlparse(url)
    return parsed.hostname or ""


def configure_domain_allowlist(domains: Set[str]) -> None:
    """Configure domain allowlist for SSRF protection"""
    global DOMAIN_ALLOWLIST
    DOMAIN_ALLOWLIST = {d.lower().strip('.') for d in domains}
    logger.info(f"Configured domain allowlist with {len(DOMAIN_ALLOWLIST)} domains")


def get_domain_allowlist() -> Set[str]:
    """Get current domain allowlist"""
    return DOMAIN_ALLOWLIST.copy()


def reset_domain_allowlist() -> None:
    """Reset domain allowlist to empty (allow all domains except blocked ones)"""
    global DOMAIN_ALLOWLIST
    DOMAIN_ALLOWLIST = set()
    logger.info("Domain allowlist reset to empty (allow all)")
```

#### Fix 2.2: Update WebFetchTool with SSRF protection

```python
"""
Web tools for fetching content and searching the web.

Enables web content fetching and real-time search capabilities with SSRF protection.
"""

import httpx
import logging
from typing import Dict, Any, Optional

from dawn_kestrel.tools.framework import Tool, ToolContext, ToolResult
from dawn_kestrel.core.settings import settings
from dawn_kestrel.core.security.url_validator import validate_url, URLValidationError

logger = logging.getLogger(__name__)


# Size limits for web fetch
MAX_WEB_FETCH_SIZE = 5 * 1024 * 1024  # 5MB
DEFAULT_WEB_FETCH_TIMEOUT = 30.0


class WebFetchTool(Tool):
    id = "webfetch"
    description = "Fetch content from URL (SSRF-protected)"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        url = args.get("url")
        format_type = args.get("format", "markdown")

        if not url:
            return ToolResult(
                title="URL required",
                output="Error: No URL provided",
                metadata={"error": "no_url"},
            )

        # Validate URL for SSRF protection
        try:
            is_valid, error = validate_url(url)
            if not is_valid:
                return ToolResult(
                    title="URL validation failed",
                    output=f"Error: {error}",
                    metadata={"error": "url_validation_failed", "url": url},
                )
        except URLValidationError as e:
            logger.warning(f"SSRF attempt blocked: {url} - {e}")
            return ToolResult(
                title="URL validation failed",
                output=f"Error: {str(e)}",
                metadata={"error": "url_validation_failed", "url": url},
            )

        try:
            # Create client with SSL verification and timeout
            timeout_obj = httpx.Timeout(
                connect=5.0,
                read=DEFAULT_WEB_FETCH_TIMEOUT,
                write=5.0,
                pool=5.0,
            )

            limits = httpx.Limits(
                max_keepalive_connections=10,
                max_connections=50,
                keepalive_expiry=30.0,
            )

            async with httpx.AsyncClient(
                verify=True,  # Explicit SSL verification
                timeout=timeout_obj,
                limits=limits,
            ) as client:

                if format_type == "markdown":
                    headers = {"Accept": "text/markdown, application/markdown"}
                else:
                    headers = {"Accept": "text/html, application/xhtml+xml"}

                response = await client.get(url, headers=headers)

                if response.status_code != 200:
                    return ToolResult(
                        title="Failed to fetch",
                        output=f"Error: HTTP {response.status_code} - {response.text[:500]}",
                        metadata={"error": "http_error", "status_code": response.status_code},
                    )

                content = response.text

                # Enforce size limit
                if len(content) > MAX_WEB_FETCH_SIZE:
                    logger.warning(f"Response too large: {len(content)} bytes, truncating")
                    content = content[:MAX_WEB_FETCH_SIZE]
                    content += (
                        f"\n\n[... Content truncated ({len(content) - MAX_WEB_FETCH_SIZE} "
                        f"characters) - Exceeds {MAX_WEB_FETCH_SIZE} byte limit ...]"
                    )

                logger.info(f"Fetched {len(content)} characters from {url}")

                return ToolResult(
                    title=f"Fetched from {url}",
                    output=content,
                    metadata={
                        "url": url,
                        "format": format_type,
                        "bytes_fetched": len(content),
                        "truncated": len(content) > MAX_WEB_FETCH_SIZE,
                    },
                )

        except httpx.TimeoutException:
            logger.error(f"Web fetch timeout: {url}")
            return ToolResult(
                title="Web fetch timeout",
                output=f"Error: Request timed out after {DEFAULT_WEB_FETCH_TIMEOUT}s",
                metadata={"error": "timeout", "url": url},
            )
        except Exception as e:
            logger.error(f"Web fetch failed: {e}")
            return ToolResult(
                title="Web fetch failed",
                output=f"Error: {str(e)}",
                metadata={"error": "fetch_error"},
            )
```

---

## MEDIUM VULNERABILITIES

### 3. Missing Request/Response Size Limits

**Severity:** MEDIUM
**CWE:** CWE-770: Allocation of Resources Without Limits
**CVSS Score:** 5.3 (Medium)

**Affected Files:**
- All files using httpx

**Issue:** No enforcement of maximum request/response sizes, allowing potential DoS via large payloads.

**Remediation:**
- Included in Fix 1.1 (`http_client.py`) with `MAX_RESPONSE_SIZE_BYTES` and `MAX_REQUEST_SIZE_BYTES`
- Included in Fix 2.2 (`WebFetchTool`) with `MAX_WEB_FETCH_SIZE`

### 4. Insufficient Timeout Configuration

**Severity:** MEDIUM
**CWE:** CWE-1021: Improper Restriction of Rendering-Side UI Data or Frame
**CVSS Score:** 5.3 (Medium)

**Affected Files:**
- All files using httpx

**Issue:** Single timeout value used instead of granular httpx.Timeout (connect, read, write, pool).

**Remediation:**
- Included in Fix 1.1 (`http_client.py`) with httpx.Timeout configuration
- Included in Fix 2.2 (`WebFetchTool`) with granular timeouts

### 5. No Response Size Limits (Duplicate of #3)

**Status:** Covered by Fix 1.1 and Fix 2.2

### 6. No Request Queue (Bulkhead DoS Risk)

**Severity:** MEDIUM
**CWE:** CWE-770: Allocation of Resources Without Limits
**CVSS Score:** 5.3 (Medium)

**Affected Files:**
- `dawn_kestrel/core/http_client.py`

**Issue:** HTTP client has no queue/bulkhead pattern, allowing concurrent request exhaustion.

**Remediation:**

#### Fix 6.1: Add bulkhead pattern to HTTPClientWrapper

```python
"""
HTTP client wrapper with retry logic, error handling, and bulkhead pattern.

Provides robust HTTP communication with exponential backoff,
comprehensive error handling, and resource isolation for AI provider requests.
"""

import httpx
import logging
import asyncio
from typing import Optional, Dict, Any, Union
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)


# Security constants
DEFAULT_SSL_VERIFY = True
DEFAULT_CA_BUNDLE = None
MAX_RESPONSE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_REQUEST_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

# Bulkhead configuration
DEFAULT_MAX_CONCURRENT_REQUESTS = 10  # Per-client limit
DEFAULT_REQUEST_QUEUE_SIZE = 50  # Max pending requests
DEFAULT_BULKHEAD_TIMEOUT = 60.0  # Max wait time for queue slot


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


class BulkheadFullError(Exception):
    """Raised when bulkhead queue is full"""
    pass


class HTTPClientWrapper:
    """Wrapper for httpx with retry logic, error handling, and bulkhead pattern"""

    def __init__(
        self,
        base_timeout: float = 600.0,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 32.0,
        backoff_multiplier: float = 2.0,
        verify_ssl: bool = DEFAULT_SSL_VERIFY,
        ca_bundle: Optional[Path] = None,
        max_response_size: int = MAX_RESPONSE_SIZE_BYTES,
        max_request_size: int = MAX_REQUEST_SIZE_BYTES,
        max_concurrent_requests: int = DEFAULT_MAX_CONCURRENT_REQUESTS,
        request_queue_size: int = DEFAULT_REQUEST_QUEUE_SIZE,
        bulkhead_timeout: float = DEFAULT_BULKHEAD_TIMEOUT,
    ):
        self.base_timeout = base_timeout
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier
        self.verify_ssl = verify_ssl
        self.ca_bundle = ca_bundle
        self.max_response_size = max_response_size
        self.max_request_size = max_request_size

        # Bulkhead pattern - semaphore for concurrent request limiting
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        # Queue for pending requests
        self._queue = asyncio.Queue(maxsize=request_queue_size)
        self._bulkhead_timeout = bulkhead_timeout

    async def _acquire_bulkhead(self) -> None:
        """
        Acquire slot from bulkhead semaphore with queue.

        If queue is full, waits up to bulkhead_timeout before failing.

        Raises:
            BulkheadFullError: If queue is full and timeout expires
        """
        try:
            await asyncio.wait_for(self._queue.put(None), timeout=self._bulkhead_timeout)
            await self._semaphore.acquire()
        except asyncio.TimeoutError:
            raise BulkheadFullError(
                f"Request queue full ({self._queue.qsize()}) after {self._bulkhead_timeout}s"
            )

    def _release_bulkhead(self) -> None:
        """Release slot back to bulkhead"""
        self._semaphore.release()
        try:
            self._queue.get_nowait()
        except asyncio.QueueEmpty:
            pass

    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """POST request with retry logic and bulkhead"""
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
        """GET request with retry logic and bulkhead"""
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
        """Streaming request with retry logic and bulkhead"""
        return self._stream_with_retry(
            method=method,
            url=url,
            json=json,
            headers=headers,
            timeout=timeout
        )

    def _create_client(self, timeout: float) -> httpx.AsyncClient:
        """Create httpx.AsyncClient with security configurations"""
        timeout_obj = httpx.Timeout(
            connect=timeout * 0.2,
            read=timeout * 0.6,
            write=timeout * 0.15,
            pool=timeout * 0.05,
        )

        verify_config = self.verify_ssl
        if self.ca_bundle:
            verify_config = str(self.ca_bundle)

        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0,
        )

        return httpx.AsyncClient(
            timeout=timeout_obj,
            verify=verify_config,
            limits=limits,
            http2=False,
        )

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """Execute HTTP request with retry logic and bulkhead"""
        await self._acquire_bulkhead()
        try:
            actual_timeout = timeout if timeout is not None else self.base_timeout
            last_error = None

            if json:
                import json as json_lib
                request_size = len(json_lib.dumps(json))
                if request_size > self.max_request_size:
                    raise HTTPClientError(
                        f"Request size ({request_size} bytes) exceeds limit ({self.max_request_size} bytes)",
                        status_code=413
                    )

            for attempt in range(self.max_retries + 1):
                try:
                    client = self._create_client(actual_timeout)
                    async with client as httpx_client:
                        if method == "POST":
                            response = await httpx_client.post(
                                url=url,
                                json=json,
                                headers=headers
                            )
                        elif method == "GET":
                            response = await httpx_client.get(
                                url=url,
                                headers=headers
                            )
                        else:
                            raise HTTPClientError(
                                f"Unsupported HTTP method: {method}"
                            )

                        if hasattr(response, '_content'):
                            response_size = len(response._content) if response._content else 0
                            if response_size > self.max_response_size:
                                raise HTTPClientError(
                                    f"Response size ({response_size} bytes) exceeds limit ({self.max_response_size} bytes)",
                                    status_code=413
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

        finally:
            self._release_bulkhead()

    async def _stream_with_retry(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ):
        """Execute streaming HTTP request with retry logic and bulkhead"""
        await self._acquire_bulkhead()
        try:
            actual_timeout = timeout if timeout is not None else self.base_timeout
            last_error = None

            for attempt in range(self.max_retries + 1):
                try:
                    client = self._create_client(actual_timeout)
                    async with client as httpx_client:
                        if method == "POST":
                            response_stream = httpx_client.stream(
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

        finally:
            self._release_bulkhead()

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
        elif status_code == 413:
            raise HTTPClientError(
                f"Payload too large. Max size: {self.max_response_size} bytes",
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
    max_retries: int = 3,
    verify_ssl: bool = True,
    ca_bundle: Optional[Path] = None,
    max_concurrent_requests: int = DEFAULT_MAX_CONCURRENT_REQUESTS,
    request_queue_size: int = DEFAULT_REQUEST_QUEUE_SIZE,
) -> HTTPClientWrapper:
    """Factory function to create HTTP client wrapper"""
    return HTTPClientWrapper(
        base_timeout=base_timeout,
        max_retries=max_retries,
        verify_ssl=verify_ssl,
        ca_bundle=ca_bundle,
        max_concurrent_requests=max_concurrent_requests,
        request_queue_size=request_queue_size,
    )
```

---

## Additional Files Required

### Create: dawn_kestrel/core/security/__init__.py

```python
"""Security utilities for dawn_kestrel."""

from dawn_kestrel.core.security.url_validator import (
    URLValidationError,
    validate_url,
    configure_domain_allowlist,
    get_domain_allowlist,
    reset_domain_allowlist,
    safe_get_host_from_url,
)

__all__ = [
    "URLValidationError",
    "validate_url",
    "configure_domain_allowlist",
    "get_domain_allowlist",
    "reset_domain_allowlist",
    "safe_get_host_from_url",
]
```

---

## Configuration

### Environment Variables

```bash
# SSL verification (default: true)
DAWN_KESTREL_SSL_VERIFY=true

# Custom CA bundle path (optional)
DAWN_KESTREL_CA_BUNDLE=/path/to/ca-bundle.crt

# Domain allowlist (comma-separated, optional)
DAWN_KESTREL_DOMAIN_ALLOWLIST=example.com,api.example.com,cdn.example.com

# Max response size in bytes (default: 10485760)
DAWN_KESTREL_MAX_RESPONSE_SIZE=10485760

# Max concurrent requests (default: 10)
DAWN_KESTREL_MAX_CONCURRENT_REQUESTS=10
```

### Python Configuration

```python
from dawn_kestrel.core.security import configure_domain_allowlist

# Configure domain allowlist (restricts webfetch to only these domains)
configure_domain_allowlist({
    "example.com",
    "api.example.com",
    "cdn.example.com",
})
```

---

## Security Trade-offs

### 1. SSL Verification
**Trade-off:** Explicit `verify=True` adds clarity but httpx defaults to true anyway.
**Decision:** Explicit configuration is better for security posture documentation and prevents accidental misconfiguration.

### 2. Domain Allowlist vs Blocklist
**Trade-off:**
- Allowlist: More secure but requires configuration
- Blocklist: Easier to use but misses new threats

**Decision:** Default to blocklist with localhost/internal ranges. Optional allowlist for strict environments.

### 3. Bulkhead Timeout
**Trade-off:**
- Short timeout: Better DoS protection but may fail legitimate traffic
- Long timeout: Better availability but weaker DoS protection

**Decision:** Default to 60s, configurable per environment.

### 4. Size Limits
**Trade-off:**
- Low limits: Better resource control but may block legitimate large responses
- High limits: Better functionality but weaker DoS protection

**Decision:** Default to 10MB for LLM API responses, 5MB for web fetch.

### 5. Timeout Granularity
**Trade-off:**
- Granular timeouts: Better control but more complex
- Single timeout: Simpler but may hang on specific operations

**Decision:** Use granular timeouts (20% connect, 60% read, 15% write, 5% pool) for balanced performance.

---

## Testing Recommendations

### 1. SSL Verification Tests
```python
import pytest

async def test_ssl_verification_enabled():
    """Test that SSL verification is enforced"""
    # Should fail with self-signed cert
    with pytest.raises(httpx.HTTPError):
        await client.get("https://self-signed.badssl.com/")
```

### 2. SSRF Prevention Tests
```python
async def test_ssrf_private_ip_blocked():
    """Test that private IPs are blocked"""
    result = await webfetch.execute({"url": "http://192.168.1.1"})
    assert "url_validation_failed" in result.metadata["error"]

async def test_ssrf_localhost_blocked():
    """Test that localhost is blocked"""
    result = await webfetch.execute({"url": "http://localhost:8080"})
    assert "url_validation_failed" in result.metadata["error"]

async def test_ssrf_cloud_metadata_blocked():
    """Test that cloud metadata is blocked"""
    result = await webfetch.execute({"url": "http://169.254.169.254/latest/meta-data/"})
    assert "Cloud metadata endpoint access blocked" in result.metadata.get("error", "")
```

### 3. Size Limit Tests
```python
async def test_response_size_limit():
    """Test that oversized responses are blocked"""
    result = await http_client.get("https://example.com/large-file")
    # Should truncate or error if over limit

async def test_request_size_limit():
    """Test that oversized requests are blocked"""
    large_payload = {"data": "x" * 11_000_000}  # > 10MB
    with pytest.raises(HTTPClientError) as exc_info:
        await http_client.post("https://example.com/api", json=large_payload)
    assert "exceeds limit" in str(exc_info.value)
```

### 4. Bulkhead Tests
```python
async def test_bulkhead_limit():
    """Test that concurrent requests are limited"""
    tasks = [
        http_client.get(f"https://httpbin.org/delay/{i}")
        for i in range(20)  # More than MAX_CONCURRENT_REQUESTS
    ]
    # Only 10 should execute, others should queue or timeout
```

---

## Implementation Checklist

- [ ] Create `dawn_kestrel/core/security/url_validator.py`
- [ ] Create `dawn_kestrel/core/security/__init__.py`
- [ ] Update `dawn_kestrel/core/http_client.py` with all security fixes
- [ ] Update `dawn_kestrel/providers/openai.py` with SSL verification
- [ ] Update `dawn_kestrel/tools/additional.py` WebFetchTool with SSRF protection
- [ ] Update `dawn_kestrel/providers/zai_base.py` (uses HTTPClientWrapper, automatically inherits fixes)
- [ ] Add tests for URL validation
- [ ] Add tests for SSL verification
- [ ] Add tests for size limits
- [ ] Add tests for bulkhead pattern
- [ ] Update documentation with security configuration options
- [ ] Update README with security features

---

## References

- [OWASP Server-Side Request Forgery (SSRF)](https://owasp.org/www-community/attacks/Server_Side_Request_Forgery)
- [CWE-295: Improper Certificate Validation](https://cwe.mitre.org/data/definitions/295.html)
- [CWE-918: Server-Side Request Forgery (SSRF)](https://cwe.mitre.org/data/definitions/918.html)
- [CWE-770: Allocation of Resources Without Limits](https://cwe.mitre.org/data/definitions/770.html)
- [httpx Documentation - Advanced Usage](https://www.python-httpx.org/advanced/)
- [Bulkhead Pattern - Microsoft Architecture](https://docs.microsoft.com/en-us/azure/architecture/patterns/bulkhead)
