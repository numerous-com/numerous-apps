from numerous.apps._builtins import tab_visibility


class MockTabsWidget:
    def __init__(self, tabs, active_tab):
        self.tabs = tabs
        self.active_tab = active_tab
        self._observers = []

    def observe(self, callback, names):
        self._observers.append((callback, names))

    def trigger_tab_change(self, new_tab):
        class Event:
            def __init__(self, new_value):
                self.new = new_value

        self.active_tab = new_tab
        for callback, names in self._observers:
            if names == "active_tab":
                callback(Event(new_tab))


def test_tab_visibility():
    # Create mock tabs widget with 3 tabs
    mock_tabs = MockTabsWidget(tabs=["tab1", "tab2", "tab3"], active_tab="tab1")

    # Get visibility widgets
    visibility_widgets = tab_visibility(mock_tabs)

    # Check initial state
    assert len(visibility_widgets) == 3
    assert visibility_widgets[0].visible == True  # First tab should be visible
    assert visibility_widgets[1].visible == False
    assert visibility_widgets[2].visible == False

    # Test tab change
    mock_tabs.trigger_tab_change("tab2")
    assert visibility_widgets[0].visible == False
    assert visibility_widgets[1].visible == True  # Second tab should be visible
    assert visibility_widgets[2].visible == False

    # Test another tab change
    mock_tabs.trigger_tab_change("tab3")
    assert visibility_widgets[0].visible == False
    assert visibility_widgets[1].visible == False
    assert visibility_widgets[2].visible == True  # Third tab should be visible
