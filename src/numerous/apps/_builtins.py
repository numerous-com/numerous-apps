import pathlib
from typing import Any

import anywidget
import traitlets
from anywidget import AnyWidget


class ParentVisibility(anywidget.AnyWidget):  # type: ignore [misc]
    _esm = pathlib.Path(__file__).parent / "js" / "parent_visibility.js"
    _css = """
    .numerous-apps-visible {
        display: var(--display-value) !important;
    }
    .numerous-apps-hidden {
        display: none !important;
    }
    [data-display="block"] {
        --display-value: block;
    }
    [data-display="flex"] {
        --display-value: flex;
    }
    [data-display="inline"] {
      --display-value: inline;
    }
    [data-display="inline-block"] {
      --display-value: inline-block;
    }
    [data-display="grid"] {
      --display-value: grid;
    }
    """

    visible = traitlets.Bool(default_value=True).tag(sync=True)

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        super().__init__(**kwargs)
        self._visible = True
        self.observe(self._update_visibility, names="visible")

    def _update_visibility(self, event: Any) -> None:  # noqa: ANN401
        self._visible = event.new


def tab_visibility(tabs_widget: AnyWidget) -> list[ParentVisibility]:
    visibility_widgets = [
        ParentVisibility(visible=tab == tabs_widget.active_tab)
        for tab in tabs_widget.tabs
    ]

    def on_tab_change(event: Any) -> None:  # noqa: ANN401
        for i, tab in enumerate(tabs_widget.tabs):
            visibility_widgets[i].visible = tab == event.new

    tabs_widget.observe(on_tab_change, names="active_tab")
    return visibility_widgets
