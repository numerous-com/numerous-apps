import numerous.widgets as wi
from numerous.apps import create_app
from numerous.apps._builtins import tab_visibility
from charts import map_widget, chart

# APP UI

tabs = wi.Tabs(["Basic", "Map", "ChartJS"])

tab_show_basic, tab_show_map, tab_show_chart = tab_visibility(tabs)

counter = wi.Number(default=0, label="Counter:", fit_to_content=True)

counter2 = wi.Number(default=0, label="Counter2:", fit_to_content=True)

def on_click(event):
    counter.value += 1

increment_counter = wi.Button(label="Increment Counter", on_click=on_click)

selection_widget = wi.DropDown(["1", "2", "3"], label="Select Value", fit_to_content=True)


def on_selection_change(event):
    print(f"Selected value: {selection_widget.value}")

selection_widget.observe(on_selection_change, names='value')

map_widget = map_widget()
chart = chart()

app = create_app(template="index.html.j2", dev=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
