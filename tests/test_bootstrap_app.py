import pytest
from numerous.apps.bootstrap_app.app import run_app

def test_run_app():
    # Run the app to get the components
    components = run_app()

    # Check that the components dictionary contains the expected keys
    expected_keys = [
        "counter", "counter2", "increment_counter", 
        "selection_widget", "tabs", "tab_show_basic", 
        "tab_show_map", "tab_show_chart", "map_widget", "chart"
    ]
    for key in expected_keys:
        assert key in components, f"Missing component: {key}"

    # Check that the counter is initialized correctly
    assert components["counter"].value == 0, "Counter should be initialized to 0"
    assert components["counter2"].value == 0, "Counter2 should be initialized to 0"

    # Check that the increment button is present
    # assert components["increment_counter"].label == "Increment Counter", "Button label mismatch"

    # Check that the selection widget has the correct options
    assert components["selection_widget"].options == ["1", "2", "3"], "Selection options mismatch"

    # Additional checks can be added here for other components

# Run the test
if __name__ == "__main__":
    pytest.main()
