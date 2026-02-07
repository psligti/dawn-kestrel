"""Compatibility package redirecting opencode_python imports to dawn_kestrel."""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
import warnings
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import Sequence

_LEGACY_PREFIX = "opencode_python"
_TARGET_PREFIX = "dawn_kestrel"


class _CompatLoader(importlib.abc.Loader):
    def __init__(self, alias_name: str, target_name: str) -> None:
        self.alias_name = alias_name
        self.target_name = target_name

    def create_module(self, spec: ModuleSpec) -> ModuleType:
        module = importlib.import_module(self.target_name)
        sys.modules[self.alias_name] = module
        return module

    def exec_module(self, module: ModuleType) -> None:
        sys.modules[self.alias_name] = module


class _CompatFinder(importlib.abc.MetaPathFinder):
    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        if not fullname.startswith(f"{_LEGACY_PREFIX}."):
            return None

        target_name = f"{_TARGET_PREFIX}{fullname[len(_LEGACY_PREFIX) :]}"
        target_spec = importlib.util.find_spec(target_name)
        if target_spec is None:
            return None

        is_package = target_spec.submodule_search_locations is not None
        loader = _CompatLoader(fullname, target_name)
        return importlib.util.spec_from_loader(fullname, loader, is_package=is_package)


def _install_finder() -> None:
    if any(isinstance(finder, _CompatFinder) for finder in sys.meta_path):
        return
    sys.meta_path.insert(0, _CompatFinder())


warnings.warn(
    "opencode_python is deprecated; import dawn_kestrel instead.",
    DeprecationWarning,
    stacklevel=2,
)

_install_finder()

_target = importlib.import_module(_TARGET_PREFIX)
sys.modules[_LEGACY_PREFIX] = _target
