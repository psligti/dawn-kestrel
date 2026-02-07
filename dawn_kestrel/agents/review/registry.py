"""Reviewer registry for agent composition.

This module provides a factory/registry seam for managing reviewer agents.
It enables dynamic registration and composition of reviewers while preserving
default behavior for backward compatibility.

Usage:
    # Get default core reviewers
    core_reviewers = ReviewerRegistry.get_core_reviewers()

    # Get all reviewers (core + optional)
    all_reviewers = ReviewerRegistry.get_all_reviewers()

    # Get specific reviewer by name
    reviewer_class = ReviewerRegistry.get_reviewer("security")
    reviewer = reviewer_class()

    # Register custom reviewer
    ReviewerRegistry.register("custom_review", CustomReviewer)
"""
from __future__ import annotations

from typing import Dict, List, Type, Optional

from dawn_kestrel.agents.review.base import BaseReviewerAgent


class ReviewerRegistry:
    """Registry for managing reviewer agent classes.

    Provides factory methods for creating reviewer instances and supports
    dynamic registration of custom reviewers. Default reviewers are registered
    at module import time.

    Thread-safety: This class uses class-level state and is not thread-safe.
    Concurrent modifications should be avoided.
    """

    _registry: Dict[str, Type[BaseReviewerAgent]] = {}
    _core_reviewers: List[str] = []
    _optional_reviewers: List[str] = []

    @classmethod
    def register(
        cls,
        name: str,
        reviewer_class: Type[BaseReviewerAgent],
        is_core: bool = False,
    ) -> None:
        """Register a reviewer class.

        Args:
            name: Unique name for the reviewer (used for CLI selection)
            reviewer_class: Reviewer class to register
            is_core: If True, reviewer is in core set (default: False = optional)

        Raises:
            ValueError: If reviewer name already registered
        """
        if name in cls._registry:
            raise ValueError(f"Reviewer '{name}' already registered")

        cls._registry[name] = reviewer_class

        if is_core:
            if name not in cls._core_reviewers:
                cls._core_reviewers.append(name)
        else:
            if name not in cls._optional_reviewers:
                cls._optional_reviewers.append(name)

    @classmethod
    def get_reviewer(cls, name: str) -> Type[BaseReviewerAgent]:
        """Get reviewer class by name.

        Args:
            name: Registered reviewer name

        Returns:
            Reviewer class

        Raises:
            KeyError: If reviewer name not found in registry
        """
        if name not in cls._registry:
            raise KeyError(
                f"Unknown reviewer: '{name}'. "
                f"Available reviewers: {', '.join(sorted(cls._registry.keys()))}"
            )
        return cls._registry[name]

    @classmethod
    def create_reviewer(cls, name: str) -> BaseReviewerAgent:
        """Create reviewer instance by name.

        Args:
            name: Registered reviewer name

        Returns:
            Reviewer instance

        Raises:
            KeyError: If reviewer name not found in registry
        """
        reviewer_class = cls.get_reviewer(name)
        return reviewer_class()

    @classmethod
    def get_core_reviewers(cls) -> List[BaseReviewerAgent]:
        """Get list of core reviewer instances.

        Returns:
            List of instantiated core reviewers
        """
        return [cls.create_reviewer(name) for name in cls._core_reviewers]

    @classmethod
    def get_all_reviewers(cls) -> List[BaseReviewerAgent]:
        """Get list of all reviewer instances (core + optional).

        Returns:
            List of instantiated reviewers
        """
        all_names = cls._core_reviewers + cls._optional_reviewers
        return [cls.create_reviewer(name) for name in all_names]

    @classmethod
    def get_all_names(cls) -> List[str]:
        """Get list of all registered reviewer names.

        Returns:
            Sorted list of reviewer names
        """
        return sorted(cls._registry.keys())

    @classmethod
    def get_core_names(cls) -> List[str]:
        """Get list of core reviewer names.

        Returns:
            Sorted list of core reviewer names
        """
        return sorted(cls._core_reviewers)

    @classmethod
    def get_optional_names(cls) -> List[str]:
        """Get list of optional reviewer names.

        Returns:
            Sorted list of optional reviewer names
        """
        return sorted(cls._optional_reviewers)


def _register_default_reviewers() -> None:
    """Register all default reviewers at module import time."""
    from dawn_kestrel.agents.review.agents.architecture import ArchitectureReviewer
    from dawn_kestrel.agents.review.agents.security import SecurityReviewer
    from dawn_kestrel.agents.review.agents.documentation import DocumentationReviewer
    from dawn_kestrel.agents.review.agents.telemetry import TelemetryMetricsReviewer
    from dawn_kestrel.agents.review.agents.linting import LintingReviewer
    from dawn_kestrel.agents.review.agents.unit_tests import UnitTestsReviewer
    from dawn_kestrel.agents.review.agents.diff_scoper import DiffScoperReviewer
    from dawn_kestrel.agents.review.agents.requirements import RequirementsReviewer
    from dawn_kestrel.agents.review.agents.performance import PerformanceReliabilityReviewer
    from dawn_kestrel.agents.review.agents.dependencies import DependencyLicenseReviewer
    from dawn_kestrel.agents.review.agents.changelog import ReleaseChangelogReviewer

    ReviewerRegistry.register("architecture", ArchitectureReviewer, is_core=True)
    ReviewerRegistry.register("security", SecurityReviewer, is_core=True)
    ReviewerRegistry.register("documentation", DocumentationReviewer, is_core=True)
    ReviewerRegistry.register("telemetry", TelemetryMetricsReviewer, is_core=True)
    ReviewerRegistry.register("linting", LintingReviewer, is_core=True)
    ReviewerRegistry.register("unit_tests", UnitTestsReviewer, is_core=True)

    ReviewerRegistry.register("diff_scoper", DiffScoperReviewer, is_core=False)
    ReviewerRegistry.register("requirements", RequirementsReviewer, is_core=False)
    ReviewerRegistry.register("performance", PerformanceReliabilityReviewer, is_core=False)
    ReviewerRegistry.register("dependencies", DependencyLicenseReviewer, is_core=False)
    ReviewerRegistry.register("changelog", ReleaseChangelogReviewer, is_core=False)
_register_default_reviewers()
