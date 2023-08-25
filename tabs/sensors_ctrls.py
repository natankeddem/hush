import logging

logger = logging.getLogger(__name__)
from nicegui import app, ui
from . import *

cpu_sensor_names = [
    "None",
    "Dell iDRAC 7",
    "Dell iDRAC 8",
    "Dell iDRAC 9",
    "HP iLO 4",
    "Supermicro X9",
    "Supermicro X10",
    "Supermicro X11",
    "Cisco M3",
    "Cisco M4",
    "Cisco M5",
]
speed_ctrl_names = [
    "None",
    "Dell iDRAC 7",
    "Dell iDRAC 8",
    "Dell iDRAC 9",
    "HP iLO 4",
    "Supermicro X9",
    "Supermicro X10",
    "Supermicro X11",
    "Cisco M3",
    "Cisco M4",
    "Cisco M5",
]
drive_sensor_names = ["None", "SMART"]
gpu_sensor_names = ["None", "Nvidia"]


class Settings:
    def __init__(self, name, expansion):
        self._name = name
        self._expansion = expansion
        with self._expansion:
            self._add_selections()

    def _add_selections(self):
        ui.select(
            speed_ctrl_names,
            label="Speed Controller",
            value=configs[self._name].get("speed", speed_ctrl_names[0]),
            on_change=lambda e: self._store("speed", e.value),
        ).classes("w-full")
        ui.select(
            cpu_sensor_names,
            label="CPU Temperature Sensor",
            value=configs[self._name].get("cpu", cpu_sensor_names[0]),
            on_change=lambda e: self._store("cpu", e.value),
        ).classes("w-full")
        ui.select(
            drive_sensor_names,
            label="Drive Temperature Sensor",
            value=configs[self._name].get("drive", drive_sensor_names[0]),
            on_change=lambda e: self._store("drive", e.value),
        ).classes("w-full")
        ui.select(
            gpu_sensor_names,
            label="GPU Temperature Sensor",
            value=configs[self._name].get("gpu", gpu_sensor_names[0]),
            on_change=lambda e: self._store("gpu", e.value),
        ).classes("w-full")

    def _store(self, setting, value):
        configs[self._name][setting] = value
        if "algo" in configs[self._name]:
            del configs[self._name]["algo"]
        app.storage.general[configs_version_string] = configs.to_dict()
        tabs.rebuild_server(name=self._name, tabs=["Algorithms"])


class SensorsCtrls(Tab):
    def __init__(self):
        self._name = None
        self._card = None
        super().__init__()

    def _tab_populate(self):
        self._card = ui.card().style("min-width: 700px").classes("justify-center no-shadow border-[2px]")
        with self._card:
            self._servers_column = ui.column().classes("w-full")

    def _add_server_content(self, name, row):
        row.classes("justify-start")
        expansion = ui.expansion(name, icon="settings").classes("w-full")
        Settings(name=name, expansion=expansion)
