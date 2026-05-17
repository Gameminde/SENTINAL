"""Phase C subpackage: context, prompt, and decision-frame caches."""

# Additive re-exports introduced by ``sentinel-context-cache-runtime-closure``
# (Task 2.3). The implementations live in
# :mod:`sentinel.perf.caches.context_cache_key`; this package-level surface
# lets callers write ``from sentinel.perf.caches import ContextCacheKeyBuilder``
# without reaching into the submodule. No existing export is removed or
# renamed; this is purely additive.
from sentinel.perf.caches.context_cache_key import (  # noqa: F401
    CacheKeySanitizerRejection,
    ContextCacheKey,
    ContextCacheKeyBuilder,
    MissingCacheKeyComponent,
    OrganStateEntry,
    OrganStateView,
)

__all__ = [
    "CacheKeySanitizerRejection",
    "ContextCacheKey",
    "ContextCacheKeyBuilder",
    "MissingCacheKeyComponent",
    "OrganStateEntry",
    "OrganStateView",
]
