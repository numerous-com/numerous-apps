import numerous.widgets as wi
from numerous.apps import app, tab_visibility
import numpy as np
from numerous.widgets.base.plotly import Plot

import traitlets as tl

# APP UI

tabs = wi.Tabs(["Plotly", "Basic", "Map", "ChartJS"])

tab_show_plotly, tab_show_basic, tab_show_map, tab_show_chart = tab_visibility(tabs)

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



# Create a line chart
chart = wi.Chart(
    type="line",
    data={
        "labels": ["January", "February", "March", "April", "May"],
        "datasets": [{
            "label": "My Dataset",
            "data": [65, 59, 80, 81, 56],
            "borderColor": "rgb(75, 192, 192)",
            "tension": 0.1
        }]
    },
    options={
        "responsive": True,
        "plugins": {
            "title": {
                "display": True,
                "text": "My Chart"
            }
        }
    }
)




# Generate some sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create the scatter plot data
data = [{
    'type': 'scatter',
    'x': x,
    'y': y,
    'mode': 'markers',
    'name': 'Sin Wave'
}]

# Configure the layout
layout = {
    'title': 'Simple Scatter Plot',
    'xaxis': {'title': 'X'},
    'yaxis': {'title': 'sin(x)'}
}

# Optional configuration (e.g., disable the modebar)
config = {
    'displayModeBar': True
}

# Create and display the plot
plot = Plot(
    data=data,
    layout=layout,
    config=config
)

widgets = {
    "tabs": tabs,
    "tab_show_basic": tab_show_basic,
    "tab_show_map": tab_show_map,
    "tab_show_chart": tab_show_chart,
    "tab_show_plotly": tab_show_plotly,
    "counter": counter,
    "increment_counter": increment_counter,
    "selection_widget": selection_widget,
    "map_widget": map_widget,
    "chart": chart,
    "plot": plot,
    }

app = app(widgets, template="index.html.j2", dev=True)

if __name__ == "__main__":
    app.run()

