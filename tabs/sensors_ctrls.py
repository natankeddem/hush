import logging

logger = logging.getLogger(__name__)
from nicegui import app, ui
from . import *

cpu_temp_types = ["None", "iDRAC 7", "iDRAC 8", "iDRAC 9", "iLO 4", "X9", "X10", "X11"]
speed_ctrl_types = ["None", "iDRAC 7", "iDRAC 8", "iDRAC 9", "iLO 4", "X9", "X10", "X11"]
drive_temp_types = ["None", "SMART"]


class SensorsCtrls(Tab):
    def __init__(self):
        super().__init__()
        self._name = None
        self._card = None
        self._column = None

    def tab_populate(self):
        self._card = ui.card().style("min-width: 600px").classes("justify-center no-shadow border-[2px]")
        with self._card:
            self._column = ui.column().classes("w-full")

    def add_server_to_tab(self, name):
        row = add_row(name=name, column=self._column)
        if row is not None:
            with row.classes("justify-start"):
                with ui.expansion(name, icon="settings").classes("w-full"):
                    ui.select(
                        speed_ctrl_types,
                        label="Speed Controller",
                        value=configs[name].get("speed_ctrl_type", speed_ctrl_types[0]),
                        on_change=lambda v: self.set_sensor_ctrl("speed_ctrl_type", v),
                    ).classes("w-full")
                    ui.select(
                        cpu_temp_types,
                        label="Cpu Temperature Sensor",
                        value=configs[name].get("cpu_temp_type", speed_ctrl_types[0]),
                        on_change=lambda v: self.set_sensor_ctrl("cpu_temp_type", v),
                    ).classes("w-full")
                    ui.select(
                        drive_temp_types,
                        label="Drive Temperature Sensor",
                        value=configs[name].get("drive_temp_type", speed_ctrl_types[0]),
                        on_change=lambda v: self.set_sensor_ctrl("drive_temp_type", v),
                    ).classes("w-full")

    def set_sensor_ctrl(self, sensor_ctrl, value):
        n = value.sender.parent_slot.parent.parent_slot.name
        configs[n][sensor_ctrl] = value.sender.value
        sensor = sensor_ctrl.split("_")[0]
        if "algo" in configs[n]:
            del configs[n]["algo"]
        app.storage.general[configs_version_string] = configs.to_dict()
        self.remove_server_from_tabs(name=n, tabs=["Algorithms"])
        self.add_server_to_tabs(name=n, tabs=["Algorithms"])

    def remove_server_from_tab(self, name):
        remove_row(name, self._column)
