"""Root app module - public survey app at root path (no authentication)."""

from typing import Any

import numerous.widgets as wi
from numerous.apps import create_app
from pathlib import Path


def run_app() -> dict[str, Any]:
    """Create the root survey app widgets."""
    survey_counter = wi.Number(default=0, label="Survey Count:", fit_to_content=True)

    def on_submit(event: dict[str, Any]) -> None:  # noqa: ARG001
        survey_counter.value += 1

    submit_btn = wi.Button(label="Submit Survey", on_click=on_submit)

    return {
        "survey_counter": survey_counter,
        "submit_btn": submit_btn,
    }


# Create the app at root with path_prefix="" for multi-app deployment
app = create_app(
    template="index.html.j2",
    dev=True,
    path_prefix="",  # Explicitly empty for root app in multi-app mode
    app_generator=run_app,
    base_dir=Path(__file__).parent,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

