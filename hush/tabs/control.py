from typing import Any, Dict, List, Union
from dataclasses import dataclass, field
from collections import deque
import string
import asyncio
from datetime import datetime
import time
import json
import httpx
from nicegui import app, ui  # type: ignore
from . import Tab
from hush.storage import host, algo_sensor, curve_speed, curve_temp, pid_coefficient


class Control(Tab):
    def __init__(self, host=None) -> None:
        self._sensor_names = ["cpu", "pci", "drive", "gpu"]
        super().__init__(host)

    def _build(self):
        self._add()

    def _add(self):
        default_tab = None
        control_tabs = ui.tabs().classes("w-full")
        control_panels = ui.tab_panels(control_tabs, animated=False).classes("w-full").style("min-height: 300px")
        for sensor in self._sensor_names:
            if host(self.host).get(sensor, "None") != "None":
                with control_tabs:
                    tab = ui.tab(sensor.upper())
                if default_tab is None:
                    default_tab = tab
                    control_panels.value = default_tab
                with control_panels:
                    with ui.tab_panel(tab).classes("w-full"):
                        with ui.column().classes("w-full flex-center") as column:
                            ctrl_type = host(self.host).get("speed", "None")
                            if ctrl_type == "Dell iDRAC 9":
                                iDrac9Control(self.host, sensor, column)
                            elif ctrl_type == "Cisco M3" or ctrl_type == "Cisco M4" or ctrl_type == "Cisco M5":
                                CiscoControl(self.host, sensor, column)
                            else:
                                PwmControl(self.host, sensor, column)


class PwmControl:
    def __init__(self, host, sensor, column):
        self.host = host
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
            value=algo_sensor(self.host, self._sensor)["type"],
            on_change=lambda v: self._set_algo(v),
        )

    def _set_algo(self, v):
        algo_sensor(self.host, self._sensor)["type"] = v.value
        self._card.clear()
        self._add_control()

    def _add_control(self):
        with self._card:
            algo = algo_sensor(self.host, self._sensor)["type"]
            if algo == "curve":
                self._add_curve()
            elif algo == "pid":
                self._add_pid()

    def _add_pid(self):
        with ui.column().classes("w-full items-center justify-around"):
            with ui.row().classes("w-full items-center justify-around"):
                ui.number(
                    label="Kp",
                    value=pid_coefficient(self.host, self._sensor, "Kp"),
                    on_change=lambda e: self._store_pid("kp", e.value),
                )
                ui.number(
                    label="Ki",
                    value=pid_coefficient(self.host, self._sensor, "Ki"),
                    on_change=lambda e: self._store_pid("ki", e.value),
                )
            with ui.row().classes("w-full items-center justify-around"):
                ui.number(
                    label="Kd",
                    value=pid_coefficient(self.host, self._sensor, "Kd"),
                    on_change=lambda e: self._store_pid("kd", e.value),
                )
                ui.number(
                    label="Target",
                    value=pid_coefficient(self.host, self._sensor, "Target"),
                    on_change=lambda e: self._store_pid("target", e.value),
                )

    def _store_pid(self, parameter, value):
        host(self.host)["algo"][self._sensor]["pid"][parameter] = value

    def _add_curve(self):
        self._chart = ui.highchart(
            self._chart_options,
            extras=["draggable-points"],
            on_point_drop=lambda e: self._set_point(e.point_index, e.point_x, e.point_y),
        ).classes("w-full h-64")

    def _set_point(self, index, x, y):
        if x > 100:
            x = 100
        if y > 100:
            y = 100
        curve = self._curve
        curve[index] = [x, y]
        self._curve = curve

    @property
    def _curve(self):
        x = curve_temp(self.host, self._sensor)
        y = curve_speed(self.host, self._sensor, default=dict(zip(self._levels, [5, 20, 50, 70, 100])))
        curve = []
        for level in self._levels:
            curve.append([x[level], y[level]])
        return curve

    @_curve.setter
    def _curve(self, curve):
        temps, speeds = zip(*curve)
        curve_speed(self.host, self._sensor).update(dict(zip(self._levels, list(speeds))))
        curve_temp(self.host, self._sensor).update(dict(zip(self._levels, list(temps))))
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
    def __init__(self, host, sensor, column):
        super().__init__(host, sensor, column)

    @property
    def _curve(self):
        x = curve_temp(self.host, self._sensor)
        y = curve_speed(self.host, self._sensor, default=dict(zip(self._levels, list(self._modes))))
        curve = []
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
        curve_speed(self.host, self._sensor).update(dict(zip(self._levels, speeds)))
        curve_temp(self.host, self._sensor).update(dict(zip(self._levels, list(temps))))
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
