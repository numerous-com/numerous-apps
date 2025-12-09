"""Public API for the Numerous framework (factory-only)."""

from __future__ import annotations

import inspect
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from anywidget import AnyWidget

from .app_factory import create_numerous_app
from .multi_app import combine_apps as combine_apps


if TYPE_CHECKING:
    from collections.abc import Callable

    from .server import NumerousApp


T = TypeVar("T")


def create_app(  # noqa: C901
    template: str,
    dev: bool = False,
    widgets: dict[str, AnyWidget] | None = None,
    app_generator: Callable[[], dict[str, AnyWidget]] | None = None,
    auth_provider: object | None = None,
    login_template: str | None = None,
    public_routes: list[str] | None = None,
    protected_routes: list[str] | None = None,
    path_prefix: str = "",
    base_dir: Path | str | None = None,
    theme_css: str | None = None,
    **kwargs: object,
) -> NumerousApp:
    """
    Backwards-compatible wrapper that delegates to `create_numerous_app`.

    This keeps the legacy signature while routing everything through the factory,
    eliminating the old singleton/global path.
    """
    widgets = widgets or {}

    # Collect AnyWidget instances passed as kwargs (legacy behaviour)
    for key, value in list(kwargs.items()):
        if isinstance(value, AnyWidget):
            widgets[key] = value
            kwargs.pop(key)

    # Optional override to force threaded execution
    allow_threaded = bool(kwargs.pop("allow_threaded", app_generator is not None))

    # Stable app identifier so child processes can select the correct NumerousApp
    explicit_app_id = kwargs.pop("app_id", None)
    if explicit_app_id is not None:
        explicit_app_id = str(explicit_app_id)
    if explicit_app_id is None:
        if path_prefix:
            explicit_app_id = path_prefix.lstrip("/").replace("/", "_") or "root"
        else:
            explicit_app_id = Path(template).stem or "root"

    # Resolve module path from caller (best effort)
    module_path = None
    if (frame := inspect.currentframe()) and frame.f_back:
        module_path = frame.f_back.f_code.co_filename
    if module_path is None:
        module_path = str(Path.cwd() / "app.py")

    # Resolve base_dir
    app_base_dir = (
        Path(base_dir) if isinstance(base_dir, str) else (base_dir or Path.cwd())
    )

    widget_dict = app_generator() if app_generator else widgets

    # Legacy behaviour: collect AnyWidget instances from caller locals if none provided
    if (
        not widget_dict
        and app_generator is None
        and (frame := inspect.currentframe())
        and frame.f_back
    ):
        for key, value in frame.f_back.f_locals.items():
            if isinstance(value, AnyWidget):
                widget_dict[key] = value

    return create_numerous_app(
        base_dir=app_base_dir,
        module_path=str(module_path),
        template=template,
        dev=dev,
        path_prefix=path_prefix,
        widgets=widget_dict,
        allow_threaded=allow_threaded,
        auth_provider=auth_provider,
        login_template=login_template,
        public_routes=public_routes,
        protected_routes=protected_routes,
        theme_css=theme_css,
        app_id=explicit_app_id,
    )


def action(func: Callable[..., T]) -> Callable[..., T]:
    """Decorate a method to mark it as an action that can be called via the API."""

    @wraps(func)
    def wrapper(*args: tuple[object, ...], **kwargs: dict[str, object]) -> T:
        return func(*args, **kwargs)

    wrapper._is_action = True  # type: ignore[attr-defined] # noqa: SLF001
    return wrapper
