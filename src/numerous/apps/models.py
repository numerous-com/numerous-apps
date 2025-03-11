"""Models for the Numerous app framework."""

import json
from collections.abc import Sequence
from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel


class MessageType(str, Enum):
    """Message types for communication between server and client."""

    WIDGET_UPDATE = "widget-update"
    GET_STATE = "get-state"
    GET_WIDGET_STATES = "get-widget-states"
    ACTION_REQUEST = "action-request"
    ACTION_RESPONSE = "action-response"
    ERROR = "error"
    INIT_CONFIG = "init-config"
    SESSION_ERROR = "session-error"


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
    type: str = MessageType.WIDGET_UPDATE.value
    widget_id: str
    property: str
    value: Any
    client_id: str | None = None
    request_id: str | None = None


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
    type: MessageType = MessageType.GET_STATE


class GetWidgetStatesMessage(BaseModel):
    type: MessageType = MessageType.GET_WIDGET_STATES
    client_id: str


class TraitDescription(BaseModel):
    """Description of a widget trait."""

    type: str
    default: Any
    read_only: bool
    description: str | None = None


class ActionParameter(BaseModel):
    """Description of an action parameter."""

    name: str
    type: str
    default: Any | None = None
    is_optional: bool = False


class ActionDescription(BaseModel):
    """Description of a widget action."""

    name: str
    doc: str
    parameters: list[ActionParameter]
    return_type: str


class WidgetDescription(BaseModel):
    """Description of a widget."""

    type: str
    traits: dict[str, TraitDescription]
    actions: dict[str, ActionDescription]


class TemplateDescription(BaseModel):
    """Description of the app template."""

    name: str
    source: str
    variables: list[str]


class AppInfo(BaseModel):
    """Basic information about the app."""

    dev_mode: bool
    base_dir: str
    module_path: str
    allow_threaded: bool


class AppDescription(BaseModel):
    """Complete description of a Numerous app."""

    app_info: AppInfo
    template: TemplateDescription
    widgets: dict[str, WidgetDescription]


class TraitValue(BaseModel):
    """Value of a widget trait."""

    widget_id: str
    trait: str
    value: Any
    session_id: str


class SetTraitValue(BaseModel):
    """Model for setting a trait value."""

    value: Any


class WidgetUpdateRequestMessage(BaseModel):
    type: MessageType = MessageType.WIDGET_UPDATE
    widget_id: str
    property: str
    value: Any


class WebSocketBatchUpdateMessage(BaseModel):
    """Message for batch update of multiple widget properties."""

    type: str = "widget-batch-update"
    widget_id: str
    properties: dict[str, Any]
    request_id: str | None = None


class HandlerResponse(BaseModel):
    """Base class for all handler responses."""

    messages: Sequence[BaseModel]

    @classmethod
    def none(cls) -> "HandlerResponse":
        """Create a HandlerResponse with no messages."""
        return cls(messages=[])


class ActionRequestMessage(BaseModel):
    """Message for requesting an action to be executed."""

    type: str = MessageType.ACTION_REQUEST.value
    widget_id: str
    action_name: str
    args: tuple[Any, ...] | None = None
    kwargs: dict[str, Any] | None = None
    request_id: str
    client_id: str | None = None


class ActionResponseMessage(BaseModel):
    """Message containing the response from an action execution."""

    type: str = MessageType.ACTION_RESPONSE.value
    widget_id: str
    action_name: str
    result: Any | None = None
    error: str | None = None
    client_id: str | None = None
    request_id: str


class SessionErrorMessage(BaseModel):
    """Message indicating a session error."""

    type: str = MessageType.SESSION_ERROR.value
    message: str = "Session not found or expired"


WebSocketMessage = (
    WidgetUpdateMessage
    | ActionResponseMessage
    | InitConfigMessage
    | ErrorMessage
    | WebSocketBatchUpdateMessage
    | SessionErrorMessage
)
