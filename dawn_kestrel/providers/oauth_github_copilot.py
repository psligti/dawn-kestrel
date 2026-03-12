"""GitHub OAuth 2.0 Device Code Flow implementation.

Implements and standard OAuth 2.0 Device Authorization Grant for GitHub.
This allows authenticating CLI tools without running a local HTTP server.

Based on: RFC 8628 (OAuth 2.0 Device Authorization Grant)
GitHub endpoints: https://docs.github.com/en/developers/apps/authorizing-oauth-apps
"""

import time
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GitHubOAuthClient:
    """GitHub OAuth Device Authorization Grant client.

    Standard OAuth 2.0 Device Authorization Grant implementation
    for authenticating CLI tools and headless applications.
    """

    DEVICE_CODE_URL = "https://github.com/login/device/code"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    DEFAULT_CLIENT_ID = "Ov23li8tweQw6odWQebz"

    def __init__(self, client_id: str | None = None) -> None:
        self.client_id = client_id or self.DEFAULT_CLIENT_ID

    def request_device_code(
        self,
        scopes: list[str] | None = None,
    ) -> dict[str, Any]:
        if not self.client_id:
            raise RuntimeError("client_id is required")

        scope_str = "read:user" if scopes else ""

        payload = {
            "client_id": self.client_id,
            "scope": scope_str,
        }

        try:
            with httpx.Client() as client:
                response = client.post(
                    self.DEVICE_CODE_URL,
                    json=payload,
                    timeout=30.0,
                    headers={"Accept": "application/json", "Content-Type": "application/json"},
                )
                response.raise_for_status()

                content = response.text.strip()
                if not content:
                    raise RuntimeError(f"Empty response from GitHub: {response.status_code}")

                return response.json()
        except httpx.HTTPStatusError as e:
            error_text = e.response.text if e.response else str(e)
            raise RuntimeError(
                f"Failed to request device code (HTTP {e.response.status_code}): {error_text}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to request device code: {e}") from e

    def exchange_device_code(
        self,
        device_code: str,
    ) -> dict[str, Any]:
        if not self.client_id:
            raise RuntimeError("client_id is required")

        payload = {
            "client_id": self.client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }

        try:
            with httpx.Client() as client:
                response = client.post(self.TOKEN_URL, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Token exchange failed: {e.response.text}") from e
        except Exception as e:
            raise RuntimeError(f"Token exchange failed: {e}") from e

    async def poll_for_token(
        self,
        device_code_response: dict[str, Any],
    ) -> dict[str, Any]:
        device_code = device_code_response.get("device_code", "")
        interval = device_code_response.get("interval", 5)
        expires_in = device_code_response.get("expires_in", 900)

        if not device_code:
            raise RuntimeError("No device code in response")

        end_time = time.time() + expires_in

        last_poll_time = time.time()

        poll_count = 0
        max_polls = 900 / max(interval, 1)

        while time.time() < end_time and poll_count < max_polls:
            poll_count += 1
            elapsed_since_last_poll = time.time() - last_poll_time

            if elapsed_since_last_poll >= interval:
                last_poll_time = time.time()
                try:
                    tokens = self.exchange_device_code(device_code)
                except Exception as e:
                    logger.debug(f"Poll {poll_count} failed: {e}")
                    raise RuntimeError(f"Token exchange failed: {e}") from e

                if "access_token" in tokens:
                    logger.debug(f"Got token after {poll_count} polls")
                    return tokens
                elif "error" in tokens:
                    error = tokens.get("error", "")
                    if error == "authorization_pending":
                        logger.debug(f"Still pending after poll {poll_count}")
                        continue
                    else:
                        logger.debug(f"Got error: {error}")
                        raise RuntimeError(f"Token exchange failed: {error}")
            else:
                time.sleep(1)

        raise RuntimeError("Authorization timed out - user didn't authorize in time")

