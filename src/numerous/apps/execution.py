"""Module for executing apps."""

import inspect
import json
import logging
from collections.abc import Callable, Sequence
from inspect import getmembers
from queue import Empty
from typing import TYPE_CHECKING, Any, TypedDict, cast, get_type_hints

from anywidget import AnyWidget


if TYPE_CHECKING:
    from pydantic import BaseModel

from .communication import CommunicationChannel as CommunicationChannel
from .communication import QueueCommunicationManager as CommunicationManager
from .models import (
    ActionDescription,
    ActionParameter,
    ActionRequestMessage,
    ActionResponseMessage,
    ErrorMessage,
    GetWidgetStatesMessage,
    HandlerResponse,
    InitConfigMessage,
    MessageType,
    NumpyJSONEncoder,
    WidgetUpdateMessage,
    WidgetUpdateRequestMessage,
)


ignored_traits = [
    "comm",
    "layout",
    "log",
    "tabbable",
    "tooltip",
    "keys",
    "_esm",
    "_css",
    "_anywidget_id",
    "_msg_callbacks",
    "_dom_classes",
    "_model_module",
    "_model_module_version",
    "_model_name",
    "_property_lock",
    "_states_to_send",
    "_view_count",
    "_view_module",
    "_view_module_version",
    "_view_name",
]


class WidgetConfig(TypedDict):
    moduleUrl: str
    defaults: dict[str, Any]
    keys: list[str]
    css: str | None


def _transform_widgets(
    widgets: dict[str, AnyWidget],
) -> dict[str, WidgetConfig] | dict[str, Any]:
    transformed = {}
    for key, widget in widgets.items():
        widget_key = f"{key}"

        # Get all the traits of the widget
        args = widget.trait_values()
        traits = widget.traits()

        # Remove ignored traits
        for trait_name in ignored_traits:
            args.pop(trait_name, None)
            traits.pop(trait_name, None)

        json_args = {}
        for outer_key, arg in args.items():
            try:
                json_args[outer_key] = json.dumps(arg, cls=NumpyJSONEncoder)
            except Exception:
                logger.exception(f"Failed to serialize {outer_key}")
                raise

        # Handle both URL-based and string-based widget definitions
        module_source = widget._esm  # noqa: SLF001

        transformed[widget_key] = {
            "moduleUrl": module_source,  # Now this can be either a URL or a JS string
            "defaults": json.dumps(args, cls=NumpyJSONEncoder),
            "keys": list(args.keys()),
            "css": widget._css,  # noqa: SLF001
        }
    return transformed


logger = logging.getLogger(__name__)


def create_handler(
    communication_manager: CommunicationManager, wid: str, trait: str
) -> Callable[[Any], None]:
    def sync_handler(change: Any) -> None:  # noqa: ANN401
        # Skip broadcasting for 'clicked' events to prevent recursion

        if trait == "clicked":
            return

        communication_manager.from_app_instance.send(
            {
                "type": "widget-update",
                "widget_id": wid,
                "property": change.name,
                "value": change.new,
            }
        )

    return sync_handler


class MessageHandler:
    def __init__(
        self,
        widgets: dict[str, AnyWidget],
        template: str,
        transformed_widgets: dict[str, WidgetConfig],
    ) -> None:
        self.widgets = widgets
        self.template = template
        self.transformed_widgets = transformed_widgets
        self.handlers = {
            MessageType.GET_STATE: self._handle_get_state,
            MessageType.GET_WIDGET_STATES: self._handle_get_widget_states,
            MessageType.WIDGET_UPDATE: self._handle_widget_update,
            MessageType.ACTION_REQUEST: self._handle_action_request,
        }

    def handle(self, message: dict[str, Any]) -> HandlerResponse | None:
        """Handle incoming messages."""
        try:
            message_type = MessageType(message.get("type"))
            handler = self.handlers.get(message_type)
            if not handler:
                logger.error(f"No handler found for message type: {message_type}")
                return None

            return handler(message)
        except ValueError:
            logger.exception(f"Unknown message type: {message.get('type')}")
            return None

    def _handle_get_state(self, _: dict[str, Any]) -> HandlerResponse:
        return _handle_get_state(self.widgets, self.template)

    def _handle_get_widget_states(self, message: dict[str, Any]) -> HandlerResponse:
        return _handle_get_widget_states(
            GetWidgetStatesMessage(**message), self.widgets, self.transformed_widgets
        )

    def _handle_widget_update(self, message: dict[str, Any]) -> HandlerResponse:
        return _handle_widget_update(
            WidgetUpdateRequestMessage(**message), self.widgets
        )

    def _handle_action_request(self, message: dict[str, Any]) -> HandlerResponse:  # noqa: C901
        """Handle action request messages."""
        try:
            request = ActionRequestMessage(**message)
            widget = self.widgets.get(request.widget_id)

            def validate_widget(widget: AnyWidget | None) -> None:
                def _raise_if_none() -> None:
                    raise ValueError(f"Widget {request.action_name} not found")  # noqa: TRY301

                if widget is None:
                    _raise_if_none()

            def validate_action(
                widget: AnyWidget, action_name: str
            ) -> Callable[..., Any]:
                def _raise_missing_action() -> None:
                    raise TypeError(  # noqa: TRY301
                        f"Action {action_name} not found on widget {request.widget_id}"
                    )

                def _raise_not_callable() -> None:
                    raise TypeError(f"{action_name} is not a callable action")  # noqa: TRY301

                if not hasattr(widget, action_name):
                    _raise_missing_action()
                if not callable(getattr(widget, action_name)):
                    _raise_not_callable()

                return getattr(widget, action_name)  # type: ignore[no-any-return]

            validate_widget(widget)
            action = validate_action(
                widget=cast(AnyWidget, widget),
                action_name=request.action_name,
            )

            if request.kwargs is None:
                request.kwargs = {}

            if request.args is None:
                request.args = ()

            # Execute the action
            result = action(*tuple(request.args), **request.kwargs)

            # Create response message
            response = ActionResponseMessage(
                type=MessageType.ACTION_RESPONSE.value,
                widget_id=request.widget_id,
                action_name=request.action_name,
                result=result,
                client_id=request.client_id,
                request_id=request.request_id,
            )

            return HandlerResponse(messages=[response])

        except Exception as e:
            logger.exception("Error executing action")
            return HandlerResponse(
                messages=[
                    ActionResponseMessage(
                        type=MessageType.ACTION_RESPONSE.value,
                        widget_id=message.get("widget_id", ""),
                        action_name=message.get("action_name", ""),
                        result=None,
                        error=str(e),
                        client_id=message.get("client_id"),
                        request_id=message.get("request_id", "unknown"),
                    )
                ]
            )


def _execute(
    communication_manager: CommunicationManager,
    widgets: dict[str, AnyWidget],
    template: str,
) -> None:
    """Handle widget logic in the separate process."""
    logger.debug("Starting widget transformation")
    transformed_widgets = _transform_widgets(widgets)
    logger.debug(f"Transformed {len(widgets)} widgets")

    # Set up observers for all widgets
    for widget_id, widget in widgets.items():
        logger.debug(f"Setting up observers for widget {widget_id}")
        for trait in transformed_widgets[widget_id]["keys"]:
            trait_name = trait
            widget.observe(
                create_handler(communication_manager, widget_id, trait),
                names=[trait_name],
            )

    # Send initial app configuration
    logger.debug("Sending initial app configuration")
    init_config = InitConfigMessage(
        type="init-config",
        widgets=list(transformed_widgets.keys()),
        widget_configs=transformed_widgets,
        template=template,
    )
    communication_manager.from_app_instance.send(init_config.model_dump())
    logger.debug("Initial config sent successfully")

    message_handler = MessageHandler(widgets, template, transformed_widgets)
    logger.debug("Message handler initialized, starting message loop")

    # Listen for messages from the main process
    while not communication_manager.stop_event.is_set():
        try:
            message = communication_manager.to_app_instance.receive(timeout=0.1)
            response = message_handler.handle(message)

            # Send all messages from the handler response
            if response:
                for msg in response.messages:
                    communication_manager.from_app_instance.send(msg.model_dump())

        except Empty:
            continue


def _handle_get_state(widgets: dict[str, AnyWidget], template: str) -> HandlerResponse:
    logger.info("[App] Sending initial config to main process")
    return HandlerResponse(
        messages=[
            InitConfigMessage(
                type="init-config",
                widgets=list(widgets.keys()),
                widget_configs=_transform_widgets(widgets),
                template=template,
            )
        ]
    )


def _handle_get_widget_states(
    message: GetWidgetStatesMessage,
    widgets: dict[str, AnyWidget],
    transformed_widgets: dict[str, WidgetConfig],
) -> HandlerResponse:
    logger.info(f"[App] Sending widget states to client {message.client_id}")
    messages = [
        WidgetUpdateMessage(
            type="widget-update",
            widget_id=widget_id,
            property=trait,
            value=getattr(widget, trait),
            client_id=message.client_id,
        )
        for widget_id, widget in widgets.items()
        for trait in transformed_widgets[widget_id]["keys"]
    ]
    return HandlerResponse(messages=messages)


def _handle_widget_update(
    message: WidgetUpdateRequestMessage,
    widgets: dict[str, AnyWidget],
) -> HandlerResponse:
    """Handle incoming widget update messages and update states."""
    try:
        widget = widgets.get(message.widget_id)
        if not widget:
            logger.error(f"Widget {message.widget_id} not found")
            return HandlerResponse.none()

        setattr(widget, message.property, message.value)

        # Create the messages list and cast it to Sequence[BaseModel]
        messages = cast(
            "Sequence[BaseModel]",
            [
                WidgetUpdateMessage(
                    type="widget-update",
                    widget_id=message.widget_id,
                    property=message.property,
                    value=message.value,
                )
            ],
        )
        return HandlerResponse(messages=messages)

    except Exception as e:
        logger.exception("Failed to handle widget message.")
        error_message = ErrorMessage(
            type="error",
            error_type=type(e).__name__,
            message=str(e),
            traceback="",
        )
        return HandlerResponse(messages=cast("Sequence[BaseModel]", [error_message]))


def _get_widget_actions(widget: AnyWidget) -> dict[str, ActionDescription]:
    """Get all actions defined on a widget with detailed parameter information."""
    actions = {}
    for name, member in getmembers(widget.__class__):
        if hasattr(member, "_is_action"):
            # Get function signature
            sig = inspect.signature(member)

            # Get type hints including return type
            type_hints = get_type_hints(member)
            return_type = type_hints.get("return", "Any")
            if hasattr(return_type, "__name__"):
                return_type = return_type.__name__

            # Build parameter list
            parameters = []
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue

                param_type = type_hints.get(param_name, Any).__name__
                parameters.append(
                    ActionParameter(
                        name=param_name,
                        type=param_type,
                        default=None if param.default is param.empty else param.default,
                        is_optional=param.default is not param.empty,
                    )
                )

            actions[name] = ActionDescription(
                name=name,
                doc=member.__doc__ or "",
                parameters=parameters,
                return_type=return_type,
            )

    return actions


def _describe_widgets(widgets: dict[str, AnyWidget]) -> dict[str, Any]:
    """Generate a complete description of widgets and their traits."""
    widget_descriptions = {}
    for widget_id, widget in widgets.items():
        traits = {}
        all_traits = widget.traits()

        # Filter out ignored traits
        valid_traits = {
            name: trait
            for name, trait in all_traits.items()
            if name not in ignored_traits
        }

        for name, trait in valid_traits.items():
            # Handle default value serialization
            default_value = trait.default_value
            # Convert Sentinel values to string representation
            if (
                hasattr(default_value, "__class__")
                and default_value.__class__.__name__ == "Sentinel"
            ):
                default_value = str(default_value)

            # Get basic trait information
            trait_info = {
                "type": trait.__class__.__name__,
                "default": default_value,
                "read_only": trait.read_only if hasattr(trait, "read_only") else False,
            }
            # Add description if available
            if hasattr(trait, "help") and trait.help:
                trait_info["description"] = trait.help

            traits[name] = trait_info

        widget_descriptions[widget_id] = {
            "type": widget.__class__.__name__,
            "traits": traits,
            "actions": _get_widget_actions(
                widget
            ),  # Updated to use new _get_widget_actions
        }

    return widget_descriptions
