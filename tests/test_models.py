import numpy as np
import pytest
from numerous.apps.models import (
    NumpyJSONEncoder,
    encode_model,
    WidgetUpdateMessage,
    InitConfigMessage,
    ErrorMessage,
    GetStateMessage,
    GetWidgetStatesMessage,
    MessageType,
)


@pytest.fixture
def encoder():
    return NumpyJSONEncoder()


# Test data fixtures
@pytest.fixture
def sample_widget_update():
    return {
        "widget_id": "test-widget",
        "property": "value",
        "value": 42,
        "client_id": "client1",
    }


@pytest.fixture
def sample_init_config():
    return {
        "widgets": ["widget1", "widget2"],
        "widget_configs": {"widget1": {"prop": "value"}},
        "template": "<template>",
    }


def test_numpy_encoder_handles_array(encoder):
    arr = np.array([1, 2, 3])
    result = encoder.default(arr)

    assert isinstance(result, list)
    assert result == [1, 2, 3]


def test_numpy_encoder_handles_integer(encoder):
    num = np.int64(42)
    result = encoder.default(num)

    assert isinstance(result, int)
    assert result == 42


def test_numpy_encoder_handles_float(encoder):
    num = np.float64(3.14)
    result = encoder.default(num)

    assert isinstance(result, float)
    assert result == pytest.approx(3.14)


def test_numpy_encoder_handles_boolean(encoder):
    val = np.bool_(True)
    result = encoder.default(val)

    assert isinstance(result, bool)
    assert result is True


def test_numpy_encoder_truncates_css(encoder):
    data = {"css": "a" * 150, "other": "value"}
    result = encoder.default(data)

    assert result["css"] == "<CSS content truncated>"
    assert result["other"] == "value"
    assert len(result) == len(data)


def test_encode_model(sample_widget_update):
    message = WidgetUpdateMessage(**sample_widget_update)
    encoded = encode_model(message)

    assert isinstance(encoded, str)
    for value in sample_widget_update.values():
        assert str(value) in encoded


def test_widget_update_message(sample_widget_update):
    message = WidgetUpdateMessage(**sample_widget_update)

    assert message.type == "widget-update"
    for key, value in sample_widget_update.items():
        assert getattr(message, key) == value


def test_init_config_message(sample_init_config):
    message = InitConfigMessage(**sample_init_config)

    assert message.type == "init-config"
    for key, value in sample_init_config.items():
        assert getattr(message, key) == value


def test_error_message():
    error_data = {
        "error_type": "ValueError",
        "message": "Invalid input",
        "traceback": "traceback content",
    }
    message = ErrorMessage(**error_data)

    assert message.type == "error"
    for key, value in error_data.items():
        assert getattr(message, key) == value


def test_get_state_message():
    message = GetStateMessage()

    assert message.type.value == "get-state"


def test_get_widget_states_message():
    client_id = "client1"
    message = GetWidgetStatesMessage(client_id=client_id)

    assert message.type == MessageType.GET_WIDGET_STATES
    assert message.client_id == client_id
    assert message.model_dump() == {"type": MessageType.GET_WIDGET_STATES, "client_id": client_id}
