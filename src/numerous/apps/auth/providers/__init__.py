"""Built-in authentication providers."""

from typing import Any

from .env_auth import EnvAuthProvider


__all__ = ["EnvAuthProvider"]


# DatabaseAuthProvider is only available with [auth-db] extra
# Use lazy loading to avoid import errors
def __getattr__(name: str) -> Any:
    if name == "DatabaseAuthProvider":
        try:
            from .database_auth import DatabaseAuthProvider

            return DatabaseAuthProvider
        except ImportError as e:
            raise ImportError(
                "DatabaseAuthProvider requires additional dependencies. "
                "Install with: pip install numerous-apps[auth-db]"
            ) from e
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
