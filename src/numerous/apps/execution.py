"""Module for executing apps."""

import json
import logging
from collections.abc import Callable
from queue import Empty
from typing import Any, TypedDict

from anywidget import AnyWidget

from .communication import CommunicationChannel as CommunicationChannel
from .communication import QueueCommunicationManager as CommunicationManager
from .models import (
    ErrorMessage,
    InitConfigMessage,
    NumpyJSONEncoder,
    WidgetUpdateMessage,
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
                "type": "widget_update",
                "widget_id": wid,
                "property": change.name,
                "value": change.new,
            }
        )

    return sync_handler


def _execute(
    communication_manager: CommunicationManager,
    widgets: dict[str, AnyWidget],
    template: str,
) -> None:
    """Handle widget logic in the separate process."""
    transformed_widgets = _transform_widgets(widgets)

    # Set up observers for all widgets
    for widget_id, widget in widgets.items():
        for trait in transformed_widgets[widget_id]["keys"]:
            trait_name = trait
            widget.observe(
                create_handler(communication_manager, widget_id, trait),
                names=[trait_name],
            )

    # Send initial app configuration
    communication_manager.from_app_instance.send(
        InitConfigMessage(
            type="init-config",
            widgets=list(transformed_widgets.keys()),
            widget_configs=transformed_widgets,
            template=template,
        ).model_dump()
    )

    # Listen for messages from the main process
    while not communication_manager.stop_event.is_set():
        try:
            # Block until a message is available, with a timeout
            message = communication_manager.to_app_instance.receive(timeout=0.1)

            if message.get("type") == "get_state":
                logger.info("[App] Sending initial config to main process")
                communication_manager.from_app_instance.send(
                    InitConfigMessage(
                        type="init-config",
                        widgets=list(widgets.keys()),
                        widget_configs=_transform_widgets(widgets),
                        template=template,
                    ).model_dump()
                )
            elif message.get("type") == "get_widget_states":
                logger.info(
                    f"[App] Sending widget states to client {message.get('client_id')}"
                )
                for widget_id, widget in widgets.items():
                    for trait in transformed_widgets[widget_id]["keys"]:
                        communication_manager.from_app_instance.send(
                            WidgetUpdateMessage(
                                type="widget_update",
                                widget_id=widget_id,
                                property=trait,
                                value=getattr(widget, trait),
                                client_id=message.get("client_id"),
                            ).model_dump()
                        )

            else:
                _handle_widget_message(
                    message, communication_manager.from_app_instance, widgets=widgets
                )
        except Empty:
            # No message available, continue waiting
            continue


def _handle_widget_message(
    message: dict[str, Any],
    send_channel: CommunicationChannel,
    widgets: dict[str, AnyWidget],
) -> None:
    """Handle incoming widget messages and update states."""
    widget_id = str(message.get("widget_id"))

    _property_name = message.get("property")
    if _property_name is None:
        logger.error("Property name is None")
        return

    property_name = str(_property_name)

    new_value = message.get("value")

    if not all([widget_id, property_name is not None]):
        logger.error("Invalid widget message format")
        return

    try:
        # Get widget and validate it exists
        widget = widgets.get(widget_id)
        if not widget:
            logger.error(f"Widget {widget_id} not found")
            return

        # Update the widget state
        setattr(widget, property_name, new_value)

        # Send update confirmation back to main process
        send_channel.send(
            WidgetUpdateMessage(
                type="widget_update",
                widget_id=widget_id,
                property=property_name,
                value=new_value,
            ).model_dump()
        )

    except Exception as e:
        logger.exception("Failed to handle widget message.")
        send_channel.send(
            ErrorMessage(
                type="error",
                error_type=type(e).__name__,
                message=str(e),
                traceback="",  # traceback.format_exc()
            ).model_dump()
        )


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
        }

    return widget_descriptions
