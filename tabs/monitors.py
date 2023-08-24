import logging

logger = logging.getLogger(__name__)
from typing import List
from collections import deque
from addict import Dict as AdDict
from nicegui import app, ui
from . import *


class Monitor:
    def __init__(self, name, expansion):
        self._name = name
        self._expansion = expansion
        self._time = None
        self._cpu_temp = None
        self._drive_temp = None
        self._gpu_temp = None
        self._speed = None
        self._status = None
        self._history = dict()
        self._history["speed"] = deque(maxlen=100)
        self._history["cpu_temp"] = deque(maxlen=100)
        self._history["drive_temp"] = deque(maxlen=100)
        self._history["gpu_temp"] = deque(maxlen=100)
        with self._expansion:
            self._add_labels()
            self._add_chart()

    def _add_labels(self):
        self._time = ui.label()
        self._cpu_temp = ui.label()
        self._drive_temp = ui.label()
        self._gpu_temp = ui.label()
        self._speed = ui.label()
        self._status = ui.label()

    def _add_chart(self):
        self._chart = ui.chart(
            {
                "title": False,
                "chart": {
                    "type": "line",
                    "backgroundColor": "#222",
                },
                "xAxis": {
                    "title": {"text": None},
                    "labels": {"enabled": False},
                    "lineColor": "#FFF",
                    "tickColor": "#FFF",
                },
                "yAxis": {
                    "title": {"text": None},
                    "lineColor": "#FFF",
                    "tickColor": "#FFF",
                    "labels": {"style": {"color": "#FFF"}},
                },
                "legend": {"itemStyle": {"color": "#FFF"}},
                "tooltip": {"split": True, "shared": True, "distance": 30, "padding": 5},
                "series": [
                    {"name": "Speed", "data": [0, 0]},
                    {"name": "CPU", "data": [0, 0]},
                    {"name": "Drive", "data": [0, 0]},
                    {"name": "GPU", "data": [0, 0]},
                ],
                "credits": {"enabled": False},
            }
        ).classes("w-full h-64")

    def update_field(self, field, value):
        if field == "time":
            time = value.strftime("%m/%d/%Y, %H:%M:%S")
            self._time.text = f"Last Run Time = {time}"
        elif field == "cpu_temp":
            self._cpu_temp.text = f"Last CPU Temperature = {str(value)}"
            self._history["cpu_temp"].append(value)
            self._chart.options["series"][1]["data"] = list(self._history["cpu_temp"])
        elif field == "drive_temp":
            self._drive_temp.text = f"Last Drive Temperature = {str(value)}"
            self._history["drive_temp"].append(value)
            self._chart.options["series"][2]["data"] = list(self._history["drive_temp"])
        elif field == "gpu_temp":
            self._gpu_temp.text = f"Last GPU Temperature = {str(value)}"
            self._history["gpu_temp"].append(value)
            self._chart.options["series"][3]["data"] = list(self._history["gpu_temp"])
        elif field == "speed":
            self._speed.text = f"Last Speed Adjustment = {str(value)}"
            self._history["speed"].append(value)
            self._chart.options["series"][0]["data"] = list(self._history["speed"])
            self._chart.update()
        elif field == "status":
            self._status.text = f"Last Status = {str(value)}"


class Monitors(Tab):
    def __init__(self):
        self._name = None
        self._card = None
        self._monitors = dict()
        super().__init__()

    def _tab_populate(self):
        self._card = ui.card().style("min-width: 700px").classes("justify-center no-shadow border-[2px]")
        with self._card:
            self._servers_column = ui.column().classes("w-full")

    def _add_server_content(self, name, row):
        expansion = ui.expansion(name, icon="query_stats").classes("w-full")
        self._monitors[name] = Monitor(name=name, expansion=expansion)

    def remove_server(self, name):
        # self._servers[name].remove()
        super().remove_server(name)
        del self._monitors[name]

    def update_field(self, name, field, value):
        self._monitors[name].update_field(field, value)
