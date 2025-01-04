"""Models for the Numerous app framework."""

import json
from typing import Any

import numpy as np
from pydantic import BaseModel


class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy arrays and other numpy types."""

    def default(
        self,
        obj: np.ndarray | np.integer | np.floating | np.bool_ | dict[str, Any],
    ) -> list[Any] | int | float | bool | dict[str, Any]:
        """Encode numpy arrays and other numpy types to JSON."""
        if isinstance(obj, np.ndarray):
            return obj.tolist()  # type: ignore[no-any-return]
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, dict) and "css" in obj:
            obj_copy = obj.copy()
            max_css_length = 100
            if len(obj_copy.get("css", "")) > max_css_length:
                obj_copy["css"] = "<CSS content truncated>"
            return obj_copy
        return super().default(obj)  # type: ignore[no-any-return]


def encode_model(model: BaseModel) -> str:
    _dict = model.model_dump()
    return json.dumps(_dict, cls=NumpyJSONEncoder)


class WidgetUpdateMessage(BaseModel):
    type: str = "widget_update"
    widget_id: str
    property: str
    value: Any
    client_id: str | None = None


class InitConfigMessage(BaseModel):
    type: str = "init-config"
    widgets: list[str]
    widget_configs: dict[str, Any]
    template: str


class ErrorMessage(BaseModel):
    type: str = "error"
    error_type: str
    message: str
    traceback: str


class GetStateMessage(BaseModel):
    type: str = "get_state"


class GetWidgetStatesMessage(BaseModel):
    type: str = "get_widget_states"
    client_id: str
