import numerous.widgets as wi
from numerous.apps import app, ParentVisibility
import traitlets as tl

tab_show_basic = ParentVisibility(visible=True)
tab_show_map = ParentVisibility(visible=False)

tabs = wi.Tabs(["Basic", "Map"])

def on_tab_change(event):
    active_tab = event['new']
    print(f"Selected tab: {active_tab}")
    if active_tab == "Basic":
        tab_show_basic.visible = True
        tab_show_map.visible = False
    elif active_tab == "Map":
        tab_show_basic.visible = False
        tab_show_map.visible = True

tabs.observe(on_tab_change, names='active_tab')



counter = wi.Number(default=0, label="Counter:", fit_to_content=True)

def on_click(event):
    counter.value += 1

increment_counter = wi.Button(label="Increment Counter", on_click=on_click)

selection_widget = wi.DropDown(["1", "2", "3"], label="Select Value", fit_to_content=True)


def on_selection_change(event):
    print(f"Selected value: {selection_widget.value}")

selection_widget.observe(on_selection_change, names='value')

map_widget = wi.MapSelector(points={
    'New York': [-73.985428, 40.748817],    # New York
    'Paris': [2.294481, 48.858370],     # Paris
    'Tokyo': [139.839478, 35.652832]    # Tokyo
}, center= [2.294481, 48.858370], zoom=1)



widgets = {
    "tabs": tabs,
    "tab_show_basic": tab_show_basic,
    "tab_show_map": tab_show_map,
    "counter": counter,
    "increment_counter": increment_counter,
    "selection_widget": selection_widget,
    "map_widget": map_widget
}

app = app(widgets, template="index.html.j2", dev=True)

if __name__ == "__main__":
    app.run()

