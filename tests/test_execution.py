from unittest.mock import Mock, call
from queue import Empty

import numpy as np
import pytest
from anywidget import AnyWidget
from traitlets import Int, Unicode

from numerous.apps.execution import (
    NumpyJSONEncoder,
    _execute,
    # _handle_widget_message,
    _transform_widgets,
    create_handler,
    _describe_widgets,
    _get_widget_actions,
    MessageHandler
)
from numerous.apps.models import WidgetUpdateMessage
from numerous.apps import action

class MockWidget(AnyWidget):
    test_trait = Unicode("test_value")
    number_trait = Int()

    def __init__(self, esm, css=None):
        self._esm = esm
        self._css = css
        super().__init__()

    def trait_values(self):
        return {"test_trait": "test_value", "number_trait": 0}

    def traits(self, sync=True):
        return {"test_trait": None, "number_trait": None}


class CommunicationMock:
    def __init__(self):
        self.from_app_instance = Mock()
        self.to_app_instance = Mock()
        self.stop_event = Mock()

        # Configure stop_event to stop after two iterations
        self.stop_event.is_set.side_effect = [False, False, True]

        # Configure to_app_instance to return one message then raise Empty
        self.to_app_instance.receive.side_effect = [
            {"type": "get_state"},
            Empty()
        ]


class MockCommunicationChannel:
    def __init__(self):
        self.sent_messages = []

    def send(self, message):
        self.sent_messages.append(message)


def test_transform_widgets_module_source():
    """Test that the moduleUrl is correctly set from _esm"""
    test_esm = "test_module_source"
    widgets = {"widget1": MockWidget(esm=test_esm)}

    result = _transform_widgets(widgets)

    assert result["widget1"]["moduleUrl"] == test_esm


def test_transform_widgets_keys():
    """Test that the keys list contains the correct trait names"""
    widgets = {"widget1": MockWidget(esm="test")}

    result = _transform_widgets(widgets)

    assert result["widget1"]["keys"] == ["test_trait", "number_trait"]


def test_transform_widgets_css():
    """Test that the CSS is correctly transferred"""
    test_css = "test_css"
    widgets = {"widget1": MockWidget(esm="test", css=test_css)}

    result = _transform_widgets(widgets)

    assert result["widget1"]["css"] == test_css


def test_transform_widgets_correct_key():
    """Test that the widget key in the transformed dict matches the input key"""
    widgets = {"test_widget": MockWidget(esm="test")}

    result = _transform_widgets(widgets)

    assert "test_widget" in result


def test_execute_sends_initial_config():
    """Test that _execute sends the initial configuration message"""
    # Arrange
    comm_manager = CommunicationMock()
    widgets = {"widget1": MockWidget(esm="test")}
    template = "<div>test</div>"

    # Act
    _execute(comm_manager, widgets, template)

    # Assert
    expected_config = {
        "type": "init-config",
        "widgets": ["widget1"],
        "widget_configs": _transform_widgets(widgets),
        "template": template,
    }
    comm_manager.from_app_instance.send.assert_any_call(expected_config)


def test_execute_sets_up_observers():
    """Test that _execute sets up observers for widget traits"""
    # Arrange
    comm_manager = CommunicationMock()
    widget = MockWidget(esm="test")
    widgets = {"widget1": widget}

    # Act
    _execute(comm_manager, widgets, "")

    # Trigger the observer by changing the trait
    widget.test_trait = "new_value"

    # Assert
    expected_update = {
        "type": "widget-update",
        "widget_id": "widget1",
        "property": "test_trait",
        "value": "new_value",
    }
    comm_manager.from_app_instance.send.assert_any_call(expected_update)


def test_execute_handles_get_state_message():
    """Test that _execute properly handles get_state messages"""
    # Arrange
    comm_manager = CommunicationMock()
    widgets = {"widget1": MockWidget(esm="test")}
    template = "<div>test</div>"

    # Configure stop_event to stop after three iterations to ensure message processing
    comm_manager.stop_event.is_set.side_effect = [False, False, False, True]

    # Configure to_app_instance to return one message then raise Empty
    comm_manager.to_app_instance.receive.side_effect = [
        {"type": "get-state"},
        Empty(),
        Empty()
    ]

    # Act
    _execute(comm_manager, widgets, template)

    # Assert
    # Verify that send was called exactly twice
    assert comm_manager.from_app_instance.send.call_count == 2

    # Verify the calls were correct
    expected_config = {
        "type": "init-config",
        "widgets": ["widget1"],
        "widget_configs": _transform_widgets(widgets),
        "template": template,
    }
    
    # Both calls should be the same config message
    comm_manager.from_app_instance.send.assert_has_calls([
        call(expected_config),
        call(expected_config)
    ])


def test_execute_handles_get_widget_states():
    """Test that _execute properly handles get_widget_states messages"""
    # Arrange
    comm_manager = CommunicationMock()
    widgets = {"widget1": MockWidget(esm="test")}

    # Configure stop_event to stop after three iterations to ensure message processing
    comm_manager.stop_event.is_set.side_effect = [False, False, False, True]

    # Configure to_app_instance to return get_widget_states message then Empty
    comm_manager.to_app_instance.receive.side_effect = [
        {
            "type": "get-widget-states",
            "client_id": "test_client",
        },
        Empty(),
        Empty()
    ]

    # Act
    _execute(comm_manager, widgets, "")

    # Assert
    # Instead of checking for exact field match, check key fields
    # and ignore request_id which is now added by default
    calls = comm_manager.from_app_instance.send.call_args_list
    widget_update_calls = [
        call_args[0][0] for call_args in calls 
        if isinstance(call_args[0][0], dict) and call_args[0][0].get("type") == "widget-update"
    ]
    
    # Find a call with the right basic properties
    matching_calls = [
        update for update in widget_update_calls
        if update.get("widget_id") == "widget1" 
        and update.get("property") == "test_trait"
        and update.get("value") == "test_value"
        and update.get("client_id") == "test_client"
    ]
    
    assert matching_calls, "No matching widget update call found"


def _test_handle_widget_message_successful_update():
    """Test successful widget property update"""
    # Arrange
    widget = MockWidget(esm="test")
    widgets = {"test_widget": widget}
    send_channel = MockCommunicationChannel()
    message = WidgetUpdateMessage(
        widget_id="test_widget",
        property="test_trait",
        value="new_value",
        type="widget_update",
    ).model_dump()

    # Act
    _handle_widget_message(message, send_channel, widgets)

    # Assert
    assert widget.test_trait == "new_value"
    sent_message = send_channel.sent_messages[0]
    assert sent_message == message


def _test_handle_widget_message_invalid_widget():
    """Test handling of message for non-existent widget"""
    # Arrange
    widgets = {}
    send_channel = MockCommunicationChannel()
    message = {
        "widget_id": "non_existent_widget",
        "property": "test_trait",
        "value": "new_value",
    }

    # Act
    _handle_widget_message(message, send_channel, widgets)

    # Assert
    assert len(send_channel.sent_messages) == 0  # No update message should be sent


def _test_handle_widget_message_missing_required_fields():
    """Test handling of message with missing required fields"""
    # Arrange
    widgets = {"test_widget": MockWidget(esm="test")}
    send_channel = MockCommunicationChannel()
    message = {
        "widget_id": "test_widget"
        # Missing 'property' and 'value'
    }

    # Act
    _handle_widget_message(message, send_channel, widgets)

    if send_channel.sent_messages:
        print("Sent messages:")
        print(send_channel.sent_messages)

    # Assert
    assert len(send_channel.sent_messages) == 0  # No update message should be sent


def _test_handle_widget_message_invalid_property():
    """Test handling of message with invalid property value type"""
    # Arrange
    widget = MockWidget(esm="test")
    widgets = {"test_widget": widget}
    send_channel = MockCommunicationChannel()
    message = {
        "widget_id": "test_widget",
        "property": "number_trait",
        "value": "not_a_number",
    }

    # Act
    _handle_widget_message(message, send_channel, widgets)

    # Assert
    assert len(send_channel.sent_messages) == 1
    assert send_channel.sent_messages[0]["type"] == "error"
    assert "TraitError" in send_channel.sent_messages[0]["error_type"]
    assert "message" in send_channel.sent_messages[0]


def test_numpy_json_encoder_ndarray():
    """Test NumpyJSONEncoder handles numpy arrays correctly"""
    encoder = NumpyJSONEncoder()
    test_array = np.array([1, 2, 3])
    result = encoder.default(test_array)
    assert result == [1, 2, 3]


def test_numpy_json_encoder_numeric_types():
    """Test NumpyJSONEncoder handles various numpy numeric types"""
    encoder = NumpyJSONEncoder()

    assert encoder.default(np.int32(42)) == 42
    assert encoder.default(np.float32(3.14)) == pytest.approx(3.14)
    assert encoder.default(np.bool_(True)) == True


def test_numpy_json_encoder_css_truncation():
    """Test NumpyJSONEncoder truncates long CSS content"""
    encoder = NumpyJSONEncoder()
    long_css = "a" * 200
    test_dict = {"css": long_css}

    result = encoder.default(test_dict)
    assert result["css"] == "<CSS content truncated>"


def test_numpy_json_encoder_fallback():
    """Test NumpyJSONEncoder falls back to default for unsupported types"""
    encoder = NumpyJSONEncoder()

    # Should raise TypeError for unsupported type
    with pytest.raises(TypeError):
        encoder.default(set([1, 2, 3]))


def test_transform_widgets_serialization_error():
    """Test error handling during widget transformation when serialization fails"""

    class UnserializableWidget(MockWidget):
        def trait_values(self):
            return {"bad_trait": set()}  # Sets are not JSON serializable

    widgets = {"widget1": UnserializableWidget(esm="test")}

    with pytest.raises(Exception):
        _transform_widgets(widgets)


def test_execute_clicked_trait_no_broadcast():
    """Test that 'clicked' trait changes are not broadcasted"""
    # Arrange
    comm_manager = CommunicationMock()
    widget = MockWidget(esm="test")
    widgets = {"widget1": widget}

    # Act
    _execute(comm_manager, widgets, "")

    # Simulate a 'clicked' trait change
    class ChangeEvent:
        name = "clicked"
        new = True

    # Create and call a handler directly to simulate clicked event
    handler = create_handler(comm_manager, "widget1", "clicked")
    handler(ChangeEvent())

    # Assert no widget_update message was sent for the clicked trait
    for call in comm_manager.from_app_instance.send.call_args_list:
        args = call[0][0]
        if args.get("type") == "widget_update":
            assert args.get("property") != "clicked"


def _test_handle_widget_message_with_none_property():
    """Test handling widget message with None property value"""
    # Arrange
    widget = MockWidget(esm="test")
    widgets = {"test_widget": widget}
    send_channel = MockCommunicationChannel()
    message = {"widget_id": "test_widget", "property": None, "value": "new_value"}

    # Act
    _handle_widget_message(message, send_channel, widgets)

    # Assert
    # Check that no message is sent if the property is None
    assert len(send_channel.sent_messages) == 0


def test_get_widget_actions():
    """Test _get_widget_actions function"""
    class TestWidget(MockWidget):
        @action
        def action1(self):
            """Test action 1"""
            return None

        @action
        def action2(self):
            """Test action 2"""
            pass

    widget = TestWidget(esm="test")
    assert widget.action1._is_action == True
    assert widget.action2._is_action == True
    
def test_describe_widgets():
    """Test _describe_widgets function"""
    class MockTrait:
        def __init__(self, default="test_value", read_only=False, help=None):
            self.default_value = default
            self.read_only = read_only
            self.help = help

    class TestWidget(MockWidget):
        @action
        def action1(self):
            """Test action"""
            pass

        def traits(self, sync=True):
            return {
                "test_trait": MockTrait(
                    default="test_value",
                    read_only=False,
                    help="Test trait help"
                )
            }

    widget = TestWidget(esm="test")
    widgets = {"test_widget": widget}
    
    description = _describe_widgets(widgets)
    
    assert "test_widget" in description
    widget_desc = description["test_widget"]
    assert widget_desc["type"] == "TestWidget"
    assert "traits" in widget_desc
    assert "actions" in widget_desc
    assert "action1" in widget_desc["actions"]
    
    # Verify trait description
    trait_info = widget_desc["traits"]["test_trait"]
    assert trait_info["type"] == "MockTrait"
    assert trait_info["default"] == "test_value"
    assert trait_info["read_only"] is False
    assert trait_info["description"] == "Test trait help"


def test_describe_widgets_with_sentinel_value():
    """Test _describe_widgets handling of Sentinel values"""
    class SentinelMock:
        @property
        def __class__(self):
            return type("Sentinel", (), {})

    class TraitWithSentinel:
        default_value = SentinelMock()
        read_only = False

    class TestWidget(MockWidget):
        def traits(self, sync=True):
            return {"test_trait": TraitWithSentinel()}

    widget = TestWidget(esm="test")
    widgets = {"test_widget": widget}
    
    description = _describe_widgets(widgets)
    
    trait_info = description["test_widget"]["traits"]["test_trait"]
    assert isinstance(trait_info["default"], str)


def test_describe_widgets_with_trait_help():
    """Test _describe_widgets handling of trait help text"""
    class TraitWithHelp:
        default_value = "default"
        read_only = False
        help = "Help text"

    class TestWidget(MockWidget):
        def traits(self, sync=True):
            return {"test_trait": TraitWithHelp()}

    widget = TestWidget(esm="test")
    widgets = {"test_widget": widget}
    
    description = _describe_widgets(widgets)
    
    trait_info = description["test_widget"]["traits"]["test_trait"]
    assert trait_info["description"] == "Help text"


def test_message_handler_handle_invalid_message_type():
    """Test handling of invalid message type"""
    handler = MessageHandler({}, "", {})
    
    response = handler.handle({"type": "invalid_type"})
    
    assert response is None


def test_message_handler_handle_missing_type():
    """Test handling of message without type"""
    handler = MessageHandler({}, "", {})
    
    response = handler.handle({})
    
    assert response is None


def test_execute_empty_queue():
    """Test _execute handling of empty queue"""
    comm_manager = CommunicationMock()
    # Configure to_app_instance to always raise Empty
    comm_manager.to_app_instance.receive.side_effect = Empty()
    
    # Should not raise any exceptions
    _execute(comm_manager, {}, "")


def test_execute_multiple_messages():
    """Test _execute handling multiple messages"""
    comm_manager = CommunicationMock()
    # Configure stop_event to stop after four iterations to ensure all messages are processed
    comm_manager.stop_event.is_set.side_effect = [False, False, False, False, True]
    
    # Configure multiple messages
    comm_manager.to_app_instance.receive.side_effect = [
        {"type": "get-state"},
        {"type": "get-widget-states", "client_id": "test"},
        Empty(),
        Empty()
    ]
    
    widgets = {"widget1": MockWidget(esm="test")}
    
    _execute(comm_manager, widgets, "")
    
    # Assert
    # Should have sent at least 3 messages:
    # 1. Initial init-config
    # 2. Response to get-state
    # 3. Response to get-widget-states (widget state update)
    assert comm_manager.from_app_instance.send.call_count >= 3

    # Verify the expected messages were sent
    expected_config = {
        "type": "init-config",
        "widgets": ["widget1"],
        "widget_configs": _transform_widgets(widgets),
        "template": "",
    }
    
    # Get all the calls
    calls = comm_manager.from_app_instance.send.call_args_list
    
    # Check that we have at least two config messages
    config_calls = [
        call_args[0][0] for call_args in calls 
        if isinstance(call_args[0][0], dict) 
        and call_args[0][0].get("type") == "init-config"
    ]
    assert len(config_calls) >= 2, "Expected at least two init-config messages"
    
    # Check that we have at least one widget update message with the right properties
    widget_update_calls = [
        call_args[0][0] for call_args in calls 
        if isinstance(call_args[0][0], dict) 
        and call_args[0][0].get("type") == "widget-update"
        and call_args[0][0].get("widget_id") == "widget1"
        and call_args[0][0].get("client_id") == "test"
    ]
    assert widget_update_calls, "No matching widget update calls found"
    
    # Check that we got updates for all the expected traits
    trait_updates = {
        update.get("property") for update in widget_update_calls
    }
    expected_traits = {"test_trait", "number_trait"}
    assert expected_traits.issubset(trait_updates), f"Missing trait updates. Found: {trait_updates}, Expected to include: {expected_traits}"


def test_action_request_with_args_kwargs():
    """Test action request with arguments"""
    class TestWidget(MockWidget):
        @action
        def test_action(self, arg1, kwarg1=None):
            return f"Received {arg1} and {kwarg1}"

    widget = TestWidget(esm="test")
    widgets = {"widget1": widget}
    handler = MessageHandler(widgets, "", {})
    
    message = {
        "type": "action-request",
        "widget_id": "widget1",
        "action_name": "test_action",
        "args": ["test_arg"],
        "kwargs": {"kwarg1": "test_kwarg"},
        "client_id": "test_client",
        "request_id": "test_request"
    }
    
    response = handler.handle(message)
    
    assert response is not None
    assert len(response.messages) == 1
    assert response.messages[0].result == "Received test_arg and test_kwarg"


def test_action_request_raises_exception():
    """Test action request that raises an exception"""
    class TestWidget(MockWidget):
        @action
        def failing_action(self):
            raise ValueError("Test error")

    widget = TestWidget(esm="test")
    widgets = {"widget1": widget}
    handler = MessageHandler(widgets, "", {})
    
    message = {
        "type": "action-request",
        "widget_id": "widget1",
        "action_name": "failing_action",
        "args": [],
        "kwargs": {},
        "client_id": "test_client",
        "request_id": "test_request"
    }
    
    response = handler.handle(message)
    
    assert response is not None
    assert len(response.messages) == 1
    assert response.messages[0].error == "Test error"
    assert response.messages[0].result is None
