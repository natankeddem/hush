import logging

logger = logging.getLogger(__name__)
from nicegui import app, ui
from . import *


class PwmControl:
    def __init__(self, name, sensor, column):
        self._name = name
        self._sensor = sensor
        self._column = column
        self._card = None
        self._chart = None
        with self._column:
            self._add_algo_select()
            self._card = ui.card().classes("justify-center w-full no-shadow border-[2px]")
            self._add_control()

    def _add_algo_select(self):
        ui.toggle(
            ["curve", "pid"],
            value=configs[self._name]["algo"][self._sensor].get("type", "curve"),
            on_change=lambda v: self._set_algo(v),
        )

    def _set_algo(self, v):
        configs[self._name]["algo"][self._sensor]["type"] = v.value
        app.storage.general[configs_version_string] = configs.to_dict()
        self._card.clear()
        self._add_control()

    def _add_control(self):
        with self._card:
            algo = configs[self._name]["algo"][self._sensor].get("type", "curve")
            if algo == "curve":
                self._add_curve()
            elif algo == "pid":
                self._add_pid()

    def _add_pid(self):
        with ui.column().classes("w-full items-center justify-around"):
            with ui.row().classes("w-full items-center justify-around"):
                ui.number(
                    label="Kp",
                    value=configs[self._name]["algo"][self._sensor]["pid"].get("kp", 5),
                    on_change=lambda e: self._store_pid("kp", e.value),
                ).props("outlined dense").classes("text-right q-pa-xs q-ma-xs")
                ui.number(
                    label="Ki",
                    value=configs[self._name]["algo"][self._sensor]["pid"].get("ki", 0.01),
                    on_change=lambda e: self._store_pid("ki", e.value),
                ).props("outlined dense").classes("text-right q-pa-xs q-ma-xs")
            with ui.row().classes("w-full items-center justify-around"):
                ui.number(
                    label="Kd",
                    value=configs[self._name]["algo"][self._sensor]["pid"].get("kd", 0.1),
                    on_change=lambda e: self._store_pid("kd", e.value),
                ).props("outlined dense").classes("text-right q-pa-xs q-ma-xs")
                ui.number(
                    label="Target",
                    value=configs[self._name]["algo"][self._sensor]["pid"].get("target", 40),
                    on_change=lambda e: self._store_pid("target", e.value),
                ).props("outlined dense").classes("text-right q-pa-xs q-ma-xs")

    def _store_pid(self, parameter, value):
        configs[self._name]["algo"][self._sensor]["pid"][parameter] = value
        app.storage.general[configs_version_string] = configs.to_dict()

    def _add_curve(self):
        self._chart = ui.chart(
            self._chart_options,
            extras=["draggable-points"],
            on_point_drop=lambda e: self._set_point(e.point_index, e.point_x, e.point_y),
        ).classes("w-full h-64")

    def _set_point(self, index, x, y):
        curve = self._curve
        curve[index] = [x, y]
        self._curve = curve

    @property
    def _curve(self):
        if (
            "speed" not in configs[self._name]["algo"][self._sensor]["curve"]
            or "temp" not in configs[self._name]["algo"][self._sensor]["curve"]
        ):
            speed_defaults = [5, 20, 50, 70, 100]
            temp_defaults = [30, 40, 50, 60, 70]
            self._curve = list(zip(temp_defaults, speed_defaults))
        x = configs[self._name]["algo"][self._sensor]["curve"]["temp"]
        y = configs[self._name]["algo"][self._sensor]["curve"]["speed"]
        curve = list()
        for level in self._levels:
            curve.append([x[level], y[level]])
        return curve

    @_curve.setter
    def _curve(self, curve):
        temps, speeds = zip(*curve)
        configs[self._name]["algo"][self._sensor]["curve"]["speed"] = dict(zip(self._levels, list(speeds)))
        configs[self._name]["algo"][self._sensor]["curve"]["temp"] = dict(zip(self._levels, list(temps)))
        app.storage.general[configs_version_string] = configs.to_dict()
        if self._chart is not None:
            self._chart.options["series"][0] = self._chart_options["series"][0]
            self._chart.update()

    @property
    def _chart_options(self):
        options = {
            "title": False,
            "chart": {"type": "line", "backgroundColor": "#222", "marginRight": 30},
            "legend": {"enabled": False},
            "xAxis": {
                "title": {"text": None, "style": {"color": "#FFF"}},
                "labels": {
                    "style": {"color": "#FFF", "textOverflow": "none", "whiteSpace": "nowrap"},
                    "format": "{text}°C",
                },
                "min": 20,
                "max": 100,
                "tickInterval": 10,
                "gridLineWidth": 1,
                "lineColor": "#FFF",
                "tickColor": "#FFF",
            },
            "yAxis": {
                "title": {"text": None, "style": {"color": "#FFF"}},
                "labels": {"style": {"color": "#FFF"}, "format": "{text}%"},
                "min": 0,
                "max": 100,
                "tickInterval": 10,
                "gridLineWidth": 1,
                "lineColor": "#FFF",
                "tickColor": "#FFF",
            },
            "plotOptions": {
                "series": {
                    "stickyTracking": False,
                    "dragDrop": {"draggableX": True, "dragPrecisionX": 1, "draggableY": True, "dragPrecisionY": 1},
                },
            },
            "tooltip": {
                "snap": 9,
                "split": False,
                "distance": 18,
                "format": "<span>{point.y}% @ {point.x}°C</span>",
            },
            "series": [
                {
                    "data": self._curve,
                    "color": "#F00",
                    "lineWidth": 3,
                    "marker": {"enabled": True, "radius": 6},
                    "findNearestPointBy": "xy",
                },
            ],
            "credits": {"enabled": False},
        }
        return options

    @property
    def _levels(self):
        return ["Min", "Low", "Medium", "High", "Max"]


class ModeControl(PwmControl):
    def __init__(self, name, sensor, column):
        super().__init__(name, sensor, column)

    @property
    def _curve(self):
        if (
            "speed" not in configs[self._name]["algo"][self._sensor]["curve"]
            or "temp" not in configs[self._name]["algo"][self._sensor]["curve"]
        ):
            speed_defaults = self._modes
            temp_defaults = [30, 40, 50, 60, 70]
            self._curve = list(zip(temp_defaults, speed_defaults))
        x = configs[self._name]["algo"][self._sensor]["curve"]["temp"]
        y = configs[self._name]["algo"][self._sensor]["curve"]["speed"]
        curve = list()
        for level in self._levels:
            curve.append([x[level], self._modes.index(y[level])])
        return curve

    @_curve.setter
    def _curve(self, curve):
        temps, speeds = zip(*curve)
        speeds = list(speeds)
        for speed in speeds:
            if isinstance(speed, int) is True:
                speeds[speed] = self._modes[speed]
        configs[self._name]["algo"][self._sensor]["curve"]["speed"] = dict(zip(self._levels, speeds))
        configs[self._name]["algo"][self._sensor]["curve"]["temp"] = dict(zip(self._levels, list(temps)))
        app.storage.general[configs_version_string] = configs.to_dict()
        if self._chart is not None:
            self._chart.options["series"][0] = self._chart_options["series"][0]
            self._chart.update()

    @property
    def _chart_options(self):
        options = {
            "title": False,
            "chart": {"type": "line", "backgroundColor": "#222", "marginRight": 30},
            # "chart": {"type": "line", "backgroundColor": "#222"},
            "legend": {"enabled": False},
            "xAxis": {
                "title": {"text": None, "style": {"color": "#FFF"}},
                "labels": {
                    "style": {"color": "#FFF", "textOverflow": "none", "whiteSpace": "nowrap"},
                    "format": "{text}°C",
                },
                "min": 20,
                "max": 100,
                "tickInterval": 10,
                "gridLineWidth": 1,
                "lineColor": "#FFF",
                "tickColor": "#FFF",
            },
            "yAxis": {
                "title": {"text": None, "style": {"color": "#FFF"}},
                "labels": {"style": {"color": "#FFF"}},
                "categories": self._modes,
                "gridLineWidth": 1,
                "lineColor": "#FFF",
                "tickColor": "#FFF",
            },
            "plotOptions": {
                "series": {
                    "stickyTracking": False,
                    "dragDrop": {"draggableX": True, "dragPrecisionX": 1},
                },
            },
            "tooltip": {
                "snap": 9,
                "split": False,
                "distance": 18,
                "format": "<span>{point.x}</span>",
            },
            "series": [
                {
                    "data": self._curve,
                    "color": "#F00",
                    "lineWidth": 3,
                    "marker": {"enabled": True, "radius": 6},
                    "findNearestPointBy": "xy",
                },
            ],
            "credits": {"enabled": False},
        }
        return options

    @property
    def _modes(self):
        return ["A", "B", "C", "D", "E"]


class iDrac9Control(ModeControl):
    @property
    def _modes(self):
        return ["Off", "Low", "Medium", "High", "Max"]


class CiscoControl(ModeControl):
    @property
    def _modes(self):
        return ["Low Power", "Balanced", "Performance", "High Power", "Max Power"]


class Sensors:
    def __init__(self, name, expansion):
        self._name = name
        self._expansion = expansion
        self._sensor_names = ["cpu", "drive", "gpu"]
        self._add()

    def _add(self):
        default_tab = None
        with ui.tabs().classes("w-full") as curve_tabs:
            tabs = list()
            if configs[self._name].get("cpu", "None") != "None":
                cpu_curve_tab = ui.tab("CPU")
                default_tab = cpu_curve_tab
                tabs.append(cpu_curve_tab)
            if configs[self._name].get("drive", "None") != "None":
                drives_curve_tab = ui.tab("Drive")
                default_tab = drives_curve_tab
                tabs.append(drives_curve_tab)
            if configs[self._name].get("gpu", "None") != "None":
                gpu_curve_tab = ui.tab("GPU")
                default_tab = gpu_curve_tab
                tabs.append(gpu_curve_tab)
        with ui.tab_panels(curve_tabs, value=default_tab, animated=False).classes("w-full").style("min-height: 300px"):
            for tab in tabs:
                for sensor in self._sensor_names:
                    if configs[self._name].get(sensor, "None") != "None":
                        with ui.tab_panel(tab).classes("w-full"):
                            with ui.column().classes("w-full flex-center") as column:
                                ctrl_type = configs[self._name].get("speed", "None")
                                if ctrl_type == "Dell iDRAC 9":
                                    iDrac9Control(self._name, sensor, column)
                                elif ctrl_type == "Cisco M3" or ctrl_type == "Cisco M4" or ctrl_type == "Cisco M5":
                                    CiscoControl(self._name, sensor, column)
                                else:
                                    PwmControl(self._name, sensor, column)


class Algorithms(Tab):
    def __init__(self):
        self._name = None
        self._card = None
        super().__init__()

    def _tab_populate(self):
        self._card = ui.card().style("min-width: 700px").classes("justify-center no-shadow border-[2px]")
        with self._card:
            self._servers_column = ui.column().classes("w-full")

    def _add_server_content(self, name, row):
        with ui.expansion(name, icon="bar_chart").classes("w-full") as expansion:
            Sensors(name, expansion)
