"""Built-in delegation policies.

This package provides ready-to-use delegation policies that can be
combined to create sophisticated delegation behavior.

Available policies:
- ComplexityBasedDelegationPolicy: Delegate based on task complexity
- BudgetAwareDelegationPolicy: Enforce budget constraints
- StagnationAwarePolicy: Stop when progress stalls
- DomainBasedDelegationPolicy: Route to agents by domain
"""

from dawn_kestrel.policy.builtin.delegation import (
    BudgetAwareDelegationPolicy,
    ComplexityBasedDelegationPolicy,
    DomainBasedDelegationPolicy,
    StagnationAwarePolicy,
)

__all__ = [
    "ComplexityBasedDelegationPolicy",
    "BudgetAwareDelegationPolicy",
    "StagnationAwarePolicy",
    "DomainBasedDelegationPolicy",
]
