"""Module containing the app framework."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from .app_server import create_app as create_app
from .multi_app import combine_apps as combine_apps


T = TypeVar("T")


def action(func: Callable[..., T]) -> Callable[..., T]:
    """Decorate a method to mark it as an action that can be called via the API."""

    @wraps(func)
    def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> T:
        return func(*args, **kwargs)

    # Mark the function as an action
    wrapper._is_action = True  # type: ignore[attr-defined] # noqa: SLF001
    return wrapper
