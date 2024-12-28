"""Module containing the app for the bootstrap app."""

from typing import Any

from charts import chart, map_widget

import numerous.widgets as wi
from numerous.apps import create_app
from numerous.apps._builtins import tab_visibility
from numerous.apps._communication import Event
from numerous.logger import logger


# APP UI


def run_app() -> dict[str, Any]:
    tabs = wi.Tabs(["Basic", "Map", "ChartJS"])

    tab_show_basic, tab_show_map, tab_show_chart = tab_visibility(tabs)

    counter = wi.Number(default=0, label="Counter:", fit_to_content=True)

    counter2 = wi.Number(default=0, label="Counter2:", fit_to_content=True)

    def on_click(event: Event) -> None:  # noqa: ARG001
        counter.value += 1

    increment_counter = wi.Button(label="Increment Counter", on_click=on_click)

    selection_widget = wi.DropDown(
        ["1", "2", "3"], label="Select Value", fit_to_content=True
    )

    def on_selection_change(event: Event) -> None:  # noqa: ARG001
        logger.debug(f"Selected value: {selection_widget.value}")

    selection_widget.observe(on_selection_change, names="value")

    return {
        "counter": counter,
        "counter2": counter2,
        "increment_counter": increment_counter,
        "selection_widget": selection_widget,
        "tabs": tabs,
        "tab_show_basic": tab_show_basic,
        "tab_show_map": tab_show_map,
        "tab_show_chart": tab_show_chart,
        "map_widget": map_widget(),
        "chart": chart(),
    }


app = create_app(template="index.html.j2", dev=True, app_generator=run_app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
