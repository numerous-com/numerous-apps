from unittest.mock import Mock, call

import numpy as np
import pytest
from anywidget import AnyWidget
from traitlets import Int, Unicode

from numerous.apps._execution import (
    NumpyJSONEncoder,
    _execute,
    _handle_widget_message,
    _transform_widgets,
    create_handler,
)


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

        # Configure stop_event to stop after first iteration
        self.stop_event.is_set.side_effect = [False, True]

        # Configure to_app_instance to return one message then raise Empty
        self.to_app_instance.receive.return_value = {"type": "get_state"}


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
        "type": "widget_update",
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

    # Act
    _execute(comm_manager, widgets, template)

    # Assert
    # Should be called at least twice: once for initial config and once for get_state
    assert comm_manager.from_app_instance.send.call_count >= 2

    # Verify both calls had the same init-config message
    expected_config = {
        "type": "init-config",
        "widgets": ["widget1"],
        "widget_configs": _transform_widgets(widgets),
        "template": template,
    }
    calls = [call(expected_config), call(expected_config)]
    comm_manager.from_app_instance.send.assert_has_calls(calls, any_order=True)


def test_execute_handles_get_widget_states():
    """Test that _execute properly handles get_widget_states messages"""
    # Arrange
    comm_manager = CommunicationMock()
    widgets = {"widget1": MockWidget(esm="test")}
    # Override the default message to test get_widget_states
    comm_manager.to_app_instance.receive.return_value = {
        "type": "get_widget_states",
        "client_id": "test_client",
    }

    # Act
    _execute(comm_manager, widgets, "")

    # Assert
    expected_update = {
        "type": "widget_update",
        "widget_id": "widget1",
        "property": "test_trait",
        "value": "test_value",
        "client_id": "test_client",
    }
    comm_manager.from_app_instance.send.assert_any_call(expected_update)


def test_handle_widget_message_successful_update():
    """Test successful widget property update"""
    # Arrange
    widget = MockWidget(esm="test")
    widgets = {"test_widget": widget}
    send_channel = MockCommunicationChannel()
    message = {
        "widget_id": "test_widget",
        "property": "test_trait",
        "value": "new_value",
    }

    # Act
    _handle_widget_message(message, send_channel, widgets)

    # Assert
    assert widget.test_trait == "new_value"
    assert send_channel.sent_messages[0] == {
        "type": "widget_update",
        "widget_id": "test_widget",
        "property": "test_trait",
        "value": "new_value",
    }


def test_handle_widget_message_invalid_widget():
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


def test_handle_widget_message_missing_required_fields():
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


def test_handle_widget_message_invalid_property():
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


def test_handle_widget_message_with_none_property():
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
