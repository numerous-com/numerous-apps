import numerous.widgets as wi
from numerous.apps import app, tab_visibility
import numpy as np
from numerous.widgets.base.plotly import Plot

import traitlets as tl

# APP UI

tabs = wi.Tabs(["Basic", "Map", "ChartJS", "Plotly"])

tab_show_basic, tab_show_map, tab_show_chart, tab_show_plotly = tab_visibility(tabs)

counter = wi.Number(default=0, label="Counter:", fit_to_content=True)

counter2 = wi.Number(default=0, label="Counter2:", fit_to_content=True)

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

y = np.array([100, 120, 110, 130, 125, 140, 135, 150, 145, 160, 155, 170])
months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# Add temperature data
temperatures = [5, 6, 9, 14, 18, 22, 25, 24, 20, 15, 10, 6]  # Sample temperatures in °C

# Create a bar chart
chart = wi.Chart(
    type="bar",
    data={
        "labels": months,
        "datasets": [
            {
            "label": "Average Temperature",
            "data": temperatures,
            "type": "line",
            "borderColor": "rgb(255, 99, 132)",
            "yAxisID": "temperature"
        },
            {
            "label": "Monthly Energy Consumption",
            "data": y,
            "backgroundColor": "rgb(99, 110, 250)",
        }]
    },
    options={
        "responsive": True,
        "plugins": {
            "title": {
                "display": True,
                "text": "Monthly Energy Consumption and Temperature"
            },
            "zoom": {
                "zoom": {
                    "wheel": {
                        "enabled": True
                    },
                    "pinch": {
                        "enabled": True
                    },
                    "mode": 'xy'
                },
                "pan": {
                    "enabled": True,
                    "mode": 'xy'
                }
            }
        },
        "scales": {
            "y": {
                "title": {
                    "display": True,
                    "text": "Energy Consumption (kWh)"
                }
            },
            "temperature": {
                "type": "linear",
                "position": "right",
                "title": {
                    "display": True,
                    "text": "Temperature (°C)"
                }
            }
        }
    }
)

# Generate some sample data

# Create the scatter plot data
data = [{
    'type': 'bar',
    'x': months,
    'y': y,
    'name': 'Monthly Energy Consumption'
}, {
    'type': 'scatter',
    'x': months,
    'y': temperatures,
    'name': 'Average Temperature',
    'yaxis': 'y2',
    'line': {'color': 'rgb(255, 99, 132)'}
}]

# Configure the layout
layout = {
    'title': 'Monthly Energy Consumption and Temperature',
    'xaxis': {'title': 'Month'},
    'yaxis': {'title': 'Energy Consumption (kWh)'},
    'yaxis2': {
        'title': 'Temperature (°C)',
        'overlaying': 'y',
        'side': 'right'
    }
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
    "counter2": counter2,
    }

app = app(widgets, template="index.html.j2", dev=True)

if __name__ == "__main__":
    app.run()

