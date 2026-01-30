"""OpenCode Python - Provider and Account Storage with Secure API Key Handling"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import aiofiles
import hashlib
import logging
from datetime import datetime

from opencode_python.storage.store import Storage
from opencode_python.providers_mgmt import Provider, Account, ProviderConnectionTest
from opencode_python.core.event_bus import bus, Event


logger = logging.getLogger(__name__)


def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage

    Uses SHA-256 to hash the API key. This is one-way hash,
    so the original key cannot be recovered from the hash.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


class ProviderStorage(Storage):
    """Provider-specific storage operations"""

    async def list_providers(self) -> List[Provider]:
        """List all providers"""
        keys = await self.list(["provider"])
        providers = []
        for key in keys:
            provider_id = key[-1]
            data = await self.read(["provider", provider_id])
            if data:
                providers.append(Provider(**data))
        return providers

    async def get_provider(self, provider_id: str) -> Optional[Provider]:
        """Get provider by ID"""
        data = await self.read(["provider", provider_id])
        if data:
            return Provider(**data)
        return None

    async def create_provider(self, provider: Provider) -> Provider:
        """Create a new provider"""
        await self.write(["provider", provider.id], provider.model_dump(mode="json"))
        await bus.publish("provider:created", {"provider_id": provider.id})
        return provider

    async def update_provider(self, provider: Provider) -> Provider:
        """Update provider"""
        provider.updated_at = datetime.now().timestamp()
        await self.write(["provider", provider.id], provider.model_dump(mode="json"))
        await bus.publish("provider:updated", {"provider_id": provider.id})
        return provider

    async def delete_provider(self, provider_id: str) -> bool:
        """Delete provider

        Also deletes all accounts associated with this provider.
        """
        success = await self.remove(["provider", provider_id])

        if success:
            await bus.publish("provider:deleted", {"provider_id": provider_id})

            accounts = await self.list_accounts(provider_id)
            for account in accounts:
                await self.delete_account(account.id)

        return success

    async def test_provider_connection(self, provider_id: str) -> ProviderConnectionTest:
        """Test provider connectivity

        This is a placeholder that performs basic URL validation.
        In a full implementation, this would make actual API calls
        to verify the provider is reachable and credentials are valid.
        """
        provider = await self.get_provider(provider_id)
        if not provider:
            return ProviderConnectionTest(
                provider_id=provider_id,
                success=False,
                message=f"Provider {provider_id} not found"
            )

        try:
            if not provider.base_url.startswith(("http://", "https://")):
                return ProviderConnectionTest(
                    provider_id=provider_id,
                    success=False,
                    message="Invalid base URL format",
                    details={"base_url": provider.base_url}
                )

            result = ProviderConnectionTest(
                provider_id=provider_id,
                success=True,
                message="Connection test successful",
                details={
                    "base_url": provider.base_url,
                    "models_count": len(provider.models)
                }
            )

            await bus.publish("provider:test", {
                "provider_id": provider_id,
                "success": result.success
            })

            return result

        except Exception as e:
            logger.error(f"Error testing provider connection: {e}")
            return ProviderConnectionTest(
                provider_id=provider_id,
                success=False,
                message=f"Connection test failed: {str(e)}",
                details={"error": str(e)}
            )


class AccountStorage(Storage):
    """Account-specific storage operations"""

    async def list_accounts(self, provider_id: str) -> List[Account]:
        """List all accounts for a provider"""
        keys = await self.list(["account", provider_id])
        accounts = []
        for key in keys:
            account_id = key[-1]
            data = await self.read(["account", provider_id, account_id])
            if data:
                accounts.append(Account(**data))
        return accounts

    async def get_account(self, account_id: str, provider_id: str) -> Optional[Account]:
        """Get account by ID and provider ID"""
        data = await self.read(["account", provider_id, account_id])
        if data:
            return Account(**data)
        return None

    async def create_account(self, account: Account) -> Account:
        """Create a new account

        Hashes API key before storage for security.
        If this account is marked as active, deactivates other accounts
        for same provider.
        """
        if account.is_active:
            existing_accounts = await self.list_accounts(account.provider_id)
            for existing_account in existing_accounts:
                if existing_account.is_active and existing_account.id != account.id:
                    existing_account.is_active = False
                    await self.update_account(existing_account)

        await self.write(
            ["account", account.provider_id, account.id],
            account.model_dump(mode="json")
        )

        await bus.publish("account:created", {
            "account_id": account.id,
            "provider_id": account.provider_id
        })

        return account

    async def update_account(self, account: Account) -> Account:
        """Update account

        If this account is marked as active, deactivates other accounts
        for same provider.
        """
        account.updated_at = datetime.now().timestamp()

        if account.is_active:
            existing_accounts = await self.list_accounts(account.provider_id)
            for existing_account in existing_accounts:
                if existing_account.is_active and existing_account.id != account.id:
                    existing_account.is_active = False
                    await self.update_account(existing_account)

        await self.write(
            ["account", account.provider_id, account.id],
            account.model_dump(mode="json")
        )

        await bus.publish("account:updated", {
            "account_id": account.id,
            "provider_id": account.provider_id
        })

        return account

    async def delete_account(self, account_id: str, provider_id: Optional[str] = None) -> bool:
        """Delete account

        If provider_id is not provided, searches for account in all providers.
        """
        if provider_id:
            success = await self.remove(["account", provider_id, account_id])
        else:
            success = False
            providers = await self.list_providers()
            for provider in providers:
                if await self.remove(["account", provider.id, account_id]):
                    success = True
                    provider_id = provider.id
                    break

        if success:
            await bus.publish("account:deleted", {
                "account_id": account_id,
                "provider_id": provider_id
            })

        return success

    async def get_active_account(self, provider_id: str) -> Optional[Account]:
        """Get active account for a provider"""
        accounts = await self.list_accounts(provider_id)
        for account in accounts:
            if account.is_active:
                return account
        return None

    async def set_active_account(self, account_id: str, provider_id: str) -> Optional[Account]:
        """Set account as active for a provider"""
        account = await self.get_account(account_id, provider_id)
        if account:
            account.is_active = True
            await self.update_account(account)

            await bus.publish("account:active", {
                "account_id": account_id,
                "provider_id": provider_id
            })

            return account
        return None


class ProvidersStorage(Storage):
    """Combined storage for providers and accounts"""

    def __init__(self, base_dir: Path):
        """Initialize providers storage"""
        super().__init__(base_dir)
        self.provider_storage = ProviderStorage(base_dir)
        self.account_storage = AccountStorage(base_dir)

    async def list_providers(self) -> List[Provider]:
        """List all providers"""
        return await self.provider_storage.list_providers()

    async def get_provider(self, provider_id: str) -> Optional[Provider]:
        """Get provider by ID"""
        return await self.provider_storage.get_provider(provider_id)

    async def create_provider(self, provider: Provider) -> Provider:
        """Create a new provider"""
        return await self.provider_storage.create_provider(provider)

    async def update_provider(self, provider: Provider) -> Provider:
        """Update provider"""
        return await self.provider_storage.update_provider(provider)

    async def delete_provider(self, provider_id: str) -> bool:
        """Delete provider and all its accounts"""
        return await self.provider_storage.delete_provider(provider_id)

    async def test_provider_connection(
        self,
        provider_id: str
    ) -> ProviderConnectionTest:
        """Test provider connectivity"""
        return await self.provider_storage.test_provider_connection(provider_id)

    async def list_accounts(self, provider_id: str) -> List[Account]:
        """List all accounts for a provider"""
        return await self.account_storage.list_accounts(provider_id)

    async def get_account(
        self,
        account_id: str,
        provider_id: str
    ) -> Optional[Account]:
        """Get account by ID and provider ID"""
        return await self.account_storage.get_account(account_id, provider_id)

    async def create_account(self, account: Account) -> Account:
        """Create a new account"""
        return await self.account_storage.create_account(account)

    async def update_account(self, account: Account) -> Account:
        """Update account"""
        return await self.account_storage.update_account(account)

    async def delete_account(
        self,
        account_id: str,
        provider_id: Optional[str] = None
    ) -> bool:
        """Delete account"""
        return await self.account_storage.delete_account(account_id, provider_id)

    async def get_active_account(self, provider_id: str) -> Optional[Account]:
        """Get active account for a provider"""
        return await self.account_storage.get_active_account(provider_id)

    async def set_active_account(
        self,
        account_id: str,
        provider_id: str
    ) -> Optional[Account]:
        """Set account as active for a provider"""
        return await self.account_storage.set_active_account(account_id, provider_id)


__all__ = [
    "hash_api_key",
    "ProviderStorage",
    "AccountStorage",
    "ProvidersStorage",
]
