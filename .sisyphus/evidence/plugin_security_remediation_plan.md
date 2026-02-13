# Plugin System Security Remediation Plan

## Executive Summary

The Dawn Kestrel plugin system uses Python's `entry_points` mechanism for dynamic loading of tools, providers, and agents. This analysis identified **4 CRITICAL** and **4 MEDIUM** security vulnerabilities that require immediate remediation.

**Primary Issues:**
1. Arbitrary code execution via `ep.load()` without validation
2. No plugin signature verification or trust chain
3. No sandboxing or isolation mechanism
4. JSON deserialization vulnerability in agent persistence

## Vulnerability Analysis

### CRITICAL-1: Direct Arbitrary Code Execution (plugin_discovery.py:49)

**Location:** `plugin_discovery.py:49`
```python
plugin = ep.load()  # Executes ANY code from entry point
```

**Severity:** CRITICAL
**CVSS Score:** 9.8 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

**Attack Vector:**
- Any package installed in the environment can register a `dawn_kestrel.tools`, `dawn_kestrel.providers`, or `dawn_kestrel.agents` entry point
- Malicious package can execute arbitrary code when `ep.load()` is called
- Code runs in the same process as Dawn Kestrel with all permissions

**Proof of Concept:**
```python
# In malicious package setup.py:
setup(
    name="evil-plugin",
    entry_points={
        "dawn_kestrel.tools": [
            "evil = evil_plugin:malicious_code"
        ]
    }
)

# evil_plugin.py:
def malicious_code():
    import os
    os.system("rm -rf /")  # Arbitrary code execution
```

**Remediation Options:**

#### Option 1: Allowlist-Based Plugin Loading (Recommended)

Implement a strict allowlist of trusted plugin sources with cryptographic verification.

```python
# Add to plugin_discovery.py
from typing import Set, Optional
import hashlib
from dataclasses import dataclass
import json

@dataclass
class TrustedPlugin:
    """Configuration for a trusted plugin"""
    name: str
    source: str  # PyPI package name or local path
    expected_hash: Optional[str] = None  # SHA256 hash for verification
    public_key: Optional[str] = None  # Ed25519 public key for signature verification

class PluginSecurityConfig:
    """Configuration for plugin security"""
    def __init__(self, allowlist_path: Optional[Path] = None):
        self.allowlist_path = allowlist_path
        self._allowlist: Dict[str, TrustedPlugin] = {}
        self._load_allowlist()

    def _load_allowlist(self):
        """Load trusted plugin allowlist from JSON file"""
        if not self.allowlist_path or not self.allowlist_path.exists():
            # Default allowlist with only built-in plugins
            self._allowlist = {
                # Built-in tools
                "bash": TrustedPlugin("bash", "dawn-kestrel"),
                "read": TrustedPlugin("read", "dawn-kestrel"),
                "write": TrustedPlugin("write", "dawn-kestrel"),
                "grep": TrustedPlugin("grep", "dawn-kestrel"),
                "glob": TrustedPlugin("glob", "dawn-kestrel"),
                "ast_grep_search": TrustedPlugin("ast_grep_search", "dawn-kestrel"),
                "edit": TrustedPlugin("edit", "dawn-kestrel"),
                # ... other built-in tools

                # Built-in providers
                "anthropic": TrustedPlugin("anthropic", "dawn-kestrel"),
                "openai": TrustedPlugin("openai", "dawn-kestrel"),
                "zai": TrustedPlugin("zai", "dawn-kestrel"),
                "zai_coding_plan": TrustedPlugin("zai_coding_plan", "dawn-kestrel"),

                # Built-in agents
                "build": TrustedPlugin("build", "dawn-kestrel"),
                "plan": TrustedPlugin("plan", "dawn-kestrel"),
                "general": TrustedPlugin("general", "dawn-kestrel"),
                "orchestrator": TrustedPlugin("orchestrator", "dawn-kestrel"),
                # ... other built-in agents
            }
        else:
            with open(self.allowlist_path) as f:
                data = json.load(f)
                for name, config in data.items():
                    self._allowlist[name] = TrustedPlugin(**config)

    def is_allowed(self, plugin_name: str) -> bool:
        """Check if plugin is in allowlist"""
        return plugin_name in self._allowlist

    def get_trusted_plugin(self, plugin_name: str) -> Optional[TrustedPlugin]:
        """Get trusted plugin config"""
        return self._allowlist.get(plugin_name)

# Global security configuration
_security_config: Optional[PluginSecurityConfig] = None

def get_security_config() -> PluginSecurityConfig:
    """Get or create global security configuration"""
    global _security_config
    if _security_config is None:
        # Try to load from config directory, fallback to defaults
        config_path = None
        try:
            from dawn_kestrel.core.settings import get_settings
            settings = get_settings()
            config_path = settings.config_dir_path() / "plugins" / "allowlist.json"
        except Exception:
            pass

        _security_config = PluginSecurityConfig(allowlist_path=config_path)
    return _security_config

# Modified _load_plugins with security checks
def _load_plugins_secure(group: str, plugin_type: str) -> Dict[str, Any]:
    """
    Generic plugin loader with security checks.

    Args:
        group: Entry point group name (e.g., "dawn_kestrel.tools")
        plugin_type: Type name for logging (e.g., "tool", "provider", "agent")

    Returns:
        Dictionary mapping plugin names to plugin instances
    """
    plugins: Dict[str, Any] = {}
    security_config = get_security_config()

    try:
        eps = entry_points()

        if hasattr(eps, "select"):
            plugin_entries = list(eps.select(group=group))
        else:
            plugin_entries = list(eps.get(group, []))

        for ep in plugin_entries:
            # SECURITY CHECK 1: Allowlist verification
            if not security_config.is_allowed(ep.name):
                logger.warning(
                    f"Rejecting {plugin_type} plugin '{ep.name}': not in allowlist"
                )
                continue

            try:
                # SECURITY CHECK 2: Source verification
                trusted_plugin = security_config.get_trusted_plugin(ep.name)
                if trusted_plugin and hasattr(ep, "dist") and ep.dist:
                    actual_source = ep.dist.name
                    if actual_source != trusted_plugin.source:
                        logger.error(
                            f"Rejecting {plugin_type} plugin '{ep.name}': "
                            f"expected source '{trusted_plugin.source}', got '{actual_source}'"
                        )
                        continue

                plugin = ep.load()

                if plugin is None:
                    logger.warning(
                        f"{plugin_type.capitalize()} plugin '{ep.name}' returned None, skipping"
                    )
                    continue

                # SECURITY CHECK 3: Plugin validation
                if not validate_plugin_secure(plugin, ep.name, plugin_type):
                    continue

                # For provider plugins, always return class (factory) not instance
                if group == "dawn_kestrel.providers":
                    instance = plugin
                elif isinstance(plugin, type):
                    try:
                        instance = plugin()
                    except (TypeError, ValueError):
                        instance = plugin
                else:
                    instance = plugin

                plugins[ep.name] = instance
                logger.info(f"Loaded {plugin_type} plugin: {ep.name}")

            except ImportError as e:
                logger.warning(f"Failed to import {plugin_type} plugin '{ep.name}': {e}")
            except Exception as e:
                logger.error(f"Failed to load {plugin_type} plugin '{ep.name}': {e}")

    except Exception as e:
        logger.error(f"Failed to discover {plugin_type} plugins: {e}")

    logger.info(f"Loaded {len(plugins)} {plugin_type} plugins (from allowlist)")
    return plugins
```

**Pros:**
- Complete control over what can load
- Simple to implement
- Clear audit trail
- Zero performance overhead for allowlisted plugins

**Cons:**
- Requires manual allowlist management
- Users must explicitly add trusted plugins
- Some UX friction for plugin ecosystem

#### Option 2: Plugin Source Verification with Cryptographic Signatures

Use Ed25519 signatures to verify plugin authenticity from developers.

```python
# Add to plugin_discovery.py
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
import base64

def verify_plugin_signature(plugin_path: Path, signature: str, public_key: str) -> bool:
    """
    Verify Ed25519 signature of plugin code.

    Args:
        plugin_path: Path to plugin Python file
        signature: Base64-encoded signature
        public_key: Base64-encoded Ed25519 public key

    Returns:
        True if signature valid, False otherwise
    """
    try:
        with open(plugin_path, 'rb') as f:
            plugin_data = f.read()

        # Decode signature and public key
        sig_bytes = base64.b64decode(signature)
        key_bytes = base64.b64decode(public_key)

        # Load public key
        public_key_obj = ed25519.Ed25519PublicKey.from_public_bytes(key_bytes)

        # Verify signature
        public_key_obj.verify(sig_bytes, plugin_data)
        return True

    except (InvalidSignature, ValueError, FileNotFoundError) as e:
        logger.error(f"Signature verification failed for {plugin_path}: {e}")
        return False

# Signature verification integrated into plugin loading
def _load_plugins_with_signature_verification(group: str, plugin_type: str) -> Dict[str, Any]:
    """Load plugins with signature verification"""
    plugins = {}
    security_config = get_security_config()

    # ... similar structure to allowlist option ...
    # Add signature check after ep.load()
    if trusted_plugin.public_key and hasattr(ep, "value"):
        # Get module file path
        import inspect
        try:
            module = ep.load()
            if hasattr(module, "__file__"):
                plugin_path = Path(module.__file__)
                signature_path = plugin_path.with_suffix(".sig")

                if signature_path.exists():
                    with open(signature_path) as f:
                        signature = f.read().strip()

                    if not verify_plugin_signature(plugin_path, signature, trusted_plugin.public_key):
                        logger.error(f"Invalid signature for plugin '{ep.name}'")
                        continue
                else:
                    logger.warning(f"No signature file for plugin '{ep.name}'")
        except Exception as e:
            logger.error(f"Signature check failed for '{ep.name}': {e}")

    return plugins
```

**Pros:**
- Strong cryptographic guarantees
- Enables third-party plugin marketplace
- Maintains extensibility

**Cons:**
- More complex to implement
- Requires plugin developers to sign plugins
- Key management overhead

#### Option 3: Plugin Hash Verification

Compute and verify SHA256 hashes of plugin code.

```python
def verify_plugin_hash(plugin_path: Path, expected_hash: str) -> bool:
    """
    Verify SHA256 hash of plugin code.

    Args:
        plugin_path: Path to plugin Python file
        expected_hash: Expected SHA256 hash (hex string)

    Returns:
        True if hash matches, False otherwise
    """
    try:
        sha256_hash = hashlib.sha256()
        with open(plugin_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        actual_hash = sha256_hash.hexdigest()
        return actual_hash == expected_hash.lower()

    except FileNotFoundError as e:
        logger.error(f"Plugin file not found: {plugin_path}")
        return False
```

**Pros:**
- Simple to implement
- Fast computation
- Detects tampering

**Cons:**
- Hash must be recomputed on any plugin update
- No authentication of source
- Manual hash management

---

### CRITICAL-2: No Plugin Signature Verification or Trust Checking

**Location:** System-wide (missing feature)
**Severity:** CRITICAL
**CVSS Score:** 9.1 (AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H)

**Issue:** No mechanism to verify plugin authenticity or integrity. Any code can be loaded and executed.

**Remediation:** Implement trust store with cryptographic signatures (see Option 2 above).

---

### CRITICAL-3: No Sandboxing or Isolation

**Location:** System-wide (missing feature)
**Severity:** CRITICAL
**CVSS Score:** 8.8 (AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H)

**Issue:** Plugins execute in the same process as Dawn Kestrel with full access to filesystem, network, and system resources.

**Remediation Options:**

#### Option 1: Restricted Execution Environment (Recommended)

Use Python's `restricted` capabilities and attribute whitelisting.

```python
# Add new module: dawn_kestrel/core/plugin_security.py
import sys
import types
from typing import Set, Any, Dict
import logging

logger = logging.getLogger(__name__)

class RestrictedModule:
    """
    Wrapper for modules that restricts access to dangerous attributes.
    """

    DANGEROUS_MODULES: Set[str] = {
        "os", "subprocess", "sys", "importlib", "pickle",
        "shutil", "tempfile", "socket", "urllib", "http",
        "ftplib", "smtplib", "telnetlib", "asyncio.subprocess"
    }

    DANGEROUS_FUNCTIONS: Set[str] = {
        "eval", "exec", "compile", "open", "__import__",
        "reload", "exit", "quit"
    }

    def __init__(self, wrapped_module: types.ModuleType, plugin_name: str):
        self._wrapped = wrapped_module
        self._plugin_name = plugin_name
        self._allowed_attributes = set(dir(wrapped_module))
        self._apply_restrictions()

    def _apply_restrictions(self):
        """Remove dangerous attributes from module"""
        for attr in self._allowed_attributes.copy():
            # Remove dangerous function names
            if attr in self.DANGEROUS_FUNCTIONS:
                self._allowed_attributes.remove(attr)
                logger.debug(
                    f"Restricted {self._plugin_name}: removed dangerous function '{attr}'"
                )

            # Remove dangerous modules
            if attr in self.DANGEROUS_MODULES:
                self._allowed_attributes.remove(attr)
                logger.debug(
                    f"Restricted {self._plugin_name}: removed dangerous module '{attr}'"
                )

    def __getattr__(self, name: str) -> Any:
        """Get attribute if allowed"""
        if name not in self._allowed_attributes:
            raise AttributeError(
                f"Plugin '{self._plugin_name}' is not allowed to access '{name}'"
            )
        return getattr(self._wrapped, name)

    def __dir__(self) -> Set[str]:
        """Return only allowed attributes"""
        return self._allowed_attributes.copy()


class PluginSandbox:
    """
    Sandbox for restricting plugin access to dangerous operations.
    """

    def __init__(self, plugin_name: str, capabilities: Set[str] = None):
        """
        Initialize sandbox for a plugin.

        Args:
            plugin_name: Name of plugin for logging
            capabilities: Set of allowed capabilities (e.g., {'read', 'write'})
        """
        self._plugin_name = plugin_name
        self._capabilities = capabilities or set()
        self._original_modules = {}

    def __enter__(self):
        """Enter sandbox context"""
        # Restrict os module
        if "os" in sys.modules:
            self._original_modules["os"] = sys.modules["os"]
            sys.modules["os"] = RestrictedModule(sys.modules["os"], self._plugin_name)

        # Restrict sys module
        if "sys" in sys.modules:
            self._original_modules["sys"] = sys.modules["sys"]
            sys.modules["sys"] = RestrictedModule(sys.modules["sys"], self._plugin_name)

        logger.info(f"Entered sandbox for plugin '{self._plugin_name}'")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sandbox context"""
        # Restore original modules
        for name, module in self._original_modules.items():
            sys.modules[name] = module

        self._original_modules.clear()
        logger.info(f"Exited sandbox for plugin '{self._plugin_name}'")
        return False

    def check_capability(self, capability: str) -> bool:
        """
        Check if plugin has a specific capability.

        Args:
            capability: Capability name (e.g., 'read', 'write', 'network')

        Returns:
            True if allowed, False otherwise
        """
        allowed = capability in self._capabilities
        if not allowed:
            logger.warning(
                f"Plugin '{self._plugin_name}' attempted to use capability '{capability}' "
                f"but does not have permission"
            )
        return allowed


# Plugin capability definitions
CAPABILITIES = {
    "read": "Read local files",
    "write": "Write local files",
    "network": "Make network requests",
    "execute": "Execute external commands",
    "modify_process": "Modify process state",
}


def get_plugin_capabilities(plugin_type: str, plugin_name: str) -> Set[str]:
    """
    Get default capabilities for a plugin based on type.

    Args:
        plugin_type: Type of plugin (tool, provider, agent)
        plugin_name: Name of the plugin

    Returns:
        Set of allowed capabilities
    """
    # Built-in plugins get reasonable defaults
    if plugin_type == "tool":
        READ_TOOLS = {"read", "grep", "glob", "ast_grep_search", "list", "lsp"}
        WRITE_TOOLS = {"write", "edit", "multiedit", "todowrite"}
        EXECUTE_TOOLS = {"bash"}
        NETWORK_TOOLS = {"webfetch", "websearch", "codesearch"}

        if plugin_name in READ_TOOLS:
            return {"read"}
        elif plugin_name in WRITE_TOOLS:
            return {"read", "write"}
        elif plugin_name in EXECUTE_TOOLS:
            return {"execute"}
        elif plugin_name in NETWORK_TOOLS:
            return {"network", "read"}

    elif plugin_type == "provider":
        # Providers need network access for LLM APIs
        return {"network"}

    elif plugin_type == "agent":
        # Agents need broad access but can be restricted
        return {"read", "write", "network", "execute"}

    # Unknown plugins get no capabilities by default
    return set()
```

**Usage in plugin_discovery.py:**

```python
from dawn_kestrel.core.plugin_security import PluginSandbox, get_plugin_capabilities

def _load_plugins_with_sandbox(group: str, plugin_type: str) -> Dict[str, Any]:
    """Load plugins with sandboxing"""
    plugins = {}
    security_config = get_security_config()

    # ... (same discovery loop)

    for ep in plugin_entries:
        if not security_config.is_allowed(ep.name):
            logger.warning(f"Rejecting plugin '{ep.name}': not in allowlist")
            continue

        try:
            # Load plugin within sandbox
            capabilities = get_plugin_capabilities(plugin_type, ep.name)
            with PluginSandbox(ep.name, capabilities):
                plugin = ep.load()

            if plugin is None:
                logger.warning(f"Plugin '{ep.name}' returned None, skipping")
                continue

            # Wrap plugin instances with capability checks
            if not isinstance(plugin, type):
                plugin = CapabilityRestrictedWrapper(plugin, capabilities)

            plugins[ep.name] = plugin

        except Exception as e:
            logger.error(f"Failed to load plugin '{ep.name}': {e}")

    return plugins
```

**Pros:**
- Provides defense-in-depth
- Capability-based security model
- Can be layered with allowlisting

**Cons:**
- Not a true sandbox (Python doesn't have OS-level sandboxing)
- Can be bypassed by sophisticated attacks
- Some performance overhead

#### Option 2: Separate Process Execution (Strongest Security)

Run plugins in separate processes with restricted permissions.

```python
# Add new module: dawn_kestrel/core/plugin_subprocess.py
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Dict, Callable
import logging

logger = logging.getLogger(__name__)


def _execute_in_subprocess(plugin_factory: Callable, *args, **kwargs) -> Any:
    """
    Execute plugin factory in isolated subprocess.

    Args:
        plugin_factory: Factory function to create plugin
        *args: Arguments to pass to factory
        **kwargs: Keyword arguments to pass to factory

    Returns:
        Plugin instance

    Note:
        This runs in a separate process with restricted capabilities.
    """
    # Apply process-level restrictions
    try:
        # Set process limits
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))  # 10 second CPU limit
        resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024))  # 100MB RAM
    except Exception as e:
        logger.warning(f"Could not set process limits: {e}")

    # Create and return plugin
    return plugin_factory(*args, **kwargs)


class SubprocessPluginLoader:
    """
    Load and execute plugins in isolated subprocesses.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize subprocess loader.

        Args:
            max_workers: Maximum number of concurrent plugin processes
        """
        self.executor = ProcessPoolExecutor(max_workers=max_workers)
        self._futures: Dict[str, Any] = {}

    async def load_plugin(self, plugin_factory: Callable, name: str, *args, **kwargs) -> Any:
        """
        Load plugin in subprocess.

        Args:
            plugin_factory: Factory function to create plugin
            name: Plugin name for tracking
            *args: Arguments to pass to factory
            **kwargs: Keyword arguments to pass to factory

        Returns:
            Plugin instance (proxy)
        """
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            self.executor,
            _execute_in_subprocess,
            plugin_factory,
            *args,
            **kwargs
        )

        self._futures[name] = future
        return await future

    async def shutdown(self):
        """Shutdown all plugin processes"""
        for name, future in self._futures.items():
            try:
                await future
            except Exception as e:
                logger.error(f"Error waiting for plugin '{name}': {e}")

        self.executor.shutdown(wait=True)
```

**Pros:**
- True process isolation
- Resource limits per plugin
- Plugin crashes don't affect main process

**Cons:**
- Complex IPC required
- Significant performance overhead
- Serialization of plugin state required

#### Option 3: RestrictedPython (Alternative)

Use RestrictedPython library for AST-level code restrictions.

```python
# Install: pip install RestrictedPython
from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safer_getattr
import ast

def validate_plugin_code(code: str, plugin_name: str) -> bool:
    """
    Validate plugin code using RestrictedPython.

    Args:
        code: Python source code
        plugin_name: Name for logging

    Returns:
        True if safe, False otherwise
    """
    try:
        # Compile with restrictions
        compiled = compile_restricted(
            code,
            filename=f"<{plugin_name}>",
            mode="exec"
        )

        if compiled.errors:
            logger.error(
                f"Plugin '{plugin_name}' has restricted code: {compiled.errors}"
            )
            return False

        return True

    except Exception as e:
        logger.error(f"Failed to validate plugin '{plugin_name}': {e}")
        return False


# Use with dynamic plugin loading
def load_plugin_from_code(code: str, plugin_name: str):
    """Load plugin from source code with validation"""
    if not validate_plugin_code(code, plugin_name):
        raise ValueError(f"Plugin '{plugin_name}' failed code validation")

    # Create restricted globals
    restricted_globals = {
        '__builtins__': {
            'print': print,
            'len': len,
            # Add other safe builtins as needed
        },
        '_getattr_': safer_getattr,
        '_getiter_': iter,
    }

    exec(code, restricted_globals)
    return restricted_globals
```

**Pros:**
- AST-level restrictions
- Prevents dangerous operations at compile time
- Well-tested library

**Cons:**
- Requires source code access (not pre-compiled modules)
- May break valid Python code
- Learning curve

---

### CRITICAL-4: JSON Deserialization Risk (agents/registry.py:144)

**Location:** `agents/registry.py:144`
```python
agent = Agent(**agent_data)  # Unsafe JSON deserialization
```

**Severity:** CRITICAL
**CVSS Score:** 8.6 (AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H)

**Issue:** Loading agent definitions from JSON allows arbitrary attribute assignment, potentially allowing injection of dangerous methods or properties.

**Remediation:**

```python
# Add to agents/registry.py
from pydantic import BaseModel, ValidationError
from typing import Literal, Optional

class AgentSchema(BaseModel):
    """Schema for safe agent deserialization"""
    name: str
    description: str
    mode: Literal["chat", "completion", "instruct"]
    permission: Literal["read-only", "full", "admin"]
    native: bool
    hidden: bool = False
    top_p: Optional[float] = None
    temperature: Optional[float] = None
    color: Optional[str] = None
    model: Optional[str] = None
    prompt: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    steps: Optional[List[str]] = None

    class Config:
        extra = "forbid"  # Reject unknown fields


def _load_agent_from_json_safe(agent_file: Path) -> Optional[Agent]:
    """
    Load agent from JSON file with schema validation.

    Args:
        agent_file: Path to JSON file

    Returns:
        Agent instance if valid, None otherwise
    """
    try:
        with open(agent_file, "r") as f:
            raw_data = json.load(f)

        # Validate against schema
        try:
            schema = AgentSchema(**raw_data)
        except ValidationError as e:
            logger.error(f"Invalid agent schema in {agent_file}: {e}")
            return None

        # Additional validation: check for dangerous patterns
        dangerous_patterns = ["__import__", "eval", "exec", "compile"]
        for field, value in schema.dict().items():
            if isinstance(value, str):
                for pattern in dangerous_patterns:
                    if pattern in value.lower():
                        logger.error(
                            f"Agent {agent_file.name} contains dangerous pattern '{pattern}' "
                            f"in field '{field}'"
                        )
                        return None

        # Create Agent from validated data
        agent = Agent(**schema.dict())
        return agent

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {agent_file}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load agent from {agent_file}: {e}")
        return None


# Replace _initialize_persistence method
def _initialize_persistence(self) -> None:
    """
    Initialize persistence layer with safe JSON loading.

    Loads any existing custom agents from storage/agent/
    """
    if not self.storage_dir:
        return

    agent_dir = self.storage_dir / "agent"
    if not agent_dir.exists():
        logger.debug(f"Agent storage directory does not exist: {agent_dir}")
        return

    # Load custom agents from JSON files
    for agent_file in agent_dir.glob("*.json"):
        try:
            agent = _load_agent_from_json_safe(agent_file)

            if agent is None:
                continue  # Validation failed, already logged

            # Don't overwrite built-in agents
            if self._normalize_name(agent.name) in self._agents:
                existing = self.get_agent(agent.name)
                if existing and existing.native:
                    logger.debug(f"Skipping built-in agent override: {agent.name}")
                    continue

            self._register_internal(agent)
            logger.info(f"Loaded custom agent from file: {agent_file.name}")

        except Exception as e:
            logger.error(f"Failed to load agent from {agent_file}: {e}")
```

**Pros:**
- Strict schema validation
- Rejects unknown fields
- Pattern-based injection detection
- Uses Pydantic which is already a dependency

**Cons:**
- Adds dependency on proper schema definition
- Requires maintaining AgentSchema in sync with Agent dataclass

---

### MEDIUM-1: Minimal Plugin Validation (plugin_discovery.py:284-305)

**Location:** `plugin_discovery.py:284-305`
**Severity:** MEDIUM
**CVSS Score:** 6.5 (AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:L)

**Issue:** Current validation only checks for None and __class__, allowing invalid or malformed plugins to load.

**Remediation:**

```python
def validate_plugin_secure(plugin: Any, plugin_name: str, plugin_type: str) -> bool:
    """
    Validate that a plugin meets security and functional requirements.

    Args:
        plugin: The loaded plugin object
        plugin_name: Name of the plugin (for logging)
        plugin_type: Type of plugin (tool, provider, agent)

    Returns:
        True if valid, False otherwise
    """
    # Basic validation: plugin should not be None
    if plugin is None:
        logger.warning(f"Plugin '{plugin_name}' is None, validation failed")
        return False

    # Plugin should have a class name
    if not hasattr(plugin, "__class__"):
        logger.warning(f"Plugin '{plugin_name}' has no __class__ attribute, validation failed")
        return False

    # Check for dangerous attributes
    dangerous_modules = ["os", "subprocess", "sys", "importlib", "pickle"]
    plugin_attrs = set(dir(plugin))

    for attr in dangerous_modules:
        if attr in plugin_attrs:
            # Check if it's actually the dangerous module
            try:
                value = getattr(plugin, attr)
                if isinstance(value, types.ModuleType):
                    logger.warning(
                        f"Plugin '{plugin_name}' has direct access to module '{attr}', "
                        f"validation failed"
                    )
                    return False
            except AttributeError:
                pass

    # Type-specific validation
    if plugin_type == "tool":
        # Tools should have an execute method or similar
        if not hasattr(plugin, "execute") and not callable(plugin):
            logger.warning(
                f"Tool plugin '{plugin_name}' lacks 'execute' method and is not callable"
            )
            return False

    elif plugin_type == "provider":
        # Providers should be classes with __call__ or generate methods
        if not isinstance(plugin, type):
            logger.warning(
                f"Provider plugin '{plugin_name}' is not a class, validation failed"
            )
            return False

        # Check for required provider methods
        if not (hasattr(plugin, "generate") or hasattr(plugin, "chat_complete")):
            logger.warning(
                f"Provider plugin '{plugin_name}' lacks 'generate' or 'chat_complete' method"
            )
            # Don't fail validation, but warn

    elif plugin_type == "agent":
        # Agents should have name, description, prompt attributes
        required_attrs = ["name", "description", "prompt"]
        for attr in required_attrs:
            if not hasattr(plugin, attr):
                logger.warning(
                    f"Agent plugin '{plugin_name}' lacks required attribute '{attr}'"
                )
                return False

        # Validate prompt is not malicious
        if hasattr(plugin, "prompt") and isinstance(plugin.prompt, str):
            dangerous_patterns = ["__import__", "eval(", "exec("]
            for pattern in dangerous_patterns:
                if pattern in plugin.prompt:
                    logger.error(
                        f"Agent '{plugin_name}' prompt contains dangerous pattern '{pattern}'"
                    )
                    return False

    return True
```

---

### MEDIUM-2: Callable Execution Without Restrictions (agents/registry.py:86-87)

**Location:** `agents/registry.py:86-87`
```python
if callable(agent_plugin):
    agent = agent_plugin()  # Executes ANY callable
```

**Severity:** MEDIUM
**CVSS Score:** 6.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:L)

**Issue:** Any callable is executed without validation of what it returns or side effects.

**Remediation:**

```python
def _load_agent_from_plugin_secure(self, name: str, agent_plugin) -> Optional[Agent]:
    """
    Load an Agent instance from a plugin entry point with security checks.

    Args:
        name: Plugin name
        agent_plugin: The loaded plugin (Agent instance or factory function)

    Returns:
        Agent instance if valid, None otherwise
    """
    try:
        # SECURITY CHECK: Validate before calling
        if callable(agent_plugin):
            # Check if it's a class or function
            import inspect
            if inspect.isclass(agent_plugin):
                # Factory class: instantiate
                agent = agent_plugin()
            elif inspect.isfunction(agent_plugin):
                # Factory function: call it
                # SECURITY: Timeout to prevent blocking
                import signal

                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Agent factory '{name}' timed out")

                # Set timeout (5 seconds)
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(5)

                try:
                    agent = agent_plugin()
                finally:
                    signal.alarm(0)  # Cancel timeout
            else:
                logger.warning(
                    f"Plugin '{name}' is callable but not class or function, skipping"
                )
                return None
        else:
            agent = agent_plugin

        # Validate returned object
        if not isinstance(agent, Agent):
            logger.warning(
                f"Plugin '{name}' returned {type(agent).__name__} instead of Agent, skipping"
            )
            return None

        # Validate agent attributes
        if not hasattr(agent, "name") or not agent.name:
            logger.warning(f"Agent from plugin '{name}' has no name, skipping")
            return None

        if not hasattr(agent, "prompt") or not agent.prompt:
            logger.warning(f"Agent '{agent.name}' has no prompt, skipping")
            return None

        # Check for dangerous prompt content
        dangerous_patterns = ["__import__", "eval(", "exec("]
        for pattern in dangerous_patterns:
            if pattern in agent.prompt:
                logger.error(
                    f"Agent '{agent.name}' prompt contains dangerous pattern '{pattern}'"
                )
                return None

        return agent

    except TimeoutError as e:
        logger.error(f"Agent factory '{name}' timed out: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load agent plugin '{name}': {e}")
        return None
```

---

### MEDIUM-3: No Permission Restrictions on Plugin Loading

**Location:** System-wide (missing feature)
**Severity:** MEDIUM
**CVSS Score:** 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:N)

**Issue:** No permission system controlling which plugins can be loaded or what they can do.

**Remediation:** See **Option 1: Capability-Based Security** in CRITICAL-3 (No Sandboxing).

---

### MEDIUM-4: Plugin Instances Execute with Full Process Access

**Location:** System-wide (missing feature)
**Severity:** MEDIUM
**CVSS Score:** 5.5 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:L)

**Issue:** Even after loading, plugins have unrestricted access to the process.

**Remediation:**

```python
# Add to dawn_kestrel/core/plugin_security.py
from functools import wraps

class CapabilityRestrictedWrapper:
    """
    Wrapper that restricts plugin actions based on capabilities.
    """

    def __init__(self, wrapped: Any, capabilities: Set[str]):
        """
        Initialize wrapper.

        Args:
            wrapped: Plugin object to wrap
            capabilities: Set of allowed capabilities
        """
        self._wrapped = wrapped
        self._capabilities = capabilities

    def __getattr__(self, name: str) -> Any:
        """Get attribute from wrapped object"""
        attr = getattr(self._wrapped, name)

        # If it's a method, wrap it with capability checks
        if callable(attr):
            @wraps(attr)
            def restricted_method(*args, **kwargs):
                # Check method name against capabilities
                method_name = name.lower()

                # Write operations require 'write' capability
                if method_name in ("write", "save", "create", "update", "delete"):
                    if "write" not in self._capabilities:
                        raise PermissionError(
                            f"Plugin does not have 'write' capability"
                        )

                # Network operations require 'network' capability
                if method_name in ("fetch", "request", "connect", "download"):
                    if "network" not in self._capabilities:
                        raise PermissionError(
                            f"Plugin does not have 'network' capability"
                        )

                # Execution operations require 'execute' capability
                if method_name in ("execute", "run", "spawn", "system"):
                    if "execute" not in self._capabilities:
                        raise PermissionError(
                            f"Plugin does not have 'execute' capability"
                        )

                return attr(*args, **kwargs)

            return restricted_method

        return attr

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute with capability check"""
        if name.startswith("_"):
            # Allow setting private attributes
            object.__setattr__(self, name, value)
        else:
            # Check write capability
            if "write" not in self._capabilities:
                raise PermissionError(
                    f"Plugin does not have 'write' capability to set '{name}'"
                )
            setattr(self._wrapped, name, value)
```

---

## Implementation Strategy

### Phase 1: Critical Fixes (Immediate, 1-2 weeks)

1. **Implement Allowlist-Based Plugin Loading** (CRITICAL-1)
   - Add `PluginSecurityConfig` class
   - Add `get_security_config()` function
   - Modify `_load_plugins()` to use allowlist
   - Create default allowlist with built-in plugins
   - Add tests for allowlist enforcement

2. **Fix JSON Deserialization** (CRITICAL-4)
   - Create `AgentSchema` with Pydantic
   - Implement `_load_agent_from_json_safe()`
   - Update `_initialize_persistence()`
   - Add validation tests

3. **Enhanced Plugin Validation** (MEDIUM-1)
   - Replace `validate_plugin()` with `validate_plugin_secure()`
   - Add dangerous attribute checks
   - Add type-specific validation
   - Add tests for validation logic

### Phase 2: Sandbox Implementation (2-3 weeks)

4. **Implement Capability-Based Security** (CRITICAL-3, MEDIUM-3, MEDIUM-4)
   - Create `PluginSandbox` class
   - Create `CapabilityRestrictedWrapper` class
   - Define `get_plugin_capabilities()` function
   - Add sandboxing to `_load_plugins()`
   - Add capability wrapper to plugin instances
   - Add sandbox tests

5. **Secure Callable Execution** (MEDIUM-2)
   - Update `_load_agent_from_plugin()` with security checks
   - Add timeout for factory functions
   - Add validation of returned objects
   - Add tests for factory validation

### Phase 3: Advanced Features (Optional, 4-6 weeks)

6. **Plugin Signature Verification** (CRITICAL-2, Optional)
   - Implement Ed25519 signature verification
   - Add signature check to plugin loading
   - Create plugin signing tool
   - Document signature workflow

7. **Subprocess Execution** (Alternative to sandboxing, Optional)
   - Implement `SubprocessPluginLoader`
   - Add IPC mechanism
   - Add process limits
   - Benchmark performance impact

---

## Recommended Implementation Order

**Priority 1 (Do First):**
1. Allowlist-based plugin loading (CRITICAL-1)
2. JSON deserialization fix (CRITICAL-4)
3. Enhanced plugin validation (MEDIUM-1)

**Priority 2 (Do Second):**
4. Capability-based security sandbox (CRITICAL-3)
5. Secure callable execution (MEDIUM-2)

**Priority 3 (Do Third, Optional):**
6. Plugin signature verification (CRITICAL-2)
7. Subprocess execution (advanced sandboxing)

---

## Trade-offs

### Allowlist vs. Signature Verification

| Factor | Allowlist | Signatures |
|--------|----------|------------|
| Security | High | High |
| Complexity | Low | Medium |
| Extensibility | Low (manual) | High (marketplace) |
| Performance | Zero overhead | Low overhead |
| Management | Manual | Automated with PKI |

**Recommendation:** Start with allowlist (Priority 1), add signatures later (Priority 3).

### Sandbox vs. Separate Process

| Factor | Sandbox | Separate Process |
|--------|---------|------------------|
| Security | Medium | High |
| Complexity | Medium | High |
| Performance | Low overhead | High overhead |
| IPC | None | Required |
| Debugging | Easy | Hard |

**Recommendation:** Use sandbox (Priority 2), consider separate process for high-risk plugins only.

---

## Testing Strategy

### Unit Tests

```python
# tests/core/test_plugin_security.py
import pytest
from dawn_kestrel.core.plugin_security import (
    PluginSecurityConfig,
    RestrictedModule,
    PluginSandbox,
    CapabilityRestrictedWrapper,
)

def test_allowlist_blocks_untrusted_plugins():
    """Test that untrusted plugins are rejected"""
    config = PluginSecurityConfig()

    # Built-in plugin should be allowed
    assert config.is_allowed("bash")

    # Unknown plugin should be rejected
    assert not config.is_allowed("malicious_plugin")


def test_restricted_module_blocks_dangerous_attrs():
    """Test that restricted module blocks dangerous attributes"""
    import os

    restricted = RestrictedModule(os, "test_plugin")

    # Should not have access to 'system'
    with pytest.raises(AttributeError):
        restricted.system("echo test")


def test_sandbox_restricts_capabilities():
    """Test that sandbox restricts plugin capabilities"""
    with PluginSandbox("test_plugin", capabilities={"read"}) as sandbox:
        # Should have read capability
        assert sandbox.check_capability("read")

        # Should not have write capability
        assert not sandbox.check_capability("write")


def test_capability_wrapper_restricts_operations():
    """Test that capability wrapper restricts operations"""
    class MockTool:
        def write(self, data):
            return data

    tool = MockTool()
    restricted = CapabilityRestrictedWrapper(tool, capabilities={"read"})

    # Write should raise permission error
    with pytest.raises(PermissionError):
        restricted.write("test")
```

### Integration Tests

```python
# tests/integration/test_plugin_security.py
import pytest
from dawn_kestrel.core.plugin_discovery import (
    load_tools,
    load_providers,
    load_agents,
)


@pytest.mark.asyncio
async def test_only_allowlisted_tools_load():
    """Test that only allowlisted tools load"""
    tools = await load_tools()

    # Built-in tools should load
    assert "bash" in tools
    assert "read" in tools

    # Unknown tools should not load
    assert "malicious_tool" not in tools


@pytest.mark.asyncio
async def test_plugin_validation_blocks_invalid_plugins():
    """Test that invalid plugins are rejected"""
    from dawn_kestrel.core.plugin_discovery import validate_plugin_secure

    # None should be rejected
    assert not validate_plugin_secure(None, "test", "tool")

    # Object without __class__ should be rejected
    assert not validate_plugin_secure(object(), "test", "tool")


def test_json_deserialization_validates_schema():
    """Test that JSON deserialization validates schema"""
    from dawn_kestrel.agents.registry import _load_agent_from_json_safe
    from pathlib import Path

    # Valid agent should load
    valid_json = {
        "name": "test_agent",
        "description": "Test",
        "mode": "chat",
        "permission": "read-only",
        "native": False,
        "hidden": False,
        "prompt": "Test prompt"
    }

    # Write to temp file and load
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        import json
        json.dump(valid_json, f)
        temp_path = Path(f.name)

    try:
        agent = _load_agent_from_json_safe(temp_path)
        assert agent is not None
        assert agent.name == "test_agent"
    finally:
        temp_path.unlink()

    # Invalid agent (extra field) should be rejected
    invalid_json = {
        "name": "test_agent",
        "description": "Test",
        "mode": "chat",
        "permission": "read-only",
        "native": False,
        "hidden": False,
        "prompt": "Test prompt",
        "extra_field": "should be rejected"
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(invalid_json, f)
        temp_path = Path(f.name)

    try:
        agent = _load_agent_from_json_safe(temp_path)
        assert agent is None
    finally:
        temp_path.unlink()
```

---

## Performance Considerations

### Allowlist-Based Loading

- **Overhead:** ~0ms (simple dict lookup)
- **Impact:** Negligible
- **Recommendation:** Enable by default

### Capability-Based Sandbox

- **Overhead:** ~1-5ms per plugin load (attribute filtering)
- **Impact:** Low
- **Recommendation:** Enable for all third-party plugins

### Signature Verification

- **Overhead:** ~5-10ms per plugin (hashing and crypto)
- **Impact:** Low
- **Recommendation:** Enable for third-party plugins

### Separate Process Execution

- **Overhead:** ~50-100ms per plugin (process spawn)
- **Impact:** High
- **Recommendation:** Use only for high-risk plugins

---

## Configuration

### Default Configuration

```python
# dawn_kestrel/core/plugin_config.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class PluginSecuritySettings:
    """Default security settings for plugin system"""

    # Allowlist settings
    enable_allowlist: bool = True
    allowlist_path: Path = None  # Falls back to built-in allowlist

    # Sandbox settings
    enable_sandbox: bool = True
    enable_capability_wrapper: bool = True

    # Signature settings
    enable_signature_verification: bool = False  # Disabled by default
    require_signatures: bool = False

    # Process isolation settings
    enable_subprocess_execution: bool = False  # Disabled by default
    subprocess_timeout: int = 30  # seconds
    subprocess_max_workers: int = 4


def get_default_security_settings() -> PluginSecuritySettings:
    """Get default security settings"""
    return PluginSecuritySettings()
```

### User Configuration

```json
// config/plugins/security.json
{
  "enable_allowlist": true,
  "allowlist_path": "~/.config/dawn-kestrel/plugins/allowlist.json",

  "enable_sandbox": true,
  "enable_capability_wrapper": true,

  "enable_signature_verification": false,
  "require_signatures": false,

  "enable_subprocess_execution": false,
  "subprocess_timeout": 30
}
```

### Allowlist Example

```json
// config/plugins/allowlist.json
{
  "bash": {
    "name": "bash",
    "source": "dawn-kestrel",
    "public_key": null
  },
  "read": {
    "name": "read",
    "source": "dawn-kestrel",
    "public_key": null
  },
  "third_party_tool": {
    "name": "third_party_tool",
    "source": "trusted-package",
    "public_key": "base64-encoded-ed25519-public-key"
  }
}
```

---

## Migration Path

### For Existing Users

1. **Phase 1:** New security features disabled by default
2. **Phase 2:** Enable allowlist in warning mode (log but don't block)
3. **Phase 3:** Enable allowlist in enforce mode (block unknown plugins)
4. **Phase 4:** Add user-facing warnings about untrusted plugins
5. **Phase 5:** Full enforcement

### Backward Compatibility

- Allowlist includes all built-in plugins by default
- Third-party plugins work but generate warnings
- Users can explicitly add plugins to allowlist
- Gradual rollout prevents breaking changes

---

## Conclusion

The Dawn Kestrel plugin system has critical security vulnerabilities that require immediate remediation. The recommended approach is:

1. **Implement allowlist-based plugin loading** (CRITICAL-1)
2. **Fix JSON deserialization** (CRITICAL-4)
3. **Enhanced plugin validation** (MEDIUM-1)
4. **Capability-based sandboxing** (CRITICAL-3)
5. **Secure callable execution** (MEDIUM-2)
6. **Optional: Plugin signature verification** (CRITICAL-2)

This layered security approach provides defense-in-depth while maintaining extensibility and reasonable performance.

---

## References

- [OWASP Plugin Security](https://owasp.org/www-project-plugin-security/)
- [Python RestrictedPython](https://github.com/zopefoundation/RestrictedPython)
- [PEP 451 - A ModuleSpec Type for the Import System](https://peps.python.org/pep-0451/)
- [Ed25519 Signatures in Python](https://docs.python.org/3/library/cryptography.html)
- [Pydantic Security](https://docs.pydantic.dev/usage/validators/)
