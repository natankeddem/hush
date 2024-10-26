from typing import Any, Dict, List, Union
from asyncio import run
from copy import copy, deepcopy
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
    "HP iLO 4 All",
    "HP iLO 4 Discrete",
    "Supermicro X9",
    "Supermicro X10",
    "Supermicro X11",
    "Cisco M3",
    "Cisco M4",
    "Cisco M5",
]
pci_sensor_names = [
    "None",
    "HP iLO 4 All",
    "HP iLO 4 Discrete",
]
speed_ctrl_names = [
    "None",
    "Dell iDRAC 7",
    "Dell iDRAC 8",
    "Dell iDRAC 9",
    "HP iLO 4 All",
    "HP iLO 4 Discrete",
    "Supermicro X9",
    "Supermicro X10",
    "Supermicro X11",
    "Cisco M3",
    "Cisco M4",
    "Cisco M5",
]
drive_sensor_names = ["None", "SMART All", "SMART Discrete"]
gpu_sensor_names = ["None", "Nvidia", "Supermicro"]


class Configure(Tab):
    def __init__(self, host=None, control_rebuild=None) -> None:
        self._control_rebuild = control_rebuild
        super().__init__(host)

    def _build(self):
        self._select = {}
        self._skeleton = {}
        self._ilo4 = {}
        self._smart = {}
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
                self._select["speed"] = ui.select(
                    speed_ctrl_names,
                    label="Speed Controller",
                    value=storage.host(self.host).get("speed", speed_ctrl_names[0]),
                    on_change=lambda e: self._store("speed", e.value),
                ).classes("col")
                el.LgButton("Test", on_click=lambda: self._test("speed"))
            self._skeleton["speed"] = ui.skeleton(type="QInput", height="40px").classes("w-full")
            self._skeleton["speed"].visible = False
            self._ilo4["speed"] = el.WRow()
            self._ilo4["speed"].visible = False
            with el.WRow():
                self._select["cpu"] = ui.select(
                    cpu_sensor_names,
                    label="CPU Temperature Sensor",
                    value=storage.host(self.host).get("cpu", cpu_sensor_names[0]),
                    on_change=lambda e: self._store("cpu", e.value),
                ).classes("col")
                el.LgButton("Test", on_click=lambda: self._test("cpu"))
            self._skeleton["cpu"] = ui.skeleton(type="QInput", height="40px").classes("w-full")
            self._skeleton["cpu"].visible = False
            self._ilo4["cpu"] = el.WRow()
            self._ilo4["cpu"].visible = False
            with el.WRow():
                self._select["pci"] = ui.select(
                    pci_sensor_names,
                    label="PCI Temperature Sensor",
                    value=storage.host(self.host).get("pci", pci_sensor_names[0]),
                    on_change=lambda e: self._store("pci", e.value),
                ).classes("col")
                el.LgButton("Test", on_click=lambda: self._test("pci"))
            self._skeleton["pci"] = ui.skeleton(type="QInput", height="40px").classes("w-full")
            self._skeleton["pci"].visible = False
            self._ilo4["pci"] = el.WRow()
            self._ilo4["pci"].visible = False
            with el.WRow():
                self._select["drive"] = ui.select(
                    drive_sensor_names,
                    label="Drive Temperature Sensor",
                    value=storage.host(self.host).get("drive", drive_sensor_names[0]),
                    on_change=lambda e: self._store("drive", e.value),
                ).classes("col")
                el.LgButton("Test", on_click=lambda: self._test("drive"))
            self._skeleton["drive"] = ui.skeleton(type="QInput", height="40px").classes("w-full")
            self._skeleton["drive"].visible = False
            self._smart["drive"] = el.WRow()
            self._smart["drive"].visible = False
            with el.WRow():
                ui.select(
                    gpu_sensor_names,
                    label="GPU Temperature Sensor",
                    value=storage.host(self.host).get("gpu", gpu_sensor_names[0]),
                    on_change=lambda e: self._store("gpu", e.value),
                ).classes("col")
                el.LgButton("Test", on_click=lambda: self._test("gpu"))
            ui.timer(0, self._update_ctrls, once=True)

    async def _store(self, group, value):
        storage.host(self.host)[group] = value
        if group == "speed" and "algo" in storage.host(self.host):
            del storage.host(self.host)["algo"]
        await self._build_ilo4_ctrl(group)
        await self._build_smart_ctrl()
        await Factory.close(self.host, group)
        self._control_rebuild()

    async def _build_ilo4_ctrl(self, group):
        if self._select[group].value == "HP iLO 4 Discrete":
            self._skeleton[group].visible = True
            self._ilo4[group].bind_visibility_from(self._skeleton[group], value=False)
            labels = {"speed": "HP iLO 4 Fans", "cpu": "HP iLO 4 CPUs", "pci": "HP iLO 4 PCIs"}
            self._ilo4[group].clear()
            with self._ilo4[group]:
                await Factory.close(self.host, group)
                device = await Factory.driver(self.host, group)
                if group == "speed":
                    options = await device.get_fan_names()
                elif group == "cpu":
                    options = await device.get_cpu_temp_names()
                elif group == "pci":
                    options = await device.get_pci_temp_names()
                else:
                    options = []
                ui.select(
                    options,
                    label=labels[group],
                    value=storage.host(self.host)["ilo4"].get(group, []),
                    on_change=lambda e: self._store_ilo4(group, e.value),
                    multiple=True,
                ).classes("col")
            self._skeleton[group].visible = False
        else:
            if group in self._ilo4:
                self._ilo4[group].visible = False

    async def _build_smart_ctrl(self):
        if self._select["drive"].value == "SMART Discrete":
            self._skeleton["drive"].visible = True
            self._smart["drive"].bind_visibility_from(self._skeleton["drive"], value=False)
            self._smart["drive"].clear()
            with self._smart["drive"]:
                await Factory.close(self.host, "drive")
                device = await Factory.driver(self.host, "drive")
                options = await device.get_drive_list()
                ui.select(
                    options,
                    label="SMART Drives",
                    value=storage.host(self.host)["smart"].get("drive", []),
                    on_change=lambda e: self._store_smart("drive", e.value),
                    multiple=True,
                ).classes("col")
            self._skeleton["drive"].visible = False
        else:
            self._smart["drive"].visible = False

    async def _update_ctrls(self):
        groups = ["speed", "cpu", "pci"]
        for group in groups:
            if self._select[group].value == "HP iLO 4 Discrete":
                self._skeleton[group].visible = True
        if self._select["drive"].value == "SMART Discrete":
            self._skeleton["drive"].visible = True
        for group in groups:
            await self._build_ilo4_ctrl(group)
        await self._build_smart_ctrl()

    async def _store_ilo4(self, group, value):
        storage.host(self.host)["ilo4"][group] = value
        await Factory.close(self.host, group)

    async def _store_smart(self, group, value):
        storage.host(self.host)["smart"][group] = value
        await Factory.close(self.host, group)

    async def _test(self, group):
        device = None
        status = None
        try:
            device = await Factory.driver(self.host, group)
            if device is None:
                el.Notification("Invalid selection.", type="info")
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
