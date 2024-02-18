from typing import Any, Dict, List, Union
from nicegui import ui  # type: ignore
from . import Tab
import hush.elements as el
from hush import storage
from hush.hardware.factory import Factory
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
gpu_sensor_names = ["None", "Nvidia", "Supermicro"]


class Configure(Tab):
    def __init__(self, host=None, control_rebuild=None) -> None:
        self._control_rebuild = control_rebuild
        super().__init__(host)

    def _build(self):
        self._add_selections()

    def _add_selections(self):
        with ui.column() as col:
            col.tailwind.align_items("center").align_self("center")
            col.tailwind.width("1/2")
            with el.WRow():
                ui.number(
                    "Delay",
                    value=storage.host(self.host).get("delay", 30),
                    on_change=lambda e: self._store("delay", e.value),
                ).classes("col")
            with el.WRow():
                ui.select(
                    speed_ctrl_names,
                    label="Speed Controller",
                    value=storage.host(self.host).get("speed", speed_ctrl_names[0]),
                    on_change=lambda e: self._store("speed", e.value),
                ).classes("col")
                el.LgButton("Test", on_click=lambda: self._test("speed"))
            with el.WRow():
                ui.select(
                    cpu_sensor_names,
                    label="CPU Temperature Sensor",
                    value=storage.host(self.host).get("cpu", cpu_sensor_names[0]),
                    on_change=lambda e: self._store("cpu", e.value),
                ).classes("col")
                el.LgButton("Test", on_click=lambda: self._test("cpu"))
            with el.WRow():
                ui.select(
                    drive_sensor_names,
                    label="Drive Temperature Sensor",
                    value=storage.host(self.host).get("drive", drive_sensor_names[0]),
                    on_change=lambda e: self._store("drive", e.value),
                ).classes("col")
                el.LgButton("Test", on_click=lambda: self._test("drive"))
            with el.WRow():
                ui.select(
                    gpu_sensor_names,
                    label="GPU Temperature Sensor",
                    value=storage.host(self.host).get("gpu", gpu_sensor_names[0]),
                    on_change=lambda e: self._store("gpu", e.value),
                ).classes("col")
                el.LgButton("Test", on_click=lambda: self._test("gpu"))

    def _store(self, setting, value):
        storage.host(self.host)[setting] = value
        if setting == "speed" and "algo" in storage.host(self.host):
            del storage.host(self.host)["algo"]
        self._control_rebuild()

    async def _test(self, group):
        device = None
        status = None
        try:
            device = await Factory.driver(self.host, group)
            if device is None:
                el.Notification(f"Invalid selection.", type="info")
            else:
                status = el.Notification("Running test...", type="ongoing", spinner=True, timeout=None)
                if group == "speed":
                    await device.set_speed(100)
                    status.message = "Speed set success."
                    status.spinner = False
                    status.type = "positive"
                else:
                    temperature = await device.get_temp()
                    status.message = f"{group.title()} sensor test success; temperature is {temperature}."
                    status.spinner = False
                    status.type = "positive"
        except Exception as e:
            status.message = f"{group.title()} test failed."
            status.spinner = False
            status.type = "negative"
            logger.exception(e)
        if status is not None:
            await asyncio.sleep(5)
            status.dismiss()
