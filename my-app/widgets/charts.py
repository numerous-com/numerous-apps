"""Module containing the widgets for the bootstrap app."""

import numpy as np

import numerous.widgets as wi


def map_widget() -> wi.MapSelector:
    return wi.MapSelector(
        points={
            "New York": [-73.985428, 40.748817],  # New York
            "Paris": [2.294481, 48.858370],  # Paris
            "Tokyo": [139.839478, 35.652832],  # Tokyo
        },
        center=[2.294481, 48.858370],
        zoom=1,
    )


y = np.array([100, 120, 110, 130, 125, 140, 135, 150, 145, 160, 155, 170])
months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

# Add temperature data
temperatures = [5, 6, 9, 14, 18, 22, 25, 24, 20, 15, 10, 6]  # Sample temperatures in °C


# Create a bar chart
def chart() -> wi.Chart:
    return wi.Chart(
        chart_type="bar",
        data={
            "labels": months,
            "datasets": [
                {
                    "label": "Average Temperature",
                    "data": temperatures,
                    "type": "line",
                    "borderColor": "rgb(255, 99, 132)",
                    "yAxisID": "temperature",
                },
                {
                    "label": "Monthly Energy Consumption",
                    "data": y,
                    "backgroundColor": "rgb(99, 110, 250)",
                },
            ],
        },
        options={
            "responsive": True,
            "plugins": {
                "title": {
                    "display": True,
                    "text": "Monthly Energy Consumption and Temperature",
                },
                "zoom": {
                    "zoom": {
                        "wheel": {"enabled": True},
                        "pinch": {"enabled": True},
                        "mode": "xy",
                    },
                    "pan": {"enabled": True, "mode": "xy"},
                },
            },
            "scales": {
                "y": {"title": {"display": True, "text": "Energy Consumption (kWh)"}},
                "temperature": {
                    "type": "linear",
                    "position": "right",
                    "title": {"display": True, "text": "Temperature (°C)"},
                },
            },
        },
    )
