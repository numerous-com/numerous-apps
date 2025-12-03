"""Public app module - no authentication required."""

from typing import Any

import numerous.widgets as wi
from numerous.apps import create_app


def run_app() -> dict[str, Any]:
    """Create the public app widgets."""
    counter = wi.Number(default=0, label="Public Counter:", fit_to_content=True)

    def on_click(event: dict[str, Any]) -> None:  # noqa: ARG001
        counter.value += 1

    increment_btn = wi.Button(label="Increment", on_click=on_click)

    message = wi.Text(default="Welcome to the public app!", label="Message:")

    return {
        "counter": counter,
        "increment_btn": increment_btn,
        "message": message,
    }


# Create the app with path prefix for multi-app deployment
app = create_app(
    template="index.html.j2",
    dev=True,
    path_prefix="/public",
    app_generator=run_app,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

