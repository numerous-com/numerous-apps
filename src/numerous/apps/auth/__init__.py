"""
Authentication module for Numerous Apps.

This module provides a pluggable authentication system with support for:
- Environment variable based authentication (simple, no external dependencies)
- Database backed authentication (PostgreSQL/SQLite with user management)
- Custom authentication providers via the AuthProvider protocol

Usage:
    from numerous.apps import create_app
    from numerous.apps.auth import EnvAuthProvider

    auth = EnvAuthProvider()
    app = create_app(template="index.html.j2", auth_provider=auth)
"""

from typing import Any

from .base import AuthProvider
from .models import AuthResult, User


# Lazy imports for optional dependencies
def _get_env_auth_provider() -> type:
    from .providers.env_auth import EnvAuthProvider

    return EnvAuthProvider


def _get_database_auth_provider() -> type:
    from .providers.database_auth import DatabaseAuthProvider

    return DatabaseAuthProvider


# Expose providers through property-like access
class _LazyProviders:
    """Lazy loader for auth providers to avoid import errors."""

    @property
    def EnvAuthProvider(self) -> type:
        return _get_env_auth_provider()

    @property
    def DatabaseAuthProvider(self) -> type:
        return _get_database_auth_provider()


_providers = _LazyProviders()


# For convenient imports: from numerous.apps.auth import EnvAuthProvider
def __getattr__(name: str) -> Any:
    if name == "EnvAuthProvider":
        return _get_env_auth_provider()
    if name == "DatabaseAuthProvider":
        return _get_database_auth_provider()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AuthProvider",
    "AuthResult",
    "User",
    "EnvAuthProvider",
    "DatabaseAuthProvider",
]
