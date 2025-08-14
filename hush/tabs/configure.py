from typing import Any, Dict, List, Union
import asyncio
from copy import copy, deepcopy
import json
from nicegui import ui, events  # type: ignore
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
    "Supermicro X10 All",
    "Supermicro X10 Discrete",
    "Supermicro X11 All",
    "Supermicro X11 Discrete",
    "Cisco M3",
    "Cisco M4",
    "Cisco M5",
    "OpenJBOD",
    "Nvidia",
    "Shared",
]
drive_sensor_names = ["None", "SMART All", "SMART Discrete"]
gpu_sensor_names = ["None", "Nvidia", "Supermicro"]
chassis_sensor_names = ["None", "OpenJBOD"]


class Configure(Tab):
    def __init__(self, host=None, control_rebuild=None) -> None:
        self._control_rebuild = control_rebuild
        super().__init__(host)

    def _build(self):
        self._select = {}
        self._skeleton = {}
        self._ilo4 = {}
        self._smart = {}
        self._shared = {}
        self._supermicro = {}
        with ui.dialog() as self.import_verify, el.Card():
            self.import_verify.props("persistent")
            el.BigLabel("Overwrite all drivers and curves?")
            with el.WRow():
                el.LgButton("Yes", on_click=lambda: self.import_verify.submit("yes")).tailwind().flex("1")
                el.LgButton("No", on_click=lambda: self.import_verify.submit("no")).tailwind().flex("1")
        with ui.dialog() as self.import_spinner:
            self.import_spinner.props("persistent")
            ui.spinner("tail", size="300px", color="orange")
        with ui.column() as self.selection_container:
            self.selection_container.tailwind.align_items("center").align_self("center")
            self.selection_container.tailwind.width("1/2")
            self._add_selections()

    def _add_selections(self):
        with el.WRow():
            upload = el.Upload(on_upload=self.handle_import_upload, on_cancelled=self.handle_import_cancelled, auto_upload=True)
            upload.props("accept=.json").classes("hidden")
            ui.button("Import", on_click=lambda _: self.handle_import_select(upload))
            ui.button("Export", on_click=self.handle_export)
        with el.WRow():
            el.Help(
                "Sets the minimum time in seconds that must pass before the fan speed can be changed again. "
                "This helps to prevent rapid, frequent fan speed adjustments. "
                "Actual delay may be slightly longer due to system processing time."
            )
            ui.number(
                "Delay",
                value=storage.host(self.host).get("delay", 30),
                on_change=lambda e: self._store_delay(e.value),
            ).classes("col")
        with el.WRow():
            self._select["speed"] = ui.select(
                speed_ctrl_names,
                label="Speed Controller",
                value=storage.host(self.host).get("speed", speed_ctrl_names[0]),
                on_change=lambda e: self._store_select("speed", e.value),
            ).classes("col")
            el.LgButton("Test", on_click=lambda: self._test("speed"))
        self._skeleton["speed"] = ui.skeleton(type="QInput", height="40px").classes("w-full")
        self._skeleton["speed"].visible = False
        self._ilo4["speed"] = el.WRow()
        self._ilo4["speed"].visible = False
        self._shared["speed"] = el.WRow()
        self._shared["speed"].visible = False
        self._supermicro["speed"] = el.WRow()
        self._supermicro["speed"].visible = False
        with el.WRow():
            self._select["cpu"] = ui.select(
                cpu_sensor_names,
                label="CPU Temperature Sensor",
                value=storage.host(self.host).get("cpu", cpu_sensor_names[0]),
                on_change=lambda e: self._store_select("cpu", e.value),
            ).classes("col")
            el.LgButton("Test", on_click=lambda: self._test("cpu"))
        self._skeleton["cpu"] = ui.skeleton(type="QInput", height="40px").classes("w-full")
        self._skeleton["cpu"].visible = False
        self._ilo4["cpu"] = el.WRow()
        self._ilo4["cpu"].visible = False
        self._shared["cpu"] = el.WRow()
        self._shared["cpu"].visible = False
        with el.WRow():
            self._select["pci"] = ui.select(
                pci_sensor_names,
                label="PCI Temperature Sensor",
                value=storage.host(self.host).get("pci", pci_sensor_names[0]),
                on_change=lambda e: self._store_select("pci", e.value),
            ).classes("col")
            el.LgButton("Test", on_click=lambda: self._test("pci"))
        self._skeleton["pci"] = ui.skeleton(type="QInput", height="40px").classes("w-full")
        self._skeleton["pci"].visible = False
        self._ilo4["pci"] = el.WRow()
        self._ilo4["pci"].visible = False
        self._shared["pci"] = el.WRow()
        self._shared["pci"].visible = False
        with el.WRow():
            self._select["drive"] = ui.select(
                drive_sensor_names,
                label="Drive Temperature Sensor",
                value=storage.host(self.host).get("drive", drive_sensor_names[0]),
                on_change=lambda e: self._store_select("drive", e.value),
            ).classes("col")
            el.LgButton("Test", on_click=lambda: self._test("drive"))
        self._skeleton["drive"] = ui.skeleton(type="QInput", height="40px").classes("w-full")
        self._skeleton["drive"].visible = False
        self._smart["drive"] = el.WRow()
        self._smart["drive"].visible = False
        self._shared["drive"] = el.WRow()
        self._shared["drive"].visible = False
        with el.WRow():
            self._select["gpu"] = ui.select(
                gpu_sensor_names,
                label="GPU Temperature Sensor",
                value=storage.host(self.host).get("gpu", gpu_sensor_names[0]),
                on_change=lambda e: self._store_select("gpu", e.value),
            ).classes("col")
            el.LgButton("Test", on_click=lambda: self._test("gpu"))
        self._skeleton["gpu"] = ui.skeleton(type="QInput", height="40px").classes("w-full")
        self._skeleton["gpu"].visible = False
        self._shared["gpu"] = el.WRow()
        self._shared["gpu"].visible = False
        with el.WRow():
            self._select["chassis"] = ui.select(
                chassis_sensor_names,
                label="Chassis Temperature Sensor",
                value=storage.host(self.host).get("chassis", chassis_sensor_names[0]),
                on_change=lambda e: self._store_select("chassis", e.value),
            ).classes("col")
            el.LgButton("Test", on_click=lambda: self._test("chassis"))
        self._skeleton["chassis"] = ui.skeleton(type="QInput", height="40px").classes("w-full")
        self._skeleton["chassis"].visible = False
        self._shared["chassis"] = el.WRow()
        self._shared["chassis"].visible = False
        ui.timer(0, self._update_ctrls, once=True)

    async def _store_delay(self, value):
        storage.host(self.host)["delay"] = value

    async def _store_select(self, group, value):
        storage.host(self.host)[group] = value
        if group == "speed" and "algo" in storage.host(self.host):
            del storage.host(self.host)["algo"]
        await self._build_ilo4_ctrl(group)
        await self._build_smart_ctrl()
        await self._build_shared_ctrl(group)
        await self._build_supermicro_ctrl(group)
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
                    on_change=lambda e: self._store_select_ilo4(group, e.value),
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
                    on_change=lambda e: self._store_select_smart("drive", e.value),
                    multiple=True,
                ).classes("col")
            self._skeleton["drive"].visible = False
        else:
            self._smart["drive"].visible = False

    async def _build_shared_ctrl(self, group):
        labels = {"speed": "Shared Speed Control Host"}
        options = list(storage.hosts.keys())
        options.remove(self.host)
        if self._select[group].value == "Shared":
            self._skeleton[group].visible = True
            self._shared[group].bind_visibility_from(self._skeleton[group], value=False)
            self._shared[group].clear()
            if options:
                with self._shared[group]:
                    select = ui.select(
                        options,
                        label=labels[group],
                        value=storage.host(self.host)["shared"].get(group, None),
                        on_change=lambda e: self._store_select_shared(group, e.value),
                    ).classes("col")
                    if select.value is None:
                        select.value = options[0]
                self._skeleton[group].visible = False
        else:
            if group in self._ilo4:
                self._shared[group].visible = False

    async def _build_supermicro_ctrl(self, group):
        if self._select[group].value == "Supermicro X10 Discrete" or self._select[group].value == "Supermicro X11 Discrete":
            self._skeleton[group].visible = True
            self._supermicro[group].bind_visibility_from(self._skeleton[group], value=False)
            labels = {"speed": "Supermicro Fan Zones"}
            self._supermicro[group].clear()
            with self._supermicro[group]:
                if group == "speed":
                    options = ["00", "01", "02", "03"]
                else:
                    options = []
                ui.select(
                    options,
                    label=labels[group],
                    value=storage.host(self.host)["supermicro"].get(group, []),
                    on_change=lambda e: self._store_select_supermicro(group, e.value),
                    multiple=True,
                ).classes("col")
            self._skeleton[group].visible = False
        else:
            if group in self._supermicro:
                self._supermicro[group].visible = False

    async def _update_ctrls(self):
        groups = ["speed", "cpu", "pci", "drive", "gpu", "chassis"]
        for group in groups:
            if self._select[group].value == "Shared":
                self._skeleton[group].visible = True
        for group in groups:
            await self._build_shared_ctrl(group)
        groups = ["speed", "cpu", "pci"]
        for group in groups:
            if "Discrete" in self._select[group].value:
                self._skeleton[group].visible = True
        for group in groups:
            await self._build_ilo4_ctrl(group)
            await self._build_supermicro_ctrl(group)
        await self._build_smart_ctrl()

    async def _store_select_ilo4(self, group, value):
        storage.host(self.host)["ilo4"][group] = value
        await Factory.close(self.host, group)

    async def _store_select_smart(self, group, value):
        storage.host(self.host)["smart"][group] = value
        await Factory.close(self.host, group)

    async def _store_select_shared(self, group, value):
        storage.host(self.host)["shared"][group] = value
        await Factory.close(self.host, group)

    async def _store_select_supermicro(self, group, value):
        storage.host(self.host)["supermicro"][group] = value
        await Factory.close(self.host, group)

    async def handle_import_select(self, upload: ui.upload):
        result = await self.import_verify
        if result == "yes":
            self.import_spinner.open()
            upload.run_method("pickFiles")

    async def handle_import_cancelled(self, e: events.UiEventArguments):
        self.import_spinner.close()

    async def handle_import_upload(self, e: events.UploadEventArguments):
        try:
            content = json.loads(e.content.read().decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Import decoding error: {e}")
        except Exception as e:
            logger.error(f"Import error occurred: {e}")
        if content:
            storage.host(self.host).update(deepcopy(content))
            self.selection_container.clear()
            with self.selection_container:
                self._add_selections()
            self._control_rebuild()
        self.import_spinner.close()

    async def handle_export(self):
        host_data = deepcopy(storage.host(self.host))
        for key in ["oob", "os", "mqtt"]:
            if key in host_data:
                del host_data[key]
        export_data = json.dumps(host_data)
        filename = "".join([i for i in self.host if i.isalpha()])
        ui.download.content(export_data, f"{filename}.json")

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
