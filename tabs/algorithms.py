import logging

logger = logging.getLogger(__name__)
from nicegui import app, ui
from . import *


class Sliders:
    def __init__(self, expansion):
        self._expansion = expansion

    def add(self):
        n = self._expansion.parent_slot.name
        default_tab = None
        with ui.tabs().classes("w-full") as curve_tabs:
            if configs[n].get("cpu_temp_type", "None") != "None":
                cpu_curve_tab = ui.tab("CPU")
                default_tab = cpu_curve_tab
            if configs[n].get("drive_temp_type", "None") != "None":
                drives_curve_tab = ui.tab("Drives")
                default_tab = drives_curve_tab
        with ui.tab_panels(curve_tabs, value=default_tab, animated=False).classes("w-full").style("min-height: 300px"):
            if configs[n].get("cpu_temp_type", "None") != "None":
                with ui.tab_panel(cpu_curve_tab).classes("w-full"):
                    with ui.row().classes("w-full flex-center"):
                        with ui.row().classes("w-full items-center justify-around"):
                            self._add_single(name=n, sensor="cpu", label="Min", pwm_default=5, temp_default=30)
                            self._add_single(name=n, sensor="cpu", label="Low", pwm_default=20, temp_default=40)
                            self._add_single(name=n, sensor="cpu", label="Medium", pwm_default=50, temp_default=50)
                            self._add_single(name=n, sensor="cpu", label="High", pwm_default=70, temp_default=60)
                            self._add_single(name=n, sensor="cpu", label="Max", pwm_default=100, temp_default=70)
                        with ui.row().classes("w-full items-end justify-center"):
                            ui.label("PWM %")
            if configs[n].get("drive_temp_type", "None") != "None":
                with ui.tab_panel(drives_curve_tab).classes("w-full"):
                    with ui.row().classes("w-full flex-center"):
                        with ui.row().classes("w-full items-center justify-around"):
                            self._add_single(name=n, sensor="drive", label="Min", pwm_default=5, temp_default=30)
                            self._add_single(name=n, sensor="drive", label="Low", pwm_default=20, temp_default=40)
                            self._add_single(name=n, sensor="drive", label="Medium", pwm_default=50, temp_default=50)
                            self._add_single(name=n, sensor="drive", label="High", pwm_default=70, temp_default=60)
                            self._add_single(name=n, sensor="drive", label="Max", pwm_default=100, temp_default=70)
                    with ui.row().classes("w-full items-end justify-center"):
                        ui.label("PWM %")

    def _add_single(self, name, sensor, label, pwm_default, temp_default):
        with ui.column().classes("items-center"):
            if type(configs[name]["algo"]["curves"][sensor]["temp"][label]) is AdDict:
                temp_value = temp_default
                configs[name]["algo"]["curves"][sensor]["temp"][label] = temp_value
            else:
                temp_value = configs[name]["algo"]["curves"][sensor]["temp"][label]
            temp = ui.slider(min=20, max=120, value=temp_value, step=5, on_change=lambda s: self._store_temp(s)).props(
                "reverse vertical label-always snap label-value='value + 'C''"
            )
            temp.default_slot.name = f"{name}.{sensor}.{label}"
            if type(configs[name]["algo"]["curves"][sensor]["pwm"][label]) is AdDict:
                pwm_value = pwm_default
                configs[name]["algo"]["curves"][sensor]["pwm"][label] = pwm_value
            else:
                pwm_value = configs[name]["algo"]["curves"][sensor]["pwm"][label]
            pwm = ui.number(
                label, value=pwm_value, min=0, max=100, step=1, on_change=lambda n: self._store_pwm(n)
            ).style("max-width: 75px")
            pwm.default_slot.name = f"{name}.{sensor}.{label}"
            app.storage.general["servers"] = configs.to_dict()

    def _store_temp(self, ctrl):
        name = ctrl.sender.default_slot.name.split(".")[0]
        sensor = ctrl.sender.default_slot.name.split(".")[1]
        level = ctrl.sender.default_slot.name.split(".")[2]
        temp = ctrl.sender.value
        configs[name]["algo"]["curves"][sensor]["temp"][level] = temp
        app.storage.general["servers"] = configs.to_dict()

    def _store_pwm(self, ctrl):
        name = ctrl.sender.default_slot.name.split(".")[0]
        sensor = ctrl.sender.default_slot.name.split(".")[1]
        level = ctrl.sender.default_slot.name.split(".")[2]
        pwm = ctrl.sender.value
        configs[name]["algo"]["curves"][sensor]["pwm"][level] = pwm
        app.storage.general["servers"] = configs.to_dict()


class iDrac9Sliders(Sliders):
    def add(self):
        n = self._expansion.parent_slot.name
        default_tab = None
        with ui.tabs().classes("w-full") as curve_tabs:
            if configs[n].get("cpu_temp_type", "None") != "None":
                cpu_curve_tab = ui.tab("CPU")
                default_tab = cpu_curve_tab
            if configs[n].get("drive_temp_type", "None") != "None":
                drives_curve_tab = ui.tab("Drives")
                default_tab = drives_curve_tab
        with ui.tab_panels(curve_tabs, value=default_tab, animated=False).classes("w-full").style("min-height: 300px"):
            if configs[n].get("cpu_temp_type", "None") != "None":
                with ui.tab_panel(cpu_curve_tab).classes("w-full"):
                    with ui.row().classes("w-full items-center justify-around"):
                        self._add_single(name=n, sensor="cpu", label="Off", temp_default=30)
                        self._add_single(name=n, sensor="cpu", label="Low", temp_default=40)
                        self._add_single(name=n, sensor="cpu", label="Medium", temp_default=50)
                        self._add_single(name=n, sensor="cpu", label="High", temp_default=60)
                        self._add_single(name=n, sensor="cpu", label="Max", temp_default=70)
            if configs[n].get("drive_temp_type", "None") != "None":
                with ui.tab_panel(drives_curve_tab).classes("w-full"):
                    with ui.row().classes("w-full items-center justify-around"):
                        self._add_single(name=n, sensor="drive", label="Off", temp_default=30)
                        self._add_single(name=n, sensor="drive", label="Low", temp_default=40)
                        self._add_single(name=n, sensor="drive", label="Medium", temp_default=50)
                        self._add_single(name=n, sensor="drive", label="High", temp_default=60)
                        self._add_single(name=n, sensor="drive", label="Max", temp_default=70)

    def _add_single(self, name, sensor, label, temp_default):
        with ui.column().classes("items-center"):
            if type(configs[name]["algo"]["curves"][sensor]["temp"][label]) is AdDict:
                temp_value = temp_default
                configs[name]["algo"]["curves"][sensor]["temp"][label] = temp_value
            else:
                temp_value = configs[name]["algo"]["curves"][sensor]["temp"][label]
            temp = ui.slider(min=20, max=120, value=temp_value, step=5, on_change=lambda s: self._store_temp(s)).props(
                "reverse vertical label-always snap label-value='value + 'C''"
            )
            temp.default_slot.name = f"{name}.{sensor}.{label}"
            ui.label(label)
            configs[name]["algo"]["curves"][sensor]["pwm"][label] = label
            app.storage.general["servers"] = configs.to_dict()


class Algorithms(Tab):
    def __init__(self):
        super().__init__()
        self._name = None
        self._card = None
        self._column = None

    def tab_populate(self):
        self._card = ui.card().style("min-width: 600px").classes("justify-center")
        with self._card:
            self._column = ui.column().classes("w-full")

    def add_server_to_tab(self, name):
        row = add_row(name=name, column=self._column)
        if row is not None:
            with row:
                with ui.expansion(name, icon="bar_chart").classes("w-full") as expansion:
                    if configs[name].get("pwm_ctrl_type", "None") == "iDRAC 9":
                        sliders = iDrac9Sliders(expansion)
                        sliders.add()
                    else:
                        sliders = Sliders(expansion)
                        sliders.add()

    def remove_server_from_tab(self, name):
        remove_row(name, self._column)
