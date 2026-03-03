from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import deque
import asyncio
from datetime import datetime
import time
from nicegui import ui
from . import Tab


last_status: dict = {}
status_history: dict = {}
fan_speed_history: dict = {}


@dataclass(kw_only=False)
class Status:
    host: str
    status: bool = False
    speed: Optional[int] = None
    temperatures: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def submit(self) -> None:
        if self.status is True:
            if self.host not in status_history:
                status_history[self.host] = {}
            if (len(self.temperatures.keys()) + 1) != len(status_history[self.host].keys()):
                status_history[self.host] = {}
                for sensor in self.temperatures.keys():
                    status_history[self.host][sensor] = deque(maxlen=100)
                status_history[self.host]["speed"] = deque(maxlen=100)
            for sensor, value in self.temperatures.items():
                status_history[self.host][sensor].append(value)
            status_history[self.host]["speed"].append(self.speed)
        last_status[self.host] = self

    @classmethod
    def clear(cls, host):
        if host in status_history:
            status_history[host] = {}


@dataclass(kw_only=False)
class FanSpeeds:
    host: str
    speeds: Dict[str, int] = field(default_factory=dict)

    def submit(self) -> None:
        if self.host not in fan_speed_history:
            fan_speed_history[self.host] = {}
        for sensor, value in self.speeds.items():
            if sensor not in fan_speed_history[self.host]:
                fan_speed_history[self.host][sensor] = deque(maxlen=100)
            fan_speed_history[self.host][sensor].append(value)

    @classmethod
    def clear(cls, host):
        if host in fan_speed_history:
            fan_speed_history[host] = {}


class Monitor(Tab):
    def __init__(self, host=None) -> None:
        self._status = None
        self._timestamp = 0
        self._groups = ["speed", "cpu", "pci", "drive", "gpu", "chassis"]
        super().__init__(host)

    def _build(self):
        self._add_labels()
        self._add_chart()

    def _add_labels(self):
        self._status = ui.label("Connection Failure").classes("text-4xl font-bold self-center text-orange-500")
        self._status.set_visibility(False)

    def _add_chart(self):
        self._status_chart = ui.highchart(
            {
                "title": {"text": "Status History", "style": {"color": "#FFF"}},
                "subtitle": {"text": "Not Available", "style": {"color": "#FFF"}},
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
                "series": [],
                "credits": {"enabled": False},
            }
        ).classes("w-full h-64")
        self._status_chart.set_visibility(False)
        for group in self._groups:
            self._status_chart.options["series"].append(dict({"name": group.title(), "data": None}))
        self._fan_chart = ui.highchart(
            {
                "title": {"text": "Fan Speed History", "style": {"color": "#FFF"}},
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
                "series": [],
                "credits": {"enabled": False},
            }
        ).classes("w-full h-64")
        self._fan_chart.set_visibility(False)
        ui.timer(interval=1, callback=self.update, once=True)

    async def update(self):
        while True:
            if self._status_chart.is_deleted is True:
                break
            if self.host in last_status:
                if last_status[self.host].timestamp > self._timestamp:
                    self._timestamp = last_status[self.host].timestamp
                    time = datetime.fromtimestamp(self._timestamp).strftime("%m/%d/%Y @ %H:%M:%S")
                    self._status.set_visibility(False if last_status[self.host].status is True else True)
                    self._status_chart.options["subtitle"]["text"] = f"Last Update: {time}"
                    if self.host in status_history and last_status[self.host].status is True:
                        for group in self._groups:
                            if group in status_history[self.host]:
                                self._status_chart.options["series"][self._groups.index(group)]["data"] = list(status_history[self.host][group])
                            else:
                                self._status_chart.options["series"][self._groups.index(group)]["data"] = None
                        self._status_chart.set_visibility(True)
                        self._status_chart.update()
                    else:
                        self._status_chart.set_visibility(False)
                        self._status_chart.update()
                    if self.host in fan_speed_history and len(fan_speed_history[self.host]) > 0 and last_status[self.host].status is True:
                        self._fan_chart.options["series"] = []
                        for sensor, data in fan_speed_history[self.host].items():
                            self._fan_chart.options["series"].append(dict({"name": sensor.title(), "data": list(data)}))
                        self._fan_chart.set_visibility(True)
                        self._fan_chart.update()
                    else:
                        self._fan_chart.set_visibility(False)
                        self._fan_chart.update()
            await asyncio.sleep(1)
