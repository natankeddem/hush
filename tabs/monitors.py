import logging

logger = logging.getLogger(__name__)
from typing import List
from collections import deque
from addict import Dict as AdDict
from nicegui import app, ui
from . import *


class Monitors(Tab):
    def __init__(self):
        super().__init__()
        self._name = None
        self._card = None
        self._column = None
        self._expansions = dict()
        self._charts = AdDict()

    def tab_populate(self):
        self._card = ui.card().style("min-width: 600px").classes("justify-center no-shadow border-[2px]")
        with self._card:
            self._column = ui.column().classes("w-full")

    def add_server_to_tab(self, name):
        row = add_row(name=name, column=self._column)
        if row is not None:
            with row:
                expansion = ui.expansion(name, icon="query_stats").classes("w-full")
                self._expansions[name] = expansion
                with expansion:
                    time = ui.label()
                    time.default_slot.name = "time"
                    cpu_temp = ui.label()
                    cpu_temp.default_slot.name = "cpu_temp"
                    drive_temp = ui.label()
                    drive_temp.default_slot.name = "drive_temp"
                    gpu_temp = ui.label()
                    gpu_temp.default_slot.name = "gpu_temp"
                    adjust = ui.label()
                    adjust.default_slot.name = "speed"
                    status = ui.label()
                    status.default_slot.name = "status"
                    self._charts[name]["display"] = ui.chart(
                        {
                            "title": False,
                            "chart": {"type": "line"},
                            "xAxis": {"title": {"text": None}, "labels": {"enabled": False}},
                            "yAxis": {"title": {"text": None}},
                            "series": [
                                {"name": "Speed", "data": []},
                                {"name": "CPUTemp", "data": []},
                                {"name": "DriveTemp", "data": []},
                                {"name": "GPUTemp", "data": []},
                            ],
                        }
                    ).classes("w-full h-64")
                    self._charts[name]["history"]["speed"] = deque(maxlen=100)
                    self._charts[name]["history"]["cpu_temp"] = deque(maxlen=100)
                    self._charts[name]["history"]["drive_temp"] = deque(maxlen=100)
                    self._charts[name]["history"]["gpu_temp"] = deque(maxlen=100)

    def remove_server_from_tab(self, name):
        remove_row(name, self._column)

    def update_field(self, name, field, value):
        if name in self._expansions:
            for c in self._expansions[name].default_slot.children:
                if c.default_slot.name == field:
                    if field == "time":
                        time = value.strftime("%m/%d/%Y, %H:%M:%S")
                        c.text = f"Last Run Time = {time}"
                    elif field == "cpu_temp":
                        c.text = f"Last CPU Temperature = {str(value)}"
                        self._charts[name]["history"]["cpu_temp"].append(value)
                        self._charts[name]["display"].options["series"][1]["data"] = list(
                            self._charts[name]["history"]["cpu_temp"]
                        )
                    elif field == "drive_temp":
                        c.text = f"Last Drive Temperature = {str(value)}"
                        self._charts[name]["history"]["drive_temp"].append(value)
                        self._charts[name]["display"].options["series"][2]["data"] = list(
                            self._charts[name]["history"]["drive_temp"]
                        )
                    elif field == "gpu_temp":
                        c.text = f"Last GPU Temperature = {str(value)}"
                        self._charts[name]["history"]["gpu_temp"].append(value)
                        self._charts[name]["display"].options["series"][3]["data"] = list(
                            self._charts[name]["history"]["gpu_temp"]
                        )
                    elif field == "speed":
                        c.text = f"Last Speed Adjustment = {str(value)}"
                        self._charts[name]["history"]["speed"].append(value)
                        self._charts[name]["display"].options["series"][0]["data"] = list(
                            self._charts[name]["history"]["speed"]
                        )
                        self._charts[name]["display"].update()
                    elif field == "status":
                        c.text = f"Last Status = {str(value)}"
